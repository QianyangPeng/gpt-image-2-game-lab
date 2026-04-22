"""Generation pipeline: sync text-to-image + image-edit with reference.

Reads prompts from a JSON spec, calls gpt-image-2, saves outputs + logs cost.
"""
import os
import sys
import base64
import json
import time
import argparse
from pathlib import Path

import urllib.request
import urllib.error

KEY_PATH = Path(r'C:\Users\qypen\Documents\kelly-coins\server\openai-key.txt')
API_KEY = KEY_PATH.read_text().strip()
# This key is associated with multiple orgs; only the verified one can use gpt-image-2.
OPENAI_ORG = 'org-0g6m9oj8poyjCJgvK9Nn1XSq'

MODEL = 'gpt-image-2'

# Pricing per 1M tokens (April 2026)
PRICE_TEXT_IN = 5.0
PRICE_IMAGE_IN = 8.0
PRICE_IMAGE_IN_CACHED = 2.0
PRICE_OUTPUT = 30.0


def cost_of(usage):
    """Compute USD cost from a usage dict returned by the API."""
    if not usage:
        return 0.0
    inp = usage.get('input_tokens_details', {})
    out = usage.get('output_tokens_details', {})
    text_in = inp.get('text_tokens', usage.get('input_tokens', 0))
    image_in = inp.get('image_tokens', 0)
    cached_image_in = inp.get('cached_image_tokens', 0)
    output_tokens = usage.get('output_tokens', 0)
    return (
        text_in * PRICE_TEXT_IN / 1_000_000
        + (image_in - cached_image_in) * PRICE_IMAGE_IN / 1_000_000
        + cached_image_in * PRICE_IMAGE_IN_CACHED / 1_000_000
        + output_tokens * PRICE_OUTPUT / 1_000_000
    )


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
        body = e.read().decode(errors='replace')
        raise RuntimeError(f'HTTP {e.code}: {body[:600]}') from None


def post_multipart(url, fields, files):
    """fields: dict[str,str], files: dict[str,(filename, bytes)]."""
    import uuid
    boundary = '----boundary' + uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\n'.encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        parts.append(f'{value}\r\n'.encode())
    for name, (filename, content) in files.items():
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


def generate(prompt, out_path, size='1024x1024', quality='medium', reference_path=None, background=None):
    """Generate one image. Returns (cost_usd, elapsed_sec)."""
    t0 = time.time()
    if reference_path:
        # Use /v1/images/edits with reference
        ref_bytes = Path(reference_path).read_bytes()
        fields = {
            'model': MODEL,
            'prompt': prompt,
            'size': size,
            'quality': quality,
        }
        if background:
            fields['background'] = background
        resp = post_multipart(
            'https://api.openai.com/v1/images/edits',
            fields=fields,
            files={'image': (Path(reference_path).name, ref_bytes)},
        )
    else:
        payload = {
            'model': MODEL,
            'prompt': prompt,
            'size': size,
            'quality': quality,
            'n': 1,
        }
        if background:
            payload['background'] = background
        resp = post_json('https://api.openai.com/v1/images/generations', payload)
    elapsed = time.time() - t0
    usage = resp.get('usage', {})
    cost = cost_of(usage)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    b64 = resp['data'][0]['b64_json']
    Path(out_path).write_bytes(base64.b64decode(b64))
    return {'cost': cost, 'elapsed': elapsed, 'usage': usage, 'path': str(out_path)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec', help='Path to generation spec JSON')
    ap.add_argument('--only', nargs='*', help='Only generate these frame names')
    ap.add_argument('--dry-run', action='store_true', help='Print what would be generated')
    args = ap.parse_args()

    spec_path = Path(args.spec)
    spec = json.loads(spec_path.read_text(encoding='utf-8'))
    out_dir = spec_path.parent / 'frames'
    log_path = spec_path.parent / 'generation-log.json'

    log = {}
    if log_path.exists():
        log = json.loads(log_path.read_text())

    total_cost = sum(e.get('cost', 0) for e in log.values())
    print(f'Loaded {len(spec["frames"])} frames, prior cost: ${total_cost:.4f}')

    for frame in spec['frames']:
        name = frame['name']
        if args.only and name not in args.only:
            continue
        out_path = out_dir / f'{name}.png'
        if out_path.exists() and name in log and not args.only:
            print(f'  skip {name} (already generated)')
            continue
        full_prompt = spec.get('style_preamble', '') + '\n\n' + frame['prompt']
        ref = frame.get('reference')
        ref_path = (spec_path.parent / 'frames' / f'{ref}.png') if ref else None
        print(f'  -> {name} (ref={ref or "none"}, quality={frame.get("quality","medium")})')
        if args.dry_run:
            print(f'     PROMPT: {full_prompt[:200]}...')
            continue
        result = generate(
            prompt=full_prompt,
            out_path=str(out_path),
            size=frame.get('size', '1024x1024'),
            quality=frame.get('quality', 'medium'),
            reference_path=ref_path,
            background=frame.get('background'),
        )
        print(f'     {result["elapsed"]:.1f}s, ${result["cost"]:.4f}, tokens={result["usage"].get("total_tokens")}')
        log[name] = {**result, 'prompt': full_prompt}
        total_cost += result['cost']
        log_path.write_text(json.dumps(log, indent=2))
    print(f'\nTotal cost for {spec_path.name}: ${total_cost:.4f}')


if __name__ == '__main__':
    main()
