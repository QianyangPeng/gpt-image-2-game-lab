"""Split the 3x3 asset_sheet into 9 individual part PNGs with chroma-keyed alpha.

Each cell is ~512x512 in a 1536x1536 sheet. We find each part's tight bbox inside
its cell via chroma-key + connected-component projection, then save trimmed PNGs.
"""
import sys
import json
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'pipeline'))
from chroma_key import strip_magenta

ROOT = Path(__file__).parent
SHEET = ROOT / 'asset_sheet.png'
OUT = ROOT / 'parts_e1'
OUT.mkdir(exist_ok=True)

# Row-major labels per E1 prompt order
NAMES = [
    ['head',        'torso',        'cape'],
    ['upper_arm',   'forearm',      'sword'],
    ['thigh',       'shin',         'shield'],
]

im = Image.open(SHEET).convert('RGB')
W, H = im.size
print(f'Sheet: {W}x{H}')

# Split into 3x3 equal cells, then trim each by mask bbox
cell_w = W // 3
cell_h = H // 3
meta = {}

for row in range(3):
    for col in range(3):
        name = NAMES[row][col]
        cx0, cy0 = col * cell_w, row * cell_h
        cx1, cy1 = cx0 + cell_w, cy0 + cell_h
        cell = im.crop((cx0, cy0, cx1, cy1))
        keyed = strip_magenta(cell, tolerance=60)
        arr = np.array(keyed)
        alpha = arr[:, :, 3]
        ys, xs = np.where(alpha > 0)
        if len(ys) == 0:
            print(f'  {name}: empty cell, skipping')
            continue
        pad = 4
        y0 = max(0, ys.min() - pad); y1 = min(cell_h, ys.max() + 1 + pad)
        x0 = max(0, xs.min() - pad); x1 = min(cell_w, xs.max() + 1 + pad)
        cropped = keyed.crop((x0, y0, x1, y1))
        cropped.save(OUT / f'{name}.png')
        meta[name] = {
            'size': [int(x1 - x0), int(y1 - y0)],
            'cell': [cx0, cy0, cx1, cy1],
            'bbox_in_cell': [int(x0), int(y0), int(x1), int(y1)],
        }
        print(f'  {name}: {x1-x0}x{y1-y0}')

(OUT / 'meta.json').write_text(json.dumps(meta, indent=2))
print(f'\nWrote {len(meta)} parts to {OUT}')
