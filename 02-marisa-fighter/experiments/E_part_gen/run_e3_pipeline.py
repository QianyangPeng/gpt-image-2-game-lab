"""End-to-end pipeline for E3 parts: detect joints + build skeleton.

Outputs:
  joints_e3.json
  skeleton_e3.json
"""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).parent
PARTS_DIR = ROOT / 'parts_e3'


def load_mask(name):
    im = Image.open(PARTS_DIR / f'{name}.png').convert('RGBA')
    arr = np.array(im)
    return arr[:, :, 3] > 0, im.size


def centroid_band(mask, y0, y1):
    band = mask[y0:y1]
    ys, xs = np.where(band)
    if len(xs) == 0: return None
    return (int(xs.mean()), int(ys.mean() + y0))


def detect_vertical(name, top_frac=0.12, bot_frac=0.12):
    mask, (w, h) = load_mask(name)
    ys, xs = np.where(mask)
    if len(ys) == 0: return None
    top_y, bot_y = int(ys.min()), int(ys.max())
    ht = bot_y - top_y
    top = centroid_band(mask, top_y, top_y + max(3, int(ht * top_frac)))
    bot = centroid_band(mask, bot_y - max(3, int(ht * bot_frac)), bot_y + 1)
    def safe(pt):
        if pt is None: return None
        x, y = pt
        if x < w * 0.1 or x > w * 0.9: x = w // 2
        return (int(x), int(y))
    return {'top': safe(top), 'bottom': safe(bot), 'size': [w, h]}


def detect_torso():
    mask, (w, h) = load_mask('torso')
    ys, xs = np.where(mask)
    top_y, bot_y = int(ys.min()), int(ys.max())
    ht = bot_y - top_y
    neck = centroid_band(mask, top_y, top_y + max(3, int(ht * 0.06)))
    pelvis = centroid_band(mask, bot_y - max(3, int(ht * 0.06)), bot_y + 1)
    # Widest row in upper 25% = shoulder line
    upper_end = top_y + int(ht * 0.25)
    widest = (top_y, 0, 0, 0)
    for y in range(top_y, upper_end):
        row = mask[y].nonzero()[0]
        if len(row) and (row[-1] - row[0]) > widest[3]:
            widest = (y, int(row[0]), int(row[-1]), int(row[-1] - row[0]))
    shoulder_y, lx, rx, _ = widest
    return {
        'top': neck, 'bottom': pelvis,
        'left_shoulder': (lx, shoulder_y),
        'right_shoulder': (rx, shoulder_y),
        'size': [w, h],
    }


def detect_head():
    mask, (w, h) = load_mask('head')
    ys, xs = np.where(mask)
    top_y, bot_y = int(ys.min()), int(ys.max())
    ht = bot_y - top_y
    # Neck stub is narrower than the head. Find the row near bottom where mask
    # width is LOCALLY MINIMAL (the neck pinch).
    row_widths = []
    for y in range(bot_y - int(ht * 0.35), bot_y + 1):
        row = mask[y].nonzero()[0]
        if len(row):
            row_widths.append((y, int(row[0]), int(row[-1]), int(row[-1] - row[0])))
    if row_widths:
        narrow = min(row_widths, key=lambda r: r[3])
        neck = ((narrow[1] + narrow[2]) // 2, narrow[0])
    else:
        neck = centroid_band(mask, bot_y - 5, bot_y + 1)
    return {'top': neck, 'bottom': neck, 'size': [w, h]}


def detect_sword():
    mask, (w, h) = load_mask('sword')
    ys, xs = np.where(mask)
    top_y, bot_y = int(ys.min()), int(ys.max())
    # Crossguard = widest row in top 30%
    upper = top_y + int((bot_y - top_y) * 0.30)
    widest = (top_y, 0)
    for y in range(top_y, upper):
        row = mask[y].nonzero()[0]
        if len(row) and (row[-1] - row[0]) > widest[1]:
            widest = (y, int(row[-1] - row[0]))
    cross_y = widest[0]
    row = mask[cross_y].nonzero()[0]
    grip_x = int(row.mean()) if len(row) else w // 2
    return {'top': (grip_x, cross_y), 'bottom': (grip_x, bot_y), 'size': [w, h]}


def detect_shield():
    mask, (w, h) = load_mask('shield')
    ys, xs = np.where(mask)
    # Grip = left-center of shield (held by arm from the back)
    return {'top': (int(w * 0.25), int(h * 0.45)), 'bottom': (int(w * 0.25), int(h * 0.45)), 'size': [w, h]}


joints = {
    'head':      detect_head(),
    'torso':     detect_torso(),
    'cape':      detect_vertical('cape', top_frac=0.05, bot_frac=0.15),
    'upper_arm': detect_vertical('upper_arm'),
    'forearm':   detect_vertical('forearm'),
    'sword':     detect_sword(),
    'thigh':     detect_vertical('thigh'),
    'shin':      detect_vertical('shin'),
    'shield':    detect_shield(),
}
for n, j in joints.items():
    print(f'  {n}: {j}')


class NumpyEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (np.integer,)): return int(o)
        if isinstance(o, (np.floating,)): return float(o)
        return super().default(o)


