"""Video con muebles (R.4/R.5): tramo → seguimiento de cámara → escena de referencia → fotogramas renderizados
en el navegador → composición con oclusión por profundidad (MoGe) → MP4.

data/videos/<vid>/clip_<cid>/: frames/ (fotogramas), depth/ (profundidad MoGe en mm, PNG 16 bits),
render/ (color y profundidad de los muebles que sube el navegador), track.json, amoblado.mp4
"""

import secrets
import shutil
from pathlib import Path
from typing import Annotated

import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel, Field

from app import jobs, storage
from app.video.track import OUT_FPS, SFM_FPS, SFM_MAX_SIDE, build_track, extract_frames

OUT_MAX_SIDE = 1280
MAX_CLIP_S = 20.0
DEPTH_FAR_M = 20.0  # la profundidad de los muebles llega empaquetada como fracción de 20 m


def clip_dir(video_id: str, clip_id: str) -> Path:
    from app.videos import video_dir

    if not clip_id.startswith("clip_") or not clip_id[5:].isalnum():
        raise ValueError("Id de tramo inválido")
    return video_dir(video_id) / clip_id


def load_track(video_id: str, clip_id: str) -> dict:
    try:
        path = clip_dir(video_id, clip_id) / "track.json"
    except ValueError:
        raise HTTPException(404, "Tramo no encontrado") from None
    if not path.is_file():
        raise HTTPException(404, "Tramo no encontrado (o todavía se está preparando)")
    return storage.read_json(path)


def prepare_clip(video_id: str, clip_id: str, t0: float, t1: float, progress: jobs.Progress) -> dict:
    from app.geometry.moge_runner import load_image, run_moge
    from app.scenes import analyze_photo
    from app.videos import video_dir

    folder = clip_dir(video_id, clip_id)
    src = next(video_dir(video_id).glob("video.*"))
    progress(0.02, "Extrayendo fotogramas…")
    out = extract_frames(src, t0, t1, OUT_FPS, folder / "frames", OUT_MAX_SIDE)
    sfm = extract_frames(src, t0, t1, SFM_FPS, folder / "sfm_frames", SFM_MAX_SIDE)
    track, _ = build_track(sfm, [t for t, _ in out], folder / "colmap", lambda p, m: progress(0.05 + 0.35 * p, m))
    ref_i = int(np.argmin([abs(t - track.ref_time) for t, _ in out]))
    progress(0.42, "Preparando el fotograma de referencia para amoblar…")
    scene = analyze_photo(out[ref_i][1])
    # profundidad por fotograma (oclusión): MoGe en cada uno, guardada en mm
    (folder / "depth").mkdir(exist_ok=True)
    for k, (_, path) in enumerate(out):
        progress(0.45 + 0.53 * k / len(out), f"Midiendo la profundidad de cada fotograma… ({k + 1}/{len(out)})")
        r = run_moge(load_image(path))
        d = np.where(r.mask & np.isfinite(r.depth), r.depth, 0.0)
        Image.fromarray(np.clip(d * 1000, 0, 65535).astype(np.uint16)).save(folder / "depth" / f"d_{k:04d}.png")
    w, h = Image.open(out[0][1]).size
    data = {
        "video_id": video_id, "clip_id": clip_id, "t0": t0, "t1": t1, "fps": OUT_FPS, "width": w, "height": h,
        "fov_y_deg": round(track.fov_y_deg, 3), "registered": round(track.registered, 3),
        "scale": round(track.scale, 4), "ref_index": ref_i, "ref_scene_id": scene.id,
        "frames": [{"i": k, "t": round(t, 3), "url": storage.file_url(p),
                    "matrix_world": [float(v) for v in track.matrices[k].T.reshape(-1)]}  # column-major
                   for k, (t, p) in enumerate(out)],
        "video_url": None,
    }
    storage.write_json_atomic(folder / "track.json", data)
    shutil.rmtree(folder / "sfm_frames", ignore_errors=True)
    return data


def unpack_depth(rgba: np.ndarray) -> np.ndarray:
    """Profundidad de los muebles empaquetada en RGB (base 255, ver frontend three/videoRender.ts) → metros.

    Solo RGB: el canal alfa marca dónde hay mueble (usarlo para datos se corrompe por el alfa premultiplicado
    del navegador). 0 donde no hay mueble.
    """
    c = rgba[..., :3].astype(np.float64) / 255.0
    v = c[..., 0] + c[..., 1] / 255.0 + c[..., 2] / 65025.0
    return np.where(rgba[..., 3] > 0, v * DEPTH_FAR_M, 0.0)


