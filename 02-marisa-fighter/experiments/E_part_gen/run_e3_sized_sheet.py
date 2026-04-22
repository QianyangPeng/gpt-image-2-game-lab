"""E3: regenerate the asset sheet with EXPLICIT PIXEL SIZES per part.

This addresses the v2 proportion issue: each part in E1 came out at its own
native pixel size, so even after scale-normalization the internal detail
density mismatches. E3 tells the model exactly how tall each part should be
on a shared body scale, so 1:1 assembly without any runtime scaling works.

Target body scale: approximately 800 px from top of head to bottom of foot.
Each cell of the 3x3 sheet is the SAME SIZE (512x512 within 1536x1536), but
the PART inside each cell is drawn at a specific height.
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
        headers={'Authorization': f'Bearer {API_KEY}', 'OpenAI-Organization': OPENAI_ORG,
                 'Content-Type': f'multipart/form-data; boundary={boundary}'},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'HTTP {e.code}: {e.read().decode()[:800]}') from None


PROMPT = (
    "Character-parts asset sheet for rigging a 2D side-view knight. Reference image is the "
    "SAME chibi knight girl (brown pigtails+red ribbons, silver plate armor with gold trim and "
    "sun emblem, red cape+tabard+gold trim, red-gold kite shield with phoenix, blue-bladed sword "
    "with gold crossguard). Chunky pixel-art style, flat shading. Each cell is isolated on "
    "pure magenta #FF00FF background. 3×3 grid, equal-size cells in a 1536×1536 canvas. "
    "NO labels, NO cell borders, NO text, NO extra UI. "
    "CRITICAL: all parts share a CONSISTENT BODY SCALE so they could be assembled into one "
    "500-px-tall character. Each cell centers its part vertically. Specific per-cell heights: "
    "\n\n"
    "Row 1: "
    "Cell (1,1) HEAD — chibi side-profile head + hair + pigtail with ribbon, ~180 px tall, "
    "drawn centered in its cell. Include 15 px of neck stub at the bottom. "
    "Cell (1,2) TORSO — silver breastplate with sun emblem + brown belt + red tabard, side view, "
    "~300 px tall TOTAL. Include small pauldron stubs at BOTH top corners (left + right shoulder "
    "joints ready for arm attachment). Neck stub at top, clean hip cutoff at bottom. NO arms, "
    "NO head, NO legs inside the torso sprite. "
    "Cell (1,3) CAPE — flowing red cape fabric only, ~380 px tall, shaped as it would hang from "
    "a back, no character body visible. "
    "\n\n"
    "Row 2: "
    "Cell (2,1) UPPER ARM — single armored upper arm + pauldron tip, HANGING VERTICAL straight "
    "down, ~170 px tall. Shoulder joint stub at top, elbow stub at bottom. NO forearm NO hand. "
    "Cell (2,2) FOREARM — armored forearm + metal gauntlet hand gripping a hilt, VERTICAL, "
    "~160 px tall. Elbow stub at top, hand + grip area at bottom. NO upper arm. "
    "Cell (2,3) SWORD — isolated sword only, blue-cyan blade + gold crossguard + gold pommel, "
    "vertical orientation blade-down, ~420 px tall TOTAL (includes grip above the crossguard). "
    "No hand, no body. "
    "\n\n"
    "Row 3: "
    "Cell (3,1) THIGH — single armored thigh with greave + small sliver of red skirt/tabard "
    "at the very top for rigging overlap, vertical, ~170 px tall. Hip joint stub at top (wider), "
    "knee joint stub at bottom. "
    "Cell (3,2) SHIN+FOOT — armored shin with gold-trimmed silver boot, vertical, ~180 px tall. "
    "Knee stub at top, foot fully rendered at bottom. "
    "Cell (3,3) SHIELD — red kite shield with gold phoenix emblem, ~220 px tall, isolated, "
    "no arm holding it. "
    "\n\n"
    "Every part at the same PIXEL-ART TECHNICAL RESOLUTION (same pixel chunkiness, same color "
    "palette, same line weight). They must be assembly-compatible."
)


def main():
    ref_bytes = REF.read_bytes()
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
    out = ROOT / 'asset_sheet_e3.png'
    out.write_bytes(base64.b64decode(b64))
    print(f'  {elapsed:.1f}s, ~${cost:.4f}, tokens={usage.get("total_tokens")}')


if __name__ == '__main__':
    main()
