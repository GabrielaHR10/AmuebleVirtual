"""Fotogramas clave de un video (PLAN 5.1): a 5 fps, N ventanas, el más nítido de cada una.

Se usa OpenCV (su FFmpeg incluido es LGPL) en vez de imageio-ffmpeg, cuyo binario puede ser GPL.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

SAMPLE_FPS = 5.0
MIN_BRIGHTNESS = 25  # descarta fotogramas casi negros


@dataclass
class VideoInfo:
    fps: float
    frames: int
    width: int
    height: int

    @property
    def duration(self) -> float:
        return self.frames / self.fps if self.fps > 0 else 0.0


@dataclass
class Keyframe:
    index: int  # fotograma del video
    time_s: float
    sharpness: float
    image: np.ndarray  # RGB


class VideoError(ValueError):
    pass


def probe(path: Path) -> VideoInfo:
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise VideoError("No se pudo abrir el video. Usa MP4 o MOV.")
        info = VideoInfo(cap.get(cv2.CAP_PROP_FPS) or 30.0, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                         int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    finally:
        cap.release()
    if info.frames <= 0:
        raise VideoError("El video no tiene fotogramas.")
    return info


def sharpness(gray: np.ndarray) -> float:
    """Varianza del Laplaciano (más alta = más nítido)."""
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def extract_keyframes(path: Path, n: int = 6, progress: Callable[[float, str], None] | None = None,
                      per_window: int = 1, min_gap_s: float = 1.0) -> list[list[Keyframe]]:
    """Por cada una de las n ventanas, los `per_window` fotogramas más nítidos (separados ≥ min_gap_s)."""
    info = probe(path)
    step = max(1, round(info.fps / SAMPLE_FPS))
    sampled = list(range(0, info.frames, step))
    windows = np.array_split(np.array(sampled), max(1, min(n, len(sampled))))
    cands: list[list[Keyframe]] = [[] for _ in windows]
    window_of = {int(f): w for w, arr in enumerate(windows) for f in arr}
    cap = cv2.VideoCapture(str(path))
    try:
        k = 0
        for frame_idx in range(info.frames):
            if not cap.grab():  # lectura secuencial: grab() es barato; solo se convierte lo muestreado
                break
            if frame_idx % step:
                continue
            k += 1
            ok, bgr = cap.retrieve()
            if not ok or frame_idx not in window_of:
                continue
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            if gray.mean() < MIN_BRIGHTNESS:
                continue
            # nitidez medida a tamaño fijo para comparar fotogramas por igual
            s = sharpness(cv2.resize(gray, (480, round(480 * gray.shape[0] / gray.shape[1]))))
            w = window_of[frame_idx]
            kf = Keyframe(frame_idx, frame_idx / info.fps, s, cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            cands[w] = _keep_best(cands[w], kf, per_window, min_gap_s)
            if progress and k % 10 == 0:
                progress(0.9 * k / len(sampled), f"Buscando los fotogramas más nítidos… ({k}/{len(sampled)})")
    finally:
        cap.release()
    return [c for c in cands if c]


def _keep_best(current: list[Keyframe], kf: Keyframe, k: int, min_gap_s: float) -> list[Keyframe]:
    """Top-k por nitidez, sin dos fotogramas a menos de min_gap_s (se queda el más nítido)."""
    close = [c for c in current if abs(c.time_s - kf.time_s) < min_gap_s]
    if any(c.sharpness >= kf.sharpness for c in close):
        return current
    rest = [c for c in current if c not in close] + [kf]
    return sorted(rest, key=lambda c: -c.sharpness)[:k]
