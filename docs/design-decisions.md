# Design Decisions — Retro AI Deity RPG (working title)

*Last updated: 2026-10-21. Source: "Design 2D RPG" ChatGPT conversation + follow-up planning with Claude.*

Status key: **DECIDED** = Zack chose it · **PROPOSED** = recommended, not yet confirmed · **OPEN** = needs a decision

---

## 1. Identity

**DECIDED** — A retro 1990s PC-style fantasy "road RPG" where an AI deity, defined by a character card, shapes your world, quests, NPCs and story. It should look like a Windows 95-era game and behave like modern AI roleplay.

Pillars:
1. Retro road exploration
2. AI roleplay dialogue
3. Turn-based retro combat
4. Deity-driven playthrough identity
5. Two deity modes (native and imported)
6. Mythic GM presence (the deity is both an in-world god and the hidden narrative manager)

## 2. Presentation

- **DECIDED** — Movement is locked: forward and back along a road, always facing it head-on. No looking left or right.
- **DECIDED** — The walking illusion uses layers: the backdrop zooms in, the road scrolls, and roadside props scale up and slide off the screen edges.
- **DECIDED** — NPCs and monsters are static avatars placed in front of the background. No character animation.
- **DECIDED** — The world is procedural, and a map fills in as you explore.
- **DECIDED** — Minimal UI: inventory menu, slash button, quick-cast button.
- **PROPOSED** — 640×480 internal resolution, scaled up pixel-perfect. Pixel portraits, grid inventory, parchment map.
- **PROPOSED** — The world is a graph of route nodes (village, shrine, crossroads, trail, ruins, cave, inn, boss, event), not a free-roaming space.

## 3. Dialogue and services

- **DECIDED** — The AI language model runs NPCs, roleplay-style. Each NPC line comes with 3 generated reply choices plus free-text input.
- **DECIDED** — Shops open from a small **Store** button on the dialogue screen (RPG Maker style), not by asking in conversation.
- **PROPOSED** — Context buttons for other services: Forge/Repair, Rent Room, Heal, Trade, Train, Show Contract.
- **PROPOSED** — The world pauses during dialogue.
- **PROPOSED** — Quests come out of commitments the player makes in conversation. There's no "Accept Quest" button.

## 4. Combat

- **DECIDED** — Turn-based, in the style of RPG Maker / Final Fantasy II.
- **PROPOSED** — Menu: Attack / Magic / Item / Defend / Flee. First-person, Dragon Quest style: the enemy lunges at the camera when it attacks.
- **PROPOSED** — Every effect is code applied to static sprites (hit flash, shake, knockback, dissolve on death, status tints, damage numbers, screen shake), plus a weapon sprite that swings in an arc.
- **PROPOSED** — A hand-made library of ~10–15 spell effect animations, recolored per spell. The AI describes a spell (element, shape, color, target) and the engine assembles it from the library.

## 5. Gods (AI Game Masters)

- **DECIDED** — The GMs are called **Gods**. The cross-world coordinator is the **Super Gods**.
- **DECIDED** — A God's power grows with how much its player has explored and accomplished.
- **DECIDED** — A God is both a real in-universe deity and the player's AI storyteller, partly visible to the player.
- **DECIDED** — Two deity types:
  1. A card written specifically as a deity.
  2. Any imported SillyTavern character card, given the prompt: *"this {{char}} has been isekaid into being the deity of this new world for {{user}}."*
- **DECIDED** — The deity card drives the style and content of the whole playthrough: lore, quests, NPC tone, monsters, items, music, voice and event framing.
- **PROPOSED** — Divine Influence weights: Exploration 30%, Achievements 30%, World Impact 25%, Discovery 15%, with diminishing returns.
- **PROPOSED** — Divine ranks: Nascent → Awakened → Ascendant → Sovereign → Celestial. A higher rank widens a God's reach but never lets it break the rules.
- **PROPOSED** — Domains (Knowledge, Conquest, Wild, Secrets…) emerge from how the player plays.
- **PROPOSED** — The player talks to their God through shrines, dreams, relics or a Pray menu: guidance, the land, fate, blessing, speak freely.
- **PROPOSED** — Support SillyTavern Character Card V2 (PNG and JSON). Each card is wrapped in a God System Prompt, so a card's claims of omnipotence don't grant real power.
- **PROPOSED** — If a player stops playing, their God goes dormant but keeps its power and can become a legend in other worlds.

## 6. Architecture rules

