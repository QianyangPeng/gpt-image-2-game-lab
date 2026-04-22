# Demo 1 — Sprout to World Tree (Evolution Clicker)

> **Premise:** Incremental clicker where a magical seed evolves through 5 radical transformations into a cosmic World Tree. Built to stress-test gpt-image-2's `image-edit` endpoint for **identity-preserving transformation** — can the same entity remain recognizable through extreme form changes?

---

## TL;DR

**gpt-image-2 passed the hardest test:** it preserved a custom identity marker (the glowing golden-rune motif from the reference seed) across 5 radically different forms — from an acorn in a pot, through a sprout, sapling, and ancient ent, all the way to a cosmic world-tree deity. No hand-holding, no inpainting, no LoRA fine-tuning. Just a reference image + natural-language prompt for each stage.

This is the capability that separates gpt-image-2 from Arena ~1200-score models like Midjourney/Imagen — and it changes what's practical to produce for games.

---

## Assets generated

| Stage | Quality | Time | Cost | Tokens | Notes |
|---|---|---|---|---|---|
| 1 — Seed (reference) | high | 166s | $0.2115 | 7,180 | text-to-image |
| 2 — Sprout | medium | 51s | $0.0618 | 2,968 | image-edit w/ ref |
| 3 — Sapling | medium | 51s | $0.0618 | 2,960 | image-edit w/ ref |
| 4 — Ancient Ent | medium | 51s | $0.0618 | 2,966 | image-edit w/ ref |
| 5 — World Tree | high | 169s | $0.2200 | 8,259 | image-edit w/ ref |
| **Total** | | **8m 8s** | **$0.62** | 24,333 | |

**All 5 frames usable on first generation** — zero re-rolls. That's 100% usable-asset rate.

---

## What worked

### ✅ Identity preservation across extreme transformations

The reference seed had two distinctive marks: a **glowing golden rune** on its shell and a **warm orange-brown palette accent**. Both survived all four edits:

- Stage 1: rune on seed shell
- Stage 2: rune visible on the half-opened seed still sitting in the pot
- Stage 3: runes floating as fireflies around trunk base
- Stage 4: runes glow in the bark cracks of the ent
- Stage 5: runes are the defining visual feature of the cosmic tree's trunk

Without being explicitly told "keep the golden rune across frames", the model carried this motif forward via the reference image. The only explicit instruction each time was "same pixel-art style, same palette, evolve to X form".

### ✅ Scene coherence alongside character evolution

Asked to evolve the *environment* from "cozy windowsill pot" → "garden" → "hilltop field" → "misty forest" → "cosmic space", each scene made sense for its evolution tier. The model understood the narrative intent, not just the subject.

### ✅ Art-style lock via reference

The "32-bit JRPG pixel-art" aesthetic carried through. Stage 4 (ent) and Stage 5 (world tree) have noticeably more painterly detail — but you can tell they belong to the same visual universe.

### ✅ Instruction following

At **low quality** the initial test seed (Gate 0) came out as proper chunky pixel art when asked. That's a stark improvement over gpt-image-1.5, which tended to produce soft-shaded illustrations regardless of "pixel art" in the prompt.

---

## What didn't work / caveats

### ⚠️ Not true pixel art

Even when asking for "32-bit pixel art, clean edges, no anti-aliasing", outputs are more accurately described as **high-resolution illustrations with a pixel-art *flavor*** — visible dithering, somewhat blocky shapes, but real smooth gradients underneath. Fine for "big standee illustration" genres (clickers, visual novels, card art), but not usable as a 48×48 sprite without significant downscaling and cleanup.

### ⚠️ Reference anchoring drifted

The contract asked "base of pot/trunk at ~75-85% down the canvas". That constraint was roughly honored but not precisely — each stage composed the subject where the model judged best. For a clicker with one image per stage this is fine. For a sprite sheet needing pixel-perfect alignment, you'd still need the sprite-contract + post-process alignment workflow.

### ⚠️ API regressions from gpt-image-1.5

gpt-image-2 **removed** three params that 1.5 had:
1. `background: "transparent"` → returns 400. No alpha output.
2. `input_fidelity: "high"` → returns 400. No way to weight reference influence.
3. Stable output size control on edits — outputs may come back at different resolutions across stages.

For RPG-style sprite work that expects transparent PNG characters, this is a real step backward and forces post-processing with `rembg` or similar.

### ⚠️ Not cheap at high quality

High-quality 1024×1024 runs ~$0.21/image. A deck of 20 high-quality reference-class frames would cost ~$4. Medium drops to ~$0.06/image and is usually the right default for production frames.

### ⚠️ Slow

Medium: ~50s. High: ~170s. Serial generation means a 5-frame chain took 8 minutes. Batch API would halve cost but not speed (batch has up to 24-hr SLA).

---

## Per-stage screenshots

See `frames/` directory. The identity-preservation arc is most striking viewed as a sequence.

---

## Pipeline notes

### sprite contract approach
Defined up-front in `contract.json`:
- canvas size (1024×1024)
- style preamble (shared across all frames)
- per-frame: role, quality, reference (if any), prompt

The `pipeline/generate.py` batch runner reads this JSON and generates only missing frames; if you want to re-roll stage 3, run `--only stage3_sapling`. Incremental generation + persistent cost log.

### Cost tracking
`generation-log.json` per demo records every call's tokens, elapsed time, cost, and full prompt. Total spend across demos comes from summing these.

### Org header gotcha
This account has multiple orgs; the key's default org wasn't the verified one. gpt-image-2 was 403-blocked until I explicitly set `OpenAI-Organization: org-0g6m9oj8poyjCJgvK9Nn1XSq` on every request. Easy to miss if you only follow the simple examples.

---

## Verdict for this genre

**Incremental / evolution-based clickers: excellent fit.** One-image-per-stage gameplay lets gpt-image-2 show its strength (dramatic transformation of a recognizable entity) without hitting its weakness (strict pixel-perfect sprite alignment). You can ship a visually compelling clicker for **<$1 in assets** and a few hours of code.

---

## Cost so far

| Demo | Spend |
|---|---|
| Demo 0 (Gate 0 probes) | $0.019 |
| Demo 1 (this) | $0.617 |
| **Running total** | **$0.636** |

Budget remaining: **$10 - $0.64 ≈ $9.36**.
