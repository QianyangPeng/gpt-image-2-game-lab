"""Use SAM (Segment Anything) to produce pixel-perfect masks for each body part.

Strategy: I know the approximate center of each body part (from my manual bboxes).
Pass those points to SAM as "positive click" prompts, get back per-part masks.
Apply the mask to the source image, save each part as a clean PNG with tight bbox
+ record the pivot location.
"""
import os
# Force CPU inference — we have CPU-only torch installed.
os.environ['CUDA_VISIBLE_DEVICES'] = ''

import json
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from segment_anything import sam_model_registry, SamPredictor

ROOT = Path(__file__).parent
WEIGHTS = ROOT / 'sam_models' / 'sam_vit_b_01ec64.pth'
SRC = ROOT / 'knight_sideview.png'
OUT = ROOT / 'parts_sam'
OUT.mkdir(exist_ok=True)

print(f'Loading SAM ViT-B from {WEIGHTS}...')
sam = sam_model_registry['vit_b'](checkpoint=str(WEIGHTS))
sam.to('cpu')
predictor = SamPredictor(sam)

print('Loading source image...')
im = Image.open(SRC).convert('RGB')
arr = np.array(im)
predictor.set_image(arr)
print(f'  source: {arr.shape}')

# Part definitions: click points (positive samples) + optional negative samples to
# constrain the mask to a subregion. Each part gets 1-3 click points near its center
# and an optional bounding box to tell SAM "don't go beyond this area."
#
# Coordinate system: full 1024x1024 source image, (x, y) with y-down.
PARTS = {
    'cape':            { 'points': [(280, 450), (330, 550), (240, 620)], 'neg_points': [(480, 500)], 'bbox': (180, 270, 440, 740) },
    'head':            { 'points': [(495, 230), (400, 180), (560, 220)], 'neg_points': [(500, 400)], 'bbox': (290, 75, 660, 340) },
    # Torso: click on breastplate only, negatives on all limbs + shield
    'torso':           {
        'points': [(475, 440), (480, 550), (470, 610)],
        'neg_points': [(650, 420), (310, 400), (480, 700), (510, 360), (520, 530), (425, 380), (440, 500)],
        'bbox': (400, 295, 570, 640),
    },
    # Shield (held by back arm) — focus on the gold-phoenix kite shield
    'back_forearm':    {
        'points': [(650, 380), (680, 430), (620, 450)],
        'neg_points': [(480, 400), (480, 500)],
        'bbox': (545, 290, 750, 540),
    },
    'front_upper_arm': {
        'points': [(520, 340), (530, 420)],
        'neg_points': [(475, 400), (475, 500), (475, 300), (560, 500)],
        'bbox': (480, 305, 570, 470),
    },
    'front_forearm':   {
        'points': [(515, 510), (520, 540)],
        'neg_points': [(460, 500), (570, 500), (480, 600), (480, 440)],
        'bbox': (460, 470, 575, 580),
    },
    # Sword: blade only — click on the blue blade in the clear zone (above legs, y<625)
    'sword':           {
        'points': [(490, 590), (495, 605), (480, 570)],
        'neg_points': [(510, 650), (470, 650), (495, 720)],
        'bbox': (440, 545, 540, 645),
    },
    'front_thigh':     {
        'points': [(515, 690), (520, 720)],
        'neg_points': [(470, 690), (480, 600), (520, 820)],
        'bbox': (460, 640, 570, 770),
    },
    'back_thigh':      {
        'points': [(455, 690), (445, 720)],
        'neg_points': [(510, 695), (480, 600), (460, 820)],
        'bbox': (408, 640, 505, 770),
    },
    'front_shin':      {
        'points': [(520, 830), (525, 900)],
        'neg_points': [(470, 840), (520, 720)],
        'bbox': (465, 770, 585, 925),
    },
    'back_shin':       {
        'points': [(465, 830), (470, 900)],
        'neg_points': [(520, 840), (465, 720)],
        'bbox': (415, 770, 520, 925),
    },
}

def run_part(name, spec):
    print(f'  {name}...')
    points = np.array(spec['points'], dtype=np.float32)
    labels = np.ones(len(points), dtype=np.int32)
    neg = spec.get('neg_points', [])
    if neg:
        points = np.concatenate([points, np.array(neg, dtype=np.float32)])
        labels = np.concatenate([labels, np.zeros(len(neg), dtype=np.int32)])
    bbox = spec.get('bbox')
    box = np.array(bbox, dtype=np.float32) if bbox else None

    masks, scores, _ = predictor.predict(
        point_coords=points,
        point_labels=labels,
        box=box,
        multimask_output=True,
    )
    # Pick the highest-scoring mask
    best_idx = int(np.argmax(scores))
    mask = masks[best_idx]
    print(f'    score={scores[best_idx]:.3f}, mask area={mask.sum()} px')
    return mask


part_info = {}
for name, spec in PARTS.items():
    mask = run_part(name, spec)

    # Build RGBA using mask as alpha
    rgba = np.concatenate([arr, mask.astype(np.uint8)[:, :, None] * 255], axis=2)
    # Find tight bbox of the mask
    ys, xs = np.where(mask)
    if len(ys) == 0:
        print(f'    WARNING: empty mask for {name}')
        continue
    y0, y1 = ys.min(), ys.max() + 1
    x0, x1 = xs.min(), xs.max() + 1
    pad = 2
    y0 = max(0, y0 - pad); y1 = min(arr.shape[0], y1 + pad)
    x0 = max(0, x0 - pad); x1 = min(arr.shape[1], x1 + pad)

    crop = rgba[y0:y1, x0:x1]
    Image.fromarray(crop).save(OUT / f'{name}.png')
    part_info[name] = {
        'bbox_full': [int(x0), int(y0), int(x1), int(y1)],
        'size': [int(x1-x0), int(y1-y0)],
    }

print('\nDone. Writing mask metadata.')
(OUT / 'parts_meta.json').write_text(json.dumps(part_info, indent=2))
print('Saved to', OUT)
