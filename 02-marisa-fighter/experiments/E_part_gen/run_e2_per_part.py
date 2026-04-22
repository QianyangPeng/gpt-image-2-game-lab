"""E2 fallback: generate each body part as its own image (11 API calls).

Slower/more expensive than E1 but gives fine control per part. Each prompt
emphasizes isolation, neutral pose, and joint-overlap regions for clean rigging.
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
OUT = ROOT / 'parts_e2'
OUT.mkdir(exist_ok=True)


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
        raise RuntimeError(f'HTTP {e.code}: {e.read().decode()[:600]}') from None


STYLE_COMMON = (
    "Use reference image as identity lock — SAME character's specific outfit palette and "
    "chunky pixel-art style. Output ONE isolated body part on uniform bright magenta #FF00FF "
    "background. The part occupies roughly 40-60% of the 1024×1024 canvas centered. Absolutely "
    "NO other body parts visible — just the single requested part. No text, no labels, no border."
)

PARTS = {
    'head': (
        STYLE_COMMON + " PART: HEAD ONLY. Shows chibi knight girl's head and hair in side profile "
        "facing right. Include: full head silhouette (brown hair, two low pigtails with red ribbons, "
        "visible ear, face with eye and mouth), plus about 30 pixels of neck stub at the bottom for "
        "rigging overlap. Absolutely no shoulders, no armor below the neck stub."
    ),
    'torso': (
        STYLE_COMMON + " PART: TORSO ONLY. Shows the knight's silver plate breastplate with gold trim "
        "and sun emblem, the brown leather belt, the red tabard/skirt, in side profile facing right. "
        "Top ends at the neck stub with about 30px clean cutoff ready for a head to attach. Bottom "
        "ends at the hip / pelvis line. On each side, include a small 20-30 px shoulder JOINT STUB "
        "(rounded pauldron nub) so an arm can rotate from there without a visible seam. ABSOLUTELY "
        "NO arms, NO legs, NO head, NO cape."
    ),
    'cape': (
        STYLE_COMMON + " PART: CAPE ONLY. A flowing red fabric cape with gold trim and a gold emblem, "
        "isolated, showing just the cape as if hung on a hook — shape similar to what would hang from "
        "the knight's back. No character body visible. Top of cape has small attachment stub."
    ),
    'upper_arm_front': (
        STYLE_COMMON + " PART: UPPER ARM (front / camera-side). A single armored upper arm including "
        "the silver-and-gold pauldron at the top, in neutral vertical pose (hanging straight down). "
        "Shoulder stub at top (about 30 px overlap for joint), elbow stub at bottom (about 20 px overlap). "
        "No body, no forearm, no hand. Just upper arm."
    ),
    'forearm_front': (
        STYLE_COMMON + " PART: FOREARM + HAND (front / camera-side) GRIPPING SWORD HILT. Vertical "
        "neutral pose — forearm hangs down with the armored vambrace visible, armored gauntlet hand "
        "at the bottom gripping the gold crossguard of the sword. Elbow stub at top. No upper arm, no body."
    ),
    'sword': (
        STYLE_COMMON + " PART: SWORD ONLY. Just the knight's sword, isolated: thin blue-cyan blade "
        "(length ~600 px), gold cross-guard, gold pommel. Vertical orientation, blade pointing down. "
        "No hand holding it, no body, no background objects. Clean magenta around the whole sword."
    ),
    'shield': (
        STYLE_COMMON + " PART: SHIELD ONLY. A red kite shield with gold trim and a gold phoenix emblem, "
        "isolated and facing slightly toward the viewer. No arm holding it, no body. Centered on magenta."
    ),
    'forearm_back': (
        STYLE_COMMON + " PART: BACK-SIDE FOREARM GRIPPING SHIELD. Forearm with armored vambrace and "
        "gauntlet gripping the inside of the red-and-gold kite shield from behind. Shield visible. "
        "Elbow stub at top. No upper arm, no body."
    ),
    'thigh_front': (
        STYLE_COMMON + " PART: THIGH (front / camera-side). A single armored thigh in neutral vertical "
        "pose, silver greave top, a small sliver of red tabard/skirt at the very top for visual overlap. "
        "Hip joint stub at top (about 30 px), knee joint stub at bottom. No body, no shin, no foot."
    ),
    'shin_front': (
        STYLE_COMMON + " PART: SHIN + FOOT (front / camera-side). Vertical neutral pose — armored "
        "silver greave over the shin, white-silver boot with gold tip at the bottom. Knee stub at top, "
        "foot fully rendered at bottom. No thigh, no body."
    ),
    'thigh_back': (
        STYLE_COMMON + " PART: THIGH (back side, slightly smaller/duller to suggest depth). Vertical "
        "neutral pose. Hip stub at top, knee stub at bottom. No other parts."
    ),
    'shin_back': (
        STYLE_COMMON + " PART: SHIN + FOOT (back side, slightly smaller/duller). Vertical neutral pose. "
        "Knee stub at top, foot at bottom. No other parts."
    ),
}


def main(only=None):
    ref_bytes = REF.read_bytes()
    log = {}
    total_cost = 0
    for name, prompt in PARTS.items():
        if only and name not in only:
            continue
        out_path = OUT / f'{name}.png'
        if out_path.exists():
            print(f'  skip {name} (exists)')
            continue
        t0 = time.time()
        resp = post_multipart(
            'https://api.openai.com/v1/images/edits',
            fields={'model': MODEL, 'prompt': prompt, 'size': '1024x1024', 'quality': 'low'},
            files={'image[]': [('ref.png', ref_bytes)]},
        )
        elapsed = time.time() - t0
        usage = resp.get('usage', {})
        cost = (usage.get('output_tokens', 0) * 30 + usage.get('input_tokens', 0) * 5) / 1_000_000
        b64 = resp['data'][0]['b64_json']
        out_path.write_bytes(base64.b64decode(b64))
        print(f'  {name}: {elapsed:.1f}s, ${cost:.4f}, tokens={usage.get("total_tokens")}')
        log[name] = {'cost': cost, 'elapsed': elapsed, 'usage': usage}
        total_cost += cost
    (OUT / 'log.json').write_text(json.dumps(log, indent=2))
    print(f'\nTotal E2 cost: ${total_cost:.4f}')


if __name__ == '__main__':
    import sys
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    main(only=only)
