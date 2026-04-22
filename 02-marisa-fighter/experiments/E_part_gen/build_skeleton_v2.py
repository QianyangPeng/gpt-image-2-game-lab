"""Build skeleton_e2.json from auto-detected joints + part-to-bone mapping.

Offsets are COMPUTED from the joints, not eyeballed. Parts that share a sprite
(back limbs reusing front limb sprites) still use the same joint keypoints.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
JOINTS = json.loads((ROOT / 'joints.json').read_text())

# Canonical body scale: we'll normalize part sprite heights so the assembled
# character has plausible proportions. Target character total height = 800 px
# breakdown: head 15% + torso 35% + thigh 25% + shin 25% = 100% (legs stack)
TARGET_H = 800
TARGET = {
    'head':      TARGET_H * 0.20,
    'torso':     TARGET_H * 0.42,
    'cape':      TARGET_H * 0.55,
    'upper_arm': TARGET_H * 0.20,
    'forearm':   TARGET_H * 0.20,
    'sword':     TARGET_H * 0.55,
    'thigh':     TARGET_H * 0.22,
    'shin':      TARGET_H * 0.22,
    'shield':    TARGET_H * 0.30,
}

# For each part sprite, compute a per-part scale so its native height maps to target.
sprite_scales = {}
for name, joint in JOINTS.items():
    native_h = joint['size'][1]
    target_h = TARGET.get(name, native_h)
    sprite_scales[name] = target_h / native_h
    print(f'  {name}: native={native_h}, target={target_h:.0f}, scale={sprite_scales[name]:.3f}')


def scaled(pt, s):
    return [int(pt[0] * s), int(pt[1] * s)]


def scaled_size(size, s):
    return [int(size[0] * s), int(size[1] * s)]


# Build skeleton.
# Bone spec: name, parent, sprite (which PNG), pivot (joint in scaled local),
# offset (from parent's pivot, in parent's scaled local coords).
skeleton = []


def add_bone(name, parent, sprite, pivot_key, offset, z):
    s = sprite_scales[sprite]
    joint = JOINTS[sprite]
    pivot = scaled(joint[pivot_key], s)
    sprite_size = scaled_size(joint['size'], s)
    skeleton.append({
        'name': name, 'parent': parent, 'sprite': sprite,
        'pivot': pivot, 'offset': offset,
        'sprite_size': sprite_size,
        'sprite_scale': s,
        'z': z,
    })


# Helper: offset to place CHILD at PARENT_JOINT in parent's scaled-local coords.
# offset = parent.joint_point - parent.pivot, both scaled by parent's sprite_scale.
def offset_from_parent_joint(parent_sprite, parent_joint_key, parent_pivot_key):
    s = sprite_scales[parent_sprite]
    p_joint = scaled(JOINTS[parent_sprite][parent_joint_key], s)
    p_pivot = scaled(JOINTS[parent_sprite][parent_pivot_key], s)
    return [p_joint[0] - p_pivot[0], p_joint[1] - p_pivot[1]]


# Virtual root
skeleton.append({'name': 'pelvis', 'parent': None, 'sprite': None,
                 'pivot': [0, 0], 'offset': [0, 0], 'z': 2})

# Torso: pivot is its own 'bottom' (pelvis attach). Offset from pelvis = 0,0.
add_bone('torso', 'pelvis', 'torso', 'bottom', [0, 0], 3)

# Head: pivot = head.bottom (neck). Offset in torso coords = torso.top - torso.bottom.
add_bone('head', 'torso', 'head', 'bottom',
         offset_from_parent_joint('torso', 'top', 'bottom'), 4)

# Cape: pivot = cape.top. Offset in torso: between neck and chest area.
cape_offset = offset_from_parent_joint('torso', 'top', 'bottom')
cape_offset[1] += int(TARGET_H * 0.05)  # a bit down from neck (upper back)
cape_offset[0] -= int(TARGET_H * 0.02)  # slight left (behind body)
add_bone('cape', 'torso', 'cape', 'top', cape_offset, 0)

# Arms: shoulder stubs on torso are left_shoulder, right_shoulder.
# Front arm (camera-side) uses right_shoulder (on the character's right, facing right = camera-side).
add_bone('front_upper_arm', 'torso', 'upper_arm', 'top',
         offset_from_parent_joint('torso', 'right_shoulder', 'bottom'), 6)
add_bone('front_forearm', 'front_upper_arm', 'forearm', 'top',
         offset_from_parent_joint('upper_arm', 'bottom', 'top'), 6)
add_bone('sword', 'front_forearm', 'sword', 'top',
         offset_from_parent_joint('forearm', 'bottom', 'top'), 6)

# Back arm (reuses upper_arm/forearm sprites, attaches at left_shoulder)
add_bone('back_upper_arm', 'torso', 'upper_arm', 'top',
         offset_from_parent_joint('torso', 'left_shoulder', 'bottom'), 1)
add_bone('back_forearm', 'back_upper_arm', 'forearm', 'top',
         offset_from_parent_joint('upper_arm', 'bottom', 'top'), 1)
# Shield attached at back_forearm's bottom (hand area)
add_bone('shield', 'back_forearm', 'shield', 'top',
         offset_from_parent_joint('forearm', 'bottom', 'top'), 1)

# Legs. Pelvis has no sprite, so offset_from_parent_joint can't compute from it.
# Instead, hardcode a small hip width offset (plus small downward shift if needed).
HIP_HALF_WIDTH = int(TARGET_H * 0.04)
add_bone('front_thigh', 'pelvis', 'thigh', 'top', [HIP_HALF_WIDTH, 0], 5)
add_bone('front_shin',  'front_thigh', 'shin', 'top',
         offset_from_parent_joint('thigh', 'bottom', 'top'), 5)
add_bone('back_thigh',  'pelvis', 'thigh', 'top', [-HIP_HALF_WIDTH, 0], 1)
add_bone('back_shin',   'back_thigh', 'shin', 'top',
         offset_from_parent_joint('thigh', 'bottom', 'top'), 1)

(ROOT / 'skeleton_e2.json').write_text(json.dumps({
    'skeleton': skeleton,
    'parts_dir': 'experiments/E_part_gen/parts_e1',
    'scales': sprite_scales,
}, indent=2))
print(f'\nSaved skeleton_e2.json with {len(skeleton)} bones')
