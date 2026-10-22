---
id: WO-004
title: Godot content loader with required-field validation
status: ready
assignee: codex
fallback: true
size: M
phase: 0
depends_on: [WO-002, WO-003]
gpu: false
playtest: false
created: 2026-10-21
---
## Goal
Godot can load the JSON content and fixtures from `data/`, reject malformed data with clear errors, and expose it through one autoload. This is the engine side of "the AI describes, the engine decides".

## Context
- Read first: `AGENTS.md`, `data/schemas/README.md` and the schemas from WO-003.
- Godot has no JSON Schema library. Implement a small validator that checks required fields, types and enums for the five schemas. Full validation stays in the Python tool.

## Files in scope
- `game/autoload/content_db.gd` (create; register as autoload `ContentDB` in `game/project.godot`)
- `game/scripts/data/schema_check.gd` (create)
- `game/tests/test_content_db.gd`, `game/tests/test_schema_check.gd` (create)
- `game/project.godot` (modify: autoload entry only)

## Requirements
1. `ContentDB.load_dir(path: String) -> int` loads every `.json` under a path (outside `res://` too, for user data later) and returns how many loaded.
2. `ContentDB.get_god_card(id)`, `get_npc(id)`, `get_scene_node(id)`, `get_spell(id)` return typed Dictionaries, or `{}` with a pushed error.
3. `SchemaCheck.validate(kind: String, data: Dictionary) -> PackedStringArray` returns human-readable errors (empty means valid). Checks required keys, basic types and enum values, read from the schema JSON files themselves so they stay in sync.
4. Invalid files are skipped with `push_warning` naming the file and the errors. They never crash the game.
5. Tests load `data/fixtures/examples`, check that every example is valid, and check that a broken in-memory example returns errors.

## Acceptance criteria
- [ ] All tests pass headless.
- [ ] Loading the fixtures produces zero warnings.
- [ ] The enum and required-key lists come from the schema files, not copied into GDScript.
- [ ] Report written to `orchestration/reports/WO-004.md`.
