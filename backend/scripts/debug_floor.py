"""Detecta el piso en cada imagen y guarda debug_XX.jpg (piso en verde + altura de cámara).

Uso: uv run python scripts/debug_floor.py <imagen> [...] [--out carpeta]
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.geometry.coords import cv_to_three
from app.geometry.floor import detect_floor, draw_floor_debug
from app.geometry.moge_runner import load_image, run_moge


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--out", default="debug_out")
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("| # | Foto | Infer (ms) | Piso (ms) | Altura cámara | % piso | Warnings |")
    print("|---|---|---|---|---|---|---|")
    for i, path in enumerate(args.images):
        img = load_image(path)
        r = run_moge(img)
        t0 = time.perf_counter()
        normals = cv_to_three(r.normal) if r.normal is not None else None
        floor = detect_floor(cv_to_three(r.points), r.mask, normals)
        floor_ms = round((time.perf_counter() - t0) * 1000)
        debug = draw_floor_debug(np.asarray(img), floor)
        Image.fromarray(debug).save(out_dir / f"debug_{i:02d}.jpg", quality=88)
        height = f"{floor.d:.2f} m" if floor.found else "—"
        print(f"| {i:02d} | {Path(path).name} | {r.infer_ms} | {floor_ms} | {height} | "
              f"{floor.inlier_ratio:.0%} | {', '.join(floor.warnings) or '—'} |")


if __name__ == "__main__":
    main()
