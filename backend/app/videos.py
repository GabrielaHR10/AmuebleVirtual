"""Video v0 (PLAN 5.1): fotogramas clave → escenas de foto que se amoblan en el Estudio."""

import secrets
import shutil
import statistics
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel

from app import jobs, storage
from app.geometry.coords import cv_to_three
from app.geometry.floor import detect_floor
from app.geometry.moge_runner import run_moge
from app.video.keyframes import VideoError, extract_keyframes, probe

MAX_SECONDS = 180  # el plan dice 60 s (pensando en el seguimiento de cámara); para fotogramas basta con 3 min
MAX_BYTES = 300 * 1024 * 1024
N_KEYFRAMES = 6
CANDIDATES_PER_WINDOW = 3


def video_dir(video_id: str) -> Path:
    if not video_id.startswith("vid_") or not video_id[4:].replace("_", "").isalnum():
        raise ValueError("Id de video inválido")
    return storage.DATA_DIR / "videos" / video_id


def load_meta(video_id: str) -> dict:
    try:
        path = video_dir(video_id) / "meta.json"
    except ValueError:
        raise HTTPException(404, "Video no encontrado") from None
    if not path.is_file():
        raise HTTPException(404, "Video no encontrado")
    return storage.read_json(path)


def save_meta(meta: dict) -> None:
    storage.write_json_atomic(video_dir(meta["video_id"]) / "meta.json", meta)


def floor_score(img: Image.Image) -> float:
    """Fracción de la imagen que es piso (0 si no se encuentra). Sirve para elegir fotogramas amoblables."""
    r = run_moge(img)
    normals = cv_to_three(r.normal) if r.normal is not None else None
    floor = detect_floor(cv_to_three(r.points), r.mask, normals)
    return floor.inlier_ratio if floor.found and "escala_dudosa" not in floor.warnings else 0.0


def keyframes_job(video_id: str, n: int, progress: jobs.Progress) -> dict:
    folder = video_dir(video_id)
    src = next(folder.glob("video.*"))
    windows = extract_keyframes(src, n, lambda p, m: progress(0.4 * p, m), per_window=CANDIDATES_PER_WINDOW)
    total = sum(len(w) for w in windows)
    done, chosen = 0, []
    for w in windows:
        best, best_score = None, -1.0
        for kf in w:
            done += 1
            progress(0.4 + 0.55 * done / total, f"Buscando fotogramas con piso visible… ({done}/{total})")
            score = floor_score(Image.fromarray(kf.image))
            if score > best_score:
                best, best_score = kf, score
        chosen.append((best, best_score))
    meta = load_meta(video_id)
    meta["keyframes"] = []
    for k, (kf, score) in enumerate(chosen):
        name = f"kf_{k:02d}.jpg"
        Image.fromarray(kf.image).save(folder / name, quality=92)
        meta["keyframes"].append({
            "k": k, "frame": kf.index, "time_s": round(kf.time_s, 2), "sharpness": round(kf.sharpness, 1),
            "floor_ratio": round(score, 3), "url": storage.file_url(folder / name), "scene_id": None,
        })
    save_meta(meta)
    return meta


def scenes_job(video_id: str, ks: list[int], progress: jobs.Progress) -> dict:
    from app.scenes import analyze_photo

    meta = load_meta(video_id)
    folder = video_dir(video_id)
    for i, k in enumerate(ks):
        progress(i / len(ks), f"Analizando el fotograma {i + 1} de {len(ks)}…")
        scene = analyze_photo(folder / f"kf_{k:02d}.jpg")
        meta["keyframes"][k]["scene_id"] = scene.id
        save_meta(meta)
    meta["summary"] = room_summary(meta)
    save_meta(meta)
    return meta


def room_summary(meta: dict) -> dict | None:
    """Mediana de la altura de techo y el mayor ancho/fondo visibles entre los fotogramas (aproximado)."""
    from app.scenes import load_scene

    ceilings, widths, depths = [], [], []
    for kf in meta.get("keyframes", []):
        if not kf.get("scene_id"):
            continue
        r = load_scene(kf["scene_id"]).room_estimate
        if r and r.ceiling_height_m:
            ceilings.append(r.ceiling_height_m)
        if r and r.floor_extent_m:
            widths.append(r.floor_extent_m.width)
            depths.append(r.floor_extent_m.depth)
    if not (ceilings or widths):
        return None
    return {
        "ceiling_height_m": round(statistics.median(ceilings), 2) if ceilings else None,
        "max_width_m": round(max(widths), 1) if widths else None,
        "max_depth_m": round(max(depths), 1) if depths else None,
    }


router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("")
def post_video(file: Annotated[UploadFile, File()]) -> dict:
    ext = Path(file.filename or "video.mp4").suffix.lower() or ".mp4"
    if ext not in {".mp4", ".mov", ".m4v"}:
        raise HTTPException(400, "Usa un video MP4 o MOV.")
    video_id = f"vid_{datetime.now(UTC).astimezone():%Y%m%d_%H%M%S}_{secrets.token_hex(2)}"
    folder = video_dir(video_id)
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"video{ext}"
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out, length=1024 * 1024)
    try:
        if dest.stat().st_size > MAX_BYTES:
            raise HTTPException(413, "El video es muy grande (máximo 300 MB).")
        info = probe(dest)
        if info.duration > MAX_SECONDS:
            raise HTTPException(413, f"El video dura {info.duration:.0f} s; el máximo es {MAX_SECONDS // 60} minutos.")
    except (HTTPException, VideoError) as e:
        shutil.rmtree(folder, ignore_errors=True)
        if isinstance(e, VideoError):
            raise HTTPException(400, str(e)) from None
        raise
    save_meta({"video_id": video_id, "duration_s": round(info.duration, 1), "width": info.width,
               "height": info.height, "fps": round(info.fps, 2), "keyframes": [], "summary": None})
    job_id = jobs.start("keyframes", lambda p: keyframes_job(video_id, N_KEYFRAMES, p))
    return {"video_id": video_id, "job_id": job_id}


@router.get("/{video_id}")
def get_video(video_id: str) -> dict:
    return load_meta(video_id)


class KeyframesBody(BaseModel):
    ks: list[int] | None = None  # None = todos


@router.post("/{video_id}/keyframes")
def post_keyframes(video_id: str, body: KeyframesBody) -> dict:
    """Crea escenas de foto (análisis completo) para los fotogramas elegidos."""
    meta = load_meta(video_id)
    n = len(meta["keyframes"])
    if n == 0:
        raise HTTPException(409, "Todavía no hay fotogramas: espera a que termine el análisis del video.")
    ks = body.ks if body.ks is not None else list(range(n))
    if any(k < 0 or k >= n for k in ks):
        raise HTTPException(422, "Fotograma inválido")
    job_id = jobs.start("scenes", lambda p: scenes_job(video_id, ks, p))
    return {"video_id": video_id, "job_id": job_id}