def compose_frame(photo: np.ndarray, color: np.ndarray, furn_depth: np.ndarray, scene_depth: np.ndarray) -> np.ndarray:
    """Muebles sobre el fotograma, tapados donde la escena real está más cerca (oclusión por profundidad)."""
    h, w = photo.shape[:2]
    scene = cv2.resize(scene_depth, (w, h), interpolation=cv2.INTER_NEAREST)
    visible = (scene <= 0) | (furn_depth <= scene * 1.04 + 0.05)
    vis = cv2.GaussianBlur(visible.astype(np.float32), (0, 0), 1.0)  # borde suave
    a = color[..., 3:4].astype(np.float32) / 255.0 * vis[..., None]
    out = photo.astype(np.float32) * (1 - a) + color[..., :3].astype(np.float32) * a
    return np.clip(out, 0, 255).astype(np.uint8)


def compose_video(video_id: str, clip_id: str, progress: jobs.Progress) -> dict:
    folder = clip_dir(video_id, clip_id)
    data = load_track(video_id, clip_id)
    n = len(data["frames"])
    missing = [k for k in range(n) if not (folder / "render" / f"c_{k:04d}.png").is_file()]
    if missing:
        raise ValueError(f"Faltan {len(missing)} fotogramas renderizados")
    w, h = data["width"], data["height"]
    out_path = folder / "amoblado.mp4"
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"avc1"), data["fps"], (w, h))
    if not writer.isOpened():  # sin H.264 (p. ej. Windows): MPEG-4
        writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), data["fps"], (w, h))
    try:
        for k in range(n):
            progress(k / n, f"Armando el video… ({k + 1}/{n})")
            photo = np.asarray(Image.open(folder / "frames" / f"f_{k:04d}.jpg").convert("RGB"))
            color = np.asarray(Image.open(folder / "render" / f"c_{k:04d}.png").convert("RGBA").resize((w, h)))
            fdepth = unpack_depth(np.asarray(Image.open(folder / "render" / f"d_{k:04d}.png").convert("RGBA")
                                             .resize((w, h), Image.Resampling.NEAREST)))
            sdepth = np.asarray(Image.open(folder / "depth" / f"d_{k:04d}.png")).astype(np.float32) / 1000.0
            frame = compose_frame(photo, color, fdepth, sdepth)
            writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
    finally:
        writer.release()
    data["video_url"] = storage.file_url(out_path) + f"?v={secrets.token_hex(3)}"
    storage.write_json_atomic(folder / "track.json", data)
    return data


router = APIRouter(prefix="/videos", tags=["videos"])


class ClipBody(BaseModel):
    t0: float = Field(ge=0)
    t1: float = Field(gt=0)


@router.post("/{video_id}/clips")
def post_clip(video_id: str, body: ClipBody) -> dict:
    from app.videos import load_meta

    meta = load_meta(video_id)
    t1 = min(body.t1, meta["duration_s"])
    if t1 - body.t0 < 2:
        raise HTTPException(422, "El tramo debe durar al menos 2 segundos.")
    if t1 - body.t0 > MAX_CLIP_S:
        raise HTTPException(422, f"El tramo puede durar máximo {MAX_CLIP_S:.0f} segundos.")
    clip_id = f"clip_{secrets.token_hex(3)}"
    clip_dir(video_id, clip_id).mkdir(parents=True, exist_ok=True)
    job_id = jobs.start("clip", lambda p: prepare_clip(video_id, clip_id, body.t0, t1, p))
    return {"clip_id": clip_id, "job_id": job_id}


@router.get("/{video_id}/clips/{clip_id}")
def get_clip(video_id: str, clip_id: str) -> dict:
    return load_track(video_id, clip_id)


@router.post("/{video_id}/clips/{clip_id}/frames/{k}")
def post_frame(video_id: str, clip_id: str, k: int, color: Annotated[UploadFile, File()],
               depth: Annotated[UploadFile, File()]) -> dict:
    """Recibe un fotograma renderizado de los muebles (color RGBA + profundidad empaquetada)."""
    data = load_track(video_id, clip_id)
    if not 0 <= k < len(data["frames"]):
        raise HTTPException(422, "Fotograma inválido")
    folder = clip_dir(video_id, clip_id) / "render"
    folder.mkdir(exist_ok=True)
    (folder / f"c_{k:04d}.png").write_bytes(color.file.read())
    (folder / f"d_{k:04d}.png").write_bytes(depth.file.read())
    return {"ok": True}


@router.post("/{video_id}/clips/{clip_id}/compose")
def post_compose(video_id: str, clip_id: str) -> dict:
    load_track(video_id, clip_id)
    return {"job_id": jobs.start("compose", lambda p: compose_video(video_id, clip_id, p))}
