"""Catálogo complementario 3D desde Poly Haven (CC0). Uso: uv run python scripts/seed_catalog.py

Descarga la variante glTF 1k de cada modelo, la convierte a un GLB optimizado con gltf-transform
(texturas webp, necesita Node/npx) y calcula las medidas reales desde el bounding box (metros → cm).
"""

import json
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import storage
from app.catalog import service
from app.schemas import AGAINST_WALL_CATEGORIES, CatalogItem

API = "https://api.polyhaven.com"
HEADERS = {"User-Agent": "SantiagoMuebles/0.1"}

# id de Poly Haven → (nombre en español, categoría). Gabriela quitó (2026-09-29) el sillón mid-century
# y la mesa de pedestal porque su escala se ve irreal.
SEED = {
    "sofa_02": ("Sofá Chesterfield de cuero negro", "sofa"),
    "sofa_03": ("Sofá clásico tapizado", "sofa"),
    "modern_arm_chair_01": ("Sillón moderno", "armchair"),
    "modern_coffee_table_01": ("Mesa de centro moderna", "coffee_table"),
    "coffee_table_round_01": ("Mesa de centro redonda", "coffee_table"),
    "dining_chair_02": ("Silla de comedor", "chair"),
    "modern_wooden_cabinet": ("Mueble bajo de madera (TV)", "tv_stand"),
    "wooden_display_shelves_01": ("Estantería de madera", "shelf"),
    "side_table_01": ("Mesa auxiliar", "nightstand"),
    "potted_plant_02": ("Planta en matera", "plant"),
}

# Modelos cuyo frente no mira a +z (revisado con vistas de frente/lado en 2.3): giro en grados
YAW_OFFSET = {"wooden_display_shelves_01": -90, "modern_coffee_table_01": -90}


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=120) as r:
        dest.write_bytes(r.read())


def to_glb(asset_id: str, out: Path) -> None:
    files = fetch_json(f"{API}/files/{asset_id}")["gltf"]["1k"]["gltf"]
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        gltf = tmp / f"{asset_id}.gltf"
        download(files["url"], gltf)
        for rel, info in files["include"].items():
            download(info["url"], tmp / rel)
        subprocess.run(["npx", "-y", "@gltf-transform/cli", "optimize", str(gltf), str(out),
                        "--texture-compress", "webp", "--texture-size", "1024", "--compress", "false"],
                       check=True, capture_output=True, text=True)


def dimensions_cm(glb: Path, yaw_deg: float = 0) -> dict:
    scene = trimesh.load(glb, force="scene")
    x, y, z = scene.extents  # glTF: +y arriba, frente hacia +z
    if abs(yaw_deg) % 180 == 90:  # girado 90°: el frente es el lado z
        x, z = z, x
    return {"width": round(x * 100, 1), "depth": round(z * 100, 1), "height": round(y * 100, 1)}


def main() -> None:
    for asset_id, (name, category) in SEED.items():
        item_id = f"ph-{service.slugify(asset_id)}"
        folder = service.item_dir(item_id)
        folder.mkdir(parents=True, exist_ok=True)
        glb = folder / "model.glb"
        if not glb.is_file():
            to_glb(asset_id, glb)
        yaw = YAW_OFFSET.get(asset_id, 0)
        dims = dimensions_cm(glb, yaw)
        existing = service.get_item(item_id)
        item = CatalogItem(
            id=item_id, name=name, category=category, dimensions_cm=dims,
            dimensions_source="modelo_3d", dimensions_verified=True,
            preferred_mode="3d", glb_url=storage.file_url(glb),
            thumb_url=existing.thumb_url if existing else None,
            yaw_offset_deg=yaw,
            against_wall=category in AGAINST_WALL_CATEGORIES,
            source=f"Poly Haven: https://polyhaven.com/a/{asset_id}", license="CC0",
        )
        storage.write_json_atomic(folder / "mueble.json", item.model_dump())
        print(f"✔ {item_id}: {dims['width']:.0f}×{dims['depth']:.0f}×{dims['height']:.0f} cm, "
              f"{glb.stat().st_size / 1e6:.1f} MB")
    print(f"catalog.json: {len(service.build_catalog())} muebles")


if __name__ == "__main__":
    main()
