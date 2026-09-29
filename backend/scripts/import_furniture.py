"""Importa los muebles de samples/furniture/<carpeta>/ (con mueble.json válido) al catálogo.

Uso: uv run python scripts/import_furniture.py [--force]
Idempotente: correrlo dos veces no duplica nada (el id viene de mueble.json). Sin --force no
recalcula recortes que ya existen.
"""

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import storage
from app.catalog import service
from app.catalog.cutout import proportion_check
from app.config import SAMPLES_DIR
from app.schemas import FurnitureSpec


def import_folder(folder: Path, force: bool) -> FurnitureSpec:
    spec = FurnitureSpec.model_validate(storage.read_json(folder / "mueble.json"))
    dest = service.item_dir(spec.id)
    dest.mkdir(parents=True, exist_ok=True)

    with Image.open(folder / (spec.main_photo or "foto.jpg")) as im:
        photo = ImageOps.exif_transpose(im).convert("RGB")
    photo.save(dest / "foto.jpg", quality=92)

    item = spec.model_copy(update={"photo_url": storage.file_url(dest / "foto.jpg"), "main_photo": "foto.jpg"})
    if force or not (dest / "cutout.png").is_file():
        item = service.apply_cutout(item, photo)
    else:
        with Image.open(dest / "cutout.png") as c:
            ratio = c.width / c.height
        dims = item.dimensions_cm
        item = item.model_copy(update={
            "cutout_url": storage.file_url(dest / "cutout.png"),
            "thumb_url": storage.file_url(dest / "thumb.png"),
            "cutout_ratio": round(ratio, 4),
            "photo_warning": proportion_check(ratio, dims.width, dims.height),
            "preferred_mode": "cutout",
        })
    notes = [n for n in item.notes if not n.startswith("Recorte:")]
    dims = item.dimensions_cm
    notes.append(f"Recorte: ancho/alto {item.cutout_ratio:.2f} vs. tabla {dims.width / dims.height:.2f}"
                 + (f" → {item.photo_warning}" if item.photo_warning else " (OK)"))
    item = item.model_copy(update={"notes": notes})
    storage.write_json_atomic(dest / "mueble.json", item.model_dump())
    return item


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="recalcular los recortes")
    args = ap.parse_args()
    for folder in sorted(p for p in (SAMPLES_DIR / "furniture").iterdir() if (p / "mueble.json").is_file()):
        item = import_folder(folder, args.force)
        flag = "" if item.dimensions_verified else "  (medidas sin verificar)"
        print(f"✔ {item.id}: {item.name}{flag}")
    items = service.build_catalog()
    print(f"catalog.json: {len(items)} muebles")


if __name__ == "__main__":
    main()
