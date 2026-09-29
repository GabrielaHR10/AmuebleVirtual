"""Utilidades 2D del mundo del piso para ubicar muebles (x, z en metros; yaw como rotation.y de three)."""

from dataclasses import dataclass

import numpy as np

from app.geometry.occupancy import BLOCKED, FREE, NEAR, WALL_EDGE, Occupancy

WALKABLE = (FREE, NEAR, WALL_EDGE)
CLEARANCE_M = 0.10
MAX_BAD_FRAC = 0.03
MAX_BLOCKED_FRAC = 0.02


@dataclass
class Box:
    """Mueble ubicado o candidato: centro (x, z), yaw en grados, medidas en metros (ya con scale_k)."""
    x: float
    z: float
    yaw: float
    w: float
    d: float
    h: float = 0.0

    def front(self) -> np.ndarray:
        a = np.radians(self.yaw)
        return np.array([np.sin(a), np.cos(a)])  # local +z (frente) en el mundo

    def right(self) -> np.ndarray:
        a = np.radians(self.yaw)
        return np.array([np.cos(a), -np.sin(a)])  # local +x

    def corners(self, grow: float = 0.0) -> np.ndarray:
        hw, hd = self.w / 2 + grow, self.d / 2 + grow
        local = np.array([[-hw, -hd], [hw, -hd], [hw, hd], [-hw, hd]])
        return self._to_world(local)

    def samples(self, step: float = 0.05) -> np.ndarray:
        nx, nz = max(2, int(np.ceil(self.w / step)) + 1), max(2, int(np.ceil(self.d / step)) + 1)
        lx, lz = np.meshgrid(np.linspace(-self.w / 2, self.w / 2, nx), np.linspace(-self.d / 2, self.d / 2, nz))
        return self._to_world(np.column_stack([lx.ravel(), lz.ravel()]))

    def _to_world(self, local: np.ndarray) -> np.ndarray:
        r, f = self.right(), self.front()
        return np.array([self.x, self.z]) + local[:, :1] * r + local[:, 1:] * f


def overlap(a: np.ndarray, b: np.ndarray) -> bool:
    """¿Se cruzan dos polígonos convexos (4, 2)? Teorema del eje separador."""
    for poly in (a, b):
        for i in range(len(poly)):
            e = poly[(i + 1) % len(poly)] - poly[i]
            axis = np.array([-e[1], e[0]])
            pa, pb = a @ axis, b @ axis
            if pa.max() <= pb.min() + 1e-9 or pb.max() <= pa.min() + 1e-9:
                return False
    return True


def project(points3: np.ndarray, frame: np.ndarray, intrinsics: np.ndarray) -> np.ndarray:
    """Puntos (N, 3) del mundo del piso → píxeles normalizados (N, 2); NaN detrás de la cámara."""
    cam = np.column_stack([points3, np.ones(len(points3))]) @ frame.T
    depth = -cam[:, 2]
    with np.errstate(divide="ignore", invalid="ignore"):
        uv = np.column_stack([0.5 + intrinsics[0, 0] * cam[:, 0] / depth,
                              0.5 - intrinsics[1, 1] * cam[:, 1] / depth])
    uv[depth <= 1e-3] = np.nan
    return uv


def in_image(uv: np.ndarray) -> np.ndarray:
    return np.isfinite(uv).all(1) & (uv >= 0).all(1) & (uv <= 1).all(1)


