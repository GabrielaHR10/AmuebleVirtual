"""Miniaturas 256×256 de los muebles 3D (PLAN 2.3).

Uso: uv run python scripts/make_thumbs.py
Corre `e2e/thumbs.spec.ts` (Playwright renderiza cada GLB) y luego recorta, reduce y registra thumb.png.
Requiere el frontend compilado (`bash scripts/build_frontend.sh`). Usa el puerto E2E_PORT (default 8001).
"""

import os
import subprocess
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import storage
from app.catalog import service
from app.catalog.cutout import crop_to_alpha, make_thumb
from app.config import REPO_DIR


def main() -> None:
    env = {**os.environ, "E2E_PORT": os.environ.get("E2E_PORT", "8001")}
    subprocess.run(["npx", "playwright", "test", "e2e/thumbs.spec.ts"], cwd=REPO_DIR / "frontend",
                   env=env, check=True)
    for item in service.list_items():
        big = service.item_dir(item.id) / "thumb_512.png"
        if not big.is_file():
            continue
        with Image.open(big) as im:
            thumb = make_thumb(crop_to_alpha(im.convert("RGBA")))
        dest = big.with_name("thumb.png")
        thumb.save(dest)
        big.unlink()
        updated = item.model_copy(update={"thumb_url": storage.file_url(dest)})
        storage.write_json_atomic(service.item_dir(item.id) / "mueble.json", updated.model_dump())
        print(f"✔ {item.id}")
    service.build_catalog()


if __name__ == "__main__":
    main()
