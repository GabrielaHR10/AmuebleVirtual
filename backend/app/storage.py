"""Guardar y leer archivos en data/ (escritura atómica para JSON)."""

import json
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path

from app.config import DATA_DIR

SCENES_DIR = DATA_DIR / "scenes"


def new_scene_id(now: datetime | None = None) -> str:
    now = now or datetime.now(UTC).astimezone()
    return f"scn_{now:%Y%m%d_%H%M%S}_{secrets.token_hex(2)}"


def scene_dir(scene_id: str) -> Path:
    if not scene_id.startswith("scn_") or "/" in scene_id or "\\" in scene_id or ".." in scene_id:
        raise ValueError("Id de escena inválido")
    return SCENES_DIR / scene_id


def file_url(path: Path) -> str:
    """URL pública (/files/...) de un archivo dentro de data/."""
    return "/files/" + path.resolve().relative_to(DATA_DIR.resolve()).as_posix()


def write_json_atomic(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
