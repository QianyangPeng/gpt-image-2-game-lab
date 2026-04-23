"""F: MediaPipe Pose Landmarker — new Tasks API (mediapipe >= 0.10.30)."""
import json
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions, RunningMode

ROOT = Path(__file__).parent
SRC = ROOT.parent / 'D_puppet_rig' / 'knight_sideview.png'
MODEL = ROOT / 'pose_landmarker.task'

im = Image.open(SRC).convert('RGB')
arr = np.array(im)
H, W = arr.shape[:2]
print(f'Image: {W}x{H}')

options = PoseLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=str(MODEL)),
    running_mode=RunningMode.IMAGE,
    num_poses=1,
    min_pose_detection_confidence=0.05,     # low threshold for stylized art
    min_pose_presence_confidence=0.05,
    min_tracking_confidence=0.05,
)
detector = PoseLandmarker.create_from_options(options)

mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=arr)
result = detector.detect(mp_image)

if not result.pose_landmarks:
    print('MediaPipe did NOT detect any pose.')
    import sys; sys.exit(1)

NAMES = [
    'nose','left_eye_inner','left_eye','left_eye_outer',
    'right_eye_inner','right_eye','right_eye_outer',
    'left_ear','right_ear','mouth_left','mouth_right',
    'left_shoulder','right_shoulder','left_elbow','right_elbow',
    'left_wrist','right_wrist','left_pinky','right_pinky',
    'left_index','right_index','left_thumb','right_thumb',
    'left_hip','right_hip','left_knee','right_knee',
    'left_ankle','right_ankle','left_heel','right_heel',
    'left_foot_index','right_foot_index',
]

keypoints = {}
for i, lm in enumerate(result.pose_landmarks[0]):
    keypoints[NAMES[i]] = {
        'x': int(lm.x * W),
        'y': int(lm.y * H),
        'z': round(lm.z, 4),
        'vis': round(lm.visibility, 3),
    }

IMPORTANT = [
    'nose','left_shoulder','right_shoulder','left_elbow','right_elbow',
    'left_wrist','right_wrist','left_hip','right_hip',
    'left_knee','right_knee','left_ankle','right_ankle',
]
for k in IMPORTANT:
    kp = keypoints[k]
    print(f'  {k:18s}: ({kp["x"]:4d}, {kp["y"]:4d})  vis={kp["vis"]:.2f}')

(ROOT / 'keypoints.json').write_text(json.dumps(keypoints, indent=2))

viz = im.copy()
draw = ImageDraw.Draw(viz)
SKELETON = [
    ('nose','left_shoulder'),('nose','right_shoulder'),
    ('left_shoulder','right_shoulder'),
    ('left_shoulder','left_elbow'),('left_elbow','left_wrist'),
    ('right_shoulder','right_elbow'),('right_elbow','right_wrist'),
    ('left_shoulder','left_hip'),('right_shoulder','right_hip'),
    ('left_hip','right_hip'),
    ('left_hip','left_knee'),('left_knee','left_ankle'),
    ('right_hip','right_knee'),('right_knee','right_ankle'),
]
for a, b in SKELETON:
    pa, pb = keypoints[a], keypoints[b]
    draw.line([(pa['x'],pa['y']),(pb['x'],pb['y'])], fill=(0,200,255), width=5)
for k in IMPORTANT:
    kp = keypoints[k]
    r = 10
    color = (0,255,0) if kp['vis'] > 0.5 else (255,100,100)
    draw.ellipse([kp['x']-r, kp['y']-r, kp['x']+r, kp['y']+r], fill=color, outline=(255,255,255))

viz.save(ROOT / 'keypoints_viz.png')
print('\nSaved keypoints.json + keypoints_viz.png')
