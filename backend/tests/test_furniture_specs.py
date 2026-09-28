import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import SAMPLES_DIR
from app.schemas import FurnitureSpec

SPEC_FILES = sorted((SAMPLES_DIR / "furniture").glob("*/mueble.json"))


def test_every_furniture_folder_has_spec():
    folders = [p for p in (SAMPLES_DIR / "furniture").iterdir() if p.is_dir()]
    missing = [f.name for f in folders if not (f / "mueble.json").is_file()]
    assert not missing, f"Carpetas sin mueble.json: {missing}"


@pytest.mark.parametrize("path", SPEC_FILES, ids=lambda p: p.parent.name)
def test_spec_is_valid(path: Path):
    spec = FurnitureSpec.model_validate(json.loads(path.read_text(encoding="utf-8")))
    assert spec.main_photo and (path.parent / spec.main_photo).is_file()
    assert spec.raw_table, "Falta raw_table para auditar la transcripción"


def test_rejects_out_of_range_dimensions():
    base = {
        "id": "x", "name": "X", "category": "sofa", "dimensions_source": "usuario",
        "against_wall": True, "source": "test", "license": "test",
    }
    for dims in ({"width": 0, "depth": 90, "height": 80},
                 {"width": 600, "depth": 90, "height": 80},
                 {"width": 200, "depth": 90, "height": 300}):
        with pytest.raises(ValidationError):
            FurnitureSpec.model_validate({**base, "dimensions_cm": dims})
