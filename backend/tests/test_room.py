import numpy as np
import pytest

from app.geometry.coords import floor_frame
from app.geometry.floor import detect_floor
from app.geometry.room import confidence, estimate_room, floor_area_and_extent, room_text

ROOM_W, ROOM_BACK, ROOM_FRONT, CEIL = 4.0, -5.0, 0.6, 2.4


def box_room(h=360, w=270, cam_h=1.5, pitch_deg=15.0, fov_y=70.0):
    """Cuarto 4 × 5.6 m con techo a 2.4 m; cámara a cam_h, mirando a −z e inclinada hacia abajo.

    Devuelve puntos y normales en coords three de la cámara.
    """
    a = np.radians(pitch_deg)
    # rotación cámara → mundo (pitch hacia abajo alrededor de x)
    r = np.array([[1, 0, 0], [0, np.cos(a), np.sin(a)], [0, -np.sin(a), np.cos(a)]])
    fy = 0.5 / np.tan(np.radians(fov_y) / 2)
    v, u = np.mgrid[0:h, 0:w]
    d_cam = np.stack([(u / w - 0.5) / fy * w / h, -(v / h - 0.5) / fy, -np.ones_like(u, float)], -1)
    d_w = d_cam @ r.T
    origin = np.array([0.0, cam_h, 0.0])
    planes = [  # (eje, valor, normal hacia dentro)
        (1, 0.0, [0, 1, 0]), (1, CEIL, [0, -1, 0]),
        (0, -ROOM_W / 2, [1, 0, 0]), (0, ROOM_W / 2, [-1, 0, 0]),
        (2, ROOM_BACK, [0, 0, 1]), (2, ROOM_FRONT, [0, 0, -1]),
    ]
    best_t = np.full((h, w), np.inf)
    best_n = np.zeros((h, w, 3))
    for axis, val, n in planes:
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (val - origin[axis]) / d_w[..., axis]
        t = np.where(t > 1e-6, t, np.inf)
        closer = t < best_t
        best_t[closer] = t[closer]
        best_n[closer] = n
    pts_w = origin + d_w * best_t[..., None]
    pts_cam = (pts_w - origin) @ r  # mundo → cámara
    normals_cam = best_n @ r
    return pts_cam, normals_cam


def _estimate(**kw):
    pts, normals = box_room(**kw)
    valid = np.ones(pts.shape[:2], bool)
    floor = detect_floor(pts, valid, normals)
    frame = floor_frame(floor.normal, floor.d)
    return floor, estimate_room(pts, valid, normals, floor, frame)


def test_box_room_measurements():
    floor, est = _estimate()
    assert floor.found and floor.d == pytest.approx(1.5, abs=0.03)
    ext = est["floor_extent_m"]
    assert ext["width"] == pytest.approx(ROOM_W, rel=0.1)  # se ve todo el ancho
    assert 2.0 < ext["depth"] < abs(ROOM_BACK) + 0.1  # el fondo visible es parcial
    assert est["ceiling_height_m"] == pytest.approx(CEIL, abs=0.05)
    area = est["visible_floor_area_m2"]
    assert 0.8 * ext["width"] * ext["depth"] < area < 1.1 * ext["width"] * ext["depth"]
    assert "techo 2.4" in room_text(est)


def test_no_ceiling_when_not_visible():
    _, est = _estimate(pitch_deg=30.0, fov_y=40.0)
    assert est["ceiling_height_m"] is None


def test_scale_k_divides_measurements():
    pts, normals = box_room()
    valid = np.ones(pts.shape[:2], bool)
    floor = detect_floor(pts, valid, normals)
    frame = floor_frame(floor.normal, floor.d)
    base = estimate_room(pts, valid, normals, floor, frame)
    scaled = estimate_room(pts, valid, normals, floor, frame, scale_k=2.0)
    assert scaled["floor_extent_m"]["width"] == pytest.approx(base["floor_extent_m"]["width"] / 2, abs=0.01)
    assert scaled["visible_floor_area_m2"] == pytest.approx(base["visible_floor_area_m2"] / 4, abs=0.02)


def test_extent_width_is_the_side_along_x():
    rng = np.random.default_rng(0)
    xz = np.column_stack([rng.uniform(-1.5, 1.5, 5000), rng.uniform(-4, -3, 5000)])  # 3 × 1 m
    _, ext = floor_area_and_extent(xz)
    assert ext["width"] == pytest.approx(3.0, rel=0.05)
    assert ext["depth"] == pytest.approx(1.0, rel=0.05)


def test_confidence_levels():
    from app.geometry.floor import FloorResult
    assert confidence(FloorResult(True, np.array([0, 1, 0]), 1.4, 0.3, None, [])) == "alta"
    assert confidence(FloorResult(True, np.array([0, 1, 0]), 1.4, 0.1, None, [])) == "media"
    assert confidence(FloorResult(True, np.array([0, 1, 0]), 1.4, 0.3, None, ["escala_dudosa"])) == "baja"
