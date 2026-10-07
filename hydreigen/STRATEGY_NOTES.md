# Strategy Notes

## Current milestone

This is the stable heuristic baseline for the PTCG AI Battle Challenge Simulation Category. It uses the provided cabt legal-option interface and never simulates card legality itself. The engine supplies legal actions; the agent only ranks legal option indices and sanitizes the returned count.

Local full-game execution is blocked on this Mac because `sample_submission/cg/libcg.so` is a Linux x86-64 shared library and Docker is not installed. The runners are ready for Linux/Kaggle and fail gracefully here.

## Deck concept

The current deck is Hydreigon ex / Mega Gengar ex setup:

- Hydreigon ex and Mega Gengar ex are both main damage dealers.
- Mega Gengar ex is a real attacker and prize-route engine; build it when Gastly/Haunter is live or the opponent is using ex attackers.
- Toxel is an early setup Basic for Call for Family; Toxtricity is support only and should not receive manual Energy or attack.
- The opening setup goal is one each of Deino, Gastly, and Toxel before taking duplicate setup pieces when possible.
- Fezandipiti ex and Pecharunt ex are support Pokemon but are treated as two-prize liabilities.
- Buddy-Buddy Poffin, Ultra Ball, Rare Candy, Lillie's Determination, Dawn, Crispin, and Secret Box are setup accelerants.
- Boss's Orders is prioritized when it creates a KO or final-prize route.
- Darkness Energy is reserved for Mega Gengar ex or the Hydreigon line unless it is clearly extra discard fodder; Metal/Psychic Energy are protected and reserved for the Deino evolution chain.

`build_deck_csv.py` maps the user-provided normal deck export to competition numeric IDs. In this local metadata, `Special Red Card CRI 82` is absent, so `deck.csv` currently uses `Meddling Memo` as an explicit local placeholder. This is not treated as an identical gameplay substitution; it is documented in `deck_mapping_report.md` and should be replaced once cabt metadata includes the real card.

## Architecture

- `agent.py`: Kaggle entry point with `def agent(obs_dict: dict) -> list[int]`.
- `main.py`: compatibility shim because the official sample submission uses `main.py`.
- `config.py`: mode guard. The default is `CABT_SUBMISSION_MODE`, with UI automation and memory file writes disabled.
- `core/`: shared adapter-neutral layer for normalized state parsing, action classification, intent creation, deck profile access, option scoring, decision reasons, and `AgentMemory`.
- `core/evolution_planner.py`, `core/energy_planner.py`, `core/search_planner.py`, `core/supporter_planner.py`, and `core/pass_guard.py`: Hydreigon ex / Mega Gengar ex rule-based priority layer that boosts legal setup, evolution, reserved Energy attachments, safe search/discard choices, and prevents early pass.
- `adapters/cabt/`: submission-safe cabt input/output adapter. It reads only `obs_dict`, legal options, and returns legal option indices.
- `build_deck_csv.py`: strict deck export converter and mapping-report generator.
- `action_classifier.py`: public natural action classifier with the exact category vocabulary used for logs and inspection.
- `turn_sequencer.py`: turn-window sequencing policy that adjusts scores according to mandatory prompts, win/prize checks, loss prevention, prize mapping, setup, energy, board development, disruption, attack timing, and end/pass logic.
- `decision_reason.py`: short reason-string generator and optional JSONL decision logger.
- `action_reasoner.py`: internal rule-context layer used by scoring for once-per-turn and turn-timing penalties.
- `policy.py`: deterministic state-machine router, legal-option scoring, fallback, and sanitization.
- `state_eval.py` / `state_parser.py`: safe observation parsing helpers for dicts/dataclasses.
- `option_scorer.py`: scorer compatibility module.
- `card_db.py`: lazy metadata loading from cabt `all_card_data()` / `all_attack()` when available, otherwise from `EN_Card_Data.csv`.
- `deck_profile.py` and `deck_profile.json`: human-editable strategy priorities.
- `search_policy.py`: disabled tactical-search hook for the next milestone.
- `memory.py`: lightweight public/revealed-card and timing bookkeeping.
- `make_submission.py`: builds a cabt-safe submission archive and verifies local results, memory files, screenshots, and logs are excluded.

## Decision logic

The active pipeline is adapter-based:

`obs_dict -> adapters.cabt.parse_obs -> NormalizedGameState -> AgentMemory -> core.policy.choose_intent -> ActionIntent -> adapters.cabt.intent_to_option_indices -> list[int]`

The policy first classifies every legal cabt option into a natural TCG action, then assigns the decision window to a moment type: setup, our main turn, attack selection, effect resolution, prize selection, forced replacement, opponent-turn response, or unknown. It produces an abstract `ActionIntent` before the cabt adapter converts that intent back to option indices. It never invents actions or performs UI automation; "play/attach/evolve/bench" always means "choose the matching legal option index from `obs_dict['select']['option']`."

`AgentMemory` stores only adapter-neutral, legally available information: turn number, known hand/discard/public cards, revealed cards, usage flags, inferred public counts, previous intents, reasons, and local analysis mistakes. In submission mode it is in-process only by default and does not rely on persistent learning.

Set `PTCG_AGENT_DECISION_LOG=stdout` or `PTCG_AGENT_DECISION_LOG=/path/to/decisions.jsonl` to log each decision point with turn number, select context, legal option categories, heuristic scores, chosen index, and a short reason string.

The policy then scores card tactics and passes those scores through the turn sequencer. The sequencer treats a turn as a chain of decision windows, not one isolated action. Its priority order is:

