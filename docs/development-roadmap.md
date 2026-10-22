# Development Roadmap — Retro AI Deity RPG

*Created 2026-10-18 · updated 2026-10-21 (orchestration and tool lineup). Companion to `design-decisions.md`.*

## How we work

Five rules for the whole project:

1. **Prove the risky parts before building anything else.** The unknowns are AI art quality, the walking illusion, AI latency, VRAM and packaging. Each gets a small throwaway test (a "spike") before real code depends on it.
2. **Build in vertical slices.** Every phase ends with something playable. Don't build all the systems first and the game last.
3. **The AI describes, the engine decides.** All AI output is structured data (JSON) that Godot validates. Any AI output can be replaced with a hand-written stub, so the game can run without AI for testing.
4. **One AI interface.** Godot talks to a single local "AI service" API. Behind it, development uses Ollama + ComfyUI and the shipped game uses llama.cpp + stable-diffusion.cpp. Changing what's behind it never touches game code.
5. **Content is data.** Biomes, props, enemies, spell effects, sound settings and God cards all live in data files with schemas, not hard-coded.

### Workflow: foreman and work orders
See `orchestration/README.md` for the full setup.

1. **Plan:** Claude (the foreman, in an interactive Claude Code session) breaks the next milestone into small, self-contained work orders in `orchestration/work-orders/`.
2. **Route:** each work order goes to **Codex** (the default for well-specified implementation), a **Claude Code worker** (architecture, AI layer, judgment-heavy or network-needing work), or **either**. "Either" work is balanced toward a target split (65/35 to start).
3. **Build:** `wo.py run-ready` runs workers in parallel, each in its own git worktree and branch. Tests run automatically afterward.
4. **Review:** the *other* agent cross-reviews, then the foreman merges or sends the work back with rework notes.
5. **Playtest:** Zack plays anything marked `playtest: true` before it merges, and makes every design call.

### Tool roles
| Tool | Role |
|---|---|
| **Claude Code (foreman)** | Plans, writes work orders, reviews, merges, keeps the docs current |
| **Codex** | Main implementation worker: scenes, UI, data plumbing, tests, tooling |
| **Claude Code (worker)** | Architecture, AI service and prompts, God systems, anything ambiguous or needing network access |
| **OpenClaw** | Remote control from the phone: board status, dispatching, pings for playtests and blocked work, optional overnight runs. It can't merge. |
| **ComfyUI** | Local image generation during development (SDXL plus a retro LoRA), driven through its API by `tools/art_pipeline` |
| **NovelAI** | Concept art, style exploration, test God portraits and reference images. Outputs go through `pixelize.py`. Review anything before shipping it. |
| **ChatGPT** | Image generation for concept art, UI mockups, item icons, spell-effect references and style sheets. Good at following detailed layout instructions. Outputs go through `pixelize.py` like everything else. |
| **16 GB GPU** | ComfyUI and local models. One GPU job at a time (`gpu: true` work orders). Coding agents run in the cloud and don't use it. |
| **Zack** | Design decisions, playtesting, final call on look and feel |

---

## Phase 0 — Foundations

Goal: a repo the AI agents can work in without losing the plot.

- [ ] GitHub repo, orchestration kit, `AGENTS.md` / `CLAUDE.md`, Git LFS for art and audio.
- [ ] WO-001 Godot project skeleton with 640×480 pixel-perfect scaling.
- [ ] WO-002 GUT test harness and headless test command.
- [ ] WO-003 Data schemas v0: God card, NPC record, scene node, world event, spell descriptor.
- [ ] WO-004 Godot content loader with validation.
- [ ] WO-005 AI service contract, stub server and Godot `AIService` client.

**Done when:** the project boots, tests run headless, and the schemas, content loader and stubbed AI service are merged.

## Phase 1 — Technical spikes (throwaway, de-risking)

