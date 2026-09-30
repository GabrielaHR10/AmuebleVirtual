import numpy as np
import trimesh

from app.catalog.to3d import align_yaw, normalize


def _box_rotated(yaw_deg: float) -> trimesh.Trimesh:
    """Caja 2.0 × 0.9 (x × z en glTF) girada yaw alrededor de +y, expresada en ejes de TripoSR (z arriba)."""
    box = trimesh.creation.box(extents=[2.0, 0.8, 0.9])  # glTF: ancho x, alto y, fondo z
    a = np.radians(yaw_deg)
    ry = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
    v = box.vertices @ ry.T
    # glTF (x, y, z) → TripoSR: normalize aplica (x, y, z)_tsr → (y, z, x), así que tsr = (z, x, y)
    box.vertices = v[:, [2, 0, 1]]
    return box


def test_align_yaw_undoes_rotation():
    for yaw in (-40, -18, 0, 25, 60):
        v = _box_rotated(yaw).vertices[:, [1, 2, 0]]  # de vuelta a ejes glTF
        assert abs(align_yaw(v[:, [0, 2]]) + yaw) < 1.5  # el giro que la deshace


def test_normalize_gives_real_dimensions_and_axes():
    m = normalize(_box_rotated(20), (1.98, 1.0, 0.91))
    assert np.allclose(m.extents, [1.98, 0.91, 1.0], atol=0.02)
    assert abs(m.bounds[0][1]) < 1e-6  # apoyado en y = 0
    # sin giro residual: las esquinas quedan sobre los bordes de la caja alineada con los ejes
    xz = np.abs(m.vertices[:, [0, 2]])
    assert np.allclose(xz, [0.99, 0.5], atol=0.02)
