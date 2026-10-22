# Deity Road RPG (working title)

A retro 1990s PC-style fantasy road RPG built in Godot 4. An AI deity, defined by a character card, shapes your world, quests, NPCs and story.

- **Design:** [`docs/design-decisions.md`](docs/design-decisions.md)
- **Plan:** [`docs/development-roadmap.md`](docs/development-roadmap.md)
- **How it gets built:** [`orchestration/README.md`](orchestration/README.md). Claude is the foreman, and Codex and Claude Code are the workers.
- **Rules for AI agents:** [`AGENTS.md`](AGENTS.md)

## Quick start
```
python orchestration/scripts/wo.py board          # what's queued
python orchestration/scripts/wo.py run-ready      # build everything that's ready
```
Or open Claude Code in this folder and type `/foreman`.
