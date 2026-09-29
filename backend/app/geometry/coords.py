"""Conversiones de coordenadas (PLAN §4). Único lugar donde se pasa de OpenCV a three.js.

- MoGe / OpenCV: x derecha, y abajo, z adelante (metros).
- three.js: x derecha, y arriba, z hacia atrás (la cámara mira a −z).
- OpenCV → three: (x, y, z) → (x, −y, −z). Igual para puntos y normales.

Hallazgo (tarea 1.1, MoGe-2 commit 925b8ed, 14 fotos de samples/rooms):
los intrínsecos de `model.infer` vienen NORMALIZADOS (fx/W, fy/H, cx/W, cy/H); cx = cy = 0.500 exactos.
"""

import numpy as np

_CV_TO_THREE = np.array([1.0, -1.0, -1.0])


def cv_to_three(arr: np.ndarray) -> np.ndarray:
    """Convierte puntos o normales (..., 3) de OpenCV a three.js."""
    arr = np.asarray(arr)
    if arr.shape[-1] != 3:
        raise ValueError(f"Se esperaba última dimensión 3, llegó {arr.shape}")
    return arr * _CV_TO_THREE.astype(arr.dtype if arr.dtype.kind == "f" else np.float64)


def fov_y_deg(intrinsics_norm: np.ndarray) -> float:
    """FOV vertical en grados desde intrínsecos normalizados (punto principal centrado)."""
    fy = float(np.asarray(intrinsics_norm)[1, 1])
    return float(np.degrees(2.0 * np.arctan(0.5 / fy)))


def floor_frame(n: np.ndarray, d: float) -> np.ndarray:
    """Matriz 4x4 "mundo del piso" → "cámara three" para el plano n·p + d = 0 (coords three).

    En el mundo del piso: piso en y = 0, +y arriba, +z (horizontal) hacia la cámara.
    """
    n = np.asarray(n, dtype=np.float64)
    n = n / np.linalg.norm(n)
    if d < 0:  # n debe apuntar hacia el lado de la cámara (d > 0)
        n, d = -n, -d
    forward = np.array([0.0, 0.0, -1.0])
    f = forward - forward.dot(n) * n
    norm_f = np.linalg.norm(f)
    if norm_f < 1e-6:
        raise ValueError("La cámara mira perpendicular al piso: no se puede definir el marco")
    f /= norm_f
    y_axis = n
    z_axis = -f
    x_axis = np.cross(y_axis, z_axis)
    origin = -d * n
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x_axis, y_axis, z_axis, origin
    return m


def to_column_major(m: np.ndarray) -> list[float]:
    """16 números column-major para `THREE.Matrix4().fromArray(...)`."""
    return [float(v) for v in np.asarray(m, dtype=np.float64).T.reshape(-1)]