- **PROPOSED** — **"The AI describes, the engine decides."** The God proposes, the NPC AI speaks and chooses, and the Godot engine validates and resolves every outcome.
- **PROPOSED** — Separate stores for world canon, character memory, world state, story threads, player history, God notes, and an event log.
- **PROPOSED** — AI calls are triggered by events (dialogue, major actions, entering a region, a day passing), not run constantly.

## 7. Engine, tech and development process

- **DECIDED** — Godot 4.
- **PROPOSED** — Every AI call goes through one local "AI service" interface the game reaches over local HTTP. Development uses Ollama + ComfyUI. The shipped game uses llama.cpp + stable-diffusion.cpp, with no Python install.
- **PROPOSED** — Saves start as JSON, moving to SQLite later if needed.
- **DECIDED** — Development is orchestrated: Claude acts as foreman and writes work orders, and the coding is split between Codex and Claude Code workers. See `orchestration/README.md`.
- **PROPOSED** — Default split for "either" work: 65% Codex / 35% Claude, by agent-minutes. Cross-review always goes to the other agent.

## 8. AI art

- **DECIDED** — Images are generated on the player's machine. The game is a packaged product that should be easy to install.
- **PROPOSED** — SDXL plus a pixel-art LoRA (ideally a custom LoRA trained on art Zack owns or commissions). Few-step models where the license allows.
- **PROPOSED** — Sprite steps: generate → transparent background (LayerDiffuse or rembg/BiRefNet) → nearest-neighbor downscale → quantize to the game's fixed palette → outline.
- **PROPOSED** — About 50–80 images to start a new world, generated during a "your God is shaping the world" loading screen. After that, generate ahead in the background and cache everything.
- **PROPOSED** — An imported card's PNG becomes the God's portrait.
- **PROPOSED** — Ship a fallback art pack. Item icons and UI are hand-made, not generated.
- **PROPOSED** — During development, ComfyUI does pipeline work, and NovelAI and ChatGPT do concept art, style exploration, UI mockups, icons and test portraits. All of it goes through the same pixelize step. ComfyUI is the only one that can ship *inside* the game, since players generate locally.

## 9. Audio

- **DECIDED** — Digital audio and music. Retro-sounding voices.
- **PROPOSED** — Sound effects are synthesized (sfxr-style, or a generator written by Claude Code / Codex), and the God can shape the synth settings at runtime. Kenney CC0 packs cover ambient and UI sounds.
- **PROPOSED** — Music is composed as MIDI and played through a General MIDI soundfont. The God can change instruments, tempo and key.
- **PROPOSED** — Voices use Kokoro TTS plus a crunch filter (8–11 kHz, reduced bit depth).
- **NOTE** — Avoid models whose weights are non-commercial (e.g. AudioGen). Check every model's license before shipping it.

## 10. System requirements

- **DECIDED** — Minimum 16 GB VRAM.
- **OPEN** — Recommended spec. Zack proposed 32 GB. Claude suggested **24 GB recommended, with 32 GB as an optional Ultra tier**, because 32 GB is effectively only the RTX 5090.
- **PROPOSED** — An option to use a remote language model or the player's own model server (KoboldCpp, Ollama, an API key) to widen the audience.

## 11. Multiplayer and backend

- **DECIDED** — Lightweight, near-peer-to-peer hosting with no large server fleet. Hosts feed a Super God that creates crossovers.
- **PROPOSED** — No Kubernetes.
- **PROPOSED** — Co-op is host-authoritative: the host runs the world and AI, and guests receive finished art, so guests don't need 16 GB of VRAM.
- **PROPOSED** — NAT traversal through Steam networking (GodotSteam). WebRTC with a small signaling server plus coturn as the fallback outside Steam.
- **PROPOSED** — The federation works as a mailbox: hosts send signed event summaries and pull crossover proposals. One small service with SQLite (Litestream to S3), or Cloudflare Workers + D1.
- **PROPOSED** — The Super God runs on a schedule over batches of events: API calls first, opt-in volunteer GPU compute later.
- **PROPOSED** — Hybrid universe: shared base lore, with each world branching into its own history.
- **PROPOSED** — Safety:
  - Ed25519-signed events.
  - Divine Influence calculated on the server.
  - Cross-world effects are only proposals the receiving world can decline.
  - All cross-world text treated as untrusted (prompt-injection risk).
  - A content filter for imported cards, on by default.

## 12. Open questions

1. Recommended VRAM tier (24 vs 32 GB).
2. Is Steam the main storefront? This affects networking, identity and the relay setup.
3. A remote language model option: yes or no?
4. Where the art style comes from: train a custom LoRA, or license an existing one.
5. Content policy for imported cards (NSFW handling).
6. The game's name.
