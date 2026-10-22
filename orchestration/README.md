# Orchestration: how this game gets built

**Claude is the foreman** and writes work orders. **Codex and Claude Code workers** implement them in parallel, each in its own git worktree. **Zack** makes the design calls and playtests. **OpenClaw** (optional) is the remote control from your phone.

```
 Zack ──decides/playtests──► Foreman (Claude Code, interactive, on main)
                                  │ /foreman: writes WO-NNN.md files
                                  ▼
                        orchestration/work-orders/  (status: ready)
                                  │ wo.py run-ready
                ┌─────────────────┴─────────────────┐
                ▼                                   ▼
   Codex worker (codex exec)            Claude Code worker (claude -p)
   worktree ../<repo>-worktrees/WO-001  worktree ../<repo>-worktrees/WO-002
                │ commits + report                  │
                └─────────────────┬─────────────────┘
                                  ▼  status: review (tests run automatically)
                    /review-wo: cross-review by the OTHER agent
                                  ▼
                        merge to main  or  rework
```

## Work-order lifecycle
`draft → ready → in_progress → review → done`. Side paths: `rework` (back to a worker with notes) and `blocked` (the agent failed and the foreman needs to look).

## One-time setup (Windows 11)
1. **Prerequisites on PATH:** `git`, `python` 3.10+, `godot` (Godot 4 console executable, or set its real name in `config.json` → `test_command`), `codex` (Codex CLI, logged in), `claude` (Claude Code, logged in).
2. Copy this starter kit into the root of your game repo and commit it.
3. `python orchestration/scripts/wo.py init`
4. Check both agents work headless, from the repo root:
   - `echo "Reply with OK" | codex exec --sandbox read-only -`
   - `echo "Reply with OK" | claude -p`
5. **Dry run:** `python orchestration/scripts/wo.py run-ready --dry-run` shows which agent each ready work order would go to, and the exact command.
6. If a CLI flag changed in a new Codex or Claude Code version, fix it in `config.json` → `agents`. The script itself doesn't need changing.

## Daily use
| You want to… | Do this |
|---|---|
| Plan and start the next batch | Open Claude Code in the repo, type `/foreman` |
| See status | `python orchestration/scripts/wo.py board` |
| Run everything that's ready | `python orchestration/scripts/wo.py run-ready` |
| Review finished work | `/review-wo` in Claude Code |
| See the Codex vs Claude split | `python orchestration/scripts/wo.py ledger` |
| Playtest a work order before it merges | Open `../<repo>-worktrees/WO-NNN/game/project.godot` in Godot |

## Splitting usage between Codex and Claude
- `target_split` in `config.json` (default **65% Codex / 35% Claude**) applies to work orders marked `either`. The dispatcher sends each one to whichever agent is furthest under its target, measured in agent-minutes over the last 20 runs.
- Work orders assigned to a specific agent go to that agent. If it's rate-limited, `fallback: true` sends the work to the other agent, and the limited agent cools down for 60 minutes.
- Reviews always go to the *other* agent. Claude's work gets reviewed by Codex and vice versa, so neither model grades its own work.
- The foreman's own Claude usage (planning and review) isn't in the ledger. Keep it lean: plan, review, delegate.

## Files
| Path | What it is | In git? |
|---|---|---|
| `work-orders/WO-NNN-*.md` | The work orders (front-matter fields + spec) | yes |
| `reports/WO-NNN.md` | The worker's report (arrives with the merge) | yes |
| `templates/` | Work-order, worker-prompt and review-prompt templates | yes |
| `config.json` | Agent commands, split, parallelism, test command | yes |
| `scripts/wo.py` | The dispatcher (Python standard library only) | yes |
| `runs/` | Prompts, logs, summaries, `ledger.jsonl` | **no** (gitignored) |

## Safety defaults
- Codex runs with `--sandbox workspace-write` (it can only write inside its worktree; no network by default). Reviews run read-only.
- Claude workers run with `acceptEdits` plus an allowlist of `git`, `godot` and `python` commands. Reviews run with `dontAsk` (read-only tools).
- Never switch to `--yolo` / `--dangerously-*` modes on your real machine.
- Merging only happens through the foreman's review. OpenClaw can't merge.
