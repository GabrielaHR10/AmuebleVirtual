"""Modelos pydantic compartidos (PLAN §5)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Category = Literal[
    "sofa", "armchair", "chair", "bed", "nightstand", "dining_table", "coffee_table", "desk",
    "tv_stand", "shelf", "wardrobe", "rug", "lamp", "plant", "other",
]
DimensionsSource = Literal["tabla_medidas", "usuario", "modelo_3d", "vlm_extraida"]


class Dimensions(BaseModel):
    """Medidas en cm. width = ancho de frente, depth = fondo, height = alto total (PLAN §5.2)."""

    model_config = ConfigDict(extra="forbid")

    width: float = Field(gt=0, lt=500)
    depth: float = Field(gt=0)
    height: float = Field(gt=0, lt=300)


class FurnitureSpec(BaseModel):
    """Ficha de un mueble (`mueble.json`). Base del `CatalogItem`."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    name: str = Field(min_length=1)
    category: Category
    dimensions_cm: Dimensions
    extra_dimensions_cm: dict[str, float] = Field(default_factory=dict)
    dimensions_source: DimensionsSource
    dimensions_verified: bool = False
    monthly_price_cop: int | None = None
    preferred_mode: Literal["cutout", "3d"] = "cutout"
    glb_url: str | None = None
    cutout_url: str | None = None
    photo_url: str | None = None
    thumb_url: str | None = None
    yaw_offset_deg: float = 0
    against_wall: bool
    source: str
    license: str
    # Auditoría de la transcripción (solo en muebles de Gabriela)
    raw_table: dict[str, str] | None = None
    main_photo: str | None = None
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _extras_positive(self) -> "FurnitureSpec":
        bad = [k for k, v in self.extra_dimensions_cm.items() if v <= 0]
        if bad:
            raise ValueError(f"Medidas extra deben ser > 0: {', '.join(bad)}")
        return self
