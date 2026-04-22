"""Frame interpolator: in-between two keyframes using OpenCV Farneback optical flow.

Given N keyframes and a multiplier M, produce N*M output frames where between
each pair of consecutive keyframes there are M-1 interpolated frames.

Uses:
  1. Chroma-keyed alpha extraction (magenta -> transparent)
  2. Dense optical flow between consecutive frames (RGB channels)
  3. Warp-and-blend at fractional time steps
  4. Alpha composited over transparent BG

For comparison we also output a naive CROSSFADE baseline (no flow warping).
"""
import sys
import argparse
from pathlib import Path

import numpy as np
import cv2
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'pipeline'))
from chroma_key import strip_magenta


def to_rgba_arr(im):
    arr = np.array(im.convert('RGBA'))
    return arr


def interpolate_pair_flow(a_arr, b_arr, n_intermediate):
    """Generate n_intermediate warped frames between a and b using optical flow.

    Input and output are 3-channel RGB arrays (magenta-bg). Returns list.
    """
    a_rgb = cv2.cvtColor(a_arr, cv2.COLOR_RGB2GRAY)
    b_rgb = cv2.cvtColor(b_arr, cv2.COLOR_RGB2GRAY)

    # Farneback dense optical flow
    flow_ab = cv2.calcOpticalFlowFarneback(
        a_rgb, b_rgb, None, pyr_scale=0.5, levels=3, winsize=15,
        iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
    )
    flow_ba = cv2.calcOpticalFlowFarneback(
        b_rgb, a_rgb, None, pyr_scale=0.5, levels=3, winsize=15,
        iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
    )

    h, w = a_rgb.shape
    xs, ys = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))

    out = []
    for i in range(1, n_intermediate + 1):
        t = i / (n_intermediate + 1)
        # Warp A forward by t * flow_ab, and B backward by (1-t) * flow_ba
        map_x_a = xs + flow_ab[..., 0] * t
        map_y_a = ys + flow_ab[..., 1] * t
        warped_a = cv2.remap(a_arr, map_x_a, map_y_a, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 0, 255))

        map_x_b = xs + flow_ba[..., 0] * (1 - t)
        map_y_b = ys + flow_ba[..., 1] * (1 - t)
        warped_b = cv2.remap(b_arr, map_x_b, map_y_b, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 0, 255))

        # Blend
        blend = ((1 - t) * warped_a.astype(np.float32) + t * warped_b.astype(np.float32))
        blend = np.clip(blend, 0, 255).astype(np.uint8)
        out.append(blend)
    return out


def interpolate_pair_crossfade(a_arr, b_arr, n_intermediate):
    """Naive alpha crossfade baseline (no motion warping)."""
    out = []
    for i in range(1, n_intermediate + 1):
        t = i / (n_intermediate + 1)
        blend = ((1 - t) * a_arr.astype(np.float32) + t * b_arr.astype(np.float32))
        blend = np.clip(blend, 0, 255).astype(np.uint8)
        out.append(blend)
    return out


def process(keyframe_paths, n_intermediate, method, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    # KEEP magenta background during flow computation -- stripping to alpha=0 creates
    # black (0,0,0) in RGB which optical flow misreads as foreground. Instead work on
    # RGB-with-magenta, THEN chroma-key each final frame.
    keyframes = []
    for p in keyframe_paths:
        im = Image.open(p).convert('RGBA')
        arr = np.array(im)
        alpha = arr[:, :, 3]
        rgb = arr[:, :, :3].copy()
        # Fill transparent regions with magenta so flow doesn't mistake black for fg
        transparent = alpha == 0
        rgb[transparent] = [255, 0, 255]
        keyframes.append(rgb)

    all_frames = []
    for i in range(len(keyframes)):
        all_frames.append(keyframes[i])
        if i < len(keyframes) - 1:
            pair_fn = interpolate_pair_flow if method == 'flow' else interpolate_pair_crossfade
            intermediates = pair_fn(keyframes[i], keyframes[i + 1], n_intermediate)
            all_frames.extend(intermediates)
    # Close loop last -> first
    pair_fn = interpolate_pair_flow if method == 'flow' else interpolate_pair_crossfade
    closing = pair_fn(keyframes[-1], keyframes[0], n_intermediate)
    all_frames.extend(closing)

    for idx, f in enumerate(all_frames):
        # Convert 3-channel magenta-bg back to RGBA + chroma-key
        im = Image.fromarray(f, mode='RGB')
        keyed = strip_magenta(im, tolerance=80)  # looser tolerance for blended magenta
        keyed.save(out_dir / f'frame_{idx:03d}.png')
    print(f'  wrote {len(all_frames)} frames to {out_dir}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--in-dir', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--n-intermediate', type=int, default=3)
    ap.add_argument('--method', choices=['flow', 'crossfade'], default='flow')
    args = ap.parse_args()

    in_dir = Path(args.in_dir)
    keyframes = sorted(in_dir.glob('walk_*.png'))
    print(f'Using {len(keyframes)} keyframes from {in_dir}')
    print(f'Method={args.method}, n_intermediate={args.n_intermediate}')
    process(keyframes, args.n_intermediate, args.method, Path(args.out_dir))
