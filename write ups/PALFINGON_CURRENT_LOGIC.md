# Palfingon: Current Submission Logic

## Scope and Identity

This document describes the implemented **palfingon 1.3** policy, not the union
of all historical deck requests. The current workspace matches all **76 files**
in [submission palfingon 1.3.zip](../palfingon/submission%20palfingon%201.3.zip),
with no missing or differing packaged files at the time of this analysis.
The archive SHA-256 is
`c473bc1209b253be6b0f6604905d81dbc2972e9b8b69b9ee457c572a73a97863`.
Extra workspace tests and documentation are not implied to be packaged.

The engine supplies legal choices and resolves card effects. The agent uses
deterministic, hand-authored scoring, explicit match memory, conditional
selection branches, and bounded combination evaluation. It is not a trained
neural policy. The statistical equations and archive experiments in the
[methods supplement](SCIENTIFIC_METHODS_AND_RESULTS.md) are offline analyses,
not newly added runtime features.

## 1. Strategic Objective

Build repeatable Palafin ex attacks by solving three linked problems:

1. Establish and legally evolve Finizen into the **Zero to Hero Palafin**.
2. Move that Palafin from Active to Bench, resolve its legal transformation,
   and return a powered attacker to Active when the available moves permit.
3. On subsequent turns, clear Giga Impact's restriction through a productive
   Bench-and-return route, or attack with another ready Pokemon.

The Dragonite line supplies evolution search and switching, with a distinct
three-Energy attack plan. Tatsugiri supplies Supporter access and a free-retreat
pivot when equipped. The second normal Palafin printing is a separate
one-prize attack option, not another transformation engine.

## 2. Every Decision Window

The actual entry path is
[`agent.py`](../palfingon/agent.py) ->
[`adapters/cabt/submission_entry.py`](../palfingon/adapters/cabt/submission_entry.py)
-> [`core/policy.py`](../palfingon/core/policy.py) ->
[`policy.py`](../palfingon/policy.py).
The module called `legacy_policy` inside the core is still on this live path;
it is not unused historical code.

| Stage | Current behavior |
| --- | --- |
| Deck handshake | Return deck IDs for the recognized cabt deck-loading prompt. This is separate from normal option-index selection. |
| Parse | Read the latest board, legal options, selection limits, context and logs. Missing ordinary choices return an empty list. |
| Update memory | Use observed turn/player/once-per-turn flags and structured events. Track attack restrictions by Pokemon instance and observer. |
| Identify moment | Mandatory resolution, setup, opponent prompt, effect resolution, main turn, or fallback. |
| Score | Combine ordinary heuristics, sequence adjustments, deck priorities, card analysis and reviewed constraints. |
| Select | Apply the conditional control flow below, not merely the maximum displayed score. |
| Return | Map to legal option indices, sanitize count/range/uniqueness, and record decision information when enabled. |
| Next call | Repeat the analysis after the chosen action and any effect prompts resolve. |

Fallback paths preserve legal output where possible, but may lose strategic
quality. Valid indices alone do not demonstrate that no exception occurred.

### Main-turn branch order

`choose_with_state_machine_scores` currently checks:

1. A recognized finishing route, including a final-prize attack or enabling move.
2. The reviewed `before_commit_choice` preparation function.
3. A sufficiently valuable productive move to another attacker or pivot.
4. When no immediate KO/win shortcut applies: evolution, attack readiness,
   useful Basics, transformation, setup abilities, another preparation check,
   Poffin, Pad, stalled-hand recovery, the broader plan, and Supporter routing.
5. Remaining score-based choice and legal fallback.

This is conditional, not a universal card order. In particular, **the reviewed
preparation branch runs before ordinary KO shortcuts**. The implementation can
choose development before a nonwinning KO; the article should not say that all
KOs always take precedence.

### Preparation function

[`before_commit_choice`](../palfingon/core/reviewed_turn_planner.py) first selects
an Active Tatsugiri's legal search Ability when the Supporter flag is unused.
It can also select productive Dragonair Guidance before a legal Secret Box.
If an attack option exists, it invokes the larger preparation checklist.

