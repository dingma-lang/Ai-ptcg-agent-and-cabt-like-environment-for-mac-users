# Cross-Deck Evidence Map

Historical evidence for the multi-deck report, not part of the article body.
The active draft is `cross_deck_strategy_draft_v8.md`. It merges the earlier
and later Palafin ex deck development under one name; original archive names
and paths below remain unchanged for traceability. The subsequent
retrospective audit in `DATA_AUDIT.md` adds results omitted from early drafts,
including the imported 1.3-vs-1.2 losses and incomplete records.

## Evidence Labels

- **Requested/reported:** stated by the player in the conversation; useful
  discovery history, not independently measured performance evidence.
- **Implemented:** located in source or confirmed by comparing archived code.
- **Focused recheck:** named tests rerun successfully against the current
  source in that deck's folder, not a complete archive or tournament evaluation.
- **Recorded integration evidence:** existing tests, episodes, and validation
  notes from official-engine runs. No new games were run for this editorial task.

The conversation gives the sequence of requests but is not a complete commit
history. Do not assign exact dates to every historical implementation from the
order of the messages alone. Do not treat the initial, later-replaced decklists
as the final lists.

## 1. Hydreigon / Mega Gengar (`hydreigen/`)

Requested/reported: bench Basics, correctly resolve Poffin and Call for Family,
establish multiple useful evolution lines, stop Energy on support Pokemon,
preserve setup pieces, and connect cards in hand with those in play.

Implemented evidence:

- `hydreigen/STRATEGY_NOTES.md`: distinct attacker/support roles and Energy plan.
- `hydreigen/core/combo_presence_planner.py`: `hydreigon_bridge_needed`,
  `gengar_bridge_needed`, and `secret_box_energy_recycler_combo` encode
  hand/board prerequisites rather than unconditional card popularity.
- `hydreigen/tests/test_poffin_pokepad_priority.py`: eligible Basics, distinct
  prompt structures, missing setup pieces, optional empty selections, and
  reduced selections when Bench space is limited.
- `hydreigen/tests/test_combo_presence_planner.py`: search-before-refresh
  and multi-card discard/recovery examples.

Focused recheck: **36 tests passed** with:

```sh
python3 -B -m unittest tests.test_poffin_pokepad_priority tests.test_combo_presence_planner tests.test_energy_waste_guard -q
```

Limits: this is not proof that every historical benching, discard, attachment,
or copied prompt issue is fixed. The old notes still describe the Mac engine
as unavailable and an unresolved-card placeholder; those are historical states,
not evidence that the current simulator is unavailable or every old deck legal.

## 2. Palaking (`Palaking/`)

Requested/reported: exact Water-only Palafin investment, Dragonair/Tatsugiri
search, multi-move Zero to Hero and reset routes, pre-refresh checks, and
reduced meaningless retreat. The player reported 1.21 weaker than 1.20.

Implemented evidence:

- `Palaking/README.md`: version descriptions for Energy, prompt routing,
  Supporter checks, and switch changes. Some current-version labels are stale.
- `Palaking/STRATEGY_NOTES.md`: plan-first priorities and distinctions between
  productive setup and blindly filling the Bench.
- `Palaking/core/energy_planner.py`: separates Water and Lightning plans,
  delegates to the deck-specific planner.
- `Palaking/core/switch_usage_guard.py` and `core/air_balloon_planner.py` in
  archived packages demonstrate the movement-policy change directly.

Archive comparison:

| Archive | Confirmed change |
| --- | --- |
| 1.20 -> 1.21 | Tightened reset eligibility; removed a generic ready-attacker switch branch; Tatsugiri Balloon score changed from 4000 to 1200. |
| 1.21 -> 1.22 | Added explicit free Balloon-Tatsugiri retreat into a ready attacker; raised contextual Balloon scores, including 8800 for Active Tatsugiri. |

This explains a plausible lost route, not the size or certainty of a win-rate
effect. No fabricated leaderboard values or controlled A/B result are included.

Focused recheck: **10 tests passed** with:

```sh
python3 -B -m unittest tests.test_energy_planner_palafin tests.test_zero_to_hero tests.test_switch_engine tests.test_supporter_router_palafin -q
```

