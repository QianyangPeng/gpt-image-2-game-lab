"""Chroma-key remover: strips magenta (#FF00FF) background to alpha=0.

Usage: python chroma_key.py <input_dir_or_file> [--out <output_dir>]

Places cleaned PNGs in <out> (default: same-dir + '_alpha' suffix).
"""
import sys
import argparse
from pathlib import Path

from PIL import Image
import numpy as np


def strip_magenta(im: Image.Image, tolerance: int = 60) -> Image.Image:
    """Replace pixels that are close to pure magenta (#FF00FF) with transparency.

    Uses a distance-in-RGB-space threshold. Keeps pixels with noticeable green
    content (character stays solid), kills pixels that are near-magenta.
    Also feathers edges via an alpha gradient within the tolerance band.
    """
    im = im.convert('RGBA')
    arr = np.array(im)
    r = arr[:, :, 0].astype(int)
    g = arr[:, :, 1].astype(int)
    b = arr[:, :, 2].astype(int)

    # distance to #FF00FF in a weighted way: penalize low green, high red+blue
    # d = 0 means exactly magenta, d = big means far from magenta
    d = np.sqrt((255 - r) ** 2 + g ** 2 + (255 - b) ** 2)

    alpha = np.where(d <= tolerance, 0, 255).astype(np.uint8)
    # Feather: within tolerance..tolerance+40 ramp alpha smoothly
    band_hi = tolerance + 40
    band_mask = (d > tolerance) & (d < band_hi)
    ramp = ((d - tolerance) / 40 * 255).clip(0, 255).astype(np.uint8)
    alpha = np.where(band_mask, ramp, alpha)

    arr[:, :, 3] = alpha

    # Zero out RGB in fully transparent pixels to prevent magenta fringing.
    fully_transparent = alpha == 0
    arr[fully_transparent, 0] = 0
    arr[fully_transparent, 1] = 0
    arr[fully_transparent, 2] = 0

    return Image.fromarray(arr, mode='RGBA')


def trim_transparent(im: Image.Image, pad: int = 4) -> Image.Image:
    """Crop to the tight bounding box of non-transparent pixels (+pad)."""
    arr = np.array(im)
    alpha = arr[:, :, 3]
    rows = alpha.any(axis=1).nonzero()[0]
    cols = alpha.any(axis=0).nonzero()[0]
    if len(rows) == 0 or len(cols) == 0:
        return im
    y0 = max(0, rows[0] - pad)
    y1 = min(im.height, rows[-1] + 1 + pad)
    x0 = max(0, cols[0] - pad)
    x1 = min(im.width, cols[-1] + 1 + pad)
    return im.crop((x0, y0, x1, y1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input', help='Input file or directory')
    ap.add_argument('--out', help='Output directory (default: <input>_alpha)')
    ap.add_argument('--tolerance', type=int, default=60, help='RGB distance to magenta')
    ap.add_argument('--no-trim', action='store_true', help='Skip bbox crop')
    args = ap.parse_args()

    inp = Path(args.input)
    if inp.is_file():
        files = [inp]
        out_dir = Path(args.out) if args.out else inp.parent.parent / (inp.parent.name + '_alpha')
    else:
        files = sorted(inp.glob('*.png'))
        out_dir = Path(args.out) if args.out else inp.parent / (inp.name + '_alpha')
    out_dir.mkdir(parents=True, exist_ok=True)

    for f in files:
        im = Image.open(f)
        out = strip_magenta(im, tolerance=args.tolerance)
        if not args.no_trim:
            out = trim_transparent(out)
        out_path = out_dir / f.name
        out.save(out_path)
        print(f'  {f.name}: {im.size} -> {out.size}')

    print(f'\nWrote {len(files)} files to {out_dir}')


if __name__ == '__main__':
    main()
