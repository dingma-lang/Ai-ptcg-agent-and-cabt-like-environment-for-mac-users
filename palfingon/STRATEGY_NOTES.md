# palfingon Strategy Notes

## Approach

Deterministic legal-choice heuristics inherited from Palaking's current source,
with separate deck/profile loading and no cross-deck fallback. Re-evaluate the
hand and available actions on every cabt decision window. The official engine
enforces once-per-turn limits, evolution timing, attack restrictions, and hidden
information. The agent does not create game actions or simulate its own rules.

## Opening and Attack Plan

Prefer going first and opening Finizen. Establish a second useful Finizen and
Dratini; use Tatsugiri for Supporter access and as an Air Balloon pivot. Poffin
can find Finizen/Tatsugiri but cannot find this 80-HP Dratini. Use Poke Pad for
Dratini, then Dragonair, or for the missing normal Palafin evolution.

Normal Palafin ID 106 must move Active-to-Bench to trigger Zero to Hero. Keep
Palafin ex in the deck until that effect resolves. Plan enough separate moves
to return a powered attacker Active. Giga Impact's next-turn restriction is
specific to that Pokemon; moving it to the Bench clears the attack restriction.
Use Sky Transport, Surfing Beach, Switch, and free retreat through Air Balloon
when they produce a useful transformation, reset, or attack.

Do not retreat Mega Dragonite ex by discarding its two-Energy cost. Build its
Stage 1 for Evolutionary Guidance, and use Sky Transport only when movement
helps. Its 330-damage attack costs Water + Lightning + Lightning and discards
two Energy; this is a different resource plan from Palafin ex.

## New and Changed Cards

| Card | Timing and limits |
| --- | --- |
| Palafin TEF 49, ID 51 | One-prize attacker with 130-damage Vanguard Punch for one Water. Self-damage equals its existing damage. Prefer a clean KO; avoid nonwinning self-KO. It has no Zero to Hero. |
| Judge | Use on a dead hand or to reduce a visibly large opposing hand. Check useful Items, evolution, Basics, and Energy first. Prefer Lillie for stronger own setup; do not choose by hand index. |
| Battle Cage | Respond to visible opposing damage-counter placement threats on the Bench. Preserve Surfing Beach when needed for this turn's movement. Cage does not prevent damage from attacks. |
| Night Stretcher, two copies | Recover a missing playable Basic, evolution, or useful Energy. It returns one card to hand, not deck. Recover Palafin ex only with a productive shuffle-back plan. |

The current list has no mass Pokemon recovery or damage-boosting switch
Supporter. Those cards are absent from the profile, deck, and relationship map.
Secret Box must not assume one Night Stretcher can restore three discarded
attackers. Protect needed Poffin on a sparse Bench and play useful cards before
paying discard costs or refreshing the hand.

## Energy and Sequencing

- Palafin ex: one Water maximum.
- Finizen / both normal Palafin variants: one Water as the planned investment;
  their other printed attacks can cost more, but this policy does not fund them.
- Dragonite line: at most one Water plus two Lightning; prioritize an Energy on
  Dragonair when it enables Evolutionary Guidance, then attack access.
- Tatsugiri: no Energy investment; use an Air Balloon pivot.
- Never attach Lightning to the Palafin line. Apply caps to manual attachments
  and forced effect-target scoring, choosing a legal target if the effect is mandatory.
- Use active Tatsugiri's Ability before choosing a Supporter when productive.
- Check useful Items, legal evolutions, Basics, abilities, and Energy before
  Lillie/Judge, then recheck after the refresh resolves.
- Before a nonwinning attack or pass, check productive setup and unused
  Supporter/attachment opportunities. Passing remains valid when actions waste resources.

## Data and Rule Sources

The supplied nested `pokemon-tcg-ai-battle-challenge-strategy/EN_Card_Data.csv`
was copied into this folder. It has 1,267 unique card IDs and 2,022 rows. Its
contents match the existing top-level organizer CSV. The additional variant
and Trainer cards in this deck are resolved by ID, not merely by name.

The installed official cabt worker supplied 1,267 cards and 1,556 attacks. The
offline snapshots preserve real attack IDs, including Vanguard Punch 51,
Giga Impact 134, and Ryuno Glide 1302. Runtime makes no metadata network calls.

