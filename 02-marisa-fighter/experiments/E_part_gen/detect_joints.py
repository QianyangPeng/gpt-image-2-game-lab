"""Auto-detect joint keypoints on each part from pixel geometry.

For each part's alpha mask we compute:
  - 'top':    the attachment point at the top (shoulder/hip/neck/etc.)
  - 'bottom': the attachment point at the bottom (elbow/knee/wrist/etc.)
  - Extra per-part keypoints where needed (torso has two shoulder stubs).

Method:
  Vertical parts (arm, leg, sword, cape): top = centroid of top 8% of mask rows,
  bottom = centroid of bottom 8%. This handles slight asymmetry from the generator.

  Torso: top = bottom-center of the neck stub area (centroid of top 5% mask),
  bottom = centroid of bottom 5%, plus left/right shoulder stubs detected as
  the local-maximum horizontal extent near the top (rows 5-20% from top).

  Head: bottom = centroid of the bottom 5% (neck).

  Shield: keep for now — pivot at centroid (shield is attached rigidly to arm
  via a fixed offset from hand).

Output: 'joints.json' with each part's keypoints in its LOCAL pixel coords.
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).parent
PARTS_DIR = ROOT / 'parts_e1'
OUT = ROOT / 'joints.json'


def load_mask(name):
    im = Image.open(PARTS_DIR / f'{name}.png').convert('RGBA')
    arr = np.array(im)
    return arr[:, :, 3] > 0, im.size  # mask, (w, h)


def centroid_of_band(mask, y_start, y_end):
    """Return (x, y) centroid of alpha pixels within rows y_start..y_end.
    Result is always a plain-int tuple."""
    band = mask[y_start:y_end]
    ys, xs = np.where(band)
    if len(xs) == 0:
        return None
    return (int(xs.mean()), int(ys.mean() + y_start))


def detect_vertical_part(name, top_band=0.15, bot_band=0.15):
    """For vertically-oriented parts: return {top, bottom} keypoints.
    Uses a larger band (default 15%) for robust centroid; falls back to
    width-center x if the detected x is in the outer 15% of the sprite
    (indicating a tip artifact rather than the joint)."""
    mask, (w, h) = load_mask(name)
    ys, xs = np.where(mask)
    if len(ys) == 0:
        return None
    top_y = ys.min()
    bot_y = ys.max()
    ht = bot_y - top_y
    top_pt = centroid_of_band(mask, top_y, top_y + max(3, int(ht * top_band)))
    bot_pt = centroid_of_band(mask, bot_y - max(3, int(ht * bot_band)), bot_y + 1)
    # Sanity: if x is in outer 10% of sprite, fall back to center-x.
    def safe(pt):
        if pt is None: return None
        x, y = pt
        if x < w * 0.1 or x > w * 0.9: x = w // 2
        return (int(x), int(y))
    return {'top': safe(top_pt), 'bottom': safe(bot_pt), 'size': [w, h]}


def detect_torso(name='torso'):
    """Torso: detect neck-top, pelvis-bottom, and two shoulder stubs."""
    mask, (w, h) = load_mask(name)
    ys, xs = np.where(mask)
    top_y, bot_y = ys.min(), ys.max()
    ht = bot_y - top_y
    neck = centroid_of_band(mask, top_y, top_y + max(1, int(ht * 0.05)))
    pelvis = centroid_of_band(mask, bot_y - max(1, int(ht * 0.05)), bot_y + 1)
    # Shoulder stubs: find the WIDEST row in the upper ~25% of the torso
    # (pauldrons typically stick out to the sides near the top)
    upper_band_end = top_y + int(ht * 0.25)
    row_widths = []
    for y in range(top_y, upper_band_end):
        row = mask[y].nonzero()[0]
        if len(row) > 0:
            row_widths.append((y, row.min(), row.max(), row.max() - row.min()))
    if row_widths:
        # Row with max width = shoulder line
        shoulder_row = max(row_widths, key=lambda r: r[3])
        left_shoulder = (shoulder_row[1], shoulder_row[0])
        right_shoulder = (shoulder_row[2], shoulder_row[0])
    else:
        left_shoulder = right_shoulder = neck
    return {
        'top': neck, 'bottom': pelvis,
        'left_shoulder': left_shoulder, 'right_shoulder': right_shoulder,
        'size': [w, h],
    }


def detect_head(name='head'):
    """Head: bottom = neck attachment. Top doesn't matter for rigging."""
    mask, (w, h) = load_mask(name)
    ys, xs = np.where(mask)
    top_y, bot_y = ys.min(), ys.max()
    ht = bot_y - top_y
    neck = centroid_of_band(mask, bot_y - max(1, int(ht * 0.05)), bot_y + 1)
    return {'top': neck, 'bottom': neck, 'size': [w, h]}


