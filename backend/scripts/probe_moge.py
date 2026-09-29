"""Prueba MoGe sobre una o más imágenes: imprime shapes, rangos e intrínsecos y guarda la profundidad.

Uso: uv run python scripts/probe_moge.py <imagen> [<imagen> ...] [--out carpeta]
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.geometry.moge_runner import load_image, run_moge


def depth_png(depth: np.ndarray, mask: np.ndarray) -> Image.Image:
    valid = mask & np.isfinite(depth)
    out = np.zeros(depth.shape, dtype=np.uint8)
    if valid.any():
        lo, hi = np.percentile(depth[valid], [1, 99])
        norm = np.clip((depth - lo) / max(hi - lo, 1e-6), 0, 1)
        out[valid] = (255 * (1 - norm[valid])).astype(np.uint8)  # cerca = claro
    return Image.fromarray(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--out", default="probe_out")
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, path in enumerate(args.images):
        img = load_image(path)
        r = run_moge(img)
        valid = r.mask & np.isfinite(r.points).all(-1)
        pts = r.points[valid]
        k = r.intrinsics
        print(f"\n== {Path(path).name}  original {img.size[0]}x{img.size[1]}")
        print(f"device={r.device} load_ms={r.load_ms} infer_ms={r.infer_ms}")
        print(f"points {r.points.shape} depth {r.depth.shape} mask {r.mask.shape} "
              f"normal {None if r.normal is None else r.normal.shape} valid={valid.mean():.1%}")
        for axis, name in enumerate("xyz"):
            print(f"  {name}: [{pts[:, axis].min():.2f}, {pts[:, axis].max():.2f}] m")
        print(f"  depth: [{r.depth[valid].min():.2f}, {r.depth[valid].max():.2f}] m")
        print(f"  intrinsics fx={k[0, 0]:.4f} fy={k[1, 1]:.4f} cx={k[0, 2]:.4f} cy={k[1, 2]:.4f}")
        fov_y = np.degrees(2 * np.arctan(0.5 / k[1, 1]))
        print(f"  fov_y={fov_y:.1f}°  ({'normalizados' if abs(k[0, 2] - 0.5) < 0.05 else 'en píxeles'})")
        depth_png(r.depth, valid).save(out_dir / f"depth_{i:02d}.png")


if __name__ == "__main__":
    main()
