"""Medidas estimadas del espacio desde la foto (PLAN 1.7). El usuario no da medidas."""

import cv2
import numpy as np

from app.geometry.floor import FloorResult, _planes_from_triplets

CELL_M = 0.05
EXTREME_FRAC = 0.02
CEIL_MAX_DEG = 20.0
CEIL_MIN_HEIGHT_M = 1.8
CEIL_ITERS = 400
CEIL_THRESH_M = 0.04
CEIL_MIN_PTS = 300
SEED = 4321


def to_floor_world(points: np.ndarray, frame: np.ndarray) -> np.ndarray:
    """Puntos (N, 3) de cámara three → mundo del piso (inversa de floor_frame)."""
    inv = np.linalg.inv(frame)
    return points @ inv[:3, :3].T + inv[:3, 3]


def _trim_extremes(xz: np.ndarray) -> np.ndarray:
    lo = np.percentile(xz, 100 * EXTREME_FRAC / 2, axis=0)
    hi = np.percentile(xz, 100 * (1 - EXTREME_FRAC / 2), axis=0)
    return xz[((xz >= lo) & (xz <= hi)).all(axis=1)]


def floor_area_and_extent(xz: np.ndarray) -> tuple[float, dict | None]:
    """Área visible (celdas de 5 cm) y rectángulo de área mínima (ancho ≈ eje x, fondo ≈ eje z)."""
    if len(xz) < 10:
        return 0.0, None
    cells = np.unique(np.floor(xz / CELL_M).astype(np.int64), axis=0)
    area = len(cells) * CELL_M * CELL_M
    # Recortar extremos sobre celdas (peso uniforme en metros), no sobre píxeles: lejos de la cámara
    # cada píxel cubre más piso y un recorte por píxeles se come las esquinas del fondo.
    trimmed = _trim_extremes((cells + 0.5) * CELL_M)
    (_, _), (w, h), angle = cv2.minAreaRect(trimmed.astype(np.float32))
    # OpenCV: el lado `w` forma `angle` grados con el eje x
    a = abs(angle) % 180
    along_x = min(a, 180 - a) <= 45
    width, depth = (w, h) if along_x else (h, w)
    width, depth = width + CELL_M, depth + CELL_M  # de centro a centro de celda → borde a borde
    return float(area), {"width": round(float(width), 2), "depth": round(float(depth), 2)}


def ceiling_height(points: np.ndarray, valid: np.ndarray, normals: np.ndarray | None,
                   floor: FloorResult) -> float | None:
    """RANSAC de un plano de techo (mitad superior, normal opuesta a la del piso ±20°, > 1.8 m)."""
    h = valid.shape[0]
    n_f, d_f = floor.normal, floor.d
    upper = valid & (np.arange(h)[:, None] < h / 2)
    if normals is not None:
        upper &= np.nan_to_num(normals) @ -n_f >= np.cos(np.radians(CEIL_MAX_DEG))
    pts = points[upper]
    pts = pts[pts @ n_f + d_f > CEIL_MIN_HEIGHT_M]
    if len(pts) < CEIL_MIN_PTS:
        return None
    rng = np.random.default_rng(SEED)
    if len(pts) > 20_000:
        pts = pts[rng.choice(len(pts), 20_000, replace=False)]
    n, d, ok = _planes_from_triplets(pts[rng.integers(0, len(pts), size=(CEIL_ITERS, 3))])
    ok &= n @ -n_f >= np.cos(np.radians(CEIL_MAX_DEG))
    if not ok.any():
        return None
    n, d = n[ok], d[ok]
    counts = (np.abs(pts @ n.T + d) < CEIL_THRESH_M).sum(axis=0)
    best = int(np.argmax(counts))
    if counts[best] < CEIL_MIN_PTS:
        return None
    inliers = pts[np.abs(pts @ n[best] + d[best]) < CEIL_THRESH_M]
    return round(float(np.median(inliers @ n_f + d_f)), 2)


def confidence(floor: FloorResult) -> str:
    if floor.warnings or not floor.found:
        return "baja"
    if floor.inlier_ratio >= 0.2 and 1.0 <= floor.d <= 1.8:
        return "alta"
    return "media"


