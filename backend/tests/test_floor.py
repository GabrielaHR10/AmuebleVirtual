import numpy as np
import pytest

from app.geometry.floor import detect_floor, fit_plane_svd, ransac_floor


def synthetic_room(h=240, w=180, cam_height=1.5, pitch_deg=20.0, fov_y=65.0,
                   noise=0.01, outlier_frac=0.3, seed=0):
    """Mapa de puntos (coords three) de una cámara inclinada sobre un piso, con paredes a 5 m."""
    rng = np.random.default_rng(seed)
    a = np.radians(pitch_deg)
    n = np.array([0.0, np.cos(a), np.sin(a)])  # arriba del mundo, en coords de cámara
    fy = 0.5 / np.tan(np.radians(fov_y) / 2)
    v, u = np.mgrid[0:h, 0:w]
    rays = np.stack([(u / w - 0.5) / fy * w / h, -(v / h - 0.5) / fy, -np.ones_like(u, float)], -1)
    rays /= np.linalg.norm(rays, axis=-1, keepdims=True)
    denom = rays @ n
    t_floor = np.where(denom < -1e-6, -cam_height / np.where(denom < -1e-6, denom, 1), np.inf)
    t = np.minimum(t_floor, 5.0)
    pts = rays * t[..., None]
    on_floor = t_floor <= 5.0
    pts += rng.normal(0, noise, pts.shape)
    lower = np.arange(h)[:, None] >= 0.45 * h
    outliers = lower & (rng.random((h, w)) < outlier_frac)
    pts[outliers] += rng.uniform(-0.8, 0.8, (outliers.sum(), 3))
    return pts, np.ones((h, w), bool), n, cam_height, on_floor


def test_ransac_synthetic_floor_with_noise_and_outliers():
    # PLAN 1.3: ruido 1 cm + 30 % outliers → normal < 3°, d < 3 cm. Se prueba el ajuste sobre la nube
    # (la máscara con outliers sueltos píxel a píxel no es realista; se prueba aparte sin outliers).
    pts, _, n_true, d_true, on_floor = synthetic_room()
    lower = np.arange(pts.shape[0])[:, None] >= 0.45 * pts.shape[0]
    cloud = pts[lower & np.ones_like(on_floor)]
    n, d, frac = ransac_floor(cloud, np.random.default_rng(0))
    angle = np.degrees(np.arccos(np.clip(n @ n_true, -1, 1)))
    assert angle < 3.0
    assert abs(d - d_true) < 0.03
    assert frac > 0.05


def test_floor_mask_covers_floor_region():
    pts, valid, *_, on_floor = synthetic_room(outlier_frac=0.0)
    res = detect_floor(pts, valid)
    overlap = (res.mask & on_floor).sum() / on_floor.sum()
    assert overlap > 0.9
    assert res.inlier_ratio > 0.08 and res.warnings == []


def test_warns_on_odd_camera_height():
    pts, valid, *_ = synthetic_room(cam_height=3.0, outlier_frac=0.0)
    assert "escala_dudosa" in detect_floor(pts, valid).warnings


def test_no_floor_when_only_walls():
    rng = np.random.default_rng(1)
    h, w = 120, 90
    pts = np.stack([rng.uniform(-2, 2, (h, w)), rng.uniform(-1, 1, (h, w)), np.full((h, w), -3.0)], -1)
    res = detect_floor(pts, np.ones((h, w), bool))
    assert not res.found and res.warnings == ["piso_no_encontrado"]


def test_ignores_planes_through_the_camera():
    # Solo paredes frontales + un plano que pasa por la cámara: no debe "encontrar piso"
    rng = np.random.default_rng(2)
    h, w = 120, 90
    x, z = rng.uniform(-2, 2, (h, w)), rng.uniform(-4, -1, (h, w))
    pts = np.stack([x, -0.05 * z, z], -1)  # plano casi horizontal con d = 0
    res = detect_floor(pts, np.ones((h, w), bool))
    assert not res.found or res.d >= 0.3


def test_normals_reject_wall_band():
    # Pared frontal (normal hacia la cámara, +z) con un piso real abajo: con normales, la máscara
    # solo debe quedarse con píxeles que miran hacia arriba.
    pts, valid, n_true, d_true, on_floor = synthetic_room(outlier_frac=0.0)
    normals = np.where(on_floor[..., None], n_true, np.array([0.0, 0.0, 1.0]))
    res = detect_floor(pts, valid, normals)
    assert res.found and abs(res.d - d_true) < 0.03
    # el cierre morfológico puede sumar algún píxel del borde piso/pared, pero nunca una franja
    assert (res.mask & ~on_floor).sum() < 0.01 * res.mask.sum()


def test_normals_without_up_facing_pixels_means_no_floor():
    pts, valid, *_ = synthetic_room(outlier_frac=0.0)
    walls = np.broadcast_to(np.array([0.0, 0.0, 1.0]), pts.shape)
    res = detect_floor(pts, valid, walls)
    assert not res.found and res.warnings == ["piso_no_encontrado"]


def test_prefers_floor_below_a_counter():
    # Mesón grande a 0.9 m del piso ocupa la mayor parte; el piso real se ve en una franja inferior
    pts, valid, n_true, d_true, on_floor = synthetic_room(outlier_frac=0.0)
    h = pts.shape[0]
    counter = on_floor & (np.arange(h)[:, None] < 0.85 * h)
    t = -(d_true - 0.9) / (pts[counter] @ n_true / np.linalg.norm(pts[counter], axis=1))
    rays = pts[counter] / np.linalg.norm(pts[counter], axis=1, keepdims=True)
    pts[counter] = rays * t[:, None]
    res = detect_floor(pts, valid)
    assert res.found and abs(res.d - d_true) < 0.03


def test_fit_plane_svd_orients_towards_camera():
    pts = np.array([[0, -1.2, -1], [1, -1.2, -2], [-1, -1.2, -3], [0.5, -1.2, -4]], float)
    n, d = fit_plane_svd(pts)
    assert n[1] == pytest.approx(1.0) and d == pytest.approx(1.2)
