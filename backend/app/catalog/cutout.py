"""Quitar el fondo a la foto de un mueble con rembg (modo recorte 2D, PLAN 2.5)."""

import logging
import threading
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image

log = logging.getLogger("santiago.cutout")

MODELS = ("birefnet-general-lite", "isnet-general-use")  # ambos MIT/Apache
MAX_SIDE = 1024
THUMB = 256
MARGIN = 0.02
RATIO_TOLERANCE = 0.15

_lock = threading.Lock()
_session = None


@dataclass
class Cutout:
    image: Image.Image  # RGBA recortado al objeto
    thumb: Image.Image  # RGBA 256×256
    ratio: float  # ancho/alto en píxeles del recorte


def get_session():
    """Sesión de rembg (singleton). Si el modelo principal falla, usa el de respaldo."""
    global _session
    with _lock:
        if _session is None:
            from rembg import new_session

            for name in MODELS:
                try:
                    _session = new_session(name)
                    break
                except Exception:
                    log.warning("No se pudo cargar rembg '%s'", name, exc_info=True)
            if _session is None:
                raise RuntimeError("No se pudo cargar ningún modelo para quitar el fondo")
        return _session


def keep_main_object(alpha: np.ndarray) -> np.ndarray:
    """Deja solo el componente más grande del alfa (quita plantas/lámparas sueltas alrededor)."""
    solid = (alpha > 127).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(solid, connectivity=8)
    if count <= 2:
        return alpha
    main = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    keep = cv2.dilate((labels == main).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    return np.where(keep, alpha, 0).astype(np.uint8)


def crop_to_alpha(rgba: Image.Image, margin: float = MARGIN) -> Image.Image:
    alpha = np.asarray(rgba)[..., 3]
    ys, xs = np.nonzero(alpha > 16)
    if len(xs) == 0:
        raise ValueError("No se detectó ningún mueble en la foto")
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    mx, my = round((x1 - x0) * margin), round((y1 - y0) * margin)
    box = (max(0, x0 - mx), max(0, y0 - my), min(rgba.width, x1 + mx), min(rgba.height, y1 + my))
    return rgba.crop(box)


def make_thumb(rgba: Image.Image, size: int = THUMB) -> Image.Image:
    img = rgba.copy()
    img.thumbnail((size - 16, size - 16), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(img, ((size - img.width) // 2, (size - img.height) // 2), img)
    return canvas


def make_cutout(photo: Image.Image) -> Cutout:
    from rembg import remove

    rgb = photo.convert("RGB")
    rgb.thumbnail((2048, 2048))
    rgba = remove(rgb, session=get_session())
    arr = np.asarray(rgba).copy()
    arr[..., 3] = keep_main_object(arr[..., 3])
    cut = crop_to_alpha(Image.fromarray(arr, "RGBA"))
    cut.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    return Cutout(image=cut, thumb=make_thumb(cut), ratio=cut.width / cut.height)


def proportion_check(photo_ratio: float, width_cm: float, height_cm: float) -> str | None:
    """Aviso si la proporción del recorte difiere > 15 % de la tabla (PLAN 2.5)."""
    table_ratio = width_cm / height_cm
    if abs(photo_ratio - table_ratio) / table_ratio > RATIO_TOLERANCE:
        return "La foto no está de frente o las medidas no coinciden"
    return None
