"""Overlay part bboxes + pivot points on the source image to visually tune them."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'pipeline'))
from chroma_key import strip_magenta
from segment import PARTS

ROOT = Path(__file__).parent
SRC = ROOT / 'knight_sideview.png'

im = strip_magenta(Image.open(SRC)).convert('RGBA')
bg = Image.new('RGBA', im.size, (235, 235, 240, 255))
canvas = Image.alpha_composite(bg, im)
draw = ImageDraw.Draw(canvas)

COLORS = {
    'cape':             (200, 50, 50, 180),
    'back_thigh':       (80, 150, 200, 180),
    'back_shin':        (80, 100, 180, 180),
    'back_upper_arm':   (120, 200, 100, 180),
    'back_forearm':     (80, 180, 60, 180),
    'torso':            (200, 100, 200, 180),
    'head':             (240, 180, 100, 180),
    'front_thigh':      (100, 200, 220, 180),
    'front_shin':       (60, 160, 220, 180),
    'front_upper_arm':  (220, 140, 60, 180),
    'front_forearm':    (200, 120, 40, 180),
    'sword':            (100, 150, 250, 200),
}

for name, spec in PARTS.items():
    x0, y0, x1, y1 = spec['bbox']
    px, py = spec['pivot_full']
    color = COLORS[name]
    draw.rectangle([x0, y0, x1, y1], outline=color, width=3)
    draw.text((x0 + 4, y0 + 4), name, fill=color[:3])
    # pivot marker
    r = 6
    draw.ellipse([px - r, py - r, px + r, py + r], fill=(0, 0, 0, 255), outline=(255, 255, 255, 255), width=2)

# Scale down to 640 wide for easy viewing
disp_w = 640
disp_h = int(im.height * (disp_w / im.width))
canvas.resize((disp_w, disp_h), Image.LANCZOS).save(ROOT / 'parts_overlay.png')
print('saved parts_overlay.png')
