import numpy as np
import pytest

from app.geometry.coords import cv_to_three, floor_frame, fov_y_deg, to_column_major


def _pixel_ray_cv(u: float, v: float, k: np.ndarray, depth: float = 2.0) -> np.ndarray:
    """Punto OpenCV a `depth` metros sobre el rayo del píxel normalizado (u, v)."""
    x = (u - k[0, 2]) / k[0, 0]
    y = (v - k[1, 2]) / k[1, 1]
    return np.array([x, y, 1.0]) * depth


K = np.array([[0.78, 0, 0.5], [0, 1.04, 0.5], [0, 0, 1]])


def test_cv_to_three_flips_y_and_z():
    assert np.allclose(cv_to_three(np.array([1.0, 2.0, 3.0])), [1.0, -2.0, -3.0])
    grid = np.ones((4, 5, 3), np.float32)
    out = cv_to_three(grid)
    assert out.shape == grid.shape and out.dtype == np.float32
    assert np.allclose(out[..., 1], -1) and np.allclose(out[..., 2], -1)


def test_bottom_center_pixel_is_below_camera_in_three():
    p = cv_to_three(_pixel_ray_cv(0.5, 0.95, K))
    assert p[1] < 0  # parte inferior de la foto → y < 0
    assert p[2] < 0  # delante de la cámara → z < 0


def test_fov_y_deg():
    assert fov_y_deg(K) == pytest.approx(np.degrees(2 * np.arctan(0.5 / 1.04)))
    assert fov_y_deg(np.diag([1.0, 0.5, 1.0])) == pytest.approx(90.0)


def test_floor_frame_synthetic_level_plane():
    m = floor_frame(np.array([0.0, 1.0, 0.0]), 1.5)
    assert np.allclose(m[:3, 3], [0, -1.5, 0])
    assert np.allclose(m[:3, 0], [1, 0, 0])
    assert np.allclose(m[:3, 1], [0, 1, 0])
    assert np.allclose(m[:3, 2], [0, 0, 1])
    assert np.allclose(m[3], [0, 0, 0, 1])


@pytest.mark.parametrize("pitch_deg", [5, 20, 40])
def test_floor_frame_tilted_camera(pitch_deg):
    # Cámara mirando hacia abajo: en coords three de la cámara, el "arriba" del mundo se inclina hacia +z
    a = np.radians(pitch_deg)
    n = np.array([0.0, np.cos(a), np.sin(a)])
    m = floor_frame(n, 1.4)
    r = m[:3, :3]
    assert np.linalg.det(r) == pytest.approx(1.0)
    assert np.allclose(r.T @ r, np.eye(3), atol=1e-9)
    assert m[0, 0] > 0  # x_axis ≈ derecha
    # el origen está sobre el plano y la cámara queda a altura d en el mundo del piso
    origin = m[:3, 3]
    assert n.dot(origin) + 1.4 == pytest.approx(0.0)
    cam_in_floor = np.linalg.inv(m) @ np.array([0, 0, 0, 1.0])
    assert cam_in_floor[1] == pytest.approx(1.4)
    assert cam_in_floor[0] == pytest.approx(0.0) and cam_in_floor[2] == pytest.approx(0.0)


def test_floor_frame_flips_negative_d():
    a = floor_frame(np.array([0.0, 1.0, 0.0]), 1.5)
    b = floor_frame(np.array([0.0, -1.0, 0.0]), -1.5)
    assert np.allclose(a, b)


def test_point_in_front_of_camera_has_negative_floor_z():
    m = floor_frame(np.array([0.0, 1.0, 0.0]), 1.5)
    p_cam = np.array([0.0, -1.5, -3.0, 1.0])  # en el piso, 3 m delante de la cámara
    p_floor = np.linalg.inv(m) @ p_cam
    assert p_floor[1] == pytest.approx(0.0)
    assert p_floor[2] == pytest.approx(-3.0)  # +z apunta hacia la cámara


def test_to_column_major_matches_three_layout():
    m = np.arange(16, dtype=float).reshape(4, 4)
    cm = to_column_major(m)
    assert cm[:4] == [0.0, 4.0, 8.0, 12.0]  # primera columna
    assert cm[12:15] == [3.0, 7.0, 11.0]  # traslación en posiciones 12..14
