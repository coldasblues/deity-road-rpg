---
id: WO-007
title: ComfyUI generation client (spike S1, part 2)
status: draft
assignee: either
fallback: true
size: M
phase: 1
depends_on: [WO-006]
gpu: true
playtest: true
created: 2026-10-21
---
## Goal
Generate a road backdrop, 3 roadside props and a merchant sprite on Zack's PC through ComfyUI's HTTP API, pipe them through `pixelize.py`, and record timings and peak VRAM. This answers spike S1: does local AI art look like one 90s game?

## Before this can be set to ready (foreman: get these from Zack)
- [ ] Zack exports his ComfyUI workflow in **API format** (Save (API)) for SDXL plus his chosen pixel/retro LoRA, saved to `tools/art_pipeline/workflows/sdxl_retro_api.json`.
- [ ] Confirm the ComfyUI address (default `http://127.0.0.1:8188`) and that ComfyUI is running when this is dispatched.

## Files in scope
- `tools/art_pipeline/generate.py`, `tools/art_pipeline/prompts/s1_test_set.json`, `tools/art_pipeline/tests/test_generate.py` (mocked HTTP)
- `spikes/s1_art/` (outputs, timing CSV, contact sheet)

## Requirements
1. Load the API-format workflow, inject prompt, negative prompt, seed and size into the right nodes (found by node title, configurable), queue it via `/prompt`, poll `/history`, and download outputs via `/view`.
2. The prompt set: 1 backdrop, 3 props (tree, rock, signpost), 1 merchant sprite. Fixed style prefix, fixed seeds.
3. Post-process every output with `pixelize.py` and build a contact sheet PNG of raw vs pixelized.
4. Log seconds per image and peak VRAM (via `nvidia-smi` polling) to `spikes/s1_art/timings.csv`.

## Acceptance criteria
- [ ] One command produces all outputs, the contact sheet and the timings.
- [ ] Unit tests use mocked HTTP and pass with no GPU.
- [ ] Report written to `orchestration/reports/WO-007.md`, with timings and a pass/fail opinion on the look, for Zack to confirm.
