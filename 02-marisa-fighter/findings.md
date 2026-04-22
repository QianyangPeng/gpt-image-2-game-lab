# Demo 2 — Marisa Kirisame Fighter Training

> **Premise:** Can gpt-image-2 produce a usable 2D fighting-game character move set — one character, 14 animation frames — with enough identity/outfit consistency that a player wouldn't notice anything weird mid-combo? This is the depth test I promised after Demo 1 underperformed on pairwise consistency.

---

## TL;DR

**Keyframes: genuinely revolutionary.** The same Marisa with the same outfit, hat, braid, apron-bow, boots, and Hakkero shows up across all 14 frames with no "different character" moments. One frame — the Master Spark firing shot — is honest-to-god splash-art quality on its own.

**Tween animation (esp. walk cycle): still not there.** The model pushes back against *small* pose deltas — when I ask for frame 2 of a 4-frame walk it largely redraws frame 1 with minor tweaks, rather than advancing the pose meaningfully. Chaining each frame off the previous helped but didn't solve it. For pixel-perfect animation loops you still need an animator.

So: gpt-image-2 lets you ship the **static asset library** of a fighting game character (portrait + idle + action keyframes + hurt + victory) for ~$1.20. It does **not** let you ship the in-between frames.

---

## Assets generated (14 frames)

| # | Frame | Quality | Time | Cost | Reference |
|---|---|---|---|---|---|
| 01 | idle_front (master) | high | 124s | $0.2127 | text-to-image |
| 02 | idle_breath_a | medium | 54s | $0.0627 | 01 |
| 03 | idle_breath_b | medium | 47s | $0.0626 | 02 |
| 04 | walk_1 | medium | 45s | $0.0628 | 01 |
| 05 | walk_2 | medium | 52s | $0.0627 | 04 |
| 06 | walk_3 | medium | 46s | $0.0627 | 05 |
| 07 | walk_4 | medium | 49s | $0.0627 | 06 |
| 08 | broom_slash_windup | medium | 52s | $0.0628 | 01 |
| 09 | broom_slash_strike | medium | 49s | $0.0627 | 08 |
| 10 | broom_slash_recover | medium | 51s | $0.0627 | 09 |
| 11 | master_spark_charge | medium | 51s | $0.0628 | 01 |
| **12** | **master_spark_fire** | **high** | **148s** | **$0.2210** | 11 |
| 13 | master_spark_recover | medium | 50s | $0.0628 | 12 |
| 14 | hurt | medium | 48s | $0.0628 | 01 |
| **Total** | | | **~14m** | **$1.1866** | |

All 14 frames usable on first generation — **zero re-rolls**. Same as Demo 1.

---

## Strong results

### ✅ Identity lock — the real win

Outfit components preserved across every single frame:
- Black pointed witch hat + red ribbon + white band
- Blonde hair with long single braid
- Sleeveless black witch dress
- White frilled apron with large purple bow at waist
- Long black puffed sleeves with white cuffs
- Black knee-high buckle boots
- Octagonal brass Mini-Hakkero
- Golden eyes + confident/fierce expression per frame

None of the 14 frames has a "wait, which character is this?" moment. This would have been impossible in the 1200-score-model generation. **This IS the revolutionary capability.**

### ✅ Master Spark firing frame (12)

Requested: "rainbow laser beam erupting from Hakkero, prismatic edges". Model delivered: cone-shaped rainbow-gradient beam with magical sigil ring at origin + Hakkero glowing gold + Marisa visibly bracing against recoil. **This one frame is presentation-worthy as splash art on its own.** (high-quality budget well spent)

### ✅ Hurt frame (14)

Full knockback: hat flying off, broom dropping, body staggered back, eyes closed, star-burst impact marks. Dynamic and readable at a glance.

### ✅ Chroma key removal trivial

Asking for `#FF00FF` background + post-processing with a 20-line Python script (`pipeline/chroma_key.py`) produced clean transparent sprites. No dependency on rembg or ML segmenters. **This workaround fully compensates for gpt-image-2 dropping transparent-background support.**