| # | Spike | Question it answers | Pass criteria |
|---|---|---|---|
| S1 | Art pipeline (WO-006, WO-007) | Can local AI make art that looks 90s and consistent? | One backdrop, 3 props and a merchant sprite go through generate → bg removal → pixelize → palette, and look like one game |
| S2 | Road illusion | Does layered zoom/scale "walking" feel good? | A Godot scene using the S1 art reads as walking forward |
| S3 | AI dialogue | Can the model return an NPC line + 3 choices as valid JSON, fast enough? | 95%+ valid JSON, response in a few seconds on the 4070 Ti Super |
| S4 | VRAM sharing | Can the language model and SDXL stay loaded together on 16 GB? | Both loaded; timings and peak VRAM recorded |
| S5 | Shipping runtime | Can llama.cpp + stable-diffusion.cpp run as bundled processes called from Godot? | Godot starts both and gets text and an image back, with no Python |

**Go/no-go:** go back over the design based on the results. If S1 fails, the art plan changes (custom LoRA, more hand-made assets, a different model) before anything else gets built.

## Phase 2 — Vertical slice: "Road to the Shrine"

A small playable game, built in this order:

1. **Road and map:** 5–10 road nodes, one or two branches, forward/back movement, a map that fills in.
2. **Dialogue:** one traveler NPC, 3 choices plus free text, dialogue history.
3. **Store:** a merchant with a Store button, buy/sell, and the engine validating transactions.
4. **Combat:** one enemy, the full menu, hit and death effects, one spell from the effects library.
5. **God card:** one native deity card plus importing a SillyTavern card with the isekai prompt. The God sets the tone for the slice.
6. **Shrine:** communing with the God at a shrine.
7. **Audio:** synthesized sound effects, 2–3 MIDI tracks, a few voiced lines through Kokoro with the crunch filter.
8. **Save/load:** JSON.

**Done when:** a stranger can play 15–20 minutes, and two different God cards produce noticeably different playthroughs.

## Phase 3 — The living world (God systems)

- [ ] Generating the world from a God card: biomes, route graph, settlements, factions, lore.
- [ ] Memory stores: canon, NPC memory, world state, story threads, player history, God notes, event log.
- [ ] An event system that decides when AI calls happen.
- [ ] Quests that come from conversations (commitments the player makes).
- [ ] Divine Influence, ranks and domains.
- [ ] Generating art ahead of the player, plus the asset cache and the "God is shaping the world" loading screen.
- [ ] A content filter for imported cards.

**Done when:** a 2–3 hour session holds together without continuity breaking.

## Phase 4 — Content and polish

- [ ] 8–10 biomes with prop sets.
- [ ] The full spell effects library (10–15).
- [ ] An enemy roster with color-swapped variants.
- [ ] Music for each situation, influenced by the God.
- [ ] Settings, key rebinding, accessibility, UI polish.
- [ ] Balancing and long-session playtesting.

## Phase 5 — Packaging (single-player release candidate)

- [ ] A Windows installer.
- [ ] Model downloads on first launch, with progress and resume.
- [ ] Hardware detection that warns or refuses below 16 GB VRAM, plus an option to use an external model server or API.
- [ ] The fallback art pack.
- [ ] A license audit of every model, LoRA, soundfont and asset pack (`docs/asset-licenses.md`).
- [ ] Testing on 3–5 other people's machines with different GPUs.

**Done when:** someone who isn't technical installs and plays it with no help.

## Phase 6 — Multiplayer

1. **Co-op:** host-authoritative with GodotSteam. Guests receive the art and AI output from the host.
2. **Two simulated worlds:** run two worlds locally and pass events between them through a local Super God.
3. **Federation mailbox:** the small service + SQLite (or Cloudflare Workers + D1), signed events, a mailbox you pull on launch.
4. **Super Gods:** scheduled batch processing, crossover proposals, receiving worlds can veto.
5. **Traveling NPCs:** NPCs and their sprites moving between worlds, with untrusted-content sanitizing.

## Phase 7 — Release

- [ ] Steam page, trailer, Early Access decision.
- [ ] Final check of system requirements against benchmarks.
- [ ] Content policy and Steam AI-content disclosure.

---

## Decisions blocking early phases

- **Before Phase 1:** none. The spikes can start now. WO-007 needs Zack's ComfyUI workflow exported in API format.
- **Before Phase 2:** the art style source (custom LoRA or licensed one), based on the S1 results.
- **Before Phase 5:** the recommended VRAM tier, the remote-model option, the content policy.
- **Before Phase 6:** whether Steam is the main storefront.