The checklist ranks qualifying actions using these actual offsets:

| Candidate | Minimum strategic score or filter | Added preference offset |
| --- | --- | ---: |
| Legal evolution | At least 2,500 | 100,000 |
| Productive Ability | At least 6,500 | 95,000 |
| Non-Supporter play | Usually at least 2,500; selected setup cards can qualify at 1,200 | 90,000 |
| Useful Energy attachment | At least 2,500 | 85,000 |
| Routed Supporter | At least 500 | 80,000 |

Poffin and movement cards have additional usefulness filters. These offsets
are preference bands, not guaranteed lexicographic tiers: the strategic score
is added, and other branches can act first. Ties are resolved deterministically.
Checks before END also exist in later main-turn and scoring paths; the reviewed
pre-attack function does not handle every END case by itself.

## 3. Current Deck and Card Timing

The [verified deck counts](scientific_data/deck_counts.csv) total 60 cards:
19 Pokemon, 32 Trainers and 9 Energy. Organizer IDs distinguish the two normal
Palafin cards despite their shared name.

| Card, copies, organizer ID | Role and current use conditions |
| --- | --- |
| Finizen x4, 105 | Preferred opening Active. Establish a first and second useful Palafin line, then consider duplicate value and Bench space. Evolve when legal; a held evolution increases setup value. |
| Palafin x3, 106 | Zero to Hero bridge. Search for this normal Palafin to evolve Finizen. Active-to-Bench movement opens transformation; do not treat ordinary hand evolution into ex as the route. |
| Palafin ex x4, 107 | Main attacker: Giga Impact, 250 base damage for one Water. Prefer ex copies in the deck for transformation. Two or more stranded in hand increase the value of a checked hand refresh. |
| Palafin x1, 51 | TEF 49 one-prize attacker: Vanguard Punch, 130 for one Water. Recoil equals its existing damage. Check self-KO and prize value; this card has no Zero to Hero. |
| Dratini x2, 902 | Start the support/secondary-attack line. Obtain through Pad when missing; its 80 HP makes it ineligible for Poffin. It is not interchangeable with Tatsugiri. |
| Dragonair x2, 903 | An Energy enables Evolutionary Guidance. Prefer a normal Palafin or Mega Dragonite that advances a real evolution line. A just-evolved Dragonair cannot immediately evolve again. |
| Mega Dragonite ex x2, 904 | Sky Transport provides productive switching. Ryuno Glide is a separately funded 330-damage option costing Water + Lightning + Lightning and discarding two Energy. Its manual-retreat option is heavily penalized. |
| Tatsugiri x1, 122 | Active Supporter-search Ability; later an Air Balloon pivot. Current Energy scoring strongly rejects attachment to it. |
| Buddy-Buddy Poffin x4, 1086 | Build missing Finizen lines or useful Tatsugiri. Targets must be legal Basics with at most 70 HP, and selected count must fit the prompt/Bench. Not an unconditional play whenever any Bench slot is open. |
| Poke Pad x4, 1152 | Find missing Dratini, normal Palafin or Dragonair for actual development. The reviewed bridge favors Dragonair when an energized, evolution-ready Dratini can then help find Palafin. |
| Team Rocket's Petrel x3, 1219 | Find the best immediate Trainer bridge: needed Poffin, Pad, a movement piece, or a safely usable Secret Box package. Do not duplicate a Poffin already available without purpose. |
| Secret Box x1, 1092 | Use a feasible three-card cost for a useful Item/Tool/Supporter/Stadium package. Account for category slots, replacement availability and recovery capacity. A Supporter can be retained for next turn. |
| Lillie's Determination x4, 1227 | Check executable Items, Basics, evolution, abilities and useful Energy before refreshing. Favor dead/short hands, sparse-board emergencies and multiple stranded ex copies. Preserve a playable line when another productive Supporter is available. |
| Hilda x1, 1225 | Find needed evolution and Energy: normal Palafin, Dragonair, Mega Dragonite, or Water enabling the current attacker. Current planning does not intentionally use it to strand another Palafin ex in hand. |
| Crispin x2, 1198 | Complete a useful typed Energy requirement, especially an unpowered Active ex or the Dragonite line. Its effect and the manual attachment are distinct opportunities. |
| Boss's Orders x2, 1182 | Favor a visible KO/prize route reachable by an attacker, particularly a finishing route. Otherwise penalize casual gust use. Target scoring and initiation both matter. |
| Judge x1, 1213 | Refresh a dead hand or disrupt a visibly large opposing hand, after useful pre-refresh actions. Avoid very low remaining draw resources. |
| Surfing Beach x3, 1262 | A Water-compatible movement resource. Distinguish playing the Stadium from using its effect; a Stadium on board alone does not prove an unused switch. |
| Air Balloon x2, 1174 | High value on Active Tatsugiri, a useful Tatsugiri backup pivot, or normal Palafin/Finizen needed for a free return route. Attachment to ex requires a useful reset; avoid random tool placement. |
| Switch x1, 1123 | Spend when it produces transformation, attack reset or meaningful progress. Prefer an available productive Sky Transport route when it conserves the Item. |
| Battle Cage x1, 1264 | Respond to visible damage-counter placement threats. Preserve needed Surfing Beach movement; Cage is not generic protection from attack damage. |
| Energy Retrieval x1, 1118 | Recover useful discarded Basic Energy. Its two-card capacity can support a Box cost; recovery does not itself attach Energy. |
| Night Stretcher x2, 1097 | Recover one useful Basic, evolution or Energy to hand. Recover ex only with a useful shuffle-back plan. One Stretcher cannot recover three Box discards. |
| Basic Water Energy x6, 3 | One planned Energy per Palafin-line Pokemon, or a productive first Energy/attack completion on the Dragonite line. |
| Basic Lightning Energy x3, 4 | Dragonite-line investment; rejected on the Palafin line. Complete typed cost rather than counting arbitrary Energy cards. |

