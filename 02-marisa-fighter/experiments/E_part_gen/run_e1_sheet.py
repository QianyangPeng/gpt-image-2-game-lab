"""E1: generate all body parts as a single 3x3 asset sheet (1 API call).

If this works, it's the cheapest path — 1 call produces all 9-ish parts.
Prompt tries to force: each cell = one body part isolated on magenta bg,
T-pose-style (limbs straight) with clear joint overlap regions.
"""
import os
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
REF = ROOT.parent / 'D_puppet_rig' / 'knight_sideview.png'


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
            parts.append(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode())
            parts.append(b'Content-Type: image/png\r\n\r\n')
            parts.append(content)
            parts.append(b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    body = b''.join(parts)
    req = urllib.request.Request(
        url, data=body,
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
        raise RuntimeError(f'HTTP {e.code}: {e.read().decode()[:800]}') from None


PROMPT = (
    "Character-parts asset sheet for rigging a 2D side-view knight. Use the reference image as "
    "the identity lock — SAME chibi knight girl, SAME brown pigtails with red ribbons, SAME "
    "silver plate armor with gold trim and sun emblem, SAME red cape, SAME red shield with gold "
    "phoenix, SAME blue sword. "
    "LAYOUT: a 3×3 grid of equal cells. Each cell shows ONE body part isolated, centered in its "
    "cell, on uniform bright magenta #FF00FF background. Clean pixel-art style consistent with "
    "reference. NO labels, no text, no cell borders, just the parts on magenta. "
    "PARTS (placement in the 3x3 grid, row-major): "
    "Row 1:  [head+hair+neck side-profile facing right]  [torso only — silver breastplate + red tabard, no arms no legs, both shoulder joints stubbed for rigging overlap]  [cape only — red flowing fabric with gold trim, no character] "
    "Row 2:  [upper arm straight vertical, silver pauldron included, for rigging overlap]  [forearm straight vertical, silver vambrace, no hand]  [sword only — blue blade + gold crossguard, held vertically, isolated] "
    "Row 3:  [thigh straight vertical, silver plate greave segment, wide overlap at hip joint]  [shin + boot straight vertical, silver greave + gold-trimmed boot]  [kite shield only — red + gold phoenix emblem, no arm]. "
    "Every part is in NEUTRAL rest pose (no dynamic motion, no angular pose), aligned vertically "
    "where applicable, ready to be rigged onto a bone skeleton. "
    "Pure magenta #FF00FF fills all space between and around parts."
)


def main():
    ref_bytes = REF.read_bytes()
    ROOT.mkdir(exist_ok=True)
    t0 = time.time()
    resp = post_multipart(
        'https://api.openai.com/v1/images/edits',
        fields={'model': MODEL, 'prompt': PROMPT, 'size': '1536x1536', 'quality': 'low'},
        files={'image[]': [('ref.png', ref_bytes)]},
    )
    elapsed = time.time() - t0
    usage = resp.get('usage', {})
    cost = (usage.get('output_tokens', 0) * 30 + usage.get('input_tokens', 0) * 5) / 1_000_000
    b64 = resp['data'][0]['b64_json']
    out = ROOT / 'asset_sheet.png'
    out.write_bytes(base64.b64decode(b64))
    print(f'  {elapsed:.1f}s, ~${cost:.4f}, tokens={usage.get("total_tokens")}, size=1536x1536')


if __name__ == '__main__':
    main()
