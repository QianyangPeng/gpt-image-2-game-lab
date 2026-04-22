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
