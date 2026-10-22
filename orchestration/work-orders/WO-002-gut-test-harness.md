---
id: WO-002
title: GUT test harness and headless test command
status: ready
assignee: claude
fallback: false
size: S
phase: 0
depends_on: [WO-001]
gpu: false
playtest: false
created: 2026-10-21
---
## Goal
Godot tests run headless with one command, so `wo.py` can test every work order automatically.

## Context
- Read first: `AGENTS.md` (Testing section), `orchestration/config.json` (`test_command`).
- Assigned to the Claude worker because it needs network access to fetch GUT.

## Files in scope
- `game/addons/gut/` (create: the GUT addon, latest 9.x release compatible with the project's Godot 4 version)
- `game/project.godot` (modify: enable the GUT plugin)
- `game/tests/test_smoke.gd` (create)
- `game/.gutconfig.json` (create)
- `docs/asset-licenses.md` (modify: add GUT's license line)
- `orchestration/config.json` (modify: set `test_command` to the working command, using `test_command_after_wo_002` as the starting point, then delete that helper key)

## Requirements
1. Install GUT by cloning or downloading the official release from github.com/bitwes/Gut and copying only `addons/gut` into `game/addons/gut`. Don't commit the rest of the GUT repo.
2. `test_smoke.gd` checks that the boot scene loads and the viewport is 640×480.
3. This command exits with code 0 when tests pass and non-zero when they fail:
   `godot --headless --path game -s res://addons/gut/gut_cmdln.gd -gdir=res://tests -gexit`
4. Prove it: temporarily make a test fail, confirm the non-zero exit, then revert. Note the result in the report.

## Acceptance criteria
- [ ] The headless command passes on a clean checkout.
- [ ] A failing test produces a non-zero exit (verified, then reverted).
- [ ] GUT license recorded in `docs/asset-licenses.md`.
- [ ] Report written to `orchestration/reports/WO-002.md`, including the exact Godot executable name used.
