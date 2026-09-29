import numpy as np

from app.geometry.coords import floor_frame
from app.geometry.floor import detect_floor
from app.geometry.occupancy import BLOCKED, FREE, NEAR, UNKNOWN, WALL_EDGE, build_occupancy, occupancy_png
from tests.test_room import ROOM_BACK, ROOM_W, box_room


def _grid(**kw):
    pts, normals = box_room(**kw)
    valid = np.ones(pts.shape[:2], bool)
    floor = detect_floor(pts, valid, normals)
    frame = floor_frame(floor.normal, floor.d)
    fy = 0.5 / np.tan(np.radians(70) / 2)
    intr = np.array([[fy * pts.shape[0] / pts.shape[1], 0, 0.5], [0, fy, 0.5], [0, 0, 1]])
    return build_occupancy(pts, valid, floor.mask, frame, intr), frame


def test_box_room_has_free_floor_and_walls():
    grid, _ = _grid()
    counts = {c: int((grid.state == c).sum()) for c in (UNKNOWN, FREE, NEAR, WALL_EDGE, BLOCKED)}
    assert counts[FREE] > 200 and counts[BLOCKED] > 50 and counts[WALL_EDGE] > 30
    # centro del cuarto, 2.5 m delante: libre
    assert grid.state_at(np.array([0.0]), np.array([-2.5]))[0] == FREE
    # junto a la pared del fondo: borde de pared, con dirección hacia -z (la pared)
    iz, ix = grid.cell_of(np.array([0.0]), np.array([ROOM_BACK + 0.12]))
    assert grid.state[iz[0], ix[0]] == WALL_EDGE
    assert grid.wall_dir[iz[0], ix[0]][1] < -0.7
    # junto a la pared derecha: dirección hacia +x
    iz, ix = grid.cell_of(np.array([ROOM_W / 2 - 0.12]), np.array([-4.6]))  # visible desde ~3.9 m
    assert grid.state[iz[0], ix[0]] == WALL_EDGE and grid.wall_dir[iz[0], ix[0]][0] > 0.7


def test_png_renders():
    grid, _ = _grid()
    img = occupancy_png(grid)
    assert img.ndim == 3 and img.shape[0] == grid.state.shape[0] * 4