Primary implementation sources are
[`palafin_planner.py`](../palfingon/core/palafin_planner.py),
[`turn_plan.py`](../palfingon/core/turn_plan.py),
[`supporter_router.py`](../palfingon/core/supporter_router.py),
[`palfingon_cards.py`](../palfingon/core/palfingon_cards.py), and
[`reviewed_turn_planner.py`](../palfingon/core/reviewed_turn_planner.py).
These are aggregate descriptions: a favorable component score can still be
overridden by a higher-level branch.

## 4. Movement and Attack-State Logic

### Transformation

For an Active normal Palafin, the approximate route model counts one move to
transform and two to transform and return an attacker. Starting with normal
Palafin on the Bench requires an extra move. Partial development can be useful
even when the model cannot complete an attack immediately.

Available legal Sky Transport, compatible Stadium movement, Switch and unused
free retreat contribute to the plan. A Balloon attachment and the retreat it
enables must not be counted as two independent moves. The committed second-
Palafin pivot check specifically requires an independent return, such as an
unused free retreat or held Switch; Stadium presence alone is insufficient.

### Giga Impact reset

Structured log memory associates the attack restriction with a Pokemon
instance, rather than blocking every Pokemon named Palafin ex. Bench movement
and current state update the restriction. A productive reset can send the ex to
Bench, use an equipped Tatsugiri or normal Palafin as pivot, and return a ready
attacker. The new observation is re-evaluated after each move.

### Other productive movement

Current 1.3 behavior is broader than the old instruction to switch only for
transformation or reset. It also recognizes movement from a non-attacking
Active to a ready attacker, a better KO, and a narrow opening Tatsugiri-search
route. It can use a **switch effect** to free an Active Mega Dragonite; that does
not mean paying its manual-retreat cost.

Source: [`expert_battle_planner.py`](../palfingon/core/expert_battle_planner.py),
[`switch_usage_guard.py`](../palfingon/core/switch_usage_guard.py),
[`air_balloon_planner.py`](../palfingon/core/air_balloon_planner.py), and
[`palafin_attack_state.py`](../palfingon/core/palafin_attack_state.py).

## 5. Energy Rules and Their Exact Scope

