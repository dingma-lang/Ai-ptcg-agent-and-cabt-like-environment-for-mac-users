# Pokemon TCG Agents and a Local Battle Lab for macOS

Deterministic Python agents, a browser simulator interface, replay visualization,
and an expert-feedback study workflow for the Pokemon TCG AI Battle Challenge.

**This is not a replacement game engine.** Battle simulation depends on the
official `cabt` engine. This project supplies the agent logic, local integration,
visualization, review tools and evaluation workflow. Agents do not call an LLM
during matches.

## What Is Included

| Folder | Contents |
| --- | --- |
| `cabt-local-simulator/` | Browser app, official-engine integration, replay viewer, Study interface and tests |
| `hydreigen/` | Hydreigon ex / Mega Gengar ex strategy and agent source |
| `NsZoroark/` | N's Zoroark ex strategy and agent source |
| `Palaking/` | Earlier Palafin ex / Mega Dragonite ex agent |
| `palfingon/` | Later Palafin ex / Mega Dragonite ex agent and reviewed-decision fixtures |
| `submissions/` | Four representative, explicitly labeled source-only archives |
| `write ups/` | Final article, diagrams, recorded aggregate results and evaluation scripts |

The latest article is available as [Markdown](write%20ups/cross_deck_strategy_draft_v8.md),
[PDF](write%20ups/cross_deck_strategy_draft_v8.pdf) or
[DOCX](write%20ups/cross_deck_strategy_draft_v8.docx).

## Attribution and External Dependencies

This project contains independently developed agents, visualization tools and
an expert-feedback workflow for the Pokemon TCG AI Battle Challenge. Battle
simulation relies on the official cabt engine, which was not developed by this
project. Organizer-provided engine files and card catalogs are not included;
users must obtain them separately through authorized sources and follow the
applicable terms.

- [Official competition](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle)
- [Official cabt documentation](https://matsuoinstitute.github.io/cabt/)
- [Official API reference](https://matsuoinstitute.github.io/cabt/api.html)

The public repository excludes official `cg` code and native libraries, complete
card/attack catalogs, rulebooks, competition instruction documents, and original
bundles or replay exports containing those assets. Attribution is not a grant of
redistribution permission. Existing third-party UI notices are preserved in
[THIRD_PARTY_NOTICES.md](cabt-local-simulator/THIRD_PARTY_NOTICES.md).

## Open the Browser Interface

Use Python 3.11 for consistency with the Linux worker. From the repository root:

```bash
cd cabt-local-simulator
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install -e .
.venv/bin/python start_app.py
```

The app opens at `http://127.0.0.1:8765/` or the next available port. The interface
can open without the engine, but **new simulated battles require the authorized
engine and card data**. There are no bundled replay HTMLs: create replays locally
or import your own supported battle logs. Card labels and rule details depend on
your local catalog.

## Enable Local Battles

1. Obtain the official files through the competition organizers and accept the
   applicable terms. Do not download unofficial native binaries.
2. Put the official package at `sample_submission/cg/` in this repository root,
   beside `cabt-local-simulator/`. The Mac worker expects at least `game.py` and
   `libcg.so`, together with the rest of the official Python package.
3. Place an authorized `EN_Card_Data.csv` in each agent folder you intend to use.
   Palfingon also supports local `cabt_cards.json` and `cabt_attacks.json`
   snapshots in its own folder. Supply compatible snapshots when reproducing
   the original metadata-dependent policy behavior; the catalogs are not
   downloadable from this repository.
4. On Apple Silicon, install Rosetta through macOS if needed. From
   `cabt-local-simulator/`, run `./scripts/install_engine_runtime.sh`. This
   downloads the configured Lima/runtime dependencies and provisions a Linux
   environment. It does not supply the excluded organizer `cg` package.
5. Start the app, check the engine status, and export your local catalog with
   `PYTHONPATH=src .venv/bin/python -m cabt_local cards export`. Select two agents
   and run a battle. Open its replay under the app's outputs.

The official Linux library does not run natively on macOS. The provided Mac
integration uses Lima, Rosetta for Linux and a Linux x86-64 worker. The installer
is for Apple Silicon; other platforms require a separately configured compatible
engine environment. See the [simulator documentation](cabt-local-simulator/README.md)
for details. Its verification history describes the author's local environment,
not an engine bundled with this public checkout.

Official assets and local runtime outputs are ignored by Git. Keep them local;
do not use `git add -f` to publish them. The source-only ZIPs are for inspection,
not a promise of complete, competition-ready packages. Restore your authorized
dependencies locally before validation or packaging for the competition.

## Learning and Evaluation Code

This is **human-guided rule improvement**, not implemented neural-network
training or autonomous reinforcement learning. An expert reviews a decision,
approves or rejects a structured rule, and can validate or restore checkpoints.
Accepted rules influence deterministic action scoring when the runtime hook is
enabled. Match memory is separate from learned model weights; there are no
trained neural weights in this repository.

| File | Role |
| --- | --- |
| `cabt-local-simulator/src/cabt_local/study.py` | Analyze logs, review findings, manage approved rules and checkpoints |
| `cabt-local-simulator/src/cabt_local/study_page.py` | Human review interface |
| `palfingon/study_rule_runtime.py` | Apply approved rules while selecting actions |
| `cabt-local-simulator/src/cabt_local/recorder.py` | Record observations, decisions and outcomes |
| `cabt-local-simulator/src/cabt_local/runner.py` | Run agent comparisons through the official engine |
| `write ups/scientific_analysis.py` | Quantitative analysis and policy diagnostics |
| `write ups/probe_archived_policies.py` | Compare archived policies on reviewed states |

The research folder retains historical aggregate results. Recreating all those
results requires the original private episodes, archived packages and authorized
metadata; these inputs are not fully distributed here. Source-only archives have
different hashes from any historical package whose metadata was removed.

## Focused Tests Without the Engine

From `cabt-local-simulator/`:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_study.py
```

This exercises the Study workflow, not game-rule fidelity or match strength.
Engine-dependent matches and metadata-dependent strategy tests need the external
assets described above.
