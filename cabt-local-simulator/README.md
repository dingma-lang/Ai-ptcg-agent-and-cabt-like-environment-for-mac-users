# cabt Local Simulator

## Public Checkout

Organizer engine files, complete card catalogs and saved replay bundles are not
redistributed here. The verification history below describes the author's local
environment, not dependencies already installed in this checkout. For source-only
publication details and fresh setup instructions, see the [repository README](../README.md).
The browser interface can open without the engine; new battles require authorized
local engine files and card data. This project wraps the official engine rather
than recreating its game rules.

This is a local Python project around the official Pokémon TCG `cabt` engine for Pokémon Trading Card Game AI training and evaluation. It is not for Pokémon TCG Pocket, and it does not implement a replacement rules simulator.

The project provides deck loading, supported-card catalog tools, isolated agent processes, match-local memory, streaming JSONL episode recording, a two-deck runner, and a browser replay viewer. On this Apple Silicon Mac, real battles run the organizer-provided Linux x86-64 `libcg.so` in a private Lima VM using Apple's Rosetta for Linux.

## Official References

- Main docs: https://matsuoinstitute.github.io/cabt/
- API structures: https://matsuoinstitute.github.io/cabt/api.html
- Game API: https://matsuoinstitute.github.io/cabt/game.html
- Simulation API: https://matsuoinstitute.github.io/cabt/sim.html
- Competition: https://www.kaggle.com/competitions/pokemon-tcg-ai-battle

The docs describe `Observation` as `logs`, `current`, and `select`. Legal actions are indexes into `observation["select"]["option"]`, respecting `minCount` and `maxCount`.

## Verified Local Engine

- OS: macOS / Darwin
- Machine: Apple Silicon (`arm64`)
- Host Python: the macOS system Python or `.venv`
- Guest: Lima VZ, Linux ARM64, 4 CPUs, 6 GiB RAM
- Translation: Rosetta for Linux
- Engine process: `linux/amd64` Python 3.11 container
- Kaggle runtime: `kaggle-environments 1.32.7`, with the `cabt` environment registered
- Official metadata verified: 1,267 cards and 1,556 attacks
- Match verification: `make("cabt")` random play, random versus random, imported Palaking versus N's Zoroark, and isolated mirror play

The official library does not load directly into macOS. The browser app talks over localhost to the translated Linux worker, which imports the untouched organizer `cg` wrapper and native library.

## Installation

The Mac runtime has already been provisioned in this workspace. For a fresh Apple Silicon Mac, the one-time installer is:

```bash
./scripts/install_engine_runtime.sh
```

It downloads the pinned Lima 2.2.0 ARM64 release, verifies its SHA-256 checksum, creates `~/.cabt-lima/ce`, enables VZ/Rosetta and rootless containerd, and starts the official worker. It does not install Homebrew or alter the system Python.

The Python project itself can still be installed normally:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install -e .
```

Or run without installing:

```bash
PYTHONPATH=src python3 -m cabt_local env
```

## Browser App On Mac

Double-click `Cabt Local App.command`. It creates the local virtual environment when needed, starts the official engine worker, opens the browser app, and keeps the app running.

The equivalent command is:

```bash
.venv/bin/python start_app.py
```

The app opens at `http://127.0.0.1:8765/` or the next free port. Use **Start Engine** if the engine badge is not ready. **Verify Environment** launches a complete random-versus-random match through `kaggle_environments.make("cabt")` and reports its steps, rewards, and final statuses.

For a normal simulation, import or select Agent A and Agent B, leave both deck overrides on **Automatic from agent package**, and use **Run Match**. Match summaries, decision episodes, and replay links appear under **Outputs**.

New outputs use one shared, locally timestamped name:

```text
battle1_15-43_2026-09-02_pal_vs_pal.html
battle1_15-43_2026-09-02_pal_vs_pal.json
battle1_15-43_2026-09-02_pal_vs_pal.jsonl
```