`palaking_energy_breakpoint_score` is the live shared helper despite its name.
It assigns -100,000 to non-Water on the Palafin line, any further attachment
once that line member already has one Energy, and attachment to Tatsugiri.
The Dragonite line similarly discourages more than one Water or two Lightning.
These are strategic penalties, not changes to game legality. A mandatory effect
with no preferred target must still return a legal selection.

An unpowered Dragonair receives a large positive first-Energy score because
Guidance can unlock evolution access. An energized Dratini with Dragonair held
also receives setup value. Therefore **the current policy does not strictly
fund every Finizen before every Dragonair**.

Another important implementation detail: `palafin_attackers_are_satisfied`
checks existing **Palafin ex only**, not every unevolved member of the line.
When all existing ex have exactly one Water, Dragonite's Water completion gains
value. This differs from a literal requirement to power every Finizen first.

The caps on Finizen and normal Palafin express the chosen development plan;
they are not a claim that all of their printed attacks cost one Energy. Energy
sufficiency also does not imply legal attack readiness: position and attack
restrictions remain separate checks.

## 6. Discard as a Bounded Combination Problem

The current Secret Box evaluator does more than rank three cards independently.
It scores candidate discards, retains at most twelve candidates, and enumerates
three-card combinations. Consequently there are at most
`C(12, 3) = 220` candidate bundles, before feasibility filtering.

For bundle D, its implemented optimization is

$$D^*=\arg\max_{D\in\mathcal F,\ |D|=3}\sum_{c\in D}q(c),$$

where q is the discard preference score and the feasible set F enforces the
following checks:

- Each selected card has a nonnegative discard preference.
- Needed Dragonite-line development is preserved by the reviewed constraints.
- Surviving held recovery contributes two cards per Retrieval and one per Stretcher.
- Confirmed searchable recovery uses at most one Box Item slot: Retrieval or
  Stretcher, not an assumed simultaneous search for both.
- A searched recovery card and a replacement Item cannot spend that same slot.
- No replacement category is allocated more than once.

Own search information comes from a legitimate search prompt or retained
confirmed events, not the simulator's omniscient deck state. The evaluator is
bounded local planning, not a full-game rollout or a proof that the highest-
scoring bundle is globally optimal.

## 7. What the Scores Mean

The score pipeline includes explicit hand-tuned component weights. For example,
the deck-priority layer adds 0.25 times Zero to Hero score, 0.15 times switch-
engine score, 0.35 times switch-usage score, 0.35 times Balloon score and 0.15
times Mega Dragonite score, alongside other terms. Later constraints can clamp
or elevate particular options; preparation branches can override rankings.

These values are **preferences, not probabilities, learned Q-values or common
units of win chance**. A score explanation should identify both component
reasons and the branch that actually selected the action. Battle 24 decision
131 illustrates why: the old recorded policy selected an attack even though
Poffin had the higher displayed score.

## 8. Implemented, Measured and Still Unproven

| Status | Supported description |
| --- | --- |
| Implemented now | Legal-option selection, typed Energy preferences, per-instance attack memory, route heuristics, conditional search/Supporters, repeated preparation checks, bounded Box costs. |
| Verified locally | All 76 packaged files match current source. Fixed-state experiments made 348 legal calls on 29 distinct inputs. Full 1.3 matched 14/14 regression targets and 13/14 original expert indices. |
| Mechanism tested | Disabling only the reviewed preparation hook changed 6/14 reviewed choices; other movement fixes still acted on the saved stall inputs. |
| Not established | A general win-rate improvement. The three available imported 1.3-versus-1.2 games were one win and two losses for 1.3, with biased opening order. |
| Not runtime additions | Hypergeometric opening calculations, confidence intervals, aggregate score-discordance and Energy-snapshot statistics. |
| Future work | Held-out game evaluation, broader opponents, rule-interaction tests, more exact route feasibility, and possibly an offline learned ranker. |

Legacy handlers for cards absent from the current list are not evidence that
those cards are part of palfingon's strategy. Hydreigon/Gengar and Zoroark
development belong in historical background, not in this current logic map.
The focused article is [Palfingon strategy draft v4](palfingon_strategy_draft_v4.md).
