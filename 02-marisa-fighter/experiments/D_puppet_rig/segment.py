"""Manually segment the side-view knight into body-part sprites for the puppet rig.

Approach: chroma-key the magenta bg, then define hand-picked bounding boxes for
each body part. For each part, save a PNG + record its pivot (attachment point
to parent) in bone.json.

This is a one-off script — the numbers below were measured from the actual
generated image (knight_sideview.png, 1024x1024).
"""
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'pipeline'))
from chroma_key import strip_magenta

ROOT = Path(__file__).parent
SRC = ROOT / 'knight_sideview.png'
OUT = ROOT / 'parts'
OUT.mkdir(exist_ok=True)

# First, inspect the character bbox so we know what we're working with
im = strip_magenta(Image.open(SRC))
arr = np.array(im)
alpha = arr[:, :, 3]
rows = alpha.any(axis=1).nonzero()[0]
cols = alpha.any(axis=0).nonzero()[0]
print(f'Character tight bbox: x={cols[0]}..{cols[-1]} y={rows[0]}..{rows[-1]}')
print(f'  size: {cols[-1] - cols[0]} wide x {rows[-1] - rows[0]} tall')

# Save full chroma-keyed for reference
im.save(OUT / 'full.png')

# Part boxes: (x0, y0, x1, y1) in source 1024x1024 image.
# These are HAND-PICKED to isolate each part visually.
# pivot is in SPRITE-LOCAL coordinates (relative to the extracted sprite's top-left).
# For a bone, pivot = attachment point to parent in THIS sprite's space.
PARTS = {
    # Remeasured from knight_sideview.png (1024x1024).
    # Character bbox ~ x=186..742, y=91..927.
    'cape':             {'bbox': (186, 270, 420, 720), 'pivot_full': (400, 300)},
    'back_thigh':       {'bbox': (410, 615, 495, 770), 'pivot_full': (455, 620)},
    'back_shin':        {'bbox': (415, 755, 510, 925), 'pivot_full': (460, 765)},
    'back_upper_arm':   {'bbox': (540, 310, 620, 460), 'pivot_full': (575, 320)},
    'back_forearm':     {'bbox': (560, 310, 745, 525), 'pivot_full': (585, 320)},  # includes shield
    'torso':            {'bbox': (395, 305, 560, 625), 'pivot_full': (480, 620)},
    'head':             {'bbox': (305, 91, 545, 320), 'pivot_full': (465, 310)},
    'front_thigh':      {'bbox': (455, 615, 560, 770), 'pivot_full': (505, 620)},
    'front_shin':       {'bbox': (460, 755, 575, 925), 'pivot_full': (510, 765)},
    'front_upper_arm':  {'bbox': (475, 310, 565, 475), 'pivot_full': (520, 320)},
    'front_forearm':    {'bbox': (465, 460, 575, 575), 'pivot_full': (520, 470)},
    'sword':            {'bbox': (440, 550, 555, 925), 'pivot_full': (510, 570)},
}


def extract_part(name, bbox, pivot_full):
    """Extract rectangular region and compute local pivot."""
    x0, y0, x1, y1 = bbox
    crop = im.crop((x0, y0, x1, y1))
    local_pivot = (pivot_full[0] - x0, pivot_full[1] - y0)
    crop.save(OUT / f'{name}.png')
    print(f'  {name}: {x1-x0}x{y1-y0}, pivot_local={local_pivot}')
    return {
        'size': [x1 - x0, y1 - y0],
        'pivot': list(local_pivot),
        'bbox_full': list(bbox),
        'pivot_full': list(pivot_full),
    }


metadata = {}
for name, spec in PARTS.items():
    metadata[name] = extract_part(name, spec['bbox'], spec['pivot_full'])

# Also compute REST-POSE OFFSETS for bones so the rig knows where to place each in its parent space.
# We'll choose the parent's pivot as origin, so offset[child] = pivot_full[child] - pivot_full[parent].
HIERARCHY = {
    'cape':            'torso',
    'back_thigh':      'pelvis',
    'back_shin':       'back_thigh',
    'back_upper_arm':  'torso',
    'back_forearm':    'back_upper_arm',
    'torso':           'pelvis',
    'head':            'torso',
    'front_thigh':     'pelvis',
    'front_shin':      'front_thigh',
    'front_upper_arm': 'torso',
    'front_forearm':   'front_upper_arm',
    'sword':           'front_forearm',
}

# pelvis is a virtual root bone — no sprite. Positioned at torso's pivot_full minus a small offset.
# Actually use torso's bottom-center as pelvis.
pelvis_full = (510, 640)   # midpoint between the two hips

skeleton = []
for part_name, part_meta in metadata.items():
    parent = HIERARCHY.get(part_name, None)
    parent_pivot = pelvis_full if parent == 'pelvis' else (metadata[parent]['pivot_full'] if parent else (0, 0))
    offset = [part_meta['pivot_full'][0] - parent_pivot[0],
              part_meta['pivot_full'][1] - parent_pivot[1]]
    skeleton.append({
        'name': part_name,
        'parent': parent,
        'offset': offset,
        'pivot': part_meta['pivot'],
        'sprite_size': part_meta['size'],
    })

# Prepend pelvis as virtual root
skeleton.insert(0, {
    'name': 'pelvis',
    'parent': None,
    'offset': [0, 0],
    'pivot': [0, 0],
    'sprite_size': None,
})

# Depth: back layers first (z=0), front layers later (z=higher)
Z = {
    'cape': 0,
    'back_thigh': 1, 'back_shin': 1, 'back_upper_arm': 1, 'back_forearm': 1,
    'pelvis': 2, 'torso': 3, 'head': 4,
    'front_thigh': 5, 'front_shin': 5,
    'front_upper_arm': 6, 'front_forearm': 6, 'sword': 6,
}
for b in skeleton:
    b['z'] = Z.get(b['name'], 2)

(ROOT / 'skeleton.json').write_text(json.dumps({
    'skeleton': skeleton,
    'pelvis_anchor': list(pelvis_full),
}, indent=2))
print(f'\nWrote {len(metadata)} parts + skeleton.json')
