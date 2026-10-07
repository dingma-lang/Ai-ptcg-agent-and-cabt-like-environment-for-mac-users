# Expert Battle Study: palfingon 1.1

Reviewed 2026-09-08. Scope: palfingon only; deck remains 60 cards with two Night
Stretcher. Palaking, hydreigen, and the other archetypes are not modified.

## Evidence Register

Each archived file is one game, beginning at Setup and ending at the win line.
Turn numbers below mean Tristary's own turns, not cabt's alternating turn counter.

| Local source | Outcome | Main evidence |
| --- | --- | --- |
| expert_logs/tristary_vs_jocobosam.txt | All prizes taken, own turn 7 | Opening free Tatsugiri search; useful plays before Lillie; two transformations; Dragonair search; Dragonite finishing gust |
| expert_logs/tristary_vs_borgalatstar.txt | Concession, own turn 8 | Balloon on benched Finizen; backup transformations; bypass Cornerstone; Secret Box for the finishing Boss |
| expert_logs/tristary_vs_vtr_gamer06.txt | Concession after turn-2 KO | Two normal Palafin, two Water, Balloon on the second one; Beach out, retreat back, two transformations |

The first two files preserve the attached text. The inline third log was
normalized from Markdown bullets to plain text. Originals stay outside the ZIP;
this curated report ships with the strategy notes.

## Adopted Rules

| Lesson | Conditions, priority and limits | Runtime code |
| --- | --- | --- |
| Open Supporter access | If Finizen is Active, Tatsugiri benched, no Supporter/normal Palafin in hand and no established attacker, Balloon can enable a free retreat into Tatsugiri. Do not pay Energy for this speculative opening. | expert_battle_planner.opening_tatsugiri_route; air_balloon_planner; palafin_planner.score_retreat_option |
| Give the return pivot Balloon | With normal Palafin Active and a legal non-retreat switch, a benched Finizen or normal Palafin can hold Balloon. Prefer the normal Palafin free pivot to enable a second transformation. Retreat must be unused. ID 51 is not a Zero to Hero Pokemon. | expert_battle_planner.bench_balloon_pivot; palafin_planner.score_switch_target |
| Count distinct movement resources | Attaching Balloon and retreating are one movement opportunity, not two. Do not count spent manual retreat. All actual steps must appear among legal options. | turn_plan.MovementResources; movement_resources |
| Guidance should help this turn | If Dragonair just evolved, it cannot immediately evolve again. Prefer normal Palafin for a mature Finizen instead. A previously established Palafin ex must not block building its backup. | palafin_planner.score_dragonair_evolution_target; has_ready_finizen_for_palafin |
| Respect damage prevention | Giga Impact does zero into an enabled Cornerstone Stance because Palafin ex has an Ability. A no-Ability attacker is not blocked by that condition. Apply known weakness/resistance and correct Mega prize value. | expert_battle_planner.ability_damage_blocked; policy.estimate_attack_damage; giga_impact_planner |
| Separate gust from our pivot selection | Opponent choices are valued as KO targets, not as our retreat pivots. Bypass a protected Active for an accessible final-prize target. | expert_battle_planner.gust_target_score; palafin_planner.score_selection_option |
| Use the real finisher | Before ordinary setup/nonwinning attacks, check legal final-prize attacks, a ready benched attacker with a visible move, useful Boss, or one legal missing Energy attachment. Dragonite requires W/L/L, not any three Energy. Its paid retreat remains forbidden. | expert_battle_planner.finishing_action; policy.choose_with_state_machine_scores |
| Relax protection only after setup | Spare Palafin ex in hand can pay a cost after two powered Palafin ex are built. Spare Mega Dragonite can pay when one is built and no Dragonair needs it. This does not authorize discarding the only evolution path. | expert_battle_planner.redundant_attacker_discard; palafin_planner.score_discard_selection |
| Search for a finishing Supporter | During Secret Box selection, Boss outranks refresh when Supporter is unused and the Active's damage can take final prizes from a visible Bench target. Otherwise retain contextual Lillie/setup choices. | palafin_planner.score_secret_box_target |

## Sequences Worth Keeping

1. Vtr turn 2: use Poffin, evolve Dragonair, use both Pad searches and evolve both
   mature Finizen, put down Beach, then refresh with Lillie. Attach the second
   Water, fund Box without discarding required board pieces, Balloon the second
   normal Palafin. Beach A to B; transform A; free-retreat B to ex-A; transform B;
   attack with ex-A. Recheck legal options after every step, including mandatory
   Zero to Hero prompts. This is not a batch of invented actions.
2. JocoboSam turn 3: attach Lightning to Dragonair, use Guidance, evolve another
   mature Finizen into normal Palafin. Search choices should complete a useful
   present line rather than mechanically collect a Stage 2.
3. JocoboSam turn 7: finish Dragonite's W/L/L cost with Water, gust the two-prize
   target, bring Dragonite Active without paying its retreat cost, attack for
   330. Prioritize this route over another 250-damage attack that does not win.
4. BorgalaTstar late game: Cornerstone makes a straight Giga Impact ineffective.
   Gusting an unprotected Bench target can still finish the prize route. The
   final concession confirms the game outcome, not an unplayed final attack.

## Retained Checks

- Poffin finds only legal Basics with at most 70 HP; this Dratini needs Pad.
- Use useful Items, Basics, Energy and legal evolutions before Lillie; then
  re-evaluate the new hand. Do not label a legal first-player turn-1 pass as a
  Supporter freeze when no Supporter can legally be played.
- Palafin line: one Water maximum; Tatsugiri: no Energy; Dragonite: W/L/L cap.
- Never shuffle imagined prize identities into a plan. Unknown deck/prize
  distribution remains uncertain until a legal search reveals information.
- Preserve sparse-Bench Poffin and required evolution bridges when paying costs.

## Not Copied

- Great Haul Net appears in the first two logs but is absent from our organizer
  catalog/deck. Night Stretcher recovers one card to hand, not five to deck.
- Kieran appears in the second log, not in the current deck. No card was added.
- The paid Dragonair retreat in the second log is not a blanket instruction to
  discard Energy for movement. The existing conservative restriction stays.
- A turn-2 concession after an opponent timeout is evidence of the demonstrated
  setup sequence, not proof of matchup strength.
- We cannot infer every remaining deck card, unused Ability, legal alternative,
  or choice latency from prose. The rules are conditional heuristics, not full
  replay reconstruction, opponent omniscience, or online model training.

## Verification

`tests/test_expert_battles.py` exercises these rules through the imported agent
and focused helper tests, with actual engine card/attack IDs. Existing tests
remain enabled. An isolated temporary submission import also tests the same
code without workspace imports. Official-engine smoke results are recorded in
`local_results/expert_study_1.1_validation.json` after the run; small samples
measure integration and legality, not statistically established improvement.
