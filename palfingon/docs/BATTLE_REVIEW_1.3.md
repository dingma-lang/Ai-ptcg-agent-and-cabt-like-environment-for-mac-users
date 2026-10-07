# Battle Review: palfingon 1.3

Source: the player's 14 annotations for
`battle24_11-21_2026-09-09_sub_vs_sub`. Scope is this deck folder only.
The 60-card deck and previous submission archives are unchanged.

## What Was Wrong

Two main-window shortcuts bypassed the useful-action checklist: an ordinary KO
check and a Giga Impact priority return. High positive Poffin, Supporter, and
attachment scores therefore did not guarantee those actions would be selected.
The ready-attacker promotion calculation also counted Dragonair's low-damage
attack instead of its role as a protected evolution/search engine. Other misses
came from generic Hilda, Stadium, Balloon, and direct-search priorities.

## Applied Rules

| Reviewed decision | New behavior in the saved original window |
| --- | --- |
| 7 | Hold Beach when it has no immediate productive use; End is valid here. |
| 12 | Balloon the lone Active Dratini for free retreat into Tatsugiri. |
| 28 | Petrel finds Box when a safe three-card cost and a useful four-category package are confirmed. |
| 65 | Petrel for missing movement, not Hilda for an already-satisfied evolution package. |
| 79 | Productive Petrel before an ordinary KO. |
| 82 | Attach Water to complete Mega Dragonite's Water/Lightning/Lightning cost. |
| 84 | Pad finds energized, evolution-ready Dratini's Dragonair, enabling Guidance. |
| 87 | Petrel finds the missing Balloon for the Beach/free-retreat reset route. |
| 98 | Use Tatsugiri's legal Supporter-search ability before leaving Active. |
| 104 | Promote powered normal Palafin over Dragonair; protect the search engine. |
| 131 | Use productive Poffin before attacking. |
| 133 | Route through a second normal Palafin when an independent return move exists. |
| 136 | Complete Mega Dragonite's Water first, then re-check and use Petrel before attacking. |
| 141 | Use productive Poffin before attacking. |

Thirteen selections match the exact proposed index. Decision 136 intentionally
performs the same useful Energy completion requested in decision 82 before the
Supporter. A continuation test confirms Petrel is then selected, and an attack
follows when those preparation options are exhausted. This is not a replay of
the entire counterfactual game: later real observations change after an edit.

Every fresh main decision rechecks useful pre-attack preparation. A confirmed
final-prize winning route still has priority, avoiding needless resource use
when the game can end immediately. Boss is not played simply to spend a Supporter.
Existing once-per-turn restrictions and legal-option indices remain authoritative.

## Box Cost Accounting

- Score the three discarded cards together, not just individually.
- Protect needed Poffin, live evolution pieces, and the sole unreplaceable Mega.
- A spare Mega may be discarded when another is confirmed in the searched deck
  and no Stage 1 currently needs the held copy, or the main line is already built.
- Energy recovery must be confirmed in hand or the searched deck. Box can fetch
  only one Item: a searched Retrieval covers two Energy; a Stretcher covers one.
  Do not sum multiple searched recovery Items as though Box fetched all of them.
- Low-impact held Trainers may be exchanged for confirmed replacement categories.
  At most one needed replacement per category; an Item slot spent on recovery
  cannot also supply another required Item replacement.
- Use productive legal Guidance, and Active Tatsugiri's unused-Supporter search,
  before committing to Box. Recalculate the cost after those effects resolve.
- Remember only identified cards from our own `select.deck` and subsequent own
  movement/draw logs, separately by observing player. Clear this conservative
  search memory on the next turn or new game. Do not read omniscient player decks
  or assume a recovery card hidden in Prizes is available.

The original decision 28 contains one Mega in hand and one in the searched deck,
not two Megas in the deck. The rule follows the observed counts.

## Verification

- 215 unit tests, including isolated ZIP import and all 14 saved review windows.
- Previous battle-15 freeze regressions remain passing.
- All 186 selectable observations from battle 24 return valid unique indices
  within min/max counts; full policy execution is also checked without fallback.
- Local replay timing: 6.47 ms median, 74.06 ms p95, 99.57 ms maximum. These are
  measurements from this machine, not a hard real-time guarantee.
- Official worker smoke tests: mirrors battle27 (32 decisions, 6 engine turns)
  and battle28 (102 decisions, 18 engine turns); no engine errors or illegal
  selections. All 134 mirror decisions have traces.
- Alternating-seat random games battle29 (153 decisions, 21 engine turns) and
  battle30 (107 decisions, 15 engine turns): two wins, no engine errors or illegal
  selections. All 155 palfingon decisions have traces.

Small smoke samples do not establish a competitive win-rate gain or eliminate
every possible stall. One mirror had unpowered attackers and no useful Energy
or Supporter in hand for several turns. No-action windows can remain legitimate;
some inherited movement estimates also remain heuristic rather than full search.

## Install

Import `submission palfingon 1.3.zip` and select that new agent in the simulator.
Imported 1.2 copies are snapshots and do not change with workspace source edits.
No simulator engine reinstall is needed. Tests and original review observations
are excluded from the ZIP; the reviewed runtime module is explicitly included.
