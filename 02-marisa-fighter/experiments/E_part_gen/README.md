# Experiment E: Generate parts directly (how Spine pipelines actually work)

> User's push after D shipped: "正经动作游戏应该不会用你这套方案。你能生成身体的部件，而不是生成整个身体以后切吗?" — The Spine / Live2D industry workflow is that artists draw the character **in pieces from the start**, not as a whole to be cut up. Parts have intentional joint-overlap regions. Can gpt-image-2 do this directly?

## Answer: yes, in ONE API call.

**Cost: $0.0153. Time: 35 seconds. Output: [asset_sheet.png](asset_sheet.png)** — 9 body parts cleanly isolated in a 3×3 grid on magenta background, each with joint-overlap stubs, in neutral rest pose.

## E1 prompt strategy (the one call)

Used `gpt-image-2` `/v1/images/edits` with:
- **Reference image**: the side-view knight (D rig's source) for identity lock
- **Size**: 1536×1536 (low quality)
- **Prompt layout**: explicit 3×3 grid, row-major, with per-cell part descriptions. Each part request includes:
  - "isolated on magenta #FF00FF"
  - "neutral rest pose" / "vertical"
  - "joint stub at top/bottom for rigging overlap"
  - "no other body parts"

See [run_e1_sheet.py](run_e1_sheet.py).

## What you get

| Cell | Part | Quality |
|---|---|---|
| 1,1 | head + hair + ear + face | ✅ Clean |
| 1,2 | torso (breastplate + tabard only, both shoulder stubs visible) | ✅ Clean |
| 1,3 | cape (flowing fabric, isolated) | ✅ Clean |
| 2,1 | upper arm + pauldron (vertical) | ✅ Clean |
| 2,2 | forearm + vambrace (vertical, no hand) | ✅ Clean |
| 2,3 | sword (blade + crossguard + pommel, isolated) | ✅ Clean |
| 3,1 | thigh + upper greave | ✅ Clean |
| 3,2 | shin + boot | ✅ Clean |
| 3,3 | kite shield (red + gold phoenix) | ✅ Clean |

**All 9 parts on the first try.** Compare this to the D rig's segmentation flow (12 rectangular cuts, needed V2 fixes for the face + ground anchor, still had cross-contamination that showed up in screenshots). E parts are **categorically cleaner** — each is pixel-perfect, standalone, and drop-in ready for a rig editor like Spine or DragonBones.

## Pipeline after the sheet is generated

1. `split_sheet.py`: each cell → chroma-key magenta → trim tight bbox → save as `parts_e1/<name>.png`.
2. `build_skeleton.py`: hand-picked pivot per part (top-of-arm for upper_arm, neck-stub for head, etc. — what a Spine rigger would click) → `skeleton_e.json` with 14 bones (some reuse the same sprite — back limbs reuse front-limb sprites).
3. The SAME `PuppetRig` class in `index.html` loads this skeleton + the SAME `KNIGHT_WALK` / `KNIGHT_ATTACK` / `KNIGHT_JUMP_*` / `KNIGHT_HURT` keyframe sets and plays them. Zero animation code changes.
4. Added `E · 部件直接生成` tab in the game for side-by-side comparison with D.

## D vs E — the honest comparison

| Axis | D (cut from whole) | E (direct part gen) |
|---|---|---|
| API cost | $0.02 (1 low-res side-view) | $0.02 (1 low-res asset sheet) — same |
| Segmentation difficulty | Hard — rectangles overlap, SAM ViT-B fails on thin sword | **Trivial — each cell splits cleanly by column projection** |
| Cross-contamination | Yes — thigh box stole tabard pixels, sword box stole legs | **No — each part is already isolated** |
| Joint overlap regions | Not present — raw cuts have sharp edges, rotation shows gaps | **Designed in — model adds pauldron/elbow/knee stubs when asked** |
| Part proportions | Match the original character (already anatomically correct) | ⚠️ Each part generated at independent resolution → arm may be longer than torso. Needs per-bone scale compensation in the rig OR tighter prompt constraints. |
| Rigger effort | ~30 min of bbox tuning + pivot picking | ~15 min of pivot picking (parts already clean) |
| Overall quality bar | "works but visibly rough" | "cleaner parts, still needs scale tuning" |

**Winner: E, with caveats.** The generated parts are categorically cleaner, but gpt-image-2 produces each cell at its own convenient pixel count (head 416px tall, torso 425px tall, upper_arm 356px tall — numbers don't follow a consistent body-proportion rule). So the rigger still has to scale-correct, or the prompt needs to enforce "each part should be X px tall on a common body scale."

## The lesson

**For real production pipelines, this is the right approach.** This is what Spine artists do manually, and what commercial AI tools (SpriteFlow, God Mode AI, PixelLab) expose as one-click workflows internally. The "generate whole, segment, rig" path (D) was me reinventing the problem from the wrong end.

**What I'd do next to productionize E**:
1. Prompt for explicit pixel sizes: "head 200 px tall, torso 260 px tall, thigh 200 px, shin 180 px" — so proportions match.
2. Generate BOTH arm/leg sides in separate cells (near-camera and far-camera) rather than reusing one set.
3. Automate pivot detection: for each part, find the natural joint (e.g., topmost opaque pixel of upper_arm = shoulder). Script can guess pivots, human polishes.
4. Export to Spine `.json` / DragonBones format so the rig can use commercial runtimes.

## Cost update
E experiment: **$0.0153** (one API call).
Running total: $2.22 + $0.015 = **$2.24 / $10**. Demo 2 still cheaper than a coffee.
