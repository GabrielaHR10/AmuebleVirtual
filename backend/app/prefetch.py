"""Descarga los pesos de los modelos para que el primer uso no tarde. Uso: uv run python -m app.prefetch"""

import sys
import time

from app.config import MOGE_MODEL


def prefetch_moge() -> None:
    from moge.model.v2 import MoGeModel

    print(f"→ Modelo de geometría ({MOGE_MODEL}, ~400 MB la primera vez)…", flush=True)
    t = time.perf_counter()
    MoGeModel.from_pretrained(MOGE_MODEL)  # descarga a la caché de Hugging Face si falta
    print(f"  listo en {time.perf_counter() - t:.0f} s", flush=True)


def main() -> None:
    try:
        prefetch_moge()
    except Exception as e:  # noqa: BLE001 — mensaje claro para el usuario final
        print(f"\nNo se pudo descargar el modelo: {e}\n"
              "Revisa tu conexión a internet y vuelve a correr el instalador "
              "(lo ya descargado no se pierde).", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
