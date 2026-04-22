"""Split a sprite-strip into N character frames using column-projection detection.

Handles variable inter-character spacing by finding runs of non-transparent columns.
"""
from pathlib import Path
from PIL import Image
import numpy as np
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'pipeline'))
from chroma_key import strip_magenta


def split_strip(strip_path: Path, out_dir: Path, n_frames: int, target_canvas=(1024, 1024)):
    im = strip_magenta(Image.open(strip_path))
    arr = np.array(im)
    alpha = arr[:, :, 3]

    # Find non-empty columns
    col_has_content = alpha.any(axis=0)
    # Group contiguous runs
    runs = []
    start = None
    for x, has in enumerate(col_has_content):
        if has and start is None:
            start = x
        elif not has and start is not None:
            if x - start >= 40:
                runs.append((start, x))
            start = None
    if start is not None and len(col_has_content) - start >= 40:
        runs.append((start, len(col_has_content)))

    print(f'Found {len(runs)} content runs in {strip_path.name}, expected {n_frames}')
    for i, (s, e) in enumerate(runs):
        print(f'  run {i}: x={s}..{e} (w={e-s})')

    if len(runs) != n_frames:
        print('!! Run count mismatch. Using uniform split fallback.')
        fw = alpha.shape[1] // n_frames
        runs = [(i * fw, (i + 1) * fw) for i in range(n_frames)]

    out_dir.mkdir(parents=True, exist_ok=True)
    tc_w, tc_h = target_canvas

    for i, (xs, xe) in enumerate(runs):
        # Find the y-bbox for this character
        col_slice = alpha[:, xs:xe]
        rows = col_slice.any(axis=1).nonzero()[0]
        if len(rows) == 0:
            continue
        ys = rows[0]
        ye = rows[-1] + 1
        cropped = im.crop((xs, ys, xe, ye))
        cw, ch = cropped.size

        # Place into target canvas: center horizontally, feet at 95% vertical anchor
        canvas = Image.new('RGBA', (tc_w, tc_h), (0, 0, 0, 0))
        target_feet_y = int(tc_h * 0.95)
        target_h = int(tc_h * 0.72)  # match original sprites' character height proportion
        scale = target_h / ch
        new_w = int(cw * scale)
        new_h = int(ch * scale)
        cropped = cropped.resize((new_w, new_h), Image.LANCZOS)
        paste_x = (tc_w - new_w) // 2
        paste_y = target_feet_y - new_h
        canvas.paste(cropped, (paste_x, paste_y), cropped)
        canvas.save(out_dir / f'walk_{i+1}.png')
        print(f'  -> walk_{i+1}.png (char {cw}x{ch} -> {new_w}x{new_h}, anchored feet at y={target_feet_y})')


if __name__ == '__main__':
    ROOT = Path(__file__).parent
    strip = ROOT / 'B_sprite_strip' / 'strip_raw.png'
    out = ROOT / 'B_sprite_strip' / 'alpha'
    split_strip(strip, out, 4)
    print('Done.')
