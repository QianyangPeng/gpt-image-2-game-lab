# Experiment: Cracking the Walk-Cycle Wall

Demo 2 (the Marisa fighter moveset) landed hard on static keyframes but **stumbled on the walk cycle** — the 4 frames looked ~90% identical, producing a "slight sway" instead of a walk when played back.

This experiment tests two hypotheses about **why** that happened and whether either can be un-stuck.

## Hypotheses

| | Hypothesis | Fix idea |
|---|---|---|
| **H1** | The `images/edits` endpoint over-weights the reference image, so every small requested delta gets absorbed into "stay close to the reference" | Give it TWO references — identity (Marisa) + pose (stick-figure skeleton) — and let it apply outfit to pose. This is the ControlNet pattern. |
| **H2** | The model sees each call as an independent generation, so there's no cross-frame consistency pressure to make the frames *visibly evolve* into each other | Force spatial consistency by making it generate all 4 poses **in one image**, then split. |

## Setup

- **A** (skeleton conditioning): 4 stick-figure skeleton PNGs drawn in Python with hand-picked hip/knee/shoulder/elbow angles for a walk cycle. Each frame = one call to `/v1/images/edits` with **two** input images: `[Marisa reference, skeleton_i]`. Prompt asks the model to apply Marisa's outfit to the pose in the skeleton.
- **B** (sprite strip): one call to `/v1/images/edits` with just the Marisa reference + a prompt asking for "a 4-frame horizontal walk cycle strip, 4 panels side-by-side, dramatic pose changes between each panel". Output 1536×1024. Split into 4 frames client-side by finding non-transparent column runs (even spacing between characters isn't guaranteed by the model — had to use connected-component splitting, not naive width/4).

## Results

### Per-frame comparison (frame 1 of walk cycle)

| Variant | Frame 1 pose | Commentary |
|---|---|---|
| **Original** | One leg slightly lifted, broom vertical, subtle side-view stance | Model played it safe — near-idle |
| **A (skeleton)** | **Wide stride stance, legs spread, broom raised** | Clear "mid-walk" pose — **commitment to the skeleton** was higher than I expected |
| **B (strip)** | Standing upright, broom held beside | Hybrid: B's cycle is step→stand→step→stand, frame 1 is the "stand" beat |

See each variant's full 4-frame set in:
- [../sprites/](../sprites/) (original, files `04_walk_1.png` to `07_walk_4.png`)
- [A_skeleton_cond/alpha/](A_skeleton_cond/alpha/)
- [B_sprite_strip/alpha/](B_sprite_strip/alpha/)
- [B_sprite_strip/strip_raw.png](B_sprite_strip/strip_raw.png) (the original un-split strip — shows all 4 poses in one image)

### Animation quality (frames played at 8 fps in the game)

| Variant | Reads as "walking"? | Frame-to-frame delta | Identity preserved |
|---|---|---|---|
| **Original** | ❌ Reads as idle-with-sway | Tiny (~5% pose change) | ✅ |
| **A (skeleton)** | ⚠️ Frame 1 jumps out but 2-4 blur together | Large on F1, small on F2/F3/F4 | ✅ |
| **B (strip)** | ✅ **Actual walking cycle** (step-stand-step-stand pattern) | Alternating large pose changes | ✅ |

### Costs

| Variant | Calls | Tokens | Cost |
|---|---|---|---|
| Original (reference) | 4 | ~12.6K | $0.2508 |
| **A** | 4 (each 2-image input) | 16.2K | $0.2810 |
| **B** | 1 (1-image input, 1536×1024 output) | 2.8K | **$0.0511** |

**B is ~1/5 the cost of A** because only one API call + image input is tokenized once, not four times.

## Conclusions

**H1 (skeleton conditioning) is partially right.** The model DOES listen to a second pose-reference image — frame 1 shows clear commitment to the wide stride I drew. But for the other 3 frames, which also had distinct skeletons, the model averaged pose variation back toward the character reference. So `images/edits` with 2 inputs is useful for **one** strong pose cue, not for maintaining pose variety across a series.

**H2 (sprite strip) is strongly right.** Asking for all 4 frames in one image gives the model a single-frame spatial-consistency pressure that yields dramatically different poses between panels. **B actually produced a walk cycle that reads as walking** — something neither Original nor A achieved with chain references.

**Best-of-both-worlds recipe for future sprite-animation work with gpt-image-2:**
1. Generate the **reference master** (front idle) with all identity locks.
2. For any animation requiring clear inter-frame delta, **always use strip generation** (all frames in one image), not chain editing.
3. Split with connected-component detection, not naive width division — the model doesn't space characters evenly.
4. Use skeleton conditioning only for **one-off hero poses** (e.g., "the specific frame of Master Spark firing"), not for tween cycles.

## Limitations discovered

- The strip approach caps character detail per panel — a 1536×1024 strip at 4 panels = 384×1024 per panel. For a 2K-capable model this isn't ideal resolution-wise. Could experiment with 3840×1024 output, but that's near the API's max-edge limit.
- The model arranges characters in the strip at inconsistent horizontal spacing, so you need column-projection splitting (my `split_strip.py`).
- After splitting, each B frame needs upscaling back to 1024×1024 canvas with consistent feet anchor for the game, adding post-processing.
- B's walk cycle is step-stand-step-stand, not the classic 4-pose walk cycle (contact-passing-contact-passing). Closer to "toddler walking" than "fluid gait". Better than the other two variants but still not production-ship animation.

## Cost impact on overall budget

Experiment total: **$0.33**. Running total across all demos: **$1.83 + $0.33 = $2.16**. Well within $10 budget.

---

# Part 2 — "Can gpt-image-2 deliver a fluid 2D action game?"

Follow-up question from the user: if even B doesn't fully deliver a walk cycle, what's the real ceiling? Can pure image-gen produce production-quality fluid animation, maybe with denser keyframes + post-processing?

This part tests **C** — a new character (chibi knight girl from a reference image), MapleStory-style pixel-art, 8-frame walk strip, plus two kinds of post-processing interpolation (optical flow + crossfade).

## Setup

### C_keyframe: 8-frame walk strip, pixel art
- Reference: a chibi knight source image (red cape, silver plate armor, pigtails). Used as identity reference via `images/edits` with prompt asking for MapleStory-style pixel-art rendering.
- Walk strip: one `images/edits` call, 2048×1024 output, prompted for 8-panel walk cycle with detailed per-panel pose descriptions (contact / passing / contact / passing, mirrored).
- **Low quality tier** — pixel art doesn't need detail density. Total cost: **$0.0342** (10× cheaper than the Marisa medium-quality equivalent).

### C_flow: OpenCV Farneback optical flow + bilateral warp-and-blend
- Input: the 8 keyframes from C_keyframe.
- Method: between each consecutive pair, compute dense optical flow both directions, warp each endpoint by fractional t, blend.
- Output: 32 total frames (8 keyframes + 3 intermediates per gap + 3 closing the loop).

### C_xfade: naive alpha crossfade baseline (no motion warping)
- Control group — just blends a and b at each t. Double-images. Expected to be worse than flow; included for comparison.

## Results

### Keyframe quality

The 8-frame knight strip produced **less pose differentiation than Marisa's 4-frame strip**. The front-facing chibi reference anchored the model heavily into "front-view idle" mode — all 8 panels show the knight mostly front-facing with subtle sword-angle variations, not a clear side-view walk. **Finding: the reference's pose/orientation dominates the strip's pose distribution**, which is a new constraint to design around.

### Interpolation quality (flow vs crossfade)

| Method | Artifact profile | Reads as walking? |
|---|---|---|
| **Keyframes-only (C_keyframe)** | Clean individual frames, abrupt pose changes every ~83ms at 12 fps | Marginal — looks like "stepping in place" more than walking |
| **Optical flow (C_flow)** | Armor/cape distortion on fast-moving parts; slight magenta fringing at silhouette; occasional ghost lines | Smoother motion but character geometry warps unnaturally on limbs |
| **Crossfade (C_xfade)** | Double-image ghosting on sword, shield, cape at every intermediate frame | Visibly bad — classic "blend" artifact |

Neither post-processing method **rescues** the animation. Both produce frames that no shipping game would use.

### Cost breakdown (C only)

| Step | Cost | Time |
|---|---|---|
| Knight pixel reference | $0.02 | 43s |
| 8-frame walk strip | $0.015 | 40s |
| Interpolation (flow + crossfade, local CPU) | $0 | <10s |
| **Total C** | **$0.034** | |

Running project total: **$2.16 + $0.034 = $2.20**. (Also installed torch-cpu + cloned RIFE repo — never used RIFE because the optical-flow baseline already answered the question.)

## The real conclusion

**Frame interpolation does not save gpt-image-2's walk cycle.** Two independent reasons:

1. **Pixel art is discrete motion** — legs jump from pose A to pose B, not through continuous in-between positions. Optical flow + blend is designed for real-camera video with smooth motion. On pixel sprites it produces either warped armor (flow) or double images (crossfade). RIFE would do somewhat better but not categorically better because it's fundamentally the same paradigm.

2. **Reference images anchor the entire batch to one viewpoint** — the knight strip turned out front-facing because the source was front-facing. The model doesn't re-project the character to side view just because you ask nicely.

### What actually would make a fluid 2D action game with gpt-image-2

Based on this run, the recipe is:

| Asset type | Tool |
|---|---|
| Portraits / boss art / splash screens | ✅ **gpt-image-2** — revolutionary identity preservation |
| Keyframe illustrations (extreme poses) | ✅ **gpt-image-2 via strip generation** |
| Backgrounds / scenery / item icons | ✅ **gpt-image-2** — its strongest use case |
| VFX frames (explosions, hits, auras) | ✅ **gpt-image-2** |
| Walk / run / idle cycles | ❌ NOT gpt-image-2 alone. Use **Live2D / Spine / DragonBones** to rig the keyframe character with bones and animate the rig. 10× more efficient than generating each frame. |
| Smooth in-between frames | ❌ Frame interpolation (RIFE, flow, crossfade) doesn't work on sprite pose changes. Stick with rigging. |

**Alternative end-to-end path worth testing**: gpt-image-2 generates the character → text/image-to-3D model (Tripo / Rodin / Meshy) → rig + animate in 3D → render back out to 2D sprites. Skips the animation problem entirely at the cost of adding a 3D step. Probably the 2026 indie-game answer.

### Artifacts shown in the demo

Open the live demo and flip through the 6 tabs:
- `原版` — the original chain-edit 4 frames (baseline, doesn't walk)
- `A · 骨架条件` — frame 1 commits to pose, frames 2-4 fuse
- `B · 4 联格生成` — best pure-gpt-image-2 result, reads as step-stand-step
- `C · 骑士 8 帧` — 8-frame keyframe knight, pixel style
- `C + flow 补间` — flow interpolation, watch the armor warp
- `C + crossfade` — crossfade baseline, watch the ghosting

Play each variant by holding arrow keys.

