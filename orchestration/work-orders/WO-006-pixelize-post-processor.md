---
id: WO-006
title: Pixelize post-processor for AI art (spike S1, part 1)
status: ready
assignee: codex
fallback: true
size: S
phase: 1
depends_on: []
gpu: false
playtest: true
created: 2026-10-21
---
## Goal
A command-line tool that turns any generated image (from ComfyUI or NovelAI) into game-ready retro art: transparent background where needed, nearest-neighbor downscale, fixed palette, optional outline. This is the step that makes AI output look like real 90s art.

## Context
- Read first: `AGENTS.md`, `docs/design-decisions.md` §8.
- Input images come from ComfyUI, NovelAI or ChatGPT exports (any size, usually 1024px+, often with a flat or white background). Background removal will use rembg or BiRefNet later. For now, support an input that already has alpha, and a simple color-key removal of flat backgrounds.

## Files in scope
- `tools/art_pipeline/pixelize.py`, `tools/art_pipeline/palettes/default_32.gpl` (create: a 32-color 90s fantasy palette, GIMP .gpl format)
- `tools/art_pipeline/requirements.txt` (Pillow, numpy)
- `tools/art_pipeline/tests/test_pixelize.py`, `tools/art_pipeline/tests/fixtures/` (small generated test images, under 50 KB total)
- `tools/art_pipeline/README.md`

## Requirements
1. `python pixelize.py IN.png OUT.png --kind {backdrop,prop,sprite,portrait} [--palette path.gpl] [--outline] [--colorkey auto|#RRGGBB|none]`
2. Target sizes per kind: backdrop 640×360 (the road view area), portrait 96×96, sprite up to 160×200 (keep aspect), prop up to 128×128 (keep aspect). Downscale with nearest-neighbor after a light pre-blur option (`--preblur 0..2`).
3. Palette quantization without dithering by default (`--dither` to enable). Alpha stays 1-bit (fully opaque or fully clear).
4. `--outline` adds a 1-pixel dark outline around opaque regions.
5. `--preview` also writes `OUT_preview.png` scaled ×3 for viewing.
6. Batch mode: if IN is a folder, process every PNG into OUT as a folder.

## Acceptance criteria
- [ ] Tests cover each kind, palette compliance (every output pixel is in the palette), 1-bit alpha and outline.
- [ ] Runs on Windows with plain `python` once requirements are installed.
- [ ] README shows before/after usage.
- [ ] Report written to `orchestration/reports/WO-006.md`. Zack will judge the look by running it on his own ComfyUI/NovelAI images.
