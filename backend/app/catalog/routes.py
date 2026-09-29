"""Endpoints /api/catalog."""

import io
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import ValidationError

from app.catalog import service
from app.schemas import AGAINST_WALL_CATEGORIES, CatalogItem, Category, Dimensions

router = APIRouter(prefix="/catalog", tags=["catalog"])

MAX_PHOTO_BYTES = 30 * 1024 * 1024


def _read_photo(upload: UploadFile) -> Image.Image:
    data = upload.file.read(MAX_PHOTO_BYTES + 1)
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(413, "La foto es muy grande (máximo 30 MB).")
    try:
        with Image.open(io.BytesIO(data)) as im:
            return ImageOps.exif_transpose(im).convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, "No se pudo abrir la foto. Usa JPG o PNG.") from None


@router.get("", response_model=list[CatalogItem])
def list_catalog() -> list[CatalogItem]:
    return service.list_items()


@router.post("", response_model=CatalogItem)
def create_item(
    photo: Annotated[UploadFile, File()],
    name: Annotated[str, Form(min_length=1)],
    category: Annotated[Category, Form()],
    width_cm: Annotated[float, Form()],
    depth_cm: Annotated[float, Form()],
    height_cm: Annotated[float, Form()],
    table_image: Annotated[UploadFile | None, File()] = None,
    dimensions_source: Annotated[Literal["usuario", "vlm_extraida"], Form()] = "usuario",
) -> CatalogItem:
    try:
        dims = Dimensions(width=width_cm, depth=depth_cm, height=height_cm)
    except ValidationError:
        raise HTTPException(422, "Medidas inválidas: deben ser mayores que 0, ancho < 500 cm y alto < 300 cm.") \
            from None
    img = _read_photo(photo)
    table = _read_photo(table_image) if table_image is not None and table_image.filename else None
    item = CatalogItem(
        id=service.unique_id(name), name=name.strip(), category=category, dimensions_cm=dims,
        dimensions_source=dimensions_source, dimensions_verified=True,  # el usuario las confirmó al guardar
        against_wall=category in AGAINST_WALL_CATEGORIES,
        source="Subido por el usuario", license="propio", user_created=True,
    )
    try:
        return service.create_with_photo(item, img, table)
    except ValueError as e:  # no se detectó ningún mueble en la foto
        service.discard(item.id)
        raise HTTPException(422, f"{e}. Toma la foto de frente, con fondo despejado y buena luz.") from None


@router.post("/extract-dimensions")
def extract_dimensions(table_image: Annotated[UploadFile, File()]) -> dict:
    """Lee la foto de la tabla de medidas con la IA local para prellenar el formulario (PLAN 3.6)."""
    from app.catalog.extract import ExtractionError
    from app.catalog.extract import extract_dimensions as run

    img = _read_photo(table_image)
    try:
        return run(img).model_dump()
    except ExtractionError as e:
        raise HTTPException(503, str(e)) from None


@router.delete("/{item_id}")
def delete_item(item_id: str) -> dict:
    item = service.get_item(item_id) if service.is_valid_id(item_id) else None
    if item is None:
        raise HTTPException(404, "Mueble no encontrado")
    if not item.user_created:
        raise HTTPException(403, "Solo se pueden borrar muebles subidos desde la app.")
    service.delete_item(item_id)
    return {"ok": True}
