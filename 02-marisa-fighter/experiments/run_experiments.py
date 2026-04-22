"""Run experiments A and B for walk-cycle animation.

A) Skeleton pose conditioning: Marisa ref + stick-figure skeleton ref -> 4 frames
B) Single-call sprite strip: one 2048x512 generation showing 4 walk frames side-by-side

Output:
  experiments/A_skeleton_cond/walk_1..walk_4.png
  experiments/B_sprite_strip/strip.png      (then split client-side)
"""
import os
import json
import time
import base64
from pathlib import Path

import urllib.request
import urllib.error
import uuid

KEY_PATH = Path(r'C:\Users\qypen\Documents\kelly-coins\server\openai-key.txt')
API_KEY = KEY_PATH.read_text().strip()
OPENAI_ORG = 'org-0g6m9oj8poyjCJgvK9Nn1XSq'
MODEL = 'gpt-image-2'

ROOT = Path(__file__).parent.parent
EXP = Path(__file__).parent

PRICE_TEXT_IN = 5.0
PRICE_IMAGE_IN = 8.0
PRICE_OUTPUT = 30.0


def cost_of(usage):
    if not usage:
        return 0.0
    inp = usage.get('input_tokens_details', {})
    text_in = inp.get('text_tokens', 0)
    image_in = inp.get('image_tokens', 0)
    output_tokens = usage.get('output_tokens', 0)
    return (
        text_in * PRICE_TEXT_IN / 1_000_000
        + image_in * PRICE_IMAGE_IN / 1_000_000
        + output_tokens * PRICE_OUTPUT / 1_000_000
    )


def post_multipart(url, fields, files):
    """files: dict name -> list of (filename, bytes). Uses image[] for multi."""
    boundary = '----b' + uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\n'.encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        parts.append(f'{value}\r\n'.encode())
    for name, items in files.items():
        for filename, content in items:
            parts.append(f'--{boundary}\r\n'.encode())
            parts.append(
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
            )
            parts.append(b'Content-Type: image/png\r\n\r\n')
            parts.append(content)
            parts.append(b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    body = b''.join(parts)
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            'Authorization': f'Bearer {API_KEY}',
            'OpenAI-Organization': OPENAI_ORG,
            'Content-Type': f'multipart/form-data; boundary={boundary}',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors='replace')
        raise RuntimeError(f'HTTP {e.code}: {err[:600]}') from None


def post_json(url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            'Authorization': f'Bearer {API_KEY}',
            'OpenAI-Organization': OPENAI_ORG,
            'Content-Type': 'application/json',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors='replace')
        raise RuntimeError(f'HTTP {e.code}: {err[:600]}') from None


# ---- Experiment A: skeleton-conditioned edit ----

STYLE = (
    "2D pixel-art fighter sprite, Capcom-style, bold clean outlines, limited rich color palette. "
    "Uniform flat bright magenta #FF00FF background covering EVERY pixel that isn't the character. "
    "CHARACTER IDENTITY (MUST preserve exactly from the first reference image): "
    "Marisa Kirisame — blonde hair with a long single braid over her LEFT shoulder, "
    "black pointed witch hat with red ribbon and white band, "
    "sleeveless black witch dress with white frilled apron and large purple bow at waist, "
    "long black puffed sleeves with white cuffs, black knee-high buckle boots, "
    "octagonal brass Mini-Hakkero at right hip, holding a straw broom. "
    "NO TEXT, no UI, no border."
)