# Manual overrides for parts where auto-detection is confused by asymmetric stubs
MANUAL = {
    # head: neck is on right side of sprite (face side), not left (pigtail side)
    'head':  {'top': (290, 380), 'bottom': (290, 380)},
    # thigh: tabard overlap on one side; center the hip
    'thigh': {'top': (175, 20), 'bottom': (175, 410)},
    # shield: grip moved slightly
    'shield': {'top': (140, 240), 'bottom': (140, 240)},
}
for n, ov in MANUAL.items():
    if n in joints: joints[n].update(ov)
    print(f'  [override] {n}: {ov}')

(ROOT / 'joints_e3.json').write_text(json.dumps(joints, indent=2, cls=NumpyEncoder))
print('\nSaved joints_e3.json')


# --- Build skeleton_e3.json ---
TARGET_H = 800
TARGET = {
    'head':      TARGET_H * 0.20,
    'torso':     TARGET_H * 0.38,
    'cape':      TARGET_H * 0.47,
    'upper_arm': TARGET_H * 0.22,
    'forearm':   TARGET_H * 0.22,
    'sword':     TARGET_H * 0.52,
    'thigh':     TARGET_H * 0.22,
    'shin':      TARGET_H * 0.22,
    'shield':    TARGET_H * 0.28,
}
sprite_scales = {}
for name, joint in joints.items():
    sprite_scales[name] = TARGET[name] / joint['size'][1]
    print(f'  {name} scale: {sprite_scales[name]:.3f}')


def scaled_pt(pt, s):
    return [int(pt[0] * s), int(pt[1] * s)]


def offset_parent_joint(parent_sprite, parent_joint_key, parent_pivot_key):
    s = sprite_scales[parent_sprite]
    pj = scaled_pt(joints[parent_sprite][parent_joint_key], s)
    pp = scaled_pt(joints[parent_sprite][parent_pivot_key], s)
    return [pj[0] - pp[0], pj[1] - pp[1]]


skeleton = [
    {'name': 'pelvis', 'parent': None, 'sprite': None, 'pivot': [0, 0], 'offset': [0, 0], 'z': 2},
]


def add_bone(name, parent, sprite, pivot_key, offset, z):
    s = sprite_scales[sprite]
    pivot = scaled_pt(joints[sprite][pivot_key], s)
    size = [int(joints[sprite]['size'][0] * s), int(joints[sprite]['size'][1] * s)]
    skeleton.append({
        'name': name, 'parent': parent, 'sprite': sprite,
        'pivot': pivot, 'offset': offset, 'sprite_size': size,
        'sprite_scale': s, 'z': z,
    })


add_bone('torso', 'pelvis', 'torso', 'bottom', [0, 0], 3)
add_bone('head', 'torso', 'head', 'bottom',
         offset_parent_joint('torso', 'top', 'bottom'), 4)

cape_offset = offset_parent_joint('torso', 'top', 'bottom')
cape_offset[1] += int(TARGET_H * 0.04)
cape_offset[0] -= int(TARGET_H * 0.015)
add_bone('cape', 'torso', 'cape', 'top', cape_offset, 0)

add_bone('front_upper_arm', 'torso', 'upper_arm', 'top',
         offset_parent_joint('torso', 'right_shoulder', 'bottom'), 6)
add_bone('front_forearm', 'front_upper_arm', 'forearm', 'top',
         offset_parent_joint('upper_arm', 'bottom', 'top'), 6)
add_bone('sword', 'front_forearm', 'sword', 'top',
         offset_parent_joint('forearm', 'bottom', 'top'), 6)

add_bone('back_upper_arm', 'torso', 'upper_arm', 'top',
         offset_parent_joint('torso', 'left_shoulder', 'bottom'), 1)
add_bone('back_forearm', 'back_upper_arm', 'forearm', 'top',
         offset_parent_joint('upper_arm', 'bottom', 'top'), 1)
add_bone('shield', 'back_forearm', 'shield', 'top',
         offset_parent_joint('forearm', 'bottom', 'top'), 1)

HIP_HALF = int(TARGET_H * 0.035)
add_bone('front_thigh', 'pelvis', 'thigh', 'top', [HIP_HALF, 0], 5)
add_bone('front_shin', 'front_thigh', 'shin', 'top',
         offset_parent_joint('thigh', 'bottom', 'top'), 5)
add_bone('back_thigh', 'pelvis', 'thigh', 'top', [-HIP_HALF, 0], 1)
add_bone('back_shin', 'back_thigh', 'shin', 'top',
         offset_parent_joint('thigh', 'bottom', 'top'), 1)

(ROOT / 'skeleton_e3.json').write_text(json.dumps({
    'skeleton': skeleton,
    'parts_dir': 'experiments/E_part_gen/parts_e3',
    'scales': sprite_scales,
}, indent=2, cls=NumpyEncoder))
print(f'\nSaved skeleton_e3.json with {len(skeleton)} bones')
