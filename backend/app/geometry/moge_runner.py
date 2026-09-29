"""Carga perezosa de MoGe-2 e inferencia sobre una imagen.

Las salidas están en coordenadas OpenCV (x derecha, y abajo, z adelante), en metros.
La conversión a three.js se hace solo en `coords.py`.
"""

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from app.config import MOGE_MODEL, resolve_device

log = logging.getLogger("santiago.moge")

INFER_MAX_SIDE = 1024

_lock = threading.Lock()
_model = None
_device: str | None = None


@dataclass
class MogeResult:
    points: np.ndarray  # (H, W, 3) float32, OpenCV, metros; inf donde no es válido
    depth: np.ndarray  # (H, W) float32
    normal: np.ndarray | None  # (H, W, 3) float32, OpenCV
    mask: np.ndarray  # (H, W) bool
    intrinsics: np.ndarray  # (3, 3) normalizados (fx/W, fy/H, cx/W, cy/H)
    device: str
    load_ms: int
    infer_ms: int


class UnsupportedImageError(ValueError):
    pass


def load_image(path: str | Path) -> Image.Image:
    """Abre JPG/PNG, aplica la orientación EXIF y devuelve RGB.

    HEIC no se soporta: `pillow-heif` trae x265 (GPLv2), fuera de las licencias permitidas (PLAN §0.7).
    """
    try:
        with Image.open(path) as im:
            return ImageOps.exif_transpose(im).convert("RGB")
    except Exception as e:
        raise UnsupportedImageError(
            "No se pudo abrir la imagen. Usa JPG o PNG (las fotos HEIC de iPhone no se aceptan todavía: "
            "compártela por WhatsApp o expórtala como JPG)."
        ) from e


def resize_for_inference(img: Image.Image, max_side: int = INFER_MAX_SIDE) -> Image.Image:
    scale = max_side / max(img.size)
    if scale >= 1:
        return img
    size = (round(img.width * scale), round(img.height * scale))
    return img.resize(size, Image.Resampling.LANCZOS)


def get_model():
    """Singleton del modelo. Si falla en MPS, reintenta en CPU."""
    global _model, _device
    with _lock:
        if _model is None:
            from moge.model.v2 import MoGeModel

            device = resolve_device()
            try:
                _model = MoGeModel.from_pretrained(MOGE_MODEL).to(device).eval()
            except Exception:
                if device == "cpu":
                    raise
                log.warning("MoGe no cargó en %s; se usa CPU", device, exc_info=True)
                device = "cpu"
                _model = MoGeModel.from_pretrained(MOGE_MODEL).to(device).eval()
            _device = device
        return _model, _device


def _infer_on(model, img: Image.Image, device: str) -> dict:
    import torch

    arr = np.asarray(img, dtype=np.float32) / 255.0
    tensor = torch.from_numpy(arr).permute(2, 0, 1).to(device)
    with torch.inference_mode():
        out = model.infer(tensor)
    return {k: v.cpu().numpy() for k, v in out.items()}


def run_moge(img: Image.Image) -> MogeResult:
    """Corre MoGe sobre la imagen (ya corregida por EXIF) redimensionada a máx. 1024 px."""
    global _model, _device
    t0 = time.perf_counter()
    model, device = get_model()
    t1 = time.perf_counter()
    small = resize_for_inference(img)
    try:
        out = _infer_on(model, small, device)
    except Exception:
        if device != "mps":
            raise
        log.warning("MoGe falló en MPS; se reintenta en CPU", exc_info=True)
        with _lock:
            _model, _device = model.to("cpu"), "cpu"
        model, device = _model, "cpu"
        out = _infer_on(model, small, device)
    t2 = time.perf_counter()
    return MogeResult(
        points=out["points"].astype(np.float32),
        depth=out["depth"].astype(np.float32),
        normal=out["normal"].astype(np.float32) if "normal" in out else None,
        mask=out["mask"].astype(bool),
        intrinsics=out["intrinsics"].astype(np.float64),
        device=device,
        load_ms=round((t1 - t0) * 1000),
        infer_ms=round((t2 - t1) * 1000),
    )
