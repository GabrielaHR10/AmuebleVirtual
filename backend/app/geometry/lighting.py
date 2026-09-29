"""Luz de la foto para integrar los muebles (PLAN 4.1): color/brillo del piso y posición de la ventana."""

import numpy as np

from app.geometry.room import to_floor_world


def srgb_luminance(rgb: np.ndarray) -> np.ndarray:
    """Luminancia relativa (0–1) de colores sRGB 0–255."""
    c = rgb.astype(np.float64) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return lin @ np.array([0.2126, 0.7152, 0.0722])


def estimate_lighting(image_rgb: np.ndarray, points: np.ndarray, valid: np.ndarray, floor_mask: np.ndarray,
                      frame: np.ndarray | None) -> dict:
    """image_rgb con el mismo tamaño que points (resolución de inferencia).

    - floor_rgb / floor_luminance: color medio del piso (para la luz ambiente y el brillo de los recortes).
    - light_source: punto (mundo del piso) de la zona más brillante que no es piso (ventana/lámpara), o None.
    """
    out: dict = {"floor_rgb": None, "floor_luminance": None, "light_source": None}
    if floor_mask.any():
        px = image_rgb[floor_mask]
        out["floor_rgb"] = [round(float(v), 1) for v in np.median(px, axis=0)]
        out["floor_luminance"] = round(float(np.median(srgb_luminance(px))), 4)
    if frame is None:
        return out
    lum = srgb_luminance(image_rgb)
    cand = valid & ~floor_mask & np.isfinite(points).all(-1)
    if cand.sum() < 100:
        return out
    thr = np.percentile(lum[cand], 98)
    bright = cand & (lum >= thr)
    world = to_floor_world(points[bright], frame)
    # la ventana suele verse "lejos" (a través del vidrio): se toma la mediana y se acota la distancia
    src = np.median(world, axis=0)
    dist = np.hypot(src[0], src[2])
    if dist > 8:
        src[[0, 2]] *= 8 / dist
    src[1] = float(np.clip(src[1], 1.2, 2.6))
    out["light_source"] = [round(float(v), 3) for v in src]
    return out
