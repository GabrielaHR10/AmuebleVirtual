"""Malla de oclusión (PLAN 1.4): superficie de la foto en coords three de la cámara, sin el piso."""

from pathlib import Path

import cv2
import numpy as np
import trimesh

MAX_SIDE = 320
MAX_DEPTH_JUMP = 0.04  # salto relativo máximo entre vértices de un triángulo


def _downsample(arr: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    return cv2.resize(arr, size, interpolation=cv2.INTER_NEAREST)


def build_occlusion_mesh(points: np.ndarray, valid: np.ndarray,
                         floor: np.ndarray | None = None) -> trimesh.Trimesh:
    """points: (H, W, 3) coords three; valid, floor: (H, W) bool."""
    h, w = valid.shape
    scale = min(1.0, MAX_SIDE / max(h, w))
    size = (max(2, round(w * scale)), max(2, round(h * scale)))
    pts = _downsample(np.nan_to_num(points, posinf=0, neginf=0).astype(np.float32), size)
    ok = _downsample(valid.astype(np.uint8), size).astype(bool) & np.isfinite(pts).all(-1)
    ok &= pts[..., 2] < 0  # delante de la cámara
    is_floor = (_downsample(floor.astype(np.uint8), size).astype(bool)
                if floor is not None else np.zeros_like(ok))
    gh, gw = ok.shape

    idx = np.arange(gh * gw).reshape(gh, gw)
    a, b = idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel()
    c, d = idx[1:, :-1].ravel(), idx[1:, 1:].ravel()
    faces = np.concatenate([np.stack([a, c, b], 1), np.stack([b, c, d], 1)])  # CCW vista desde la cámara

    flat_ok, flat_floor = ok.ravel(), is_floor.ravel()
    depth = -pts[..., 2].ravel()
    fd = depth[faces]
    keep = flat_ok[faces].all(1)
    keep &= (fd.max(1) / np.maximum(fd.min(1), 1e-6) - 1) <= MAX_DEPTH_JUMP
    keep &= ~flat_floor[faces].all(1)

    mesh = trimesh.Trimesh(vertices=pts.reshape(-1, 3), faces=faces[keep], process=False)
    mesh.remove_unreferenced_vertices()
    return mesh


def export_glb(mesh: trimesh.Trimesh, path: str | Path) -> int:
    """Guarda GLB y devuelve el tamaño en bytes."""
    data = mesh.export(file_type="glb")
    Path(path).write_bytes(data)
    return len(data)
