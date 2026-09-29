"""Regenera data/catalog/catalog.json. Uso: uv run python -m app.catalog.build"""

from app.catalog.service import build_catalog

if __name__ == "__main__":
    items = build_catalog()
    print(f"catalog.json regenerado: {len(items)} muebles")
