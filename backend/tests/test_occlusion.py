import numpy as np
import trimesh

from app.geometry.occlusion import build_occlusion_mesh, export_glb


def _wall(h=240, w=320, depth=3.0):
    v, u = np.mgrid[0:h, 0:w]
    x = (u / w - 0.5) * 2 * depth * 0.6
    y = -(v / h - 0.5) * 2 * depth * 0.45
    return np.stack([x, y, np.full_like(x, -depth, dtype=float)], -1)


def test_wall_mesh_roundtrip_glb(tmp_path):
    pts = _wall()
    mesh = build_occlusion_mesh(pts, np.ones(pts.shape[:2], bool))
    assert len(mesh.faces) == 2 * 239 * 319
    size = export_glb(mesh, tmp_path / "occ.glb")
    assert size < 3_000_000
    loaded = trimesh.load(tmp_path / "occ.glb", force="mesh")
    assert len(loaded.faces) > 0


def test_downsamples_large_maps():
    pts = _wall(h=768, w=1024)
    mesh = build_occlusion_mesh(pts, np.ones(pts.shape[:2], bool))
    assert len(mesh.vertices) <= 320 * 240


def test_removes_depth_jumps_invalid_and_floor():
    pts = _wall()
    pts[:, 160:, 2] = -6.0  # salto de profundidad a la mitad
    valid = np.ones(pts.shape[:2], bool)
    valid[:20] = False
    floor = np.zeros_like(valid)
    floor[200:] = True
    mesh = build_occlusion_mesh(pts, valid, floor)
    full = 2 * 239 * 319
    assert len(mesh.faces) < full
    verts = mesh.vertices
    tris = verts[mesh.faces]
    depth = -tris[..., 2]
    assert ((depth.max(1) / depth.min(1) - 1) <= 0.04).all()
    # ningún triángulo con sus 3 vértices en las filas del piso ni en las inválidas
    assert (tris[..., 1].min(1) > pts[200, 0, 1] - 1e-6).any()
    assert tris[..., 1].max() <= pts[20, 0, 1] + 1e-6
