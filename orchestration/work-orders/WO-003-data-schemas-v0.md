---
id: WO-003
title: Data schemas v0 (God card, NPC, scene node, world event, spell)
status: ready
assignee: claude
fallback: true
size: M
phase: 0
depends_on: []
gpu: false
playtest: false
created: 2026-10-21
---
## Goal
The first versions of the five core data contracts as JSON Schemas, with a valid example for each. Every later system builds on these, so clarity matters more than completeness.

## Context
- Read first: `AGENTS.md` (golden rules 1, 2 and 4), `docs/design-decisions.md` §2, §3, §4, §5, §6.
- God cards wrap SillyTavern Character Card V2 (`spec: "chara_card_v2"`, with `data.name`, `data.description`, `data.personality`, `data.scenario`, `data.first_mes`, `data.mes_example`, `data.character_book`, `data.extensions`). Game-specific fields go under `data.extensions.deity_rpg`, so a card still round-trips to SillyTavern.

## Files in scope
- `data/schemas/god_card.schema.json`
- `data/schemas/npc.schema.json`
- `data/schemas/scene_node.schema.json`
- `data/schemas/world_event.schema.json`
- `data/schemas/spell.schema.json`
- `data/fixtures/examples/*.json` (one valid example per schema; two God cards: one native deity, one imported character marked `origin: "isekai"`)
- `data/schemas/README.md` (one paragraph per schema: purpose, who writes it (AI or engine), who validates it)
- `tools/validate_data/validate.py`, `tools/validate_data/requirements.txt`, `tools/validate_data/test_validate.py`

## Requirements
1. JSON Schema draft 2020-12. Every schema has a `$id`, a `version` field (start at `0.1.0`), and `additionalProperties: false` on objects the AI fills in.
2. **god_card:** the ST Card V2 envelope plus `extensions.deity_rpg` with: `origin` (`native` | `isekai`), `domains` (string array), `tone` (short tags), `visual_style_hints`, `music_hints`, `voice` (`pitch`, `crunch` 0–1), `divine_influence` (int, engine-owned), `rank` (enum: Nascent, Awakened, Ascendant, Sovereign, Celestial; engine-owned).
3. **npc:** id, name, role, portrait asset ref, personality, goals, secrets, knowledge (list of fact ids), relationships, memory summary, `services` (enum list: store, forge, room, heal, trade, train, contract).
4. **scene_node:** id, type (enum: road, village, shrine, crossroads, trail, ruins, cave, inn, boss, event), biome, backdrop asset ref, prop set ref, links forward/back/branches, discovered flag, encounter refs.
5. **world_event:** id, timestamp (in-game day), type, actors, location, consequences, `cross_world_eligible`, `proposed_by` (god | engine | super_god), `status` (proposed | accepted | rejected | applied). This shape is reused by the federation later.
6. **spell:** the "AI describes, engine decides" descriptor: name, flavor text, element (enum), shape (bolt | burst | beam | rain | swirl | aura), color (hex), target (one | all | self | ally), power tier 1–5. No raw damage numbers: the engine derives those.
7. `validate.py <file-or-folder>` validates every JSON against its schema (picked by a `$schema` reference or a file-name convention) and exits non-zero on any failure. Uses the `jsonschema` package.
8. Tests: every example validates, and a broken example fails.

## Acceptance criteria
- [ ] Five schemas plus examples, all valid.
- [ ] `python tools/validate_data/validate.py data/fixtures/examples` exits 0, and a deliberately broken file makes it exit 1 (covered by tests).
- [ ] The README explains AI-owned vs engine-owned fields for each schema.
- [ ] Report written to `orchestration/reports/WO-003.md`, listing design questions for Zack.