def estimate_room(points: np.ndarray, valid: np.ndarray, normals: np.ndarray | None,
                  floor: FloorResult, frame: np.ndarray | None, scale_k: float = 1.0) -> dict:
    """Devuelve el dict de `room_estimate` (§5.1). Con `scale_k` se corrigen las medidas calibradas."""
    if not floor.found or frame is None:
        return {"visible_floor_area_m2": None, "floor_extent_m": None, "ceiling_height_m": None,
                "confidence": "baja", "method": "moge2_metric"}
    world = to_floor_world(points[floor.mask], frame)
    area, extent = floor_area_and_extent(world[:, [0, 2]])
    ceil = ceiling_height(points, valid, normals, floor)
    k = scale_k if scale_k > 0 else 1.0
    if extent:
        extent = {key: round(v / k, 2) for key, v in extent.items()}
    return {
        "visible_floor_area_m2": round(area / (k * k), 2),
        "floor_extent_m": extent,
        "ceiling_height_m": round(ceil / k, 2) if ceil else None,
        "confidence": confidence(floor),
        "method": "moge2_metric",
    }


def draw_grid(image_rgb: np.ndarray, floor_mask: np.ndarray, frame: np.ndarray,
              intrinsics: np.ndarray, spacing_m: float = 1.0, extent_m: float = 12.0) -> np.ndarray:
    """Cuadrícula de 1 m sobre el piso, proyectada con la cámara y recortada a la máscara del piso."""
    out = image_rgb.copy()
    hh, ww = out.shape[:2]
    fx, fy = intrinsics[0, 0], intrinsics[1, 1]
    layer = np.zeros((hh, ww), np.uint8)
    ticks = np.arange(-extent_m, extent_m + 1e-6, spacing_m)
    samples = np.linspace(-extent_m, extent_m, 400)

    def project(xz: np.ndarray) -> np.ndarray:
        world = np.column_stack([xz[:, 0], np.zeros(len(xz)), xz[:, 1], np.ones(len(xz))])
        cam = world @ frame.T
        z = -cam[:, 2]
        u = (0.5 + fx * cam[:, 0] / np.where(z > 1e-3, z, np.nan)) * ww
        v = (0.5 - fy * cam[:, 1] / np.where(z > 1e-3, z, np.nan)) * hh
        return np.column_stack([u, v])

    thickness = max(1, round(max(hh, ww) / 500))
    for t in ticks:
        for line in (np.column_stack([np.full_like(samples, t), samples]),
                     np.column_stack([samples, np.full_like(samples, t)])):
            uv = project(line)
            good = np.isfinite(uv).all(1) & (np.abs(uv) < 4 * max(hh, ww)).all(1)
            # cortar la polilínea donde haya puntos inválidos (detrás de la cámara)
            segments = np.split(uv, np.where(~good)[0])
            for seg in segments:
                seg = seg[np.isfinite(seg).all(1)]
                if len(seg) >= 2:
                    cv2.polylines(layer, [np.round(seg).astype(np.int32)], False, 255, thickness, cv2.LINE_AA)
    m = cv2.resize(floor_mask.astype(np.uint8), (ww, hh), interpolation=cv2.INTER_NEAREST).astype(bool)
    a = (layer.astype(np.float32) / 255 * m)[..., None] * 0.85
    return (out * (1 - a) + np.array([255, 255, 255]) * a).astype(np.uint8)


def room_text(est: dict) -> str:
    parts = []
    if est.get("floor_extent_m"):
        e = est["floor_extent_m"]
        parts.append(f"visible {e['width']:.1f} x {e['depth']:.1f} m")
    if est.get("visible_floor_area_m2"):
        parts.append(f"area {est['visible_floor_area_m2']:.1f} m2")
    parts.append(f"techo {est['ceiling_height_m']:.2f} m" if est.get("ceiling_height_m") else "techo no visible")
    parts.append(f"confianza {est['confidence']}")
    return " | ".join(parts)