The official [Palafin TEF 49 reference](https://www.pokemon.com/uk/pokemon-tcg/pokemon-cards/series/sv05/49/)
confirms its separate attack/recoil plan. The official
[Great Haul Net reference](https://asia.pokemon-card.com/sg/card-search/detail/25269/)
confirms a Water recovery effect, but no organizer ID was supplied for it.
The player approved replacing it with Night Stretcher on 2026-09-07.

## Validation and Limits

Regression tests cover inherited sequencing plus distinct Palafin identities,
Energy caps, Judge timing, Cage/Stadium priority, recovery safety, legal option
indices, deck isolation, and the official metadata snapshot.

Initial official-engine checks:

- Random opponent: win, 182 total decisions, 31 engine turns.
- Mirror play: completed, 171 total decisions, 22 engine turns.
- These are integration checks, not a reliable win-rate estimate.

Heuristic movement counts and return-KO estimates remain approximations. There
is no trained model or proven tactical rollout improvement in this release.
Only observation/public information informs decisions; unknown prizes are not
assigned hidden identities.

## Expert Study, Version 1.1

Three supplied logs have been reviewed. `docs/EXPERT_STUDY_1.1.md` maps each
lesson to its code and regression coverage. The new opening route uses a free
Finizen-to-Tatsugiri retreat when Supporter access is missing. A benched normal
Palafin/Finizen may hold Air Balloon for a two-move transformation route. Spent
retreat is unavailable, and Balloon plus retreat is not counted twice.

Guidance can find a playable backup Palafin even with Palafin ex already in
play. A freshly evolved Dragonair cannot evolve again that turn. Exact typed
Energy and legal moves are checked for immediate finishing routes, including
Mega Dragonite's 330-damage attack. Gust target scoring distinguishes opponent
Pokemon from our pivots and recognizes Ability-based damage prevention.

Secret Box can use already-redundant attackers as costs without assuming mass
recovery. A playable final-prize Boss target can outrank a hand refresh. Existing
pre-Lillie checks and protection of needed Poffin remain in place.

The logs do not prove a win-rate increase: two ended by concession and one of
those included an opponent timeout. Their Great Haul Net/Kieran lines are not
available in this deck. Match clocks, complete legal-choice windows, and hidden
cards cannot be reconstructed from human-readable battle text alone.

Version 1.1 verification: 179 tests passed, including isolated submission import.
Official mirror: 117 decisions / 15 engine turns, completed. Random: 187 decisions /
37 engine turns, win. All 304 recorded choices were legal; all 204 palfingon
decisions had traces. Rechecking 117 mirror observations locally measured 6.52 ms
median, 50.57 ms p95, 130.13 ms maximum including initialization, excluding engine
and IPC time. Details are retained locally in
`local_results/expert_study_1.1_validation.json`.

## Stall Fix, Version 1.2

Battle #15 exposed a strategic deadlock despite legal selections. Version 1.2
adds structured, per-instance attack-lock memory across prompts; aligns switch
initiation and target scoring; permits free escape from Active Mega Dragonite;
and keeps its paid-retreat ban. Refresh checks depend on executable actions,
not merely a theoretical combo. Large dead hands can use Lillie/Judge, and
positive useful options are no longer rejected by a 500-point End override.

See `docs/STALL_FIX_1.2.md` for staged changes, original-observation regressions,
live-engine results, and limits. 202 tests pass. All 15 saved passes from the
problem interval now choose legal movement. Two fresh mirrors completed in
18 engine turns each with no pass-only turns. This fixes the demonstrated
palfingon failure; it is not a claim that every possible state or deck is fixed.

## Human Review, Version 1.3

The battle-24 review now affects runtime selection, not just explanatory scores.
Useful setup, search abilities, typed Energy completion and Supporters are checked
before ordinary attacks and KOs. Confirmed final-prize winning routes retain
priority. Pad may build energized Dragonair before searching Palafin; promotion
protects the Dragonair engine, and second-Palafin switch routes require a return.

Secret Box uses bounded three-card cost evaluation with confirmed replacement
and recovery capacity. Own search knowledge is turn-scoped and player-isolated;
unseen Prizes and omniscient simulator deck contents never fund the plan.
See `docs/BATTLE_REVIEW_1.3.md` for the 14 decisions, the Energy-before-Petrel
sequencing exception, validation evidence, and remaining limitations.