The fields are battle index, local 24-hour time, local ISO date, and the first three normalized characters of each agent name. Hyphens replace `:` and `/` so replay packages remain portable across macOS, Linux, Windows, and Kaggle.

The worker remains local at `http://127.0.0.1:8780`. **Stop Engine** removes its container but leaves the VM running for a fast restart.

### Agent Selection

The presentation refresh puts **Choose your agents** and **Run match** first.
Agent packages, deck overrides, engine/environment details and log import are
collapsed underneath. Open the section heading when needed; the engine badge
also opens engine controls. Recent battles are searchable and open directly
in the updated replay. Execution output and result JSON files remain available
in collapsed sections below the battle list.

**Study** uses the same visual style. Decision traces, memory and checkpoints
start collapsed; findings can be filtered by review status. An inactive runtime
hook with accepted rules still produces a visible warning. No rules are accepted
automatically. In replays, actions appear before the expandable **Card zones**
section; playback speed is selectable. Existing saved battles get the updated
presentation when opened through a restarted app, without rewriting their files.

Icons and styles are embedded locally, including in exported HTML; no CDN is
needed. See `THIRD_PARTY_NOTICES.md` for the bundled icon license.

The browser discovers top-level deck agents in the parent workspace. Current choices include Palaking, Hydreigon/Gengar, and N's Zoroark. It pairs each discovered `agent.py` with the `deck.csv` in the same folder.

Use **Import Agent A** or **Import Agent B** to select either:

- a Kaggle submission ZIP containing `agent.py`, its helper modules, and `deck.csv` (recommended), or
- a standalone `agent.py`, which is copied with the currently selected deck override.

Imported packages are stored under `data/imported_agents/`. ZIP entries are size-limited and checked for unsafe paths and symbolic links before extraction. A file agent spec looks like:

```text
file:../Palaking/agent.py:agent
```

Each selected file agent runs in its own persistent Python process. This prevents one deck's `core`, `config`, profile, or global memory modules from leaking into another deck, and makes mirror play use two independent agent states.

### Replay Visualizer

Every official match saves a standalone turn-procedure HTML replay. The default view is organized for battle review rather than raw engine debugging:

- Choose a setup or turn from the left-hand timeline.
- Read the acting player's hand immediately after the turn draw.
- Follow every play, evolution, attachment, ability, retreat, attack, effect choice, and End action in order.
- Select an action to show the board immediately after that action resolves.
- Read **Agent reasoning** under an action to see the chosen score, score band, and the agent's short decision reason.
- Expand **Compare all legal-option scores** to compare every legal index, action category, card/target, score, and reason.
- Treat the score bands as a review guide: Critical is 10,000+, High is 2,500+, Medium is 500+, Low is 0-499, and Blocked is below 0.
- Watch for a **Sequencing override** note when a state-machine rule chose an action even though another option had a higher numeric score.
- Review HP, attached Energy and Tools, Bench, deck/hand/Prize counts, and Stadium in the board panel.
- Select a card name to inspect its locally stored competition metadata, attacks or abilities, costs, damage, and effect text.
- Compare the hand before the turn ends and the summarized board-count changes for the complete turn.
- Enable **Both hands** only when reviewing a locally generated full-information match.
- Expand **Engine details** when the readable summary is insufficient and exact legal options or logs are needed.
- Use Play to advance action by action, or the arrow controls to move one complete turn at a time.

The replay is self-contained after it is written: card data used by the match is embedded from `data/catalog/cards.json`, so it remains readable without a network connection. The local catalog contains card text and statistics but no card artwork.

Score diagnostics are optional. The local isolated-agent runner captures them from agents that support `PTCG_AGENT_DECISION_LOG` and stores them in the matching episode JSONL. This does not change the Kaggle callable interface or the selected action; agents without the hook simply produce a replay without score panels. The random agent has no strategic score trace.

The browser app also includes a log replay visualizer that does not require the engine. You can paste a Kaggle/cabt battle log, or choose a `.txt`, `.log`, `.html`, or `.jsonl` file from your Mac. It parses turns, played cards, Bench changes, attachments, evolutions, attacks/abilities, Knock Outs, Prize cards, and winner lines into a timeline plus an inferred public board.

