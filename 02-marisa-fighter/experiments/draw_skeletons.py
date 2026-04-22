"""Draw 4 stick-figure walk-cycle pose skeletons on 1024x1024 transparent canvases.

Each figure is positioned to match the game's anchor (feet at ~95% down,
centered horizontally), so the model can place the outfit onto the pose with
minimal compositional drift.
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).parent / 'skeletons'
OUT.mkdir(parents=True, exist_ok=True)

W, H = 1024, 1024
# Anchor: feet touch line at y=955, center x=512
FEET_Y = 955
CENTER_X = 512
FIG_HEIGHT = 560  # total skeleton height head-to-foot (about 55% of canvas)

# Proportions (multiples of a "head" unit)
HEAD_R = FIG_HEIGHT * 0.08
NECK_LEN = FIG_HEIGHT * 0.05
TORSO_LEN = FIG_HEIGHT * 0.30
HIP_WIDTH = FIG_HEIGHT * 0.10
SHOULDER_WIDTH = FIG_HEIGHT * 0.14
UPPER_ARM = FIG_HEIGHT * 0.16
FOREARM = FIG_HEIGHT * 0.16
UPPER_LEG = FIG_HEIGHT * 0.22
LOWER_LEG = FIG_HEIGHT * 0.22


def draw_figure(pose_name: str, poses: dict):
    """Draw one stick figure.

    poses keys:
      L_thigh_deg, L_knee_deg    (angles: 0=down, +=forward, -=back)
      R_thigh_deg, R_knee_deg
      L_upper_arm_deg, L_elbow_deg
      R_upper_arm_deg, R_elbow_deg
      torso_lean_deg
    """
    im = Image.new('RGBA', (W, H), (255, 255, 255, 255))  # opaque white so model reads clearly
    d = ImageDraw.Draw(im)

    # Hip at center-feet
    hip_x = CENTER_X
    hip_y = FEET_Y - (UPPER_LEG + LOWER_LEG)

    # Torso: from hip to neck, with optional lean
    lean = math.radians(poses.get('torso_lean_deg', 0))
    neck_x = hip_x + math.sin(lean) * TORSO_LEN
    neck_y = hip_y - math.cos(lean) * TORSO_LEN
    head_x = neck_x + math.sin(lean) * NECK_LEN
    head_y = neck_y - math.cos(lean) * NECK_LEN

    BLACK = (20, 20, 30, 255)
    LW = 14

    def limb(x1, y1, length, thigh_deg, tibia_deg=None, calf_len=None):
        """Draw a 2-segment limb starting at (x1,y1). Returns end-point.
        thigh_deg: 0 = straight down, +ve = forward (toward right side of canvas)
        """
        rad = math.radians(thigh_deg)
        x2 = x1 + math.sin(rad) * length
        y2 = y1 + math.cos(rad) * length
        d.line([(x1, y1), (x2, y2)], fill=BLACK, width=LW)
        if tibia_deg is not None and calf_len is not None:
            rad2 = math.radians(tibia_deg)
            x3 = x2 + math.sin(rad2) * calf_len
            y3 = y2 + math.cos(rad2) * calf_len
            d.line([(x2, y2), (x3, y3)], fill=BLACK, width=LW)
            return x3, y3
        return x2, y2

    # Legs
    # Hip extents slightly for visual clarity
    left_hip_x = hip_x - HIP_WIDTH / 2
    right_hip_x = hip_x + HIP_WIDTH / 2
    left_foot = limb(left_hip_x, hip_y, UPPER_LEG, poses['L_thigh_deg'], poses['L_knee_deg'], LOWER_LEG)
    right_foot = limb(right_hip_x, hip_y, UPPER_LEG, poses['R_thigh_deg'], poses['R_knee_deg'], LOWER_LEG)
    # feet markers (boots)
    for fx, fy in (left_foot, right_foot):
        d.ellipse((fx - 22, fy - 10, fx + 22, fy + 18), fill=BLACK)

    # Torso line
    d.line([(hip_x, hip_y), (neck_x, neck_y)], fill=BLACK, width=LW + 4)

    # Shoulders
    left_shoulder_x = neck_x - SHOULDER_WIDTH / 2
    right_shoulder_x = neck_x + SHOULDER_WIDTH / 2

    # Arms
    left_hand = limb(left_shoulder_x, neck_y, UPPER_ARM, poses['L_upper_arm_deg'], poses['L_elbow_deg'], FOREARM)
    right_hand = limb(right_shoulder_x, neck_y, UPPER_ARM, poses['R_upper_arm_deg'], poses['R_elbow_deg'], FOREARM)
    # hand markers
    for fx, fy in (left_hand, right_hand):
        d.ellipse((fx - 12, fy - 12, fx + 12, fy + 12), fill=BLACK)

    # Head
    d.ellipse((head_x - HEAD_R, head_y - HEAD_R, head_x + HEAD_R, head_y + HEAD_R), fill=BLACK)

    # Broom indicator (thin diagonal line from right hand)
    bx1, by1 = right_hand
    bx2, by2 = bx1 + math.cos(math.radians(poses.get('broom_deg', -30))) * 280, by1 + math.sin(math.radians(poses.get('broom_deg', -30))) * 280
    d.line([(bx1, by1), (bx2, by2)], fill=(140, 100, 50, 255), width=LW - 4)
    # broom bristles at far end
    d.polygon([(bx2, by2), (bx2 - 30, by2 + 40), (bx2 + 30, by2 + 40)], fill=(180, 130, 60, 255))

    # Save
    out_path = OUT / f'{pose_name}.png'
    im.save(out_path)
    print(f'  {pose_name} -> {out_path.name}')


# Walk cycle: character faces RIGHT (our +x direction).
# Angle convention: 0 = straight down. Positive = leg pointing FORWARD (in direction of motion = +x).
POSES = {
    # Frame 1: right leg forward contact, left leg back push-off, right arm swung back, left arm forward
    'walk_1': {
        'L_thigh_deg': -35, 'L_knee_deg': -60,
        'R_thigh_deg':  40, 'R_knee_deg':  10,
        'L_upper_arm_deg':  30, 'L_elbow_deg':  45,
        'R_upper_arm_deg': -40, 'R_elbow_deg': -25,
        'torso_lean_deg': 4,
        'broom_deg': -50,
    },
    # Frame 2: passing pose — both legs near vertical, left leg rising
    'walk_2': {
        'L_thigh_deg': -10, 'L_knee_deg': 25,  # rising/bent
        'R_thigh_deg':  15, 'R_knee_deg':  10,
        'L_upper_arm_deg':  5, 'L_elbow_deg':  15,
        'R_upper_arm_deg': -10, 'R_elbow_deg': -5,
        'torso_lean_deg': 2,
        'broom_deg': -40,
    },
    # Frame 3: mirror of 1 — left leg forward contact, right leg back push-off
    'walk_3': {
        'L_thigh_deg':  40, 'L_knee_deg': 10,
        'R_thigh_deg': -35, 'R_knee_deg': -60,
        'L_upper_arm_deg': -40, 'L_elbow_deg': -25,
        'R_upper_arm_deg':  30, 'R_elbow_deg':  45,
        'torso_lean_deg': 4,
        'broom_deg': -20,
    },
    # Frame 4: passing pose mirror — right leg rising
    'walk_4': {
        'L_thigh_deg':  15, 'L_knee_deg': 10,
        'R_thigh_deg': -10, 'R_knee_deg': 25,
        'L_upper_arm_deg': -10, 'L_elbow_deg': -5,
        'R_upper_arm_deg':  5, 'R_elbow_deg':  15,
        'torso_lean_deg': 2,
        'broom_deg': -40,
    },
}

for name, pose in POSES.items():
    draw_figure(name, pose)
print('\nDone.')
