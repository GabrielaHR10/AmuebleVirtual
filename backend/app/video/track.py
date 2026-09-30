"""Seguimiento de cámara de un tramo de video (PLAN 5.2 / R.4) con pycolmap (BSD).

Resultado: poses de cámara three.js para cada fotograma de salida, relativas al fotograma de REFERENCIA (su
cámara queda en la identidad, igual que una foto), en metros (escala de MoGe en la referencia).
"""

import json
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from scipy.spatial.transform import Rotation, Slerp

SFM_FPS = 5.0
OUT_FPS = 15.0
SFM_MAX_SIDE = 960
MIN_REGISTERED = 0.7
TIPS = ("Consejos: graba un solo espacio, 10–20 s, movimiento lento, que se vean el piso, puertas y ventanas; "
        "evita apuntar a paredes blancas lisas.")

CV_TO_THREE = np.diag([1.0, -1.0, -1.0, 1.0])


class TrackError(RuntimeError):
    pass


@dataclass
class Track:
    fov_y_deg: float
    width: int
    height: int
    times: list[float]  # tiempo (s) de cada fotograma de salida
    matrices: list[np.ndarray]  # 4×4, cámara three relativa a la referencia (m)
    ref_time: float
    registered: float  # fracción de fotogramas SfM registrados
    scale: float


def extract_frames(video: Path, t0: float, t1: float, fps: float, out_dir: Path, max_side: int | None = None
                   ) -> list[tuple[float, Path]]:
    """Guarda los fotogramas entre t0 y t1 a `fps` (jpg). Devuelve [(tiempo, ruta)]."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video))
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    result = []
    try:
        i0, i1 = int(t0 * src_fps), int(t1 * src_fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, i0)
        next_t = t0
        for idx in range(i0, i1 + 1):
            if not cap.grab():
                break
            t = idx / src_fps
            if t + 1e-6 < next_t:
                continue
            ok, bgr = cap.retrieve()
            if not ok:
                continue
            if max_side:
                s = max_side / max(bgr.shape[:2])
                if s < 1:
                    bgr = cv2.resize(bgr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            path = out_dir / f"f_{len(result):04d}.jpg"
            cv2.imwrite(str(path), bgr, [cv2.IMWRITE_JPEG_QUALITY, 92])
            result.append((t, path))
            next_t += 1.0 / fps
    finally:
        cap.release()
    return result


def run_sfm(image_dir: Path, work: Path) -> dict:
    """SIFT + emparejamiento secuencial + mapeo incremental en otro proceso (ver sfm_worker)."""
    work.mkdir(parents=True, exist_ok=True)
    out = work / "sfm.json"
    cmd = [sys.executable, "-m", "app.video.sfm_worker", str(image_dir), str(work), str(out)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=Path(__file__).resolve().parents[2])
    if proc.returncode != 0 or not out.is_file():
        raise TrackError("Falló el seguimiento de la cámara. " + TIPS)
    data = json.loads(out.read_text())
    if not data.get("images"):
        raise TrackError("No se pudo reconstruir el movimiento de la cámara. " + TIPS)
    return data


def _cam_from_world(img: dict) -> np.ndarray:
    m = np.eye(4)
    m[:3, :4] = np.array(img["cam_from_world"])
    return m


def moge_scale(ref_img: dict, ref_path: Path) -> float:
    """Escala métrica: mediana de profundidad MoGe / profundidad COLMAP en los puntos 3D vistos en la referencia."""
    from app.geometry.moge_runner import load_image, run_moge

    img = load_image(ref_path)
    r = run_moge(img)
    h, w = r.depth.shape
    cfw = _cam_from_world(ref_img)
    ratios = []
    for u_px, v_px, *xyz in ref_img["obs"]:
        z_colmap = (cfw @ np.append(xyz, 1.0))[2]
        if z_colmap <= 0:
            continue
        u = int(u_px / img.width * w)
        v = int(v_px / img.height * h)
        if 0 <= u < w and 0 <= v < h and r.mask[v, u] and np.isfinite(r.depth[v, u]):
            ratios.append(r.depth[v, u] / z_colmap)
    if len(ratios) < 30:
        raise TrackError("No hay suficientes puntos para medir la escala del video. " + TIPS)
    return float(np.median(ratios))


def build_track(sfm_frames: list[tuple[float, Path]], out_times: list[float], work: Path,
                progress: Callable[[float, str], None] | None = None) -> tuple[Track, Path]:
    """SfM sobre sfm_frames → poses interpoladas en out_times. Devuelve (Track, ruta del fotograma de referencia)."""
    if progress:
        progress(0.05, "Siguiendo el movimiento de la cámara… (puede tardar un par de minutos)")
    rec = run_sfm(sfm_frames[0][1].parent, work)
    by_name = {p.name: (t, p) for t, p in sfm_frames}
    regs = [dict(img, name=name) for name, img in rec["images"].items() if name in by_name]
    frac = len(regs) / len(sfm_frames)
    if frac < MIN_REGISTERED:
        raise TrackError(f"Solo se siguió la cámara en el {frac:.0%} de los fotogramas. " + TIPS)
    ref = max(regs, key=lambda img: len(img["obs"]))
    ref_t, ref_path = by_name[ref["name"]]
    if progress:
        progress(0.6, "Midiendo la escala real con el fotograma de referencia…")
    scale = moge_scale(ref, ref_path)

    def three_world_from_cam(img) -> np.ndarray:
        m = np.linalg.inv(_cam_from_world(img))
        m[:3, 3] *= scale
        return m @ CV_TO_THREE

    ref_inv = np.linalg.inv(three_world_from_cam(ref))
    keys = sorted(((by_name[img["name"]][0], ref_inv @ three_world_from_cam(img)) for img in regs),
                  key=lambda k: k[0])
    kt = np.array([k[0] for k in keys])
    rots = Rotation.from_matrix(np.stack([k[1][:3, :3] for k in keys]))
    pos = np.stack([k[1][:3, 3] for k in keys])
    slerp = Slerp(kt, rots)
    mats = []
    for t in out_times:
        tc = float(np.clip(t, kt[0], kt[-1]))
        m = np.eye(4)
        m[:3, :3] = slerp([tc]).as_matrix()[0]
        m[:3, 3] = [np.interp(tc, kt, pos[:, i]) for i in range(3)]
        mats.append(m)
    cam = rec["cameras"][str(ref["camera_id"])]
    f = cam["params"][0]
    fov_y = float(np.degrees(2 * np.arctan(cam["height"] / (2 * f))))
    track = Track(fov_y, cam["width"], cam["height"], list(out_times), mats, ref_t, frac, scale)
    return track, ref_path