def detect_shield(name='shield'):
    """Shield grip: approximate as centroid of the mask."""
    mask, (w, h) = load_mask(name)
    ys, xs = np.where(mask)
    return {'top': (int(xs.mean()), int(ys.mean())), 'bottom': (int(xs.mean()), int(ys.mean())), 'size': [w, h]}


def detect_sword(name='sword'):
    """Sword: find the crossguard (widest horizontal segment, near the top).
    Grip is just above the crossguard. For our rig we use 'top' = grip and the sword extends DOWN.
    """
    mask, (w, h) = load_mask(name)
    ys, xs = np.where(mask)
    top_y, bot_y = ys.min(), ys.max()
    # Find the widest row in the top 30% — that's the crossguard
    upper = top_y + int((bot_y - top_y) * 0.30)
    row_widths = []
    for y in range(top_y, upper):
        row = mask[y].nonzero()[0]
        if len(row) > 0:
            row_widths.append((y, row.max() - row.min(), int(row.mean())))
    if not row_widths:
        return detect_vertical_part(name)
    crossguard = max(row_widths, key=lambda r: r[1])   # y, width, x_center
    grip = (crossguard[2], crossguard[0])
    # Blade extends down from crossguard
    return {'top': grip, 'bottom': (crossguard[2], bot_y), 'size': [w, h]}


SPEC = {
    'head':        detect_head,
    'torso':       detect_torso,
    'cape':        lambda: detect_vertical_part('cape', top_band=0.04, bot_band=0.2),
    'upper_arm':   lambda: detect_vertical_part('upper_arm'),
    'forearm':     lambda: detect_vertical_part('forearm'),
    'sword':       detect_sword,
    'thigh':       lambda: detect_vertical_part('thigh'),
    'shin':        lambda: detect_vertical_part('shin'),
    'shield':      detect_shield,
}

joints = {}
for name, fn in SPEC.items():
    try:
        result = fn()
        joints[name] = result
        print(f'  {name}: {result}')
    except Exception as e:
        print(f'  {name}: FAILED -- {e}')

# Manual overrides for parts where auto-detection is confused by asymmetric stubs.
# For each, a comment says WHY we override.
MANUAL_OVERRIDES = {
    # head: pigtail pulls centroid left; true neck is at bottom-right of face.
    'head':   {'top': (265, 380), 'bottom': (265, 380)},
    # sword: detection was ~right, but let's align bottom to blade tip center
    'sword':  {'top': (192, 50),  'bottom': (192, 510)},
    # thigh: hip-stub asymmetry; manually centered
    'thigh':  {'top': (186, 15),  'bottom': (186, 460)},
    # forearm: tip of vambrace pulls bottom-centroid to the inside
    'forearm': {'top': (107, 15), 'bottom': (107, 430)},
    # upper_arm: similar
    'upper_arm': {'top': (75, 15), 'bottom': (75, 345)},
    # shield: pivot at grip location, not centroid (grip is roughly mid-right of shield)
    'shield': {'top': (140, 240), 'bottom': (140, 240)},
    # cape: top attach centered
    'cape':   {'top': (256, 10), 'bottom': (256, 500)},
    # shin: center
    'shin':   {'top': (92, 15), 'bottom': (92, 330)},
    # torso overrides: pivot at neck-top-center + pelvis-bottom-center
    'torso':  {'top': (136, 15), 'bottom': (136, 413),
               'left_shoulder': (25, 45), 'right_shoulder': (245, 45)},
}
for name, overrides in MANUAL_OVERRIDES.items():
    if name in joints:
        joints[name].update(overrides)
        print(f'  [override] {name}: {overrides}')

class NumpyEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (np.integer,)): return int(o)
        if isinstance(o, (np.floating,)): return float(o)
        if isinstance(o, np.ndarray): return o.tolist()
        return super().default(o)

OUT.write_text(json.dumps(joints, indent=2, cls=NumpyEncoder))
print(f'\nSaved {OUT}')
