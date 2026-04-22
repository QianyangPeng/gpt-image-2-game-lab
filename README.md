# gpt-image-2 Game Lab

Testing **Claude Opus 4.7 + gpt-image-2 + Claude Code** as a complete game-asset pipeline. Goal: quantify gpt-image-2's production potential for game development across different genres.

## Demos

| # | Demo | Genre | Stress test | Assets cost | Play |
|---|---|---|---|---|---|
| 01 | [Sprout to World Tree](01-evolution-clicker/) | Incremental clicker | Identity preservation across 5 extreme transformations | $0.62 | [▶ Play](https://qianyangpeng.github.io/gpt-image-2-game-lab/01-evolution-clicker/) |
| 02 | [Marisa Kirisame — Fighter Training](02-marisa-fighter/) | 2D fighter move set | 14 animation frames of same character, outfit/identity locked | $1.19 | [▶ Play](https://qianyangpeng.github.io/gpt-image-2-game-lab/02-marisa-fighter/) |

More coming.

## Pipeline

- `pipeline/generate.py` — reads a `contract.json` per demo, generates only missing frames, logs cost per call
- Each demo's `contract.json` encodes the sprite/asset spec up-front (canvas size, style preamble, per-frame prompts and refs)
- Each demo's `generation-log.json` records token/cost/time per frame

## API notes (gpt-image-2, April 2026)

Compared to gpt-image-1.5, `gpt-image-2`:
- ✅ Better instruction following (produces actual pixel-art when asked)
- ✅ Cheaper at low quality (~55% less for the same output)
- ✅ Stronger identity preservation via `image-edit` with reference
- ❌ Does not support `background: "transparent"` (regression)
- ❌ Does not support `input_fidelity` parameter (regression)
- ⚠️ Requires **organization verification** to access
- ⚠️ Key's default org may not be the verified one — set `OpenAI-Organization` header explicitly

## Cost log

See each demo's `findings.md`.
