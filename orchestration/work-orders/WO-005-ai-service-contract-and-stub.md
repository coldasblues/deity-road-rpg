---
id: WO-005
title: AI service contract, stub server and Godot AIService client
status: ready
assignee: claude
fallback: true
size: M
phase: 0
depends_on: [WO-001, WO-003]
gpu: false
playtest: false
created: 2026-10-21
---
## Goal
Define the one interface between the game and every AI model, and make it work end to end in **stub mode** (canned fixtures, no models). Later work orders plug in Ollama, ComfyUI and finally llama.cpp / stable-diffusion.cpp behind the same contract.

## Context
- Read first: `AGENTS.md` (golden rules 1, 3 and 4), `docs/design-decisions.md` §3, §6, §7, §8, and the schemas from WO-003.
- The dev backends will be Ollama (`http://127.0.0.1:11434`) and ComfyUI (`http://127.0.0.1:8188`). Don't call them in this work order. Just leave adapter stubs with TODOs.

## Files in scope
- `ai-service/API.md` (create: the contract)
- `ai-service/server.py`, `ai-service/requirements.txt`, `ai-service/adapters/{stub,ollama,comfyui}.py`, `ai-service/tests/test_server.py` (create)
- `data/fixtures/ai/*.json` (create: canned responses)
- `game/autoload/ai_service.gd` (create; autoload `AIService`), `game/tests/test_ai_service.gd` (create)
- `game/project.godot` (modify: autoload entry only)

## Requirements
1. **Contract** (`API.md`), local HTTP + JSON, versioned under `/v1`:
   - `GET /v1/health`: backend names, loaded models, GPU-busy flag.
   - `POST /v1/dialogue`: input is the NPC id, God card id, the last N dialogue turns, the player's message and world facts. Output is `{ "npc_line": str, "choices": [3 strings], "intents": [...], "memory_note": str }`. `intents` are *proposals* (e.g. `offer_quest`, `refuse_service`, `discount`) that the engine validates.
   - `POST /v1/image`: input is `kind` (backdrop | prop | sprite | portrait), prompt parts, seed and size. Output is a job id. `GET /v1/image/{id}` returns status and the PNG path when ready.
   - `POST /v1/god/propose`: input is recent world events. Output is a list of `world_event` objects with `status: "proposed"`.
   - Error format, and timeouts per endpoint.
2. **Server:** Python standard library `http.server` *or* FastAPI (pick one and justify it in the report). `--backend stub` serves fixtures from `data/fixtures/ai/`. Binds to 127.0.0.1 only.
3. **Godot client:** `AIService` with async methods (`await AIService.dialogue(req)`) using `HTTPRequest`. Validates every response with `SchemaCheck` if WO-004 has merged, otherwise required-key checks. Falls back to local fixtures if the server is unreachable (stub mode works with no server at all).
4. Tests: Python tests for each endpoint in stub mode, and a GUT test that runs `AIService` in no-server fixture mode.

## Acceptance criteria
- [ ] `API.md` is complete enough that another agent could write a backend adapter from it alone.
- [ ] `python ai-service/server.py --backend stub` serves all endpoints, and the Python tests pass.
- [ ] The GUT test passes headless with no server running.
- [ ] No network calls to real models anywhere in this work order.
- [ ] Report written to `orchestration/reports/WO-005.md`, with open questions about the contract.
