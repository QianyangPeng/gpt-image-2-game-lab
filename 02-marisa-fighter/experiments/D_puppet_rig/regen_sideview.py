"""Regenerate the knight as a CLEAN side-view T-pose (well, A-pose) for rigging.

Needs: arms relaxed at sides, legs straight, facing right, everything on
magenta BG for easy chroma key + part segmentation.
"""
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
SOURCE = ROOT.parent / 'C_knight_pixel' / 'knight_ref_source.png'


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
        raise RuntimeError(f'HTTP {e.code}: {e.read().decode()[:500]}') from None


PROMPT = (
    "MapleStory-style 2D pixel-art game sprite, CHUNKY VISIBLE PIXELS, limited palette, "
    "clean outlines, NO anti-aliasing, flat-color shading with one-pixel-darker shadows. "
    "CHARACTER IDENTITY (preserve from source): chibi knight girl, brown hair with two low pigtails "
    "with small red ribbons, big brown eyes, cheerful closed-mouth smile, silver plate armor with "
    "gold trim and a small sun emblem on the breastplate, red tabard with gold trim, silver greaves, "
    "silver-white boots with gold tips, brown belt with small cross, red cape flowing from shoulders. "
    "Holds a blue-bladed sword with gold crossguard in her right hand, a red shield with gold phoenix "
    "in her left hand. "
    "POSE (CRITICAL): strict PROFILE SIDE VIEW facing the viewer's right. "
    "T-pose-like neutral stance: both feet flat on the ground, legs straight and parallel. "
    "BOTH ARMS HANGING STRAIGHT DOWN at her sides — sword pointing straight down held in her right hand "
    "(the arm closer to the camera), shield held straight down in her left hand (the arm further from camera, "
    "partially behind the body). "
    "Head facing sideways in the same profile direction as the body. Cape flowing gently behind her. "
    "Character at ~50% of canvas height, centered horizontally, feet at ~88% vertical. "
    "Uniform flat bright magenta #FF00FF background everywhere. No text, no UI, no border."
)


def main():
    print('Regenerating knight as side-view T-pose')
    src = SOURCE.read_bytes()
    t0 = time.time()
    resp = post_multipart(
        'https://api.openai.com/v1/images/edits',
        fields={'model': MODEL, 'prompt': PROMPT, 'size': '1024x1024', 'quality': 'low'},
        files={'image[]': [('knight_source.png', src)]},
    )
    elapsed = time.time() - t0
    usage = resp.get('usage', {})
    cost = usage.get('output_tokens', 0) * 30 / 1_000_000 + usage.get('input_tokens', 0) * 5 / 1_000_000
    b64 = resp['data'][0]['b64_json']
    out = ROOT / 'knight_sideview.png'
    out.write_bytes(base64.b64decode(b64))
    print(f'  {elapsed:.1f}s, ~${cost:.4f}, tokens={usage.get("total_tokens")}')


if __name__ == '__main__':
    main()
