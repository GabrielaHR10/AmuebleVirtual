"""Detección del plano del piso (PLAN 1.3). Todo en coordenadas three de la cámara (metros)."""

from dataclasses import dataclass, field

import cv2
import numpy as np

MAX_SAMPLES = 20_000
RANSAC_ITERS = 800
INLIER_THRESH_M = 0.03
MASK_THRESH_M = 0.04
MAX_TILT_DEG = 35.0
MIN_INLIER_FRAC = 0.05
# Un plano que pasa (casi) por la cámara corta toda superficie en una línea de la imagen y
# acumula inliers falsos en una franja: se descarta.
MIN_CAMERA_HEIGHT_M = 0.3
# Con las normales de MoGe: el piso debe "mirar hacia arriba" (descarta franjas sobre paredes)
MASK_NORMAL_MAX_DEG = 25.0
MIN_FLOOR_PIXELS_FRAC = 0.01
# Mesones/mesas: plano horizontal más bajo (≥ 30 cm) con suficientes puntos → es el piso
LOWER_PLANE_GAP_M = 0.3
LOWER_PLANE_MIN_PTS = 150
LOWER_PLANE_MIN_SHARE = 0.1
LOWER_START = 0.45
SEED = 1234

UP = np.array([0.0, 1.0, 0.0])


@dataclass
class FloorResult:
    found: bool
    normal: np.ndarray | None = None  # unitario, hacia la cámara
    d: float | None = None  # altura de la cámara sobre el piso
    inlier_ratio: float = 0.0  # píxeles de piso / píxeles totales
    mask: np.ndarray | None = None  # (H, W) bool
    warnings: list[str] = field(default_factory=list)