def run_A():
    print('=== Experiment A: skeleton-conditioned edits ===')
    ref_char = (ROOT / 'frames' / '01_idle_front_ref.png').read_bytes()
    out_dir = EXP / 'A_skeleton_cond'
    out_dir.mkdir(parents=True, exist_ok=True)
    log = {}
    total_cost = 0
    for i in range(1, 5):
        skel_path = EXP / 'skeletons' / f'walk_{i}.png'
        skel_bytes = skel_path.read_bytes()
        prompt = (
            STYLE
            + f" POSE: place Marisa in the EXACT pose shown in the SECOND reference image (a stick-figure pose diagram). "
            f"The stick-figure shows her in WALK-CYCLE FRAME {i} OF 4, side view facing right. "
            "Match the limb angles, foot positions, and arm positions from the stick-figure diagram precisely. "
            "Render the full character (outfit, braid, broom) onto this pose. "
            "Magenta #FF00FF background everywhere around her."
        )
        t0 = time.time()
        resp = post_multipart(
            'https://api.openai.com/v1/images/edits',
            fields={'model': MODEL, 'prompt': prompt, 'size': '1024x1024', 'quality': 'medium'},
            files={'image[]': [('marisa_ref.png', ref_char), ('skeleton.png', skel_bytes)]},
        )
        elapsed = time.time() - t0
        usage = resp.get('usage', {})
        cost = cost_of(usage)
        b64 = resp['data'][0]['b64_json']
        out = out_dir / f'walk_{i}.png'
        out.write_bytes(base64.b64decode(b64))
        print(f'  walk_{i}: {elapsed:.1f}s, ${cost:.4f}, tokens={usage.get("total_tokens")}')
        log[f'walk_{i}'] = {'cost': cost, 'elapsed': elapsed, 'usage': usage}
        total_cost += cost
    (out_dir / 'log.json').write_text(json.dumps(log, indent=2))
    print(f'  total A: ${total_cost:.4f}')
    return total_cost


# ---- Experiment B: single-call sprite strip ----

def run_B():
    print('\n=== Experiment B: single-call 4-frame sprite strip ===')
    ref_char = (ROOT / 'frames' / '01_idle_front_ref.png').read_bytes()
    out_dir = EXP / 'B_sprite_strip'
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt = (
        STYLE + " LAYOUT: generate a 4-FRAME HORIZONTAL WALK-CYCLE STRIP in a single image. "
        "Four side-by-side frames of Marisa walking, side view facing right, left-to-right across the image: "
        "FRAME 1 (contact): right foot planted forward with heel touching ground, left leg trailing behind with toe pushing off, arms swinging (right arm back, left arm forward). "
        "FRAME 2 (passing): both legs passing close together, right leg planted flat, left leg rising and bent at the knee, arms near vertical. "
        "FRAME 3 (contact mirror): left foot planted forward with heel touching ground, right leg trailing behind — a clear mirror of frame 1. "
        "FRAME 4 (passing mirror): legs passing again, left leg planted, right leg rising and bent — mirror of frame 2. "
        "Each frame sits in its own equal-width panel, slight visible magenta gap between frames for clean splitting. "
        "Distinct large differences between frames — each pose is dramatically different, NOT a subtle variation. "
        "Magenta #FF00FF background everywhere."
    )
    t0 = time.time()
    resp = post_multipart(
        'https://api.openai.com/v1/images/edits',
        fields={'model': MODEL, 'prompt': prompt, 'size': '1536x1024', 'quality': 'medium'},
        files={'image[]': [('marisa_ref.png', ref_char)]},
    )
    elapsed = time.time() - t0
    usage = resp.get('usage', {})
    cost = cost_of(usage)
    b64 = resp['data'][0]['b64_json']
    out = out_dir / 'strip_raw.png'
    out.write_bytes(base64.b64decode(b64))
    print(f'  strip_raw: {elapsed:.1f}s, ${cost:.4f}, tokens={usage.get("total_tokens")}, size=1536x1024')
    (out_dir / 'log.json').write_text(json.dumps({'cost': cost, 'elapsed': elapsed, 'usage': usage}, indent=2))

    # Split: load, divide width by 4, save 4 frames
    from PIL import Image
    im = Image.open(out)
    w, h = im.size
    fw = w // 4
    for i in range(4):
        f = im.crop((i * fw, 0, (i + 1) * fw, h))
        f.save(out_dir / f'walk_{i+1}.png')
    print(f'  split into 4 x {fw}x{h}')
    return cost


if __name__ == '__main__':
    a_cost = run_A()
    b_cost = run_B()
    print(f'\nTotal experiment cost: ${a_cost + b_cost:.4f}')
