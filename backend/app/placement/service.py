"""Sugerencias de ubicación para una escena: arma la grilla, corre la heurística y (opcional) la IA local."""

import secrets
from pathlib import Path

import numpy as np

from app.catalog import service as catalog
from app.geometry.occupancy import Occupancy, build_occupancy
from app.placement.geometry2d import Box
from app.placement.heuristic import Item, Result, suggest
from app.schemas import Placement, Scene
from app.storage import scene_dir


def load_occupancy(scene: Scene) -> tuple[Occupancy, np.ndarray, np.ndarray]:
    """Grilla de ocupación de la escena (recalculada desde geometry.npz). Devuelve (grilla, frame, K)."""
    if not scene.floor.found or not scene.floor.frame:
        raise ValueError("La escena no tiene piso: defínelo primero")
    path: Path = scene_dir(scene.id) / "geometry.npz"
    if not path.is_file():
        raise ValueError("Esta escena es de una versión anterior: vuelve a subir la foto")
    g = np.load(path)
    points = g["points"].astype(np.float32)
    valid = g["valid"]
    frame = np.array(scene.floor.frame, dtype=np.float64).reshape(4, 4).T  # column-major → matriz
    floor_mask = g["floor_mask"]
    if not floor_mask.any():  # piso manual: los puntos cerca del plano son piso
        n, d = np.array(scene.floor.normal), float(scene.floor.d)
        with np.errstate(invalid="ignore"):
            floor_mask = valid & (np.abs(np.nan_to_num(points) @ n + d) < 0.04)
    intr = np.array(scene.camera.intrinsics_norm, dtype=np.float64)
    normals = g["normals"].astype(np.float32) if "normals" in g.files else None
    return build_occupancy(points, valid, floor_mask, frame, intr, normals), frame, intr


def to_item(item, scale_k: float) -> Item:
    d = item.dimensions_cm
    return Item(item.id, item.name, item.category, d.width / 100 * scale_k, d.depth / 100 * scale_k,
                d.height / 100 * scale_k, item.against_wall)


def run_suggest(scene: Scene, item_ids: list[str], replace_uids: list[str]) -> tuple[Result, list[Item]]:
    grid, frame, intr = load_occupancy(scene)
    by_id = {i.id: i for i in catalog.list_items()}
    missing = [i for i in item_ids if i not in by_id]
    if missing:
        raise KeyError(f"Muebles que no están en el catálogo: {', '.join(missing)}")
    items = [to_item(by_id[i], scene.scale_k) for i in item_ids]
    existing = []
    for p in scene.placements:
        if p.uid in replace_uids or p.item_id not in by_id:
            continue
        it = to_item(by_id[p.item_id], scene.scale_k)
        existing.append(Box(p.x, p.z, p.yaw_deg, it.w, it.d, it.h))
    return suggest(grid, items, frame, intr, existing), items


def to_placements(result: Result, source: str = "heuristic") -> list[Placement]:
    by_id = {i.id: i for i in catalog.list_items()}
    out = []
    for it, box in result.placements:
        item = by_id[it.item_id]
        mode = "3d" if item.preferred_mode == "3d" and item.glb_url else "cutout"
        out.append(Placement(uid=f"p_s{secrets.token_hex(3)}", item_id=it.item_id, mode=mode,
                             x=round(box.x, 3), z=round(box.z, 3), yaw_deg=round(box.yaw % 360, 1), source=source))
    return out
