"""Experiment C: pixel-art knight from chibi reference, dense walk-cycle strip.

Pipeline:
  1. Use the chibi knight source as reference, convert style to MapleStory-chunky-pixel
     front idle master ("C_ref").
  2. Generate an 8-frame walk-cycle STRIP in one call (applying lessons from B).
  3. Split the strip into 8 frames, anchor-align, chroma-key.

Low quality tier throughout to minimize cost (pixel art doesn't need detail).
"""
import os
import sys
import json
import time
import base64
import uuid
from pathlib import Path

import urllib.request
import urllib.error

KEY_PATH = Path(r'C:\Users\qypen\Documents\kelly-coins\server\openai-key.txt')
API_KEY = KEY_PATH.read_text().strip()
OPENAI_ORG = 'org-0g6m9oj8poyjCJgvK9Nn1XSq'
MODEL = 'gpt-image-2'

ROOT = Path(__file__).parent
SOURCE = ROOT / 'knight_ref_source.png'

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
        raise RuntimeError(f'HTTP {e.code}: {err[:800]}') from None


PIXEL_STYLE = (
    "MapleStory-style 2D pixel-art game sprite, CHUNKY VISIBLE PIXELS (think 2x-3x magnified chibi pixel art), "
    "limited palette, clean outlines, NO anti-aliasing, NO blur, NO soft shading — only flat-color zones "
    "with one or two shade darker pixels for depth. Character occupies the center of the canvas, "
    "filling roughly 40-50% of the canvas height, feet at ~85% vertical. "
    "CHARACTER IDENTITY (keep from source image): "
    "chibi knight girl, brown hair in two low pigtails with small red ribbons, "
    "big dark brown eyes, cheerful expression, "
    "silver plate armor with gold trim and a sun/star emblem on the breastplate, "
    "flowing red cape, brown leather belt with small cross, "
    "red tabard/skirt with gold trim, silver greaves, white-silver boots with gold tips, "
    "holds a glowing blue-bladed sword with gold crossguard in her right hand, "
    "carries a red shield with a gold phoenix emblem in her left hand. "
    "Uniform flat bright magenta #FF00FF background everywhere around her. "
    "No text, no UI, no border."
)


def generate_reference():
    print('=== Generating pixel-art reference master ===')
    src_bytes = SOURCE.read_bytes()
    prompt = (
        PIXEL_STYLE +
        " POSE: front-facing idle, standing at attention, feet together, sword held upright "
        "in right hand resting on her shoulder, shield held in left hand resting at her side, "
        "cape flowing slightly behind. Full body visible."
    )
    t0 = time.time()
    resp = post_multipart(
        'https://api.openai.com/v1/images/edits',
        fields={'model': MODEL, 'prompt': prompt, 'size': '1024x1024', 'quality': 'low'},
        files={'image[]': [('knight_ref_source.png', src_bytes)]},
    )
    elapsed = time.time() - t0
    usage = resp.get('usage', {})
    cost = cost_of(usage)
    b64 = resp['data'][0]['b64_json']
    out = ROOT / 'C_ref.png'
    out.write_bytes(base64.b64decode(b64))
    print(f'  {elapsed:.1f}s, ${cost:.4f}, tokens={usage.get("total_tokens")}')
    return cost


def generate_walk_strip(n_frames=8):
    print(f'\n=== Generating {n_frames}-frame walk strip ===')
    ref_bytes = (ROOT / 'C_ref.png').read_bytes()
    # For 8 frames we need a wide strip. 2048x1024 = 2M pixels, OK.
    # For 12 frames: 3072x1024 = 3.15M, also OK (under 8.3M cap).
    size = f'{max(1024, 256 * n_frames)}x1024' if n_frames <= 8 else '3072x1024'
    prompt = (
        PIXEL_STYLE +
        f" LAYOUT: generate an {n_frames}-FRAME HORIZONTAL WALK-CYCLE SPRITE STRIP. "
        f"Show the knight girl walking to the viewer's right across {n_frames} equal-width panels, "
        "left-to-right. All panels share exact same character size and identical outfit details. "
        "The poses MUST be clearly different between adjacent panels, showing smooth "
        "progressive leg and arm motion: "
        "Panel 1: right foot just contacting ground forward, left foot pushing off behind; "
        "Panel 2: right foot planted, left knee lifting up bent; "
        "Panel 3: passing pose, both feet close together, left leg rising further; "
        "Panel 4: left foot swinging forward, about to contact; "
        "Panel 5 (mirror of 1): left foot just contacting forward, right foot pushing off; "
        "Panel 6 (mirror of 2): left foot planted, right knee lifting; "
        "Panel 7 (passing mirror): feet close, right leg rising; "
        "Panel 8 (mirror of 4): right foot swinging forward, about to contact. "
        "Arms swing opposite to legs. Cape flows slightly back. Sword and shield positions adjust naturally. "
        "Consistent character size, NOT different proportions per panel. "
        "Magenta #FF00FF background everywhere, with small visible gaps between the characters for clean splitting."
    )
    t0 = time.time()
    resp = post_multipart(
        'https://api.openai.com/v1/images/edits',
        fields={'model': MODEL, 'prompt': prompt, 'size': size, 'quality': 'low'},
        files={'image[]': [('C_ref.png', ref_bytes)]},
    )
    elapsed = time.time() - t0
    usage = resp.get('usage', {})
    cost = cost_of(usage)
    b64 = resp['data'][0]['b64_json']
    out = ROOT / f'walk_strip_{n_frames}.png'
    out.write_bytes(base64.b64decode(b64))
    print(f'  {elapsed:.1f}s, ${cost:.4f}, tokens={usage.get("total_tokens")}, size={size}')
    return cost


if __name__ == '__main__':
    total = 0
    total += generate_reference()
    total += generate_walk_strip(n_frames=8)
    print(f'\nTotal C cost: ${total:.4f}')
