"""Leer la tabla de medidas de una tienda con la IA local (PLAN 3.6). El usuario siempre confirma."""

import io
import urllib.error

from PIL import Image
from pydantic import BaseModel, Field, ValidationError

from app.placement import vlm

PROMPT = """This image is a furniture store's product specification table (usually in Spanish).
Extract the furniture dimensions and answer ONLY with JSON:
{"raw_table": {"<label exactly as written>": "<value exactly as written>"},
 "width_cm": <number>, "depth_cm": <number>, "height_cm": <number>,
 "extra_dimensions_cm": {"<name in snake_case>": <number>}, "units_detected": "cm|m|mm|in"}
Rules:
- width_cm = front width, the side you see when facing the furniture (labels like "Ancho", "Largo", "Frente").
- depth_cm = front-to-back depth ("Fondo", "Profundidad"). For beds, depth is the length (headboard to foot).
- height_cm = total height ("Alto", "Altura").
- If the table literally says "Ancho" use it as width and "Profundidad"/"Fondo" as depth, even if depth is larger.
- Other measures (seat height, arm height, diameter...) go in extra_dimensions_cm. Round tables: width = depth = diameter.
- Convert everything to centimeters (1 m = 100 cm, 1 mm = 0.1 cm, 1 in = 2.54 cm).
- raw_table must copy only the rows about measures, exactly as written."""


class Extracted(BaseModel):
    raw_table: dict[str, str] = Field(default_factory=dict)
    width_cm: float = Field(gt=0, lt=500)
    depth_cm: float = Field(gt=0, lt=500)
    height_cm: float = Field(gt=0, lt=300)
    extra_dimensions_cm: dict[str, float] = Field(default_factory=dict)
    units_detected: str | None = None


class ExtractionError(RuntimeError):
    pass


def _jpeg(img: Image.Image) -> bytes:
    img = img.convert("RGB")
    img.thumbnail((1400, 1400))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def extract_dimensions(table: Image.Image, timeout: float = vlm.TIMEOUT_S) -> Extracted:
    if not vlm.status()["available"]:
        raise ExtractionError("La IA local no está disponible: escribe las medidas a mano.")
    try:
        answer = vlm.ask_ollama(PROMPT, _jpeg(table), timeout=timeout)
    except (OSError, ValueError, KeyError, TimeoutError, urllib.error.URLError) as e:
        raise ExtractionError("La IA local no respondió: escribe las medidas a mano.") from e
    answer["raw_table"] = {str(k): str(v) for k, v in (answer.get("raw_table") or {}).items()}
    extras = answer.get("extra_dimensions_cm") or {}
    answer["extra_dimensions_cm"] = {str(k): v for k, v in extras.items() if isinstance(v, int | float) and v > 0}
    try:
        return Extracted.model_validate(answer)
    except ValidationError as e:
        raise ExtractionError("No se pudieron leer medidas razonables de la tabla: escríbelas a mano.") from e

