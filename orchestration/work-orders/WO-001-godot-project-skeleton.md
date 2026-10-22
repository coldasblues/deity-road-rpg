---
id: WO-001
title: Godot project skeleton with 640x480 pixel-perfect scaling
status: ready
assignee: codex
fallback: true
size: S
phase: 0
depends_on: []
gpu: false
playtest: true
created: 2026-10-21
---
## Goal
An empty Godot 4 project in `game/` that boots into a test screen at 640×480, scales cleanly to any window size with integer scaling and no blurring, and follows the folder layout in `AGENTS.md`.

## Context
- Read first: `AGENTS.md` (layout and Godot conventions), `docs/design-decisions.md` §2 (presentation).

## Files in scope
- `game/project.godot` (create)
- `game/scenes/boot/boot.tscn`, `game/scenes/boot/boot.gd` (create)
- `game/scenes/`, `game/scripts/`, `game/autoload/`, `game/tests/`, `game/assets/` (create; empty folders get a `.gitkeep`)
- `game/icon.svg` (create; any simple placeholder)
- `.gitignore`, `.gitattributes` (modify: Godot ignores, LFS rules for png/wav/ogg/mid/sf2)

## Requirements
1. Godot 4.x project named "Retro AI Deity RPG", main scene `res://scenes/boot/boot.tscn`.
2. Display settings: viewport 640×480, stretch mode `viewport`, aspect `keep`, scale mode `integer`, default texture filter `Nearest`. Window starts at 1280×960 and is resizable.
3. The boot scene shows a dark background, a 1-pixel white border around the 640×480 area, the title in a pixel-style default font, and a checkerboard test pattern in one corner to make scaling artifacts obvious.
4. Pressing `F11` toggles fullscreen. The input action `toggle_fullscreen` is defined in the project settings.
5. `.gitignore` covers `.godot/` (Godot 4's cache; keep `*.import` files *committed*), `export_presets.cfg`, `orchestration/runs/`. `.gitattributes` routes png, wav, ogg, mid and sf2 files through Git LFS.

## Acceptance criteria
- [ ] The project opens in Godot 4 with no errors and runs the boot scene.
- [ ] Resizing the window keeps sharp pixels and black bars, with no blur.
- [ ] F11 toggles fullscreen.
- [ ] Folder layout matches `AGENTS.md`.
- [ ] Report written to `orchestration/reports/WO-001.md`, with "How to test" steps Zack can follow in the editor.

## Notes for the worker
No game logic yet. Keep it minimal. GUT and tests come in WO-002.