def is_valid(box: Box, grid: Occupancy, placed: list[Box], frame: np.ndarray, intrinsics: np.ndarray,
             ignore_overlap_with: set[int] | None = None) -> bool:
    """Huella toda en celdas caminables, sin cruces (+10 cm) y esquinas + punto alto dentro de la foto."""
    states = grid.state_at(*box.samples().T)
    # tolerancia para datos reales: unos pocos centímetros en celdas desconocidas/bloqueadas
    if (~np.isin(states, WALKABLE)).mean() > MAX_BAD_FRAC or (states == BLOCKED).mean() > MAX_BLOCKED_FRAC:
        return False
    mine = box.corners()
    for i, other in enumerate(placed):
        if ignore_overlap_with and i in ignore_overlap_with:
            continue
        if overlap(mine, other.corners(grow=CLEARANCE_M)):
            return False
    c = box.corners()
    pts3 = np.column_stack([c[:, 0], np.zeros(4), c[:, 1]])
    top = np.array([[box.x, box.h, box.z]])
    return bool(in_image(project(np.vstack([pts3, top]), frame, intrinsics)).all())


def visibility(box: Box, frame: np.ndarray, intrinsics: np.ndarray) -> float:
    s = box.samples(0.1)
    uv = project(np.column_stack([s[:, 0], np.zeros(len(s)), s[:, 1]]), frame, intrinsics)
    return float(in_image(uv).mean())


def distance_score(box: Box) -> float:
    """1 entre 2 y 5 m de la cámara; baja linealmente fuera de ese rango."""
    dist = float(np.hypot(box.x, box.z))
    gap = max(0.0, 2.0 - dist, dist - 5.0)
    return max(0.0, 1.0 - gap / 2.0)


def facing_camera(box: Box) -> float:
    """1 si el frente mira a la cámara, −1 si le da la espalda (la cámara está en el origen)."""
    to_cam = -np.array([box.x, box.z])
    n = np.linalg.norm(to_cam)
    return float(box.front() @ (to_cam / n)) if n > 1e-6 else 0.0


def dominant_angle(grid: Occupancy) -> float:
    """Orientación más frecuente de las paredes (grados, módulo 90), en bins de 5°.

    Se usa la moda y no el promedio: por pequeños errores del FOV las paredes laterales pueden salir a
    ~70° de la del fondo y el promedio daría un ángulo que no corresponde a ninguna pared.
    En empate gana el ángulo más cercano a 0° (la foto suele tomarse de frente a una pared).
    """
    dirs = grid.wall_dir[grid.state == WALL_EDGE]
    if len(dirs) == 0:
        return 0.0
    ang = np.degrees(np.arctan2(dirs[:, 0], dirs[:, 1])) % 90
    bins = (np.round(ang / 5) * 5) % 90
    values, counts = np.unique(bins, return_counts=True)
    best = values[counts == counts.max()]
    signed = np.where(best > 45, best - 90, best)
    return float(signed[np.argmin(np.abs(signed))])


def local_wall_normals(grid: Occupancy, iz: np.ndarray, ix: np.ndarray, radius: float = 0.45) -> np.ndarray:
    """Dirección (x, z) hacia la pared en cada celda, ajustando una recta (PCA) a las celdas de pared cercanas.

    Devuelve NaN donde no hay suficientes celdas de pared alrededor.
    """
    from app.geometry.occupancy import BLOCKED, WALL_MIN_H

    tz, tx = np.nonzero((grid.state == BLOCKED) & (grid.max_height > WALL_MIN_H))
    wx, wz = grid.center(tz, tx)
    walls = np.column_stack([wx, wz])
    cx, cz = grid.center(iz, ix)
    out = np.full((len(iz), 2), np.nan)
    for k, c in enumerate(np.column_stack([cx, cz])):
        near = walls[np.hypot(*(walls - c).T) <= radius]
        if len(near) < 3:
            continue
        mean = near.mean(0)
        _, _, vt = np.linalg.svd(near - mean)
        n = np.array([-vt[0][1], vt[0][0]])  # perpendicular a la recta de la pared
        if n @ (mean - c) < 0:
            n = -n
        out[k] = n
    return out


def snap_yaw(yaw: float, base: float) -> float:
    """Ajusta el yaw al múltiplo de 90° (desde la orientación dominante) más cercano."""
    k = round((yaw - base) / 90.0)
    return (base + 90.0 * k) % 360.0
