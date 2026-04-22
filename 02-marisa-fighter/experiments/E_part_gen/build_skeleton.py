"""Build a skeleton JSON from the E1 parts.

Pivots are chosen by hand — each part's attachment-to-parent point in its own
local coordinate space. This is analogous to what a Spine rigger does by eye.

Key insight vs D: parts are CLEAN — pivots can be at natural joint locations
(e.g., top of upper_arm = shoulder = (width/2, 0)) without worrying about
neighbor-pixel contamination.
"""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).parent
PARTS_DIR = ROOT / 'parts_e1'
OUT = ROOT / 'skeleton_e.json'

# Load part sizes
def size_of(name):
    im = Image.open(PARTS_DIR / f'{name}.png')
    return im.size

# For each bone: parent, offset (from parent origin to this bone's origin in parent's coords),
# pivot (this bone's origin in its own sprite's local coords), z.
#
# Virtual "pelvis" is the root — no sprite, just the reference point for hip+torso.
# Lengths in pixels within each sprite's own frame.

def pivot_bottomCenter(name, offset_from_bottom=5):
    w, h = size_of(name)
    return [w // 2, h - offset_from_bottom]

def pivot_topCenter(name, offset_from_top=5):
    w, h = size_of(name)
    return [w // 2, offset_from_top]

def pivot_center(name):
    w, h = size_of(name)
    return [w // 2, h // 2]


# Sprite dimensions (for reference)
sizes = {n: size_of(n) for n in ['head', 'torso', 'cape', 'upper_arm', 'forearm', 'sword', 'thigh', 'shin', 'shield']}
for n, s in sizes.items():
    print(f'  {n}: {s[0]}x{s[1]}')

# TORSO: pivot at bottom-center = pelvis attachment point
torso_w, torso_h = sizes['torso']
torso_pivot = [torso_w // 2, torso_h - 10]
# HEAD: pivot at neck stub (bottom center of head sprite)
head_w, head_h = sizes['head']
head_pivot = [int(head_w * 0.55), head_h - 15]  # slight offset — head is side-profile with face on right
# CAPE: pivot at top (attachment to back of torso)
cape_w, cape_h = sizes['cape']
cape_pivot = [cape_w // 2, 10]
# UPPER_ARM: pivot at top (shoulder)
ua_w, ua_h = sizes['upper_arm']
ua_pivot = [ua_w // 2, 10]
# FOREARM: pivot at top (elbow)
fa_w, fa_h = sizes['forearm']
fa_pivot = [fa_w // 2, 10]
# SWORD: pivot at top (grip area) — sword hangs from grip
sw_w, sw_h = sizes['sword']
sw_pivot = [sw_w // 2, int(sw_h * 0.15)]   # slightly below top so grip is at the pivot
# THIGH: pivot at top (hip)
th_w, th_h = sizes['thigh']
th_pivot = [th_w // 2, 10]
# SHIN: pivot at top (knee)
sh_w, sh_h = sizes['shin']
sh_pivot = [sh_w // 2, 10]
# SHIELD: pivot at center-left (where gauntlet grips the inside)
sl_w, sl_h = sizes['shield']
sl_pivot = [int(sl_w * 0.35), int(sl_h * 0.5)]

# Skeleton — all offsets are FROM PARENT's origin TO THIS BONE's origin, in parent's local coords.
skeleton = [
    # Virtual root
    {'name': 'pelvis', 'parent': None, 'offset': [0, 0], 'pivot': [0, 0], 'sprite': None, 'z': 2},

    # Torso hangs from pelvis; its pivot is at its bottom. So offset_from_pelvis to torso_origin = 0,0
    # (torso origin is at pelvis origin). The sprite is drawn with its pivot there, so torso extends
    # UPWARD from pelvis.
    {'name': 'torso', 'parent': 'pelvis', 'offset': [0, 0], 'pivot': torso_pivot,
     'sprite': 'torso', 'z': 3},

    # Head attaches at the top of the torso. Top of torso in torso-local = [torso_w/2, 15] (with
    # small overlap). Offset from torso.origin (which is torso's pivot = bottom) to head origin:
    # [0 (centered), -torso_h + small_overlap].
    {'name': 'head', 'parent': 'torso', 'offset': [0, -torso_h + 25], 'pivot': head_pivot,
     'sprite': 'head', 'z': 4},

    # Cape from upper back of torso — offset upward and slightly back.
    {'name': 'cape', 'parent': 'torso', 'offset': [-20, -torso_h + 60], 'pivot': cape_pivot,
     'sprite': 'cape', 'z': 0},

    # FRONT ARM: shoulder is at torso's near-camera pauldron (rightish side of torso sprite).
    # Approximate: torso top, ~20 px right of center.
    {'name': 'front_upper_arm', 'parent': 'torso', 'offset': [15, -torso_h + 40], 'pivot': ua_pivot,
     'sprite': 'upper_arm', 'z': 6},
    {'name': 'front_forearm', 'parent': 'front_upper_arm', 'offset': [0, ua_h - 25], 'pivot': fa_pivot,
     'sprite': 'forearm', 'z': 6},
    {'name': 'sword', 'parent': 'front_forearm', 'offset': [0, fa_h - 20], 'pivot': sw_pivot,
     'sprite': 'sword', 'z': 6},

    # BACK ARM (reuses upper_arm + forearm + shield)
    {'name': 'back_upper_arm', 'parent': 'torso', 'offset': [-15, -torso_h + 40], 'pivot': ua_pivot,
     'sprite': 'upper_arm', 'z': 1},
    {'name': 'back_forearm', 'parent': 'back_upper_arm', 'offset': [0, ua_h - 25], 'pivot': fa_pivot,
     'sprite': 'forearm', 'z': 1},
    {'name': 'shield', 'parent': 'back_forearm', 'offset': [-10, fa_h // 2], 'pivot': sl_pivot,
     'sprite': 'shield', 'z': 1},

    # LEGS: two pairs, both reuse the same thigh/shin sprites.
    {'name': 'front_thigh', 'parent': 'pelvis', 'offset': [10, 0], 'pivot': th_pivot,
     'sprite': 'thigh', 'z': 5},
    {'name': 'front_shin', 'parent': 'front_thigh', 'offset': [0, th_h - 20], 'pivot': sh_pivot,
     'sprite': 'shin', 'z': 5},
    {'name': 'back_thigh', 'parent': 'pelvis', 'offset': [-10, 0], 'pivot': th_pivot,
     'sprite': 'thigh', 'z': 1},
    {'name': 'back_shin', 'parent': 'back_thigh', 'offset': [0, th_h - 20], 'pivot': sh_pivot,
     'sprite': 'shin', 'z': 1},
]

OUT.write_text(json.dumps({
    'skeleton': skeleton,
    'parts_dir': 'experiments/E_part_gen/parts_e1',
}, indent=2))
print(f'\nSaved skeleton_e.json ({len(skeleton)} bones)')
