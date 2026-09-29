import io
import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import scenes
from app.config import SAMPLES_DIR
from app.geometry.moge_runner import MogeResult
from app.main import app
from tests.test_floor import synthetic_room


def fake_moge(img):
    """Cuarto sintético en coords OpenCV con el tamaño de inferencia de la imagen."""
    w, h = img.size
    s = 1024 / max(w, h)
    pts_three, valid, n, *_ = synthetic_room(h=round(h * s * 0.25), w=round(w * s * 0.25),
                                             outlier_frac=0.0, noise=0.002)
    cv = pts_three * np.array([1, -1, -1])
    normals_cv = np.broadcast_to(n * np.array([1, -1, -1]), cv.shape).copy()
    return MogeResult(points=cv.astype(np.float32), depth=cv[..., 2].astype(np.float32),
                      normal=normals_cv.astype(np.float32), mask=valid,
                      intrinsics=np.array([[0.9, 0, 0.5], [0, 0.72, 0.5], [0, 0, 1]]),
                      device="cpu", load_ms=0, infer_ms=1)


def _jpeg(w=640, h=480) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(np.full((h, w, 3), 128, np.uint8)).save(buf, "JPEG")
    return buf.getvalue()


def test_post_scene_creates_files_and_contract(data_dir, monkeypatch):
    monkeypatch.setattr(scenes, "run_moge", fake_moge)
    client = TestClient(app)
    res = client.post("/api/scenes", files={"file": ("sala.jpg", _jpeg(), "image/jpeg")})
    assert res.status_code == 200, res.text
    scene = res.json()
    assert scene["id"].startswith("scn_")
    assert scene["image"]["width"] == 640 and scene["image"]["height"] == 480
    assert scene["floor"]["found"] and len(scene["floor"]["frame"]) == 16
    assert scene["camera_height_m"] == pytest.approx(1.5, abs=0.03)
    assert scene["camera"]["matrix_world"] == [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    assert set(scene["timings_ms"]) == {"load", "infer", "floor", "mesh", "room"}
    folder = data_dir / "scenes" / scene["id"]
    for name in ("image.jpg", "scene.json", "occlusion.glb", "floor_mask.png", "depth.png", "debug.jpg"):
        assert (folder / name).is_file(), name
    assert Image.open(folder / "floor_mask.png").size == (640, 480)
    assert json.loads((folder / "scene.json").read_text())["id"] == scene["id"]
    assert scene["assets"]["occlusion_glb"] == f"/files/scenes/{scene['id']}/occlusion.glb"

    assert client.get(f"/api/scenes/{scene['id']}").json()["id"] == scene["id"]
    assert [s["id"] for s in client.get("/api/scenes").json()] == [scene["id"]]

    placements = [{"uid": "p_1", "item_id": "sofa", "mode": "cutout", "x": 0.4, "z": -3.1, "yaw_deg": 90,
                   "source": "manual"}]
    put = client.put(f"/api/scenes/{scene['id']}/placements", json={"placements": placements, "scale_k": 1.1})
    assert put.status_code == 200, put.text
    again = client.get(f"/api/scenes/{scene['id']}").json()
    assert again["placements"][0]["z"] == -3.1 and again["scale_k"] == 1.1
    bad = client.put(f"/api/scenes/{scene['id']}/placements", json={"placements": [], "scale_k": 0})
    assert bad.status_code == 422
    assert client.put("/api/scenes/scn_no_existe/placements", json={"placements": []}).status_code == 404


def test_scene_errors_are_in_spanish(data_dir):
    client = TestClient(app)
    assert client.get("/api/scenes/scn_no_existe").status_code == 404
    assert client.get("/api/scenes/..%2F..%2Fetc").status_code == 404
    heic = client.post("/api/scenes", files={"file": ("foto.HEIC", b"x", "image/heic")})
    assert heic.status_code == 400 and "JPG" in heic.json()["detail"]
    bad = client.post("/api/scenes", files={"file": ("foto.jpg", b"no es imagen", "image/jpeg")})
    assert bad.status_code == 400 and "JPG o PNG" in bad.json()["detail"]


_REAL = SAMPLES_DIR / "rooms" / "medidas_reales.json"
REAL_MEASURES = json.loads(_REAL.read_text(encoding="utf-8")) if _REAL.is_file() else {}
ROOM_PHOTOS = sorted(p for p in (SAMPLES_DIR / "rooms").glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"})


@pytest.mark.slow
@pytest.mark.skipif(not ROOM_PHOTOS, reason="No hay fotos en samples/rooms/")
def test_real_rooms(data_dir):
    ok, report = 0, []
    for path in ROOM_PHOTOS:
        scene = scenes.analyze_photo(Path(path))
        h = scene.camera_height_m
        good = scene.floor.found and h is not None and 0.8 < h < 2.2
        ok += good
        report.append(f"{path.name}: found={scene.floor.found} h={h} warnings={scene.warnings}")
        truth = REAL_MEASURES.get(path.name)
        est = scene.room_estimate
        if truth and est and est.floor_extent_m:
            pairs = [("ancho_m", est.floor_extent_m.width), ("fondo_m", est.floor_extent_m.depth),
                     ("techo_m", est.ceiling_height_m)]
            errs = [f"{k} {100 * (v - truth[k]) / truth[k]:+.0f} %" for k, v in pairs if v and truth.get(k)]
            report.append(f"   error vs. medidas reales: {', '.join(errs)}")
    print("\n".join(report))
    # Algunas fotos de prueba no muestran piso (ducha, vista por la ventana): se exige la gran mayoría
    assert ok >= 0.8 * len(ROOM_PHOTOS), "\n".join(report)
