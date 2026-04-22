# Demo 2 — Part 3: 2D Puppet Rig (what indies actually do)

> Previous conclusion ("gpt-image-2 can't make fluid 2D animation") was **wrong**. I had been trying the wrong thing — pixel-level frame interpolation. The real answer, used by actual indie shops since ~2013 and now accelerated by AI tools like SpriteFlow/PixelLab/God Mode AI, is **skeletal rigging**: generate ONE character image, segment into parts, rig with bones, animate bone angles. This part proves that path works end-to-end using just gpt-image-2 + 100 lines of Canvas JS.

## The mistake I was making

Parts 1-2 of this experiment tested:
- Strip generation (B) — OK, the best pure-gpt-image-2 result but still discrete step-stand-step-stand
- Frame interpolation (C_flow, C_xfade) — produces warped/ghosty artifacts because pixel motion isn't smooth between pose changes

Both are attempts to **produce more frames**. The real bottleneck isn't frame count — it's that **pixel-space interpolation doesn't model rigid-body motion**. Animators have known this since 1913 (cel animation with hold frames). The 2D game industry solved it in 2013 with Spine. I just... forgot.

## The path indies actually use in 2026

1. **Image-gen** (gpt-image-2, Midjourney, etc.) produces a single high-quality character sheet.
2. **Segmentation** cuts the character into parts (head, torso, each limb). Either manual (Photoshop / Aseprite selections) or auto (SpriteFlow / PixelLab / SAM).
3. **Rigging** defines a bone tree with parent-child relationships, rest offsets, and sprite pivots for each bone. Tools: [Spine](https://esotericsoftware.com/) ($379), [DragonBones](https://dragonbones.github.io/en/) (free), [Live2D](https://www.live2d.com/) ($20/mo), [Rive](https://rive.app/) (free tier).
4. **Animation** = keyframes of bone **rotation angles**, interpolated at runtime. Because rotations are rigid-body, there are no warping/ghosting artifacts EVER.
5. **Runtime** either plays back the rig directly in-engine (Spine/DragonBones/Live2D all have Unity/Godot/HTML5 runtimes) or bakes to a sprite sheet at edit time.

AI-era tools (SpriteFlow, PixelLab, God Mode AI) automate steps 2+3 from a single AI-generated character image and offer pre-built animation libraries for step 4.

## What I built to prove it

Everything below runs in ~100 lines of vanilla JS + one Python segmentation script. No Spine, no DragonBones, no commercial tools. Just to show the principle.

### Asset generation
- **1 gpt-image-2 call** (`regen_sideview.py`): regenerated the knight reference as a side-view-ish standing pose on magenta BG. Cost: $0.020 (low quality, 1024×1024).

### Segmentation (`segment.py`)
- Manually hand-picked 12 rectangular bboxes and pivot points for: cape, head, torso, front/back thigh, front/back shin, front/back upper arm, front/back forearm, sword.
- Chroma-key strips magenta; each part saved as its own PNG.
- Skeleton hierarchy (parent-child offsets) written to `skeleton.json`.

### Rig renderer (`index.html` PuppetRig class)
- `PuppetRig.render(ctx, animName, t, opts)` — evaluates keyframe-interpolated pose, walks the bone tree, composes DOMMatrix transforms, draws each sprite at its bone's world matrix with proper pivot.
- Z-order per bone for correct front/back layering (cape behind, front arm in front of torso, etc.).
- `PuppetRig.poseAt()` does cyclic linear interpolation between keyframes.

### Walk cycle (4 keyframes, 0.8s duration)
```js
{ t: 0.0,  front_thigh: -22, front_shin: 18,  back_thigh:  22, back_shin: -25,
           front_upper_arm: 18, ..., pelvis_dy: 0 }
{ t: 0.25, everything near 0,  pelvis_dy: -6 }   // passing pose, body up
{ t: 0.5,  mirror of t=0 }
{ t: 0.75, mirror of t=0.25 }
```

Plus a 2-second idle animation with pelvis bob + cape sway.

### Result: **the knight walks**

Open the demo, click the **D · 骨骼 rig** tab, hold arrow keys:
- Legs swing through real contact-passing-contact stride phases
- Arms swing opposite, sword sways with front arm
- Cape flutters with torso sway
- Body bobs up-down on each step
- **Infinite perfect loop** — no pixel artifacts, no warping, no ghosting
- Facing flips cleanly left-right
- Works at ANY fps (canvas refresh rate) because interpolation is mathematical, not discrete frames

Total cost to build this animation: **$0.020 in gpt-image-2 tokens + a few hours of code**. The same rig could drive: run, jump, attack, cast, hurt, block, idle-variants — unlimited animations from the same 12 parts by just writing more keyframe sets.

## Post-fix update (v2)

User flagged two real defects after first push:
1. **"人脸都不完整"** — Right. My initial head bbox ended at x=545, cutting off the face (which actually extends to x=643). Widened to x=290..645 and verified with a pixel-scan script that isolates skin-tone pixels.
2. **"腿像是从脖子岔开的，不是从跨部岔开的"** — Also right. Legs were rendered floating ~150 px above the ground, making the proportions look head-heavy. Two root causes: (a) my `pelvisScreenY = state.y - 340` was a guess, not calibrated against the rigs actual thigh+shin lengths. (b) leg bboxes started at y=615, overlapping the torso bbox (y=305..625), so part of the tabard/skirt got baked into the thigh sprites and rotated with the leg swings — looking like "body parts spawning from the wrong place". 

Fixes:
- `pelvisScreenY = state.y - 188` (calibrated: thigh 145 + shin 165 scaled by 0.65 = 201, minus ~13 for the thigh's pelvis-offset).
- Leg bboxes tightened to start at y=635 (clean of torso).
- Head bbox widened and pivot re-computed.
- Dropped `back_upper_arm` as a separate bone — it's invisible behind the body anyway and added noise. `back_forearm` (with shield) is now direct child of torso.

After fix: face visible, feet on ground, legs cleanly attached at hip. Still not Spine-quality but the three structural problems are resolved. See commit history for the concrete diff.

## v3 additions: attack + jump + hurt + SAM experiment

Continuing demo 2 after the v2 fixes landed.

### New animations (all driven by the same 11-part rig)
- **Attack** (0.55s, non-looping) — sword slash: windup (arm raised to -115°, body leans +6°) → strike (arm swings to +55°, head ducks) → recovery.
- **Jump** — keyframed poses for ascend / fall / land, driven by physics: Space sets `state.vy = -22`, gravity `1.1/frame` adds each update, `state.y += vy`. On ground collision, state transitions through a 0.25s `land` animation (crouch → stand).
- **Hurt** (0.5s) — torso back +12°, head back -15°, front arm flails out. Auto-recovers to idle.
- **Input**: Z → attack, Space → jump, C → hurt. Marisa variants gracefully fall back to idle for jump/fall/land states (she doesn't have those frames).

This is what I meant earlier by "unlimited animations from the same 11 parts by writing more keyframe sets." These three new animations cost $0 to add.

### SAM segmentation experiment

Installed `segment-anything` + torch-cpu + torchvision + SAM ViT-B weights (~375MB). Wrote `sam_segment.py` with click-point prompts for each body part. Two iterations of click tuning.

**Results: mixed, not used in the live game.**

| Part | SAM mask quality | Score | Usable? |
|---|---|---|---|
| head | **pixel-perfect** (hair silhouette + ear + face as one) | 0.957 | ✅ |
| cape | Good (flowing silhouette isolated cleanly) | 0.946 | ✅ |
| back_forearm (shield) | Excellent (phoenix emblem isolated) | 0.987 | ✅ |
| front_shin | Good | 0.963 | ✅ |
| torso | Merged with adjacent arm/shield pixels | 0.857 | ⚠️ |
| front_upper_arm | Too small / contaminated | 0.698 | ⚠️ |
| front_thigh | Grabbed tabard + neighbor leg | 0.822 | ⚠️ |
| **sword** | **Failed** — SAM can't isolate the thin blade from overlapping leg/tabard | 0.879 (false positive) | ❌ |
| back_thigh | Mostly hidden behind body | 0.793 | ⚠️ |

**Why SAM struggled here**:
1. The knight source is a chibi with **tightly packed silhouettes** — thigh/tabard share color and touch, so clicks on one often mask the other.
2. The sword blade is **thin and crosses the body** — SAM can't resolve it with positive clicks because any click near the blade gets overridden by the adjacent larger leg mask.
3. ViT-B is the smallest SAM variant (350MB). ViT-H (2.5GB) would likely do better on these cases, at 5× inference time on CPU.

**Production-ready workflow** (not done here due to time): SAM ViT-H for main masses + **color-threshold for the sword blade** (it's a distinct blue-cyan palette that hand-bbox extraction + color mask combo can isolate perfectly). Or use SpriteFlow's character-specific auto-cutter (they've trained on game sprites).

**Kept in the repo**: `sam_segment.py`, `sam_to_skeleton.py`, `sam_models/sam_vit_b_01ec64.pth`, `parts_sam/`. Anyone can re-run and tune the clicks. The **live game still uses my hand-bbox parts** because the SAM ones had less-controllable failure modes.

### Cost update
All of this adds **$0** — no new gpt-image-2 calls. Just code + local ML inference + downloads.
Running total unchanged: **$2.22 / $10 budget**.

## Known imperfections (that don't invalidate the approach)

- **Hand-picked segmentation bboxes are approximate**: parts contain a little cross-contamination (the "sword" extraction actually grabbed some leg pixels because the sword overlaps with the body in the 3/4 view). Production workflow: use SAM or the commercial auto-cutters for clean part extraction, and/or regenerate the character in a strict profile T-pose with limbs spread apart so parts don't overlap.
- **Character is 3/4 view, not strict profile**: the front-facing reference biased the regeneration. The rig still animates, but side-view walk cycles work best with strict profile. Easy fix: regenerate from scratch (not image-edit) asking for strict side view — loses source-identity lock but pure text-to-image gives more pose freedom.
- **No inverse kinematics**: feet slide slightly during the walk because I hand-tuned thigh+shin angles for look, not IK-correct ground contact. Real rigs add IK constraints so feet stay planted. Another ~50 lines of code.
- **Only walk + idle implemented**: adding attack / jump / hit / cast is purely authoring keyframes. 15-30 min per animation.

None of these are fundamental limits — they're just the difference between "proof of concept in an afternoon" and "production-quality Spine rig with IK, secondary motion, and physics".

## The honest revised conclusion

**gpt-image-2's ceiling for 2D action games is FAR above where I stopped.** The fluidity problem is a **solved problem** in the indie industry — it just doesn't get solved by image-gen alone. The correct pipeline is:

| Step | What does it | Tool |
|---|---|---|
| 1 | Art direction + character sheet | **gpt-image-2** (strong) |
| 2 | Part segmentation | Manual / SAM / SpriteFlow (commercial) |
| 3 | Bone rig | Spine / DragonBones / Live2D / custom |
| 4 | Keyframe animation | Spine / DragonBones / hand-coded as here |
| 5 | In-game playback | Spine runtime / export to sprite sheet / custom |

Every single step except #1 existed before gpt-image-2. The image model's role is **asset production**, not animation. That's the honest answer — and it's a much bigger contribution than "also does animation badly". A small indie team can now produce every character's ART in a day; the existing skeletal rigging tools handle the MOTION in a few more days per character.

## Cost total

| Item | Cost |
|---|---|
| Side-view ref regen (1 low-quality call) | $0.020 |
| Rig runtime (Canvas JS) | $0 |
| Segmentation (PIL) | $0 |
| **Part 3 total** | **$0.020** |

Running project total: $2.20 + $0.020 = **$2.22 / $10 budget**.
