"""Gate 0: verify gpt-image-2 sync + batch endpoints with minimal cost."""
import os
import sys
import base64
import json
import time
from pathlib import Path

import urllib.request
import urllib.error

KEY_PATH = Path(r'C:\Users\qypen\Documents\kelly-coins\server\openai-key.txt')
API_KEY = KEY_PATH.read_text().strip()

HEADERS = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json',
}


def post(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors='replace')
        return e.code, body


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors='replace')


MODEL = os.environ.get('PROBE_MODEL', 'gpt-image-2')
# --- 1) Minimal sync test: smallest params to measure baseline cost ---
print(f'=== SYNC TEST: {MODEL}, 1024x1024, low quality ===')
t0 = time.time()
status, body = post(
    'https://api.openai.com/v1/images/generations',
    {
        'model': MODEL,
        'prompt': 'a tiny green sprout growing from soil, simple pixel art, transparent background, centered, no text',
        'size': '1024x1024',
        'quality': 'low',
        'n': 1,
    },
)
elapsed = time.time() - t0
print(f'HTTP {status} in {elapsed:.1f}s')
if status == 200 and isinstance(body, dict):
    usage = body.get('usage', {})
    print(f'  Usage: {usage}')
    # Save the image
    out_dir = Path(__file__).parent.parent / 'pipeline' / 'probe_output'
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, img in enumerate(body.get('data', [])):
        b64 = img.get('b64_json') or ''
        if b64:
            out_path = out_dir / f'sync_test_{i}.png'
            out_path.write_bytes(base64.b64decode(b64))
            print(f'  Saved: {out_path}')
        if img.get('url'):
            print(f'  URL: {img["url"]}')
    # Cost calc (approx based on token usage if reported)
    if usage:
        it = usage.get('input_tokens', 0)
        ot = usage.get('output_tokens', 0)
        # Pricing: input $5/1M text, $8/1M image; output $30/1M
        # For text-only input here, just text cost
        input_cost = it * 5 / 1_000_000
        output_cost = ot * 30 / 1_000_000
        print(f'  Estimated cost: input=${input_cost:.4f}, output=${output_cost:.4f}, total=${input_cost+output_cost:.4f}')
else:
    print(f'  Error body: {str(body)[:500]}')
    sys.exit(1)

# --- 2) Batch-API support probe: submit a tiny batch with 1 image request ---
print('\n=== BATCH TEST: check if /v1/batches accepts /v1/images/generations ===')
# Prepare JSONL
batch_req = {
    'custom_id': 'probe-1',
    'method': 'POST',
    'url': '/v1/images/generations',
    'body': {
        'model': 'gpt-image-2',
        'prompt': 'a tiny acorn on white background, simple icon',
        'size': '1024x1024',
        'quality': 'low',
        'n': 1,
    },
}
jsonl = json.dumps(batch_req).encode() + b'\n'

# Upload the file to /v1/files
boundary = '----probeBoundary123'
body_parts = []
body_parts.append(f'--{boundary}\r\n'.encode())
body_parts.append(b'Content-Disposition: form-data; name="purpose"\r\n\r\nbatch\r\n')
body_parts.append(f'--{boundary}\r\n'.encode())
body_parts.append(b'Content-Disposition: form-data; name="file"; filename="probe.jsonl"\r\n')
body_parts.append(b'Content-Type: application/jsonl\r\n\r\n')
body_parts.append(jsonl)
body_parts.append(b'\r\n')
body_parts.append(f'--{boundary}--\r\n'.encode())
file_body = b''.join(body_parts)

req = urllib.request.Request(
    'https://api.openai.com/v1/files',
    data=file_body,
    headers={
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': f'multipart/form-data; boundary={boundary}',
    },
)
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        file_resp = json.loads(r.read())
        file_id = file_resp['id']
        print(f'  Uploaded file: {file_id}')
except urllib.error.HTTPError as e:
    print(f'  File upload failed: {e.code} {e.read().decode(errors="replace")[:300]}')
    sys.exit(1)

# Create batch
status, body = post(
    'https://api.openai.com/v1/batches',
    {
        'input_file_id': file_id,
        'endpoint': '/v1/images/generations',
        'completion_window': '24h',
    },
)
print(f'  Batch create: HTTP {status}')
if status == 200 and isinstance(body, dict):
    batch_id = body['id']
    print(f'  Batch ID: {batch_id} status={body.get("status")}')
    print(f'  ==> /v1/images/generations IS supported in batch mode [OK]')
    # Cancel immediately to not waste the batch
    status, body = post(f'https://api.openai.com/v1/batches/{batch_id}/cancel', {})
    print(f'  Cancelled: HTTP {status}, status={body.get("status") if isinstance(body, dict) else body}')
else:
    print(f'  ==> NOT supported or error: {str(body)[:400]}')