The visualizer is backed by an event-sourced log replay engine. Use the first/previous/next/last controls, the event slider, or a timeline row to inspect the inferred board at that exact point. The coverage table reports how many lines were parsed; unfamiliar lines are preserved under **Unparsed Lines** with their source line numbers.

See `ENGINE_BUILD_NOTES.md` for the initial HTML audit, the recovered components, and the exact boundary between local replay reconstruction and the official cabt rules engine.

The log parser remains a review tool. Rules, legal options, shuffling, effects, and match results in generated matches come from the official cabt native engine.

### Review Alternative Actions

The turn replay includes **Card zones** for both players. Switch between **Deck**, **Prizes**, and **Discard**; each player always shows all three totals. Deck and discard lists group identical card IDs with copy counts, while Prize cards retain their recorded slot numbers. Card names open the embedded card information, and the filter searches both players' lists.

**Turn start**, **Selected action**, and **After final action** use exact recorded frames and update the board and zone lists together. The after-final-action frame can already contain the next turn's opening draw; this is labeled as a next-turn prompt, not presented as an exact pre-draw turn-end state. Selecting an action or starting playback returns the view to that action's snapshot.

**Reveal recorded deck / Prizes** is enabled for local full-information review. This is replay information, not knowledge supplied to the agent. Uncheck it to conceal those two zones; discard stays visible. Missing card identities remain unknown, and unrecorded counts show `?` rather than an empty pile. The viewer never fills gaps from later frames or a starting decklist. Browsing zones does not alter review choices, comments, or agents.

- Open a generated battle HTML from the simulator's Results. The episode view also has an **Open battle review** link.
- Expand **Review choice** under an action. Select another recorded legal action, or change the targets in a later effect-resolution window.
- Single choices use radio buttons; multiple selections use checkboxes. The engine's `minCount` and `maxCount` are enforced. Optional windows can select none. Duplicate card copies remain separate options, with their zone, slot, and serial shown.
- For Buddy-Buddy Poffin, only the engine-listed eligible Basics appear, not every card in the deck. The engine's reduced maximum applies when fewer Bench spaces are available. Energy costs, evolution timing, Supporter availability, search restrictions, and other rules come from the recorded legal options, not a new rules implementation.
- Add a comment. Choices and comments are stored temporarily in this browser tab's session storage, separately for each battle. They survive turn navigation and reloads. Closing the tab normally clears them; browsers may restore a session. If storage is blocked, edits remain in page memory only, with a warning.
- Choose **Text log** or **JSON log**, then **Export review**. The downloaded log lists every edited/commented decision in battle order, with original and proposed indices, card/effect labels, limits, comments, and the source replay fingerprint. Invalid incomplete selections block export. **Reset this review** resets one action; **Clear reviews** resets the battle's draft.

These are review annotations, not an alternate simulated battle or automatic agent edits. Every choice is valid only in its original decision window. If an earlier action is changed, subsequent entries are marked as dependent on that original position; they are not re-simulated, and a different card's unrecorded follow-up choices cannot be invented. Submit another simulation to evaluate a changed strategy.

The review uses the observing agent's recorded observation when available, not an omniscient deck/prize list. Unknown prizes stay unnamed. Windows missing legal options or count limits are comment-only. Plain imported text logs cannot supply the same legality-checked alternative choices without a matching decision recording.

Previously generated official replays are upgraded in memory when served by the updated app; the saved battle files are not overwritten. Restart an older running app, then reopen its Results link. Newly generated HTML includes review controls and can also be opened directly without a server. No agent submission or study checkpoint is modified by a review.

Developer checks: `python -m unittest discover -s tests -q`. The optional `scripts/check_replay_review_browser.py` uses Playwright and a temporary Chrome profile against a running local app; Playwright is not a simulator runtime dependency.

### Battle Study And Checkpoints

