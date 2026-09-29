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
from app.catalog.cutout import make_cutout, proportion_check
from app.config import SAMPLES_DIR
from app.schemas import FurnitureSpec

PHOTO_ISSUE_NOTE = "La foto incluye otros objetos (sillas/decoración): conviene una foto del mueble solo."


def import_folder(folder: Path, force: bool) -> FurnitureSpec:
    spec = FurnitureSpec.model_validate(storage.read_json(folder / "mueble.json"))
    dest = service.item_dir(spec.id)
    dest.mkdir(parents=True, exist_ok=True)

    with Image.open(folder / (spec.main_photo or "foto.jpg")) as im:
        photo = ImageOps.exif_transpose(im).convert("RGB")
    photo.save(dest / "foto.jpg", quality=92)

    notes = list(spec.notes)
    if force or not (dest / "cutout.png").is_file():
        cut = make_cutout(photo)
        cut.image.save(dest / "cutout.png")
        cut.thumb.save(dest / "thumb.png")
        ratio = cut.ratio
    else:
        with Image.open(dest / "cutout.png") as c:
            ratio = c.width / c.height
    dims = spec.dimensions_cm
    warning = proportion_check(ratio, dims.width, dims.height)
    notes = [n for n in notes if not n.startswith("Recorte:")]
    notes.append(f"Recorte: ancho/alto {ratio:.2f} vs. tabla {dims.width / dims.height:.2f}"
                 + (f" → {warning}" if warning else " (OK)"))

    item = spec.model_copy(update={
        "photo_url": storage.file_url(dest / "foto.jpg"),
        "cutout_url": storage.file_url(dest / "cutout.png"),
        "thumb_url": storage.file_url(dest / "thumb.png"),
        "main_photo": "foto.jpg",
        "preferred_mode": "cutout",
        "notes": notes,
    })
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
