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
    # Solo los muebles creados desde la UI se pueden borrar con DELETE /api/catalog/{id}
    user_created: bool = False
    # Recorte 2D: ancho/alto del PNG y aviso si no coincide con la tabla (> 15 %, PLAN 2.5)
    cutout_ratio: float | None = None
    cutout_luminance: float | None = None  # brillo medio del recorte, para igualarlo a la foto (4.1)
    photo_warning: str | None = None

    @model_validator(mode="after")
    def _extras_positive(self) -> "FurnitureSpec":
        bad = [k for k, v in self.extra_dimensions_cm.items() if v <= 0]
        if bad:
            raise ValueError(f"Medidas extra deben ser > 0: {', '.join(bad)}")
        return self


CatalogItem = FurnitureSpec

AGAINST_WALL_CATEGORIES = {"sofa", "bed", "tv_stand", "shelf", "wardrobe", "desk", "nightstand"}


# ---------- Escena (PLAN §5.1) ----------

class ImageInfo(BaseModel):
    url: str
    width: int
    height: int


class CameraInfo(BaseModel):
    fov_y_deg: float
    intrinsics_norm: list[list[float]]
    matrix_world: list[float]  # 16 números column-major


class FloorInfo(BaseModel):
    found: bool
    normal: list[float] | None = None
    d: float | None = None
    inlier_ratio: float = 0.0
    frame: list[float] | None = None  # 16 números column-major


class FloorExtent(BaseModel):
    width: float
    depth: float


class RoomEstimate(BaseModel):
    visible_floor_area_m2: float | None = None
    floor_extent_m: FloorExtent | None = None
    ceiling_height_m: float | None = None
    confidence: Literal["alta", "media", "baja"]
    method: str = "moge2_metric"


class Placement(BaseModel):
    uid: str
    item_id: str
    mode: Literal["3d", "cutout"] = "cutout"
    x: float
    z: float
    yaw_deg: float = 0
    source: Literal["manual", "heuristic", "vlm"] = "manual"


class Lighting(BaseModel):
    floor_rgb: list[float] | None = None
    floor_luminance: float | None = None
    light_source: list[float] | None = None  # mundo del piso (m)


class Scene(BaseModel):
    id: str
    kind: Literal["photo"] = "photo"
    image: ImageInfo
    camera: CameraInfo
    floor: FloorInfo
    camera_height_m: float | None = None
    scale_k: float = 1.0
    room_estimate: RoomEstimate | None = None
    lighting: Lighting | None = None
    warnings: list[str] = Field(default_factory=list)
    assets: dict[str, str] = Field(default_factory=dict)
    placements: list[Placement] = Field(default_factory=list)
    model: str
    timings_ms: dict[str, int] = Field(default_factory=dict)
    created_at: str | None = None
