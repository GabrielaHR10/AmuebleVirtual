"""Grilla de ocupación del piso vista desde arriba (PLAN 3.1). Mundo del piso: y arriba, metros."""

from dataclasses import dataclass

import cv2
import numpy as np

from app.geometry.room import to_floor_world

CELL_M = 0.10
OBJ_MIN_H, OBJ_MAX_H = 0.05, 1.8
NEAR_OBSTACLE_M = 0.20
WALL_MIN_H = 1.2
MARGIN_M = 0.5

UNKNOWN, FREE, NEAR, WALL_EDGE, BLOCKED = 0, 1, 2, 3, 4
COLORS = {UNKNOWN: (60, 60, 60), FREE: (90, 200, 90), NEAR: (220, 200, 60), WALL_EDGE: (60, 130, 240),
          BLOCKED: (200, 60, 60)}


@dataclass
class Occupancy:
    x0: float  # esquina (x mínima, z mínima) de la celda [0, 0]
    z0: float
    cell: float
    state: np.ndarray  # (nz, nx) int8
    wall_dir: np.ndarray  # (nz, nx, 2) dirección (x, z) hacia la pared, en celdas WALL_EDGE
    max_height: np.ndarray  # (nz, nx) altura máxima de puntos (m)

    def cell_of(self, x: np.ndarray, z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return np.floor((z - self.z0) / self.cell).astype(int), np.floor((x - self.x0) / self.cell).astype(int)

    def center(self, iz: np.ndarray, ix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return self.x0 + (ix + 0.5) * self.cell, self.z0 + (iz + 0.5) * self.cell

    def state_at(self, x: np.ndarray, z: np.ndarray) -> np.ndarray:
        iz, ix = self.cell_of(np.asarray(x), np.asarray(z))
        inside = (iz >= 0) & (iz < self.state.shape[0]) & (ix >= 0) & (ix < self.state.shape[1])
        out = np.full(np.shape(iz), UNKNOWN, dtype=np.int8)
        out[inside] = self.state[iz[inside], ix[inside]]
        return out


def project_floor_points(xz: np.ndarray, frame: np.ndarray, intrinsics: np.ndarray) -> np.ndarray:
    """Puntos (N, 2) del piso (y = 0) → píxeles normalizados (N, 2); NaN si quedan detrás de la cámara."""
    world = np.column_stack([xz[:, 0], np.zeros(len(xz)), xz[:, 1], np.ones(len(xz))])
    cam = world @ frame.T
    depth = -cam[:, 2]
    with np.errstate(divide="ignore", invalid="ignore"):
        u = 0.5 + intrinsics[0, 0] * cam[:, 0] / depth
        v = 0.5 - intrinsics[1, 1] * cam[:, 1] / depth
    uv = np.column_stack([u, v])
    uv[depth <= 1e-3] = np.nan
    return uv


def build_occupancy(points: np.ndarray, valid: np.ndarray, floor_mask: np.ndarray,
                    frame: np.ndarray, intrinsics: np.ndarray) -> Occupancy:
    """points: (H, W, 3) coords three de la cámara; floor_mask: (H, W) bool."""
    ok = valid & np.isfinite(points).all(-1)
    world = to_floor_world(points[ok], frame)
    is_floor = floor_mask[ok]
    x, h, z = world[:, 0], world[:, 1], world[:, 2]
    fx, fz = x[is_floor], z[is_floor]
    if len(fx) == 0:
        fx, fz = np.array([0.0]), np.array([-2.0])
    x0, x1 = np.percentile(fx, 0.5) - MARGIN_M, np.percentile(fx, 99.5) + MARGIN_M
    z0, z1 = np.percentile(fz, 0.5) - MARGIN_M, np.percentile(fz, 99.5) + MARGIN_M
    nx, nz = max(1, int(np.ceil((x1 - x0) / CELL_M))), max(1, int(np.ceil((z1 - z0) / CELL_M)))
    grid = Occupancy(x0, z0, CELL_M, np.zeros((nz, nx), np.int8), np.zeros((nz, nx, 2)), np.zeros((nz, nx)))

    iz, ix = grid.cell_of(x, z)
    inside = (iz >= 0) & (iz < nz) & (ix >= 0) & (ix < nx)
    has_floor = np.zeros((nz, nx), bool)
    has_obj = np.zeros((nz, nx), bool)
    sel = inside & is_floor
    has_floor[iz[sel], ix[sel]] = True
    sel = inside & ~is_floor & (h > OBJ_MIN_H) & (h < OBJ_MAX_H)
    has_obj[iz[sel], ix[sel]] = True
    sel = inside & ~is_floor & (h > OBJ_MIN_H)
    np.maximum.at(grid.max_height, (iz[sel], ix[sel]), np.minimum(h[sel], 3.0))

    state = np.full((nz, nx), UNKNOWN, np.int8)
    state[has_floor] = FREE
    state[has_obj] = BLOCKED

    # Celdas cuyo centro no se ve en la foto: desconocidas (borde del encuadre, no pared)
    cz, cx = np.mgrid[0:nz, 0:nx]
    px, pz = grid.center(cz.ravel(), cx.ravel())
    uv = project_floor_points(np.column_stack([px, pz]), frame, intrinsics)
    out_img = ~((uv >= 0) & (uv <= 1)).all(1)
    state.ravel()[out_img & (state.ravel() != BLOCKED)] = UNKNOWN

    blocked = (state == BLOCKED).astype(np.uint8)
    dist = cv2.distanceTransform(1 - blocked, cv2.DIST_L2, 3) * CELL_M
    free = state == FREE
    state[free & (dist <= NEAR_OBSTACLE_M)] = NEAR

    # Borde de pared: celda libre junto a obstáculos altos (> 1.2 m)
    tall = (blocked > 0) & (grid.max_height > WALL_MIN_H)
    for dz in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dz == 0 and dx == 0:
                continue
            neigh = np.zeros_like(tall)
            neigh[max(0, -dz):nz - max(0, dz), max(0, -dx):nx - max(0, dx)] = \
                tall[max(0, dz):nz - max(0, -dz), max(0, dx):nx - max(0, -dx)]
            cand = neigh & np.isin(state, (FREE, NEAR, WALL_EDGE))
            grid.wall_dir[cand] += np.array([dx, dz], float) / np.hypot(dx, dz)
            state[cand] = WALL_EDGE
    norm = np.linalg.norm(grid.wall_dir, axis=-1, keepdims=True)
    grid.wall_dir = np.where(norm > 0, grid.wall_dir / np.maximum(norm, 1e-9), 0)
    grid.state = state
    return grid


def occupancy_png(grid: Occupancy, scale: int = 4) -> np.ndarray:
    """Vista cenital coloreada (RGB). Arriba = lejos de la cámara."""
    img = np.zeros((*grid.state.shape, 3), np.uint8)
    for code, color in COLORS.items():
        img[grid.state == code] = color
    img = cv2.resize(img, (img.shape[1] * scale, img.shape[0] * scale), interpolation=cv2.INTER_NEAREST)
    # cámara (pie) = origen del mundo del piso
    iz, ix = grid.cell_of(np.array([0.0]), np.array([0.0]))
    cv2.circle(img, (int((ix[0] + 0.5) * scale), int((iz[0] + 0.5) * scale)), max(3, scale), (255, 255, 255), -1)
    return img