def _planes_from_triplets(p: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """p: (N, 3, 3) → normales (N, 3) orientadas hacia la cámara, d (N,), válidos (N,)."""
    n = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    norm = np.linalg.norm(n, axis=1)
    ok = norm > 1e-9
    n[ok] /= norm[ok, None]
    d = -np.einsum("ij,ij->i", n, p[:, 0])
    flip = d < 0
    n[flip] *= -1
    d[flip] *= -1
    return n, d, ok


def fit_plane_svd(pts: np.ndarray) -> tuple[np.ndarray, float]:
    """Plano por mínimos cuadrados; n orientada para que d > 0."""
    c = pts.mean(axis=0)
    _, _, vt = np.linalg.svd(pts - c, full_matrices=False)
    n = vt[-1]
    d = -float(n.dot(c))
    if d < 0:
        n, d = -n, -d
    return n, d


def ransac_floor(pts: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, float, float] | None:
    """RANSAC de plano casi horizontal. Devuelve (n, d, fracción de inliers) o None."""
    if len(pts) < 3:
        return None
    idx = rng.integers(0, len(pts), size=(RANSAC_ITERS, 3))
    n, d, ok = _planes_from_triplets(pts[idx])
    ok &= n @ UP >= np.cos(np.radians(MAX_TILT_DEG))
    ok &= d >= MIN_CAMERA_HEIGHT_M
    if not ok.any():
        return None
    n, d = n[ok], d[ok]
    counts = np.zeros(len(n), dtype=np.int64)
    for start in range(0, len(n), 100):  # por lotes para acotar memoria
        dist = np.abs(pts @ n[start:start + 100].T + d[start:start + 100])
        counts[start:start + 100] = (dist < INLIER_THRESH_M).sum(axis=0)
    best = int(np.argmax(counts))
    inliers = np.abs(pts @ n[best] + d[best]) < INLIER_THRESH_M
    n_ref, d_ref = fit_plane_svd(pts[inliers])
    if n_ref @ UP < np.cos(np.radians(MAX_TILT_DEG)) or d_ref < MIN_CAMERA_HEIGHT_M:
        n_ref, d_ref = n[best], float(d[best])
    frac = float((np.abs(pts @ n_ref + d_ref) < INLIER_THRESH_M).mean())
    return n_ref, d_ref, frac


def _prefer_lower_plane(pts: np.ndarray, fit: tuple, rng: np.random.Generator) -> tuple:
    """Si el plano elegido es un mesón/mesa y debajo se ve otro plano horizontal, el piso es el de abajo."""
    n, d, frac = fit
    below = pts[pts @ n + d < -LOWER_PLANE_GAP_M]
    if len(below) < LOWER_PLANE_MIN_PTS:
        return fit
    low = ransac_floor(below, rng)
    if low is None or low[1] < d + LOWER_PLANE_GAP_M:
        return fit
    low_count = low[2] * len(below)
    if low_count >= max(LOWER_PLANE_MIN_PTS, LOWER_PLANE_MIN_SHARE * frac * len(pts)):
        return low[0], low[1], low_count / len(pts)
    return fit


def floor_mask(points: np.ndarray, valid: np.ndarray, n: np.ndarray, d: float,
               normals: np.ndarray | None = None) -> np.ndarray:
    """Píxeles cerca del plano, limpiados y quedándose con el componente más grande de la mitad inferior."""
    h, w = valid.shape
    dist = np.full((h, w), np.inf, dtype=np.float32)
    dist[valid] = np.abs(points[valid] @ n + d)
    near = dist < MASK_THRESH_M
    if normals is not None:
        near &= normals @ n >= np.cos(np.radians(MASK_NORMAL_MAX_DEG))
    raw = near.astype(np.uint8)
    kernel = np.ones((5, 5), np.uint8)
    clean = cv2.morphologyEx(raw, cv2.MORPH_OPEN, kernel)
    clean = cv2.morphologyEx(clean, cv2.MORPH_CLOSE, kernel)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(clean, connectivity=4)
    lower = labels[int(h * LOWER_START):]
    best, best_area = 0, 0
    for label in range(1, count):
        if (lower == label).any() and stats[label, cv2.CC_STAT_AREA] > best_area:
            best, best_area = label, stats[label, cv2.CC_STAT_AREA]
    return (labels == best) & (best > 0) & valid


def detect_floor(points: np.ndarray, valid: np.ndarray, normals: np.ndarray | None = None) -> FloorResult:
    """points, normals: (H, W, 3) en coords three; valid: (H, W) bool.

    Si llegan las normales de MoGe, solo se usan como candidatos los píxeles que miran hacia arriba.
    """
    h, w = valid.shape
    valid = valid & np.isfinite(points).all(axis=-1)
    rows = np.arange(h)[:, None] >= LOWER_START * h
    cand_mask = valid & rows
    if normals is not None:
        normals = np.nan_to_num(normals)
        cand_mask &= normals @ UP >= np.cos(np.radians(MAX_TILT_DEG))
    cand = points[cand_mask]
    rng = np.random.default_rng(SEED)
    if len(cand) > MAX_SAMPLES:
        cand = cand[rng.choice(len(cand), MAX_SAMPLES, replace=False)]

    fit = ransac_floor(cand, rng)
    if fit is None or fit[2] < MIN_INLIER_FRAC:
        return FloorResult(found=False, warnings=["piso_no_encontrado"])

    n, d, _ = _prefer_lower_plane(cand, fit, rng)
    mask = floor_mask(points, valid, n, d, normals)
    ratio = float(mask.sum() / (h * w))
    if ratio < MIN_FLOOR_PIXELS_FRAC:
        return FloorResult(found=False, warnings=["piso_no_encontrado"])
    warnings = []
    if not 0.8 <= d <= 2.2:
        warnings.append("escala_dudosa")
    if ratio < 0.08:
        warnings.append("poco_piso_visible")
    return FloorResult(True, n, float(d), ratio, mask, warnings)


def draw_floor_debug(image_rgb: np.ndarray, result: FloorResult) -> np.ndarray:
    """Piso en verde semitransparente y altura de cámara escrita. Devuelve RGB uint8."""
    out = image_rgb.copy()
    h, w = out.shape[:2]
    if result.found and result.mask is not None:
        m = cv2.resize(result.mask.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST).astype(bool)
        out[m] = (0.55 * out[m] + 0.45 * np.array([40, 220, 60])).astype(np.uint8)
        text = f"camara {result.d:.2f} m | piso {result.inlier_ratio:.0%}"
    else:
        text = "piso no encontrado"
    if result.warnings:
        text += " | " + ",".join(result.warnings)
    scale = max(w, h) / 1400
    org = (int(12 * scale), int(40 * scale))
    cv2.putText(out, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), int(5 * scale) + 1, cv2.LINE_AA)
    cv2.putText(out, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), int(2 * scale) + 1, cv2.LINE_AA)
    return out
