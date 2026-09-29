"""Catálogo de muebles: una carpeta por mueble en data/catalog/<id>/ con `mueble.json`.

`catalog.json` es la lista completa, regenerada desde las carpetas (`uv run python -m app.catalog.build`).
"""

import logging
import re
import shutil
import threading
import unicodedata
from pathlib import Path

from PIL import Image

from app import storage
from app.schemas import CatalogItem

log = logging.getLogger("santiago.catalog")
_lock = threading.RLock()


def catalog_dir() -> Path:
    return storage.DATA_DIR / "catalog"


def is_valid_id(item_id: str) -> bool:
    return re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", item_id) is not None


def item_dir(item_id: str) -> Path:
    if not is_valid_id(item_id):
        raise ValueError("Id de mueble inválido")
    return catalog_dir() / item_id


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"([a-z])([A-Z])", r"\1-\2", text)  # MesaGretel → Mesa-Gretel
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "mueble"


def unique_id(name: str) -> str:
    base, n = slugify(name), 2
    candidate = base
    while (catalog_dir() / candidate).exists():
        candidate, n = f"{base}-{n}", n + 1
    return candidate


def build_catalog() -> list[CatalogItem]:
    """Regenera catalog.json desde las carpetas. Las fichas inválidas se omiten con aviso."""
    with _lock:
        items = []
        for path in sorted(catalog_dir().glob("*/mueble.json")):
            try:
                items.append(CatalogItem.model_validate(storage.read_json(path)))
            except (OSError, ValueError):
                log.warning("Ficha inválida, se omite: %s", path, exc_info=True)
        catalog_dir().mkdir(parents=True, exist_ok=True)
        storage.write_json_atomic(catalog_dir() / "catalog.json",
                                  {"items": [i.model_dump() for i in items]})
        return items


def list_items() -> list[CatalogItem]:
    path = catalog_dir() / "catalog.json"
    if not path.is_file():
        return build_catalog()
    return [CatalogItem.model_validate(i) for i in storage.read_json(path)["items"]]


def get_item(item_id: str) -> CatalogItem | None:
    return next((i for i in list_items() if i.id == item_id), None)


def save_item(item: CatalogItem) -> CatalogItem:
    """Escribe data/catalog/<id>/mueble.json y regenera catalog.json."""
    with _lock:
        folder = item_dir(item.id)
        folder.mkdir(parents=True, exist_ok=True)
        storage.write_json_atomic(folder / "mueble.json", item.model_dump())
        build_catalog()
        return item


def create_with_photo(item: CatalogItem, photo: Image.Image,
                      table_image: Image.Image | None = None) -> CatalogItem:
    """Guarda foto.jpg (máx. 2048 px), el recorte (cutout.png + thumb.png) y la ficha."""
    folder = item_dir(item.id)
    folder.mkdir(parents=True, exist_ok=True)
    photo = photo.copy()
    photo.thumbnail((2048, 2048))
    photo.save(folder / "foto.jpg", quality=90)
    if table_image is not None:
        table_image.convert("RGB").save(folder / "medidas.jpg", quality=90)
    item = item.model_copy(update={"photo_url": storage.file_url(folder / "foto.jpg"), "main_photo": "foto.jpg"})
    return save_item(apply_cutout(item, photo))


def apply_cutout(item: CatalogItem, photo: Image.Image) -> CatalogItem:
    """Quita el fondo, guarda cutout.png/thumb.png y compara la proporción con la tabla."""
    from app.catalog.cutout import make_cutout, proportion_check

    folder = item_dir(item.id)
    cut = make_cutout(photo)
    cut.image.save(folder / "cutout.png")
    cut.thumb.save(folder / "thumb.png")
    dims = item.dimensions_cm
    return item.model_copy(update={
        "cutout_url": storage.file_url(folder / "cutout.png"),
        "thumb_url": storage.file_url(folder / "thumb.png"),
        "cutout_ratio": round(cut.ratio, 4),
        "photo_warning": proportion_check(cut.ratio, dims.width, dims.height),
        "preferred_mode": "cutout",
    })


def discard(item_id: str) -> None:
    """Borra la carpeta de un mueble a medio crear (sin tocar catalog.json)."""
    shutil.rmtree(item_dir(item_id), ignore_errors=True)


def delete_item(item_id: str) -> None:
    with _lock:
        shutil.rmtree(item_dir(item_id))
        build_catalog()
