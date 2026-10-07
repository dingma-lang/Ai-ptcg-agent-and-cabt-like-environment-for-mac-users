# palfingon 1.3

Independent Palafin ex / Mega Dragonite ex agent, forked from the workspace
Palaking 1.25 logic on 2026-09-07. Palaking and its submissions are unchanged.

## Deck

`deck.csv` contains 60 organizer card IDs. The human-readable source is
`palfingon_deck_source.csv`; printing substitutions are recorded in
`deck_mapping_report.md` and `deck_resolution.json`.

Great Haul Net is absent from the supplied organizer catalog. At the player's
request, that slot is a second Night Stretcher. No other card substitution was
made beyond mapping alternate printings to the available competition cards.

- 3 normal Palafin use ID 106, with Zero to Hero.
- 1 normal Palafin uses ID 51, TEF 49, with Vanguard Punch. It cannot transform.
- Both Mega Dragonite ex printings use ID 904.
- 6 Water Energy and 3 Lightning Energy.

## Use

Upload `submission palfingon 1.3.zip` to the simulator's agent importer, or
refresh the existing local app and choose the workspace agent `palfingon`.
Its adjacent `deck.csv` supplies the deck automatically.

The callable is `agent(obs_dict: dict) -> list[int]`. It returns legal-option
indices. The official setup handshake (`current=None, select=None`) returns
the deck, matching the existing cabt sample interface.

The local engine supplies game rules and legal choices. The agent uses CPU
heuristics without a runtime LLM or network request. `cabt_cards.json` and
`cabt_attacks.json` are snapshots from the installed official worker so local
Mac execution can identify real engine attacks. Native `cg.api`, when present,
takes precedence.

## Files

| File | Purpose |
| --- | --- |
| agent.py, main.py | Submission entry and legal fallback |
| policy.py, turn_sequencer.py | Decision windows, scoring, pre-attack checks |
| core/palafin_planner.py, core/turn_plan.py | Inherited setup, switch, Energy, and resource plans |
| core/palfingon_cards.py | Variant-specific Palafin, Judge, Battle Cage, Night Stretcher rules |
| core/expert_battle_planner.py | Reviewed free pivots, exact-cost finishers, gust and discard checks |
| core/reviewed_turn_planner.py | Battle #24 pre-attack, search, promotion and bounded discard-cost rules |
| docs/BATTLE_REVIEW_1.3.md | Your 14 annotations, runtime changes, checks and remaining limits |
| docs/EXPERT_STUDY_1.1.md | Three-log evidence, adopted rules and differences from this deck |
| docs/STALL_FIX_1.2.md | Battle #15 diagnosis, staged fixes, regression and live-game evidence |
| expert_logs/ | Original battle text, retained locally and excluded from submissions |
| deck_profile.json | This deck's priorities and strategy description |
| card_db.py, EN_Card_Data.csv | Cached organizer card metadata |
| decision_reason.py | Optional decision scores and concise reasons |
| study_rule_runtime.py | Loads this folder's approved study_rules.json, when present |
| STRATEGY_NOTES.md | Strategy, limits, and validation evidence |
| tests/ | Inherited behavior checks and new-deck regressions |
| run_local.py | Recorded random, mirror, or Palaking games through the existing local worker |

## Check and Package

From this folder:

```sh
python3 build_deck_csv.py
python3 validate_deck.py
python3 -m unittest discover -s tests -q
python3 run_local.py --opponent mirror
python3 make_submission.py --out 'submission palfingon 1.3.zip'
```

The builder refuses to overwrite an existing numbered submission. Use the next
version after a logic change. Existing ZIPs do not update when source changes.
An already-imported 1.2 agent stays on 1.2. Import the new ZIP and select that
new entry to use the fix; no simulator restart or engine reinstall is required.

## Battle Logs and Study Memory

Version 1.1 incorporates reviewed deterministic rules from the three Tristary
logs supplied on 2026-09-08. Read `docs/EXPERT_STUDY_1.1.md` for evidence and
limits. This is a code update, not automatic training or a Battle Study sidecar
checkpoint. The original 1.0 ZIP remains unchanged.

Version 1.2 fixes the battle #15 switching/refresh deadlock. It retains a small
per-player attack-lock map across decision windows, uses serial IDs and absolute
turns, and clears that map at the deck handshake/new game. This is match-state
tracking, not cross-match learning. See `docs/STALL_FIX_1.2.md`.

Version 1.3 applies the battle #24 review. Ordinary KOs no longer skip useful
preparation; exact final-prize wins retain priority. The search and discard
rules retain only confirmed own-deck search cards within the current turn.
See `docs/BATTLE_REVIEW_1.3.md`. Older ZIPs and other deck folders are unchanged.

Further logs can be pasted into Battle Study with `palfingon` selected. Its
checkpoint history and runtime sidecar remain separate from Palaking's. An
imported ZIP is a distinct agent; choose the exact copy you intend to improve.

Study rules affect only supported conditions and may be superseded by fixed
sequencing guards. Check actual choices in recorded battles before accepting
a claimed improvement. No old accepted study rules were copied into this deck.