---

## Weak results

### ❌ Walk cycle barely animates

Frames 04/05/06/07 look ~90% identical. The model refused to swing limbs meaningfully when told "frame 2 of 4 walking cycle". When played back at 8 fps, it reads more like "standing still with slight sway" than walking. **For a real platformer/fighter you'd have to regen each frame with much more forceful prompt deltas, or accept hand-animating the in-betweens.**

### ⚠️ Braid & broom-hand laterality drift

Reference: broom in right hand, braid on left shoulder. Side-view frames facing right: the model sometimes mirrors (braid swings to near-camera side, broom hand swaps). Within the side-view set it's internally consistent — but if you cut from idle-front directly to a walk frame mid-game, viewers notice the flip.

### ⚠️ Height/anchor drift between poses

`slash_windup` (08) has a wide stable stance = character occupies ~90% of canvas height. `slash_recover` (10) is a crouch = character ~75%. Drawn at the same anchor (feet at canvas 95%) they work fine, but the apparent "head bobbing" during the slash is more pronounced than I'd like.

### ⚠️ spark_3 (recover) facial weirdness

The exhaustion/triumphant-grin expression in frame 13 looks slightly "off" — eyes half-closed, mouth stretched wider than in other frames. Still recognizably Marisa but the least convincing frame.

---

## Comparison against Demo 1

Demo 1 (clicker) I described as "the 5 stages kept the golden-rune identity marker". You rightly pushed back that theming-level consistency isn't impressive — Midjourney could do that.

This demo's consistency is **structurally different**. Pairing any two of the 14 frames shows the same outfit details *verbatim* — down to the apron frill pattern, ribbon placement, buckle positions, and Hakkero facet count. That's the kind of cross-frame pixel-near-identity you need for game production.

So yes — Demo 2 landed where Demo 1 didn't.

---

## Game demo implementation notes

Single HTML file, ~350 lines JS. Key integration points:

- **Chroma key**: `pipeline/chroma_key.py` replaces magenta with alpha, keeps full 1024×1024 canvas (so all sprites share anchor).
- **Animation table**: frames + per-frame duration + recovery lock (`{ frames: [...], frameDurs: [...], recovers_in: N }`).
- **Facing flip**: Canvas `scale(-1, 1)` around the sprite anchor for left-facing.
- **Master Spark beam extension**: canvas `createLinearGradient` beam drawn beyond the sprite edge only during frame 2 of `spark`. Bridges the generated rainbow beam start to a long game-world laser.
- **Training dummy**: vector-drawn with canvas primitives, wobble on hit.

Gate-failure points I hit:
- Animation auto-unlocks before frames finish if `recovers_in` < sum(frameDurs). Fixed by aligning timings.
- `tryEvolve`-style bugs from Demo 1 — caught by writing dedicated test via `preview_eval`.

---

## Cost tally

| | Spend |
|---|---|
| Demo 0 (probes) | $0.02 |
| Demo 1 (clicker) | $0.62 |
| Demo 2 (this) | $1.19 |
| **Running total** | **$1.83** |

Budget remaining: **$10 − $1.83 ≈ $8.17**.

---

## What this says about gpt-image-2 for game dev

| Use case | Verdict |
|---|---|
| Character portraits / key art | ✅ Ship-ready, cheap |
| Idle / action keyframes | ✅ Ship-ready, minor manual touch-up |
| VFX burst frames (master spark, explosions) | ✅ Often better than hand-drawn for first-pass |
| Walk cycle / attack tween frames | ⚠️ Not yet — needs either hand-animation or much denser prompts |
| 4-direction sprite grid | Not tested here (Demo 3 candidate) |
| Pixel-perfect aligned sprite sheets | ⚠️ Anchor control is loose; still need sprite-contract post-processing |
| Transparent-BG sprites | ✅ Via chroma-key workaround (no API support) |

**Bottom line:** gpt-image-2 is a genuine capability jump for "asset illustrations." It is not yet a capability jump for "animation". These are two different markets and the model solves one of them.
