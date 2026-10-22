# AGENTS.md: rules for every AI agent working in this repo

Codex reads this file automatically. Claude Code reads it through `CLAUDE.md`. Humans should read it too.

## The game in two lines
A retro 1990s PC-style fantasy "road RPG" built in Godot 4. An AI deity, defined by a character card, shapes the world, quests, NPCs and story. The full design is in `docs/design-decisions.md` and the plan in `docs/development-roadmap.md`. Read the sections that apply to your task; don't guess the design.

## Golden rules
1. **The AI describes, the engine decides.** Language-model and image-model output is *data* (JSON or PNG). Godot validates it against a schema and resolves every outcome: damage, gold, inventory, movement, world state. AI text never directly changes game state.
2. **Content is data.** Biomes, props, enemies, spells, sound settings, items and God cards live in `data/` as JSON validated by `data/schemas/`. Don't hard-code content in scripts.
3. **One AI interface.** Godot only talks to AI through the `AIService` autoload, which calls the local service in `ai-service/`. Never call Ollama, ComfyUI or any model API directly from game code.
4. **Every AI path has a stub.** Any feature that uses AI must also run from fixtures in `data/fixtures/`, so the game and tests work with no models loaded.
5. **Spikes are throwaway.** Experiments go in `spikes/<name>/`. Never import spike code into `game/`.
6. **Stay in scope.** If you are a worker on a work order, touch only its "Files in scope".

## Repo layout
```
game/                 Godot 4 project (project.godot lives here)
  scenes/             .tscn scenes, grouped by feature (road/, dialogue/, combat/, ui/)
  scripts/            .gd scripts not owned by a single scene
  autoload/           singletons (keep this list short)
  tests/              GUT tests (test_*.gd)
  addons/             third-party Godot addons (GUT)
  assets/             hand-made art/audio shipped with the game (Git LFS)
ai-service/           local AI service: HTTP API the game calls (dev: Ollama + ComfyUI adapters)
tools/                offline pipelines (art_pipeline/, audio/), Python
data/
  schemas/            JSON Schemas (draft 2020-12)
  content/            game content JSON
  fixtures/           canned AI responses for stub mode and tests
docs/                 design docs
spikes/               throwaway experiments
orchestration/        work orders, dispatcher, reports (see orchestration/README.md)
```

## Godot / GDScript conventions
- Godot 4.x, GDScript with **static typing everywhere** (`var hp: int = 10`, typed function signatures).
- Files and folders `snake_case`; classes `PascalCase` with `class_name` only when other scripts need the type.
- Internal resolution **640×480**, stretch mode `viewport`, aspect `keep`, integer scaling, nearest-neighbor filtering. Don't change these settings.
- Prefer signals over reaching into other nodes. No `get_node("../../..")` chains.
- UI text that comes from content or AI goes through one place, so it can be validated and later localized.
- Every new script that has logic gets a GUT test in `game/tests/`.

## Python conventions (tools/, ai-service/)
- Python 3.11+. Each tool folder has its own `requirements.txt`. Type hints, `pathlib`, no global state.
- Scripts take CLI arguments and never use hard-coded user paths.

## Testing
- Godot: `godot --headless --path game -s res://addons/gut/gut_cmdln.gd -gdir=res://tests -gexit` (the executable name may differ on Windows; see `orchestration/config.json`).
- Python: `python -m pytest` inside the tool folder.
- Tests must not need a GPU, a running model or the network. Use fixtures.

## Environment limits for workers
- You may not have network access. If a dependency is missing, add it to the right requirements file or note it in your report. Don't vendor random binaries.
- Don't start ComfyUI, Ollama or other GPU jobs unless the work order says `gpu: true`.
- Never commit secrets, API keys, model weights (`.safetensors`, `.gguf`, `.ckpt`) or generated caches.

## Licenses
Every third-party asset, model, LoRA, soundfont or addon gets a line in `docs/asset-licenses.md` (name, source URL, license, commercial use OK?). No line means it doesn't ship.

## Git
- Work-order branches are `wo/WO-NNN`, and commits start with `WO-NNN: `.
- Don't rewrite history on `main`. Don't force-push.
