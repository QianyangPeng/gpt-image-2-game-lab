"""Convert SAM-extracted parts into a skeleton.json compatible with PuppetRig.

Uses the same pivot_full coordinates as the manual-bbox version. Since SAM-masked
parts have tight bboxes (pixel-perfect), pivot_local = pivot_full - bbox_full_start.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
SAM_META = ROOT / 'parts_sam' / 'parts_meta.json'
OUT = ROOT / 'skeleton_sam.json'

# Pivot locations (where each bone's origin is, in full-image coords).
# These are the same rest-pose pivots as the manual-bbox version.
PIVOTS_FULL = {
    'cape':            (400, 290),
    'head':            (485, 320),
    'torso':           (480, 630),
    'back_forearm':    (575, 310),  # shield arm's shoulder attach point
    'front_upper_arm': (520, 310),
    'front_forearm':   (520, 470),
    'sword':           (495, 565),  # sword hilt / grip
    'front_thigh':     (505, 640),
    'back_thigh':      (455, 640),
    'front_shin':      (510, 770),
    'back_shin':       (465, 770),
}

HIERARCHY = {
    'cape':            'torso',
    'back_thigh':      'pelvis',
    'back_shin':       'back_thigh',
    'back_forearm':    'torso',
    'torso':           'pelvis',
    'head':            'torso',
    'front_thigh':     'pelvis',
    'front_shin':      'front_thigh',
    'front_upper_arm': 'torso',
    'front_forearm':   'front_upper_arm',
    'sword':           'front_forearm',
}

Z = {
    'cape': 0,
    'back_thigh': 1, 'back_shin': 1, 'back_forearm': 1,
    'pelvis': 2, 'torso': 3, 'head': 4,
    'front_thigh': 5, 'front_shin': 5,
    'front_upper_arm': 6, 'front_forearm': 6, 'sword': 6,
}

PELVIS_FULL = (510, 640)

meta = json.loads(SAM_META.read_text())
skeleton = [
    {'name': 'pelvis', 'parent': None, 'offset': [0, 0], 'pivot': [0, 0], 'sprite_size': None, 'z': Z['pelvis']}
]

for name, info in meta.items():
    bbox_full = info['bbox_full']   # [x0, y0, x1, y1]
    pivot_full = PIVOTS_FULL.get(name)
    if pivot_full is None:
        print(f'  skip {name}: no pivot defined')
        continue
    pivot_local = [pivot_full[0] - bbox_full[0], pivot_full[1] - bbox_full[1]]
    parent = HIERARCHY.get(name)
    if parent == 'pelvis':
        parent_pivot = PELVIS_FULL
    elif parent:
        parent_pivot = PIVOTS_FULL[parent]
    else:
        parent_pivot = (0, 0)
    offset = [pivot_full[0] - parent_pivot[0], pivot_full[1] - parent_pivot[1]]
    skeleton.append({
        'name': name, 'parent': parent, 'offset': offset,
        'pivot': pivot_local,
        'sprite_size': info['size'],
        'z': Z.get(name, 2),
    })
    print(f'  {name}: bbox={bbox_full} pivot_local={pivot_local} offset_from_{parent}={offset}')

OUT.write_text(json.dumps({'skeleton': skeleton, 'pelvis_anchor': list(PELVIS_FULL)}, indent=2))
print(f'\nSaved to {OUT}')