These tests run against current source, not the 1.20/1.21/1.22 archive snapshots.
Archived code was compared read-only; the historical packages were not modified.

## 3. N's Zoroark (`NsZoroark/`)

Requested/reported: Zoroark as the intended attacker, Zekrom as copy source,
Energy confined to the Zoroark line, and removal of unrelated deck priorities.

Implemented evidence:

- `NsZoroark/core/energy_planner_zoroark.py`: first/second Darkness priorities,
  third-Energy rejection, and non-Zorua/Zoroark target rejection.
- `NsZoroark/core/night_joker_planner.py` and its tests: copied attack evaluation
  and rejection of direct Zekrom attacks under the selected deck policy.
- `NsZoroark/core/strategy_scope.py`: profile, deck-signature, and state gates.
- `NsZoroark/STRATEGY_NOTES.md`: copy-source roles and specialized search.

Focused recheck: **17 tests passed** with:

```sh
python3 -B -m unittest tests.test_energy_discipline_zoroark tests.test_night_joker tests.test_search_supporter_zoroark -q
```

Limits: these checks do not prove that all cross-deck contamination or all
reported freezes were eliminated. A stale reason string mentions seven Energy;
do not copy that number into the report as the latest list's verified count.
Reusable card metadata containing other archetypes is not by itself evidence
that their strategy is active.

## 4. Shared Simulator and Review Tools

- `cabt-local-simulator/ENGINE_BUILD_NOTES.md`: the available engine library
  was Linux x86-64, not macOS ARM64. The unchanged official engine runs through
  Lima/Rosetta; replay reconstruction does not implement game rules.
- `cabt-local-simulator/README.md`, Battle Review: alternatives are restricted
  to the recorded legal window; later states are not counterfactually resimulated.
- The same README, Battle Study: supported approved rules require a runtime
  hook. Checkpoint existence and structural validation do not prove changed play.
- The recent battle-review patch was a direct code revision, not proof that
  every free-text annotation automatically updates an agent.

## 5. Palfingon (`palfingon/`)

- `palfingon/docs/STALL_FIX_1.2.md`: battle 15's 206 decisions, 15 saved End
  choices in turns 12-26, correct observed turn flags, structured attack-lock
  fix, and limits of observation rechecks.
- `palfingon/docs/BATTLE_REVIEW_1.3.md`: 14 reviewed windows, 13 exact matches
  plus the Energy-before-Petrel continuation, bundle costs, and smoke evidence.
- `palfingon/STRATEGY_NOTES.md`: distinct Palafin variants, exact typed attack
  requirements, recovery to hand versus recovery to deck.

The full current-source suite was rerun for this editorial check:

```sh
python3 -B -m unittest discover -s tests -q
```

**215 tests passed.** The 186-observation audit, latency figures, two mirrors,
and two random wins are previously recorded 1.3 evidence, not new games in this
turn. Their attribution must remain palfingon-specific.

## 6. Interpretation Boundaries

- Cross-deck rule reuse is software reuse, not trained transfer learning.
- Strategy leakage is code/configuration carryover, not catastrophic forgetting.
- Expert annotations are provisional preference labels, not proven optimal moves.
- The policy has no calibrated win probabilities or learned reward function.
- Match memory, approved-rule checkpoints, and immutable ZIPs serve different
  purposes; none alone is a trained model checkpoint.
- Keep DAgger, preference learning, and neural-network citations as related
  work or future possibilities, not implemented components.

## 7. Subsequent Retrospective Audit

`analyze_writeup_data.py` re-read all saved summaries and linked episodes.
There are 5,943 valid recorded decisions across 40 nonempty episodes, with
39 identified winners among 41 summaries. All 41 invalid sidecars are empty;
five additional empty episode files lack summaries. These caveats prevent
equating the corpus with 41 fully verified successful matches.

Imported 1.3 won battle 31 and lost battles 32 and 33 to imported 1.2, going
first in all three. The earlier two random smoke wins reverse seats, but
palfingon also went first in both. Workspace-based agent identities do not
prove exact historical version hashes. No new games were run for this audit.

Battle 15's turns 12-26 contain 15 END selections but 11 pass-only turns,
including eight consecutive engine turns 19-26. These are distinct measures.
`DATA_AUDIT.md` defines them and includes disaggregated tables and limitations.
