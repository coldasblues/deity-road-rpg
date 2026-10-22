---
name: foreman
description: Run the game's build loop as foreman - read the roadmap, break the next milestone into work orders, route each to Codex or a Claude Code worker, and dispatch them with orchestration/scripts/wo.py. Use when Zack says "foreman", "what's next", "plan the next phase", "dispatch", or "keep going".
---

# Foreman loop

The dispatcher is `python orchestration/scripts/wo.py` (call it `WO` below). On Windows, use `py` if `python` isn't on PATH.

## 1. Get your bearings (cheap)
1. `WO board` and `WO ledger`.
2. Read only the current phase section of `docs/development-roadmap.md`.
3. If anything is in `review`, run `/review-wo` on it before planning new work. Finishing work beats starting work.

## 2. Plan the next slice
- Pick the next unchecked roadmap items for the current phase. Plan **3–8 work orders**, not the whole phase.
- Size: **S** (under 30 min, 1–3 files), **M** (a focused feature, ≤6 files). **No L**: split it.
- Each work order must be **self-contained**. The worker never sees this conversation. Include:
  - which design-doc sections apply (by section number)
  - exact files in scope
  - data shapes (paste example JSON)
  - checkable acceptance criteria, including tests
- Express ordering with `depends_on`. Run independent work in parallel.
- Create each one with `WO new "Title" --assignee <codex|claude|either> --size <S|M> --phase <n> [--depends WO-00X ...] [--gpu]`, then fill in the generated file.

## 3. Route
| Send to **codex** (default for most implementation) | Send to **claude** (worker) |
|---|---|
| Scenes and UI screens built from a clear spec | Cross-cutting architecture: autoloads, save system, scene flow |
| Data loading, validation, plumbing | AI-service layer, prompts, JSON contracts for God/NPC output |
| Tests and the test harness | God systems, memory, narrative and quest logic |
| Tooling scripts with clear inputs/outputs (art/audio pipelines) | Specs with real judgment calls or ambiguity |
| Bug fixes with a repro, refactors with an explicit target | Anything that needs network access (cloning addons, fetching docs) |

- Use **either** for everything else. The dispatcher balances these toward the target split in `orchestration/config.json` (default 65% Codex / 35% Claude by agent-minutes).
- Leave `fallback: true` (the default) so a rate-limited agent's work moves to the other one. Set it to `false` only when the work truly needs one specific agent.
- Mark `gpu: true` only when the work runs ComfyUI or a local model. Only one GPU job runs at a time.
- Mark `playtest: true` when Zack has to see or feel the result (movement, combat feel, art).

## 4. Release and dispatch
1. `WO set <id> status=ready` for each finished draft.
2. Commit the work orders: `git add orchestration/work-orders && git commit -m "Foreman: work orders for <milestone>"`.
3. Dispatch with `WO run-ready`. Runs can take a while, so start it in the background and keep working.
4. **Check with Zack first** when a batch has more than 8 work orders, any `gpu: true` work (he may be using the GPU), or anything that changes a DECIDED design item.

## 5. After a run
- `WO board`. Run `/review-wo` on each item in `review`.
- Anything `blocked`: read `orchestration/runs/<id>/<latest>/stderr.log` and the report, then fix the work order (scope, missing info, dependency) and set it back to `ready`.
- Tell Zack in a few lines what merged, what's in rework, what needs him (playtests, decisions), and the ledger split.

## Token discipline
- You plan and review. You don't implement.
- Read reports and verdicts before diffs, and use `git diff --stat` before a full diff.
- If the ledger shows Claude far over target, route more `either` work to Codex. If Codex is cooling down from a rate limit, the fallback handles it automatically.
