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
    # V3 — widened head to include face; tightened leg bboxes below torso bottom
    # to eliminate tabard-pixel cross-contamination.
    'cape':             {'bbox': (180, 260, 425, 730), 'pivot_full': (400, 290)},
    'back_thigh':       {'bbox': (410, 635, 500, 780), 'pivot_full': (455, 640)},
    'back_shin':        {'bbox': (415, 760, 515, 925), 'pivot_full': (465, 770)},
    # Back arm: just the shield area (won't animate separately — stays glued to torso)
    'back_forearm':     {'bbox': (540, 290, 750, 535), 'pivot_full': (575, 310)},
    'torso':            {'bbox': (390, 295, 565, 640), 'pivot_full': (480, 630)},
    'head':             {'bbox': (290, 80, 645, 330), 'pivot_full': (485, 320)},
    'front_thigh':      {'bbox': (455, 635, 560, 780), 'pivot_full': (505, 640)},
    'front_shin':       {'bbox': (460, 760, 580, 925), 'pivot_full': (510, 770)},
    # Front arm: small region so rotation doesn't drag torso pixels
    'front_upper_arm':  {'bbox': (475, 300, 560, 470), 'pivot_full': (520, 310)},
    'front_forearm':    {'bbox': (460, 460, 580, 580), 'pivot_full': (520, 470)},
    'sword':            {'bbox': (440, 550, 555, 925), 'pivot_full': (505, 560)},
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
    'back_forearm':    'torso',    # shield arm glued to torso, doesn't swing independently
    'torso':           'pelvis',
    'head':            'torso',
    'front_thigh':     'pelvis',
    'front_shin':      'front_thigh',
    'front_upper_arm': 'torso',
    'front_forearm':   'front_upper_arm',
    'sword':           'front_forearm',
}

# Pelvis placed at hip-joint level (where thighs attach).
pelvis_full = (510, 640)

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