- mandatory prompts: setup active/bench, promote after KO, required discard/selection, prize selection
- immediate win and prize-taking attacks/effects; opponent deck discard is treated as a win route only when the opponent has 15 or fewer cards left
- avoid immediate loss: stuck active, deck-out risk, opponent near final prizes
- prize-map pressure: value KO routes and avoid needless two-prize liabilities
- setup engine: one each of Deino/Gastly/Toxel, Buddy-Buddy Poffin, Toxel as the Call for Family bridge when Active Deino has a low Bench and few Basic outs, Call for Family into Fezandipiti ex/Pecharunt ex when core basics are established, Ultra Ball, Rare Candy/Hydreigon ex or Haunter/Mega Gengar ex, draw/search when hand is poor
- energy plan: attach once, reserve Energy for Hydreigon ex / Deino line and Mega Gengar ex / Gastly line, avoid Energy on Fezandipiti ex, Pecharunt ex, Toxel, and Toxtricity, value Crispin
- board development: build the fastest live attacker line, Hydreigon ex or Mega Gengar ex; avoid support ex benching without need
- disruption: Petrel/Red Card/Boss when opponent hand/prize state makes it valuable
- attack timing: take KOs, otherwise use useful pre-attack actions first
- end/pass only when useful actions are gone or harmful

Selection contexts matter. Search choices prefer Buddy-Buddy Poffin, Ultra Ball, Rare Candy, Hydreigon ex, Mega Gengar ex, Deino, Gastly/Haunter, and the missing attacker pieces. Discard choices protect Hydreigon ex, Rare Candy, Mega Gengar ex, recovery cards, Boss, and Metal/Psychic Energy while discarding Darkness Energy first. Switch choices prefer powered attackers and KO-capable Pokemon. Optional selections can return `[]` when scores are not good enough.

The scorer adds specific pressure for Boss/gust effects that create KOs, disruption cards when the opponent has a large hand or our prize count is low, and avoids benching Fezandipiti ex / Pecharunt ex without a clear reason.

Mandatory/rulebook prompt handling:

- Prize selection is classified from either `CTX_TO_PRIZE` or `area=PRIZE`. Hidden prizes are not inspected; if all choices are face-down, the agent deterministically takes the highest-index/top prize per cabt ordering. Revealed prizes are ranked by win relevance, Hydreigon/evolution pieces, Energy, draw/search, then lower-value cards.
- Promotion after KO is classified as `PROMOTE_AFTER_KO`. The agent promotes an attacker that can attack immediately, then a free-retreat pivot, then a low-value sacrifice, while avoiding fragile setup Pokemon or support ex liabilities when possible.
- Forced discard is classified as `DISCARD_COST`. The discard table protects Hydreigon ex, Deino, Rare Candy, key recovery/disruption cards, and Metal/Psychic Energy; unique critical copies receive a very large penalty and low-value duplicates are preferred.
- Search choices are classified as `DRAW_OR_SEARCH`. The search scorer prioritizes immediate prize/KO enablers where visible, the fastest live attacker line, missing Hydreigon or Mega Gengar setup pieces, current-attacker Energy, then recovery/disruption/backup attackers.
- Yes/No prompts use context: mulligan and first/second prompts follow configured defaults, and optional effects are accepted only when their text looks beneficial or their cost is not clearly harmful.

Rulebook-aware adjustments are layered on top of card heuristics:

- one manual Energy attachment per turn
- one Supporter per turn, with first-player first-turn Supporter restriction
- one Stadium play/replacement per turn
- same-name Stadium play avoidance in debug/edge observations
- one retreat per turn, with retreat cost and attached Energy considered
- evolution timing via `appearThisTurn`
- first-player first-turn attack skip
- attack as the final turn action
- mandatory Active setup/replacement contexts
- special-condition contexts classified for future scoring hooks
- End/pass treated as a real strategic option when no useful legal action remains

## Hidden information

The agent only uses the observation, public board/discard data, its hand, revealed logs, and the submitted deck/profile. Opponent hand, deck, and prizes are treated as hidden unless the observation/logs reveal cards.

## Evaluation plan

Use:

- `python3 validate_deck.py`
- `python3 -m unittest`
- `python3 build_deck_csv.py` for strict mapping, or `python3 build_deck_csv.py --allow-local-placeholder` to reproduce the current local placeholder deck.
- `python3 run_local.py` on Linux/Kaggle-compatible cabt
- `python3 evaluate.py --games 100 --opponent random`
- `python3 evaluate.py --games 50 --opponent sample`
- `python3 analyze_logs.py local_results eval_results --show-findings`
- `python3 make_submission.py --out submission.zip`

Saved HTML/JSON outputs go to `local_results/` or `eval_results/`. Local battle runs also write `*.trace.jsonl` rows with observations, selected indices, elapsed decision time, and legality status so `analyze_logs.py` can review missed KOs, bad passes, unsafe benches, protected discards, prize prompts, illegal actions, and timeouts.

## Submission format

The official sample package includes a Python entry file, `deck.csv`, and the `cg/` engine bindings. This repo keeps the requested implementation in `agent.py` and also exposes the same callable from `main.py` for sample-format compatibility. The agent returns `deck.csv` during the initial `select is None` deck request, and returns only legal option indices for every later selection. `make_submission.py` excludes generated analysis artifacts.

## Known failure cases

- No live tactical search yet.
- `Special Red Card CRI 82` is not present in the local card CSV/PDF; current `deck.csv` uses a documented placeholder only for local wiring.
- CSV fallback cannot map real cabt attack IDs, so local non-engine tests use CSV-derived pseudo IDs.
- Full cabt matches cannot run on this macOS workspace with the provided Linux shared library.
- Card text heuristics are broad and need real losing logs for exact sequencing improvements.