Open `http://127.0.0.1:8765/study` or select **Battle Study** in the app header. The study workflow accepts a pasted or uploaded battle log, a discovered file agent, and an optional matching episode JSONL decision trace.

The public log supplies the turn timeline and observable actions. The decision trace adds the exact observation, legal options, selected indices, option categories, scores, and reasons needed to verify missed actions. Without a trace, findings that depend on unrecorded legal choices are explicitly marked as uncertain.

Each finding has evidence, severity, confidence, and an editable structured rule. **Accept** validates the rule, creates an immutable numbered checkpoint under `data/study_memory/<agent>/checkpoints/`, updates that agent's `study_rules.json`, and leaves every other deck profile untouched. **Reject** records the rule id so the same suggestion remains rejected in later studies. **Restore** creates a new checkpoint from an earlier rule set, preserving the complete history. Study sessions are stored under `data/studies/` and reopen through their `/study?study=...` URL.

The workspace Palaking, Hydreigon, and N's Zoroark agents include the deterministic `study_rule_runtime.py` hook. It applies only supported conditions and ignores unknown conditions. For a compatible imported agent, **Install Rule Hook** backs up `policy.py`, adds the same guarded score hook, verifies syntax, and keeps the imported agent's memory isolated. Incompatible packages remain checkpoint-only; the UI does not claim that an unhooked sidecar changed runtime play.

**Validate Agent & Memory** works before or after learning. Before the first accepted rule it checks the baseline agent and reports `baseline_pass`; after checkpoint creation it also checks rule schemas, sidecar/checkpoint consistency, and the runtime hook. It checks Python syntax without executing imported code. A structural pass is not a gameplay result; use the Simulator to run old-versus-new A/B matches before submission.

No network service or language-model token is used by parsing, findings, approval, checkpointing, or runtime scoring. Rules should be tested in local matches before building a numbered Kaggle submission. The three workspace submission builders include `study_rule_runtime.py` and include `study_rules.json` when an accepted-rule sidecar exists.

## Official Engine Files

After accepting the Kaggle competition terms, place the official runtime files in one of these ways:

- Install the official Kaggle environment/package if the competition provides it.
- Put the official `cg/` package next to this project and set:

```bash
export CABT_CG_PATH=/path/to/folder/containing/cg
```

Expected package shape:

```text
cg/
  api.py
  game.py
  sim.py
  utils.py
  libcg.so      # Linux
  cg.dll        # Windows, if applicable
```

Do not download unofficial binaries. If `battle_start()` rejects a deck, this project reports the complete available `StartData` fields.

## Decks

The primary deck format is numeric cabt IDs, one nonempty line per card:

```text
278
278
...
7
7
```

Each deck must contain exactly 60 IDs.

Included local examples:

- `decks/deck_a.csv`: copied from the current Palaking deck.
- `decks/deck_b.csv`: copied from the current N's Zoroark deck.

Validate a deck:

```bash
PYTHONPATH=src python3 -m cabt_local deck validate decks/deck_a.csv
```

Check the Palafin/Mega Dragonite deck against the available catalog:

```bash
PYTHONPATH=src python3 -m cabt_local deck check-palaking --deck ../Palaking/deck.csv
```

If the engine is unavailable, the command can use an official CSV catalog discovered from the workspace. Engine validation remains the final authority.

## Card Catalog

Export supported card data when the engine can load:

```bash
PYTHONPATH=src python3 -m cabt_local cards export
```

If the engine is unavailable but an official CSV is present:

```bash
PYTHONPATH=src python3 -m cabt_local cards export --csv-fallback "../Palaking/card list and resource/EN_Card_Data.csv"
```

Outputs:

- `data/catalog/cards.json`
- `data/catalog/cards.csv`

## PTCG Live Text Import

The optional converter only accepts exact matches by card name, set, and collector number when those fields are present in the catalog. It reports ambiguous or unsupported lines instead of guessing.

```bash
PYTHONPATH=src python3 -m cabt_local deck convert deck_a.txt decks/deck_a.csv --catalog-csv "../Palaking/card list and resource/EN_Card_Data.csv"
```

## Agents

Every agent receives only that player's observation and must return `list[int]` legal option indexes.

Supported agent specs:

- `random`
- `file:../DeckFolder/agent.py:agent` (isolated process; recommended for local deck agents)
- `module:package.module:function`
- `http` / `model` / `local-http`

Module example:

```bash
PYTHONPATH=src:/path/to/agent python3 -m cabt_local play \
  --deck-a decks/deck_a.csv \
  --deck-b decks/deck_b.csv \
  --agent-a module:my_agent:agent \
  --agent-b random
```

HTTP model adapter:

```bash
export CABT_LOCAL_MODEL_ENDPOINT=http://127.0.0.1:8000/choose
export CABT_LOCAL_STRATEGY_PROMPT=prompts/deck_a_strategy.txt
PYTHONPATH=src python3 -m cabt_local play --deck-a decks/deck_a.csv --deck-b decks/deck_b.csv --agent-a http --agent-b random
```

The model must return strict JSON:

```json
{"selected_indexes": [2], "reason": "Use reusable switch effect before spending an item."}
```

The reason is stored for analysis by adapters, but only validated indexes are sent to cabt.

## Running Matches

Random versus random:

```bash
PYTHONPATH=src python3 -m cabt_local play \
  --deck-a decks/deck_a.csv \
  --deck-b decks/deck_b.csv \
  --agent-a random \
  --agent-b random
```

Self-play:

```bash
PYTHONPATH=src python3 -m cabt_local self-play \
  --deck-a decks/deck_a.csv \
  --deck-b decks/deck_b.csv \
  --agent-a random \
  --agent-b random \
  --games 10 \
  --record
```

These commands automatically fall back to the localhost worker when the native library cannot load in the host process. Start it with `python3 manage_engine.py start` when running without the browser launcher.

## Memory Versus Offline Data

Match memory resets at the start of every match and tracks only legally observable information: turn, acting player, prize/deck/hand counts, Active/Bench, damage/conditions where visible, public discard, Stadium, logs, and visible once-per-turn flags.

Episode recording is separate. It writes every decision as streaming JSONL with schema version `1`, preserving raw observation plus stable normalized features. It never adds hidden deck order, opponent private hand, or face-down Prize identities.

Episode stats:

```bash
PYTHONPATH=src python3 -m cabt_local episodes stats data/episodes
```

Episode split by complete game:

```bash
PYTHONPATH=src python3 -m cabt_local episodes split data/episodes --train-fraction 0.8
```

Optional Parquet export:

```bash
python3 -m pip install -e ".[parquet]"
PYTHONPATH=src python3 -m cabt_local episodes to-parquet data/episodes data/episodes.parquet
```

## Search Adapter

`src/cabt_local/search.py` wraps the documented `search_begin`, `search_step`, `search_end`, and `search_release` operations. It uses the local worker on this Mac and correctly converts dictionary observations to the official API dataclass. Search is opt-in: callers must provide legal hidden-information estimates with the exact required lengths and release each search handle.

## Troubleshooting

- Engine badge says stopped: click **Start Engine** or run `python3 manage_engine.py start`.
- `slice is not valid mach-o file`: a process tried to import `libcg.so` directly on macOS; leave `CABT_CG_PATH` unset and use the worker.
- `Deck must contain exactly 60 IDs`: fix the deck CSV before trying a battle.
- `Unsupported card IDs`: export/check the official cabt catalog and update the deck mapping.
- Model timeout or malformed JSON: the wrapper records the invalid response and falls back to legal random selection.
- Worker startup failure: run `python3 manage_engine.py status`, then check `~/.cabt-lima/ce` exists and Rosetta is installed.

## Runtime Management

```bash
python3 manage_engine.py status
python3 manage_engine.py start
python3 manage_engine.py stop
```

The runtime uses the official organizer files under `../sample_submission/cg/`. It does not make network calls during matches. Lima's VM state lives at `~/.cabt-lima`; downloaded tooling under `.runtime/` is intentionally excluded from submissions and source archives.
