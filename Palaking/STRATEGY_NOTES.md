# Palaking Strategy Notes

This folder is the clean starting workspace for the Palafin ex / Mega Dragonite ex water-lightning deck.

## Current State

- `palaking_deck_source.csv` contains the modified 60-card list supplied by the player.
- `build_deck_csv.py` has a forced mapping for `Palafin SVALT 81` to local ID `106`.
- `deck_profile.json` is a Palaking-only starter profile with `strategy_id: palaking`.
- Strategy rules from other deck folders are gated off by `core/strategy_scope.py` and should not affect this deck.

## Deck Concept

- Establish Finizen early and evolve through Palafin into Palafin ex.
- Establish Dratini and Dragonair as the route to Mega Dragonite ex.
- The current override is plan-first: win/prevent immediate loss, choose the best Prize trade, make a legal attack this turn, prepare next turn's attack, develop evolution/switching, then conserve optional resources.
- Use Buddy-Buddy Poffin only when it finds a concrete Finizen or Tatsugiri setup target. A developed Bench with only one open slot should often save that slot for Palafin movement or a follow-up attacker.
- Do not route Dratini through Poffin; Dratini has 80 HP in local metadata and must come from Poké Pad/Hilda-style search.
- Use Poké Pad, Team Rocket's Petrel, Secret Box, and Lillie's Determination to assemble missing setup pieces.
- Treat Palafin ex and Mega Dragonite ex as the real damage dealers.
- Treat Tatsugiri as support, not the main plan.
- In setup, prefer Finizen in the Active Spot over the Dragonite line when both are legal. Dratini/Dragonair/Mega Dragonite ex are board-development pieces, not preferred opening actives.
- Keep Palafin ex to one useful Energy. Manual attachments and effect attachments to an already powered Palafin ex are hard-blocked when another legal target/pass exists.
- Only attach Water Energy to the Finizen / Palafin / Palafin ex line. Reserve Lightning Energy for Dratini/Dragonair/Mega Dragonite ex.
- Attach Air Balloon to active Palafin for Zero to Hero movement, active attack-locked Palafin ex for a reset line, or Tatsugiri as a high-value Dragonite reset pivot. Active Tatsugiri with Air Balloon is a strong pivot because it can retreat without discarding Energy.
- Hilda should never search Palafin ex as the evolution target. Use Hilda for normal Palafin, Dragonair/Mega Dragonite ex, or the Water Energy needed by an active Palafin ex.
- If active Palafin ex has no Energy, Hilda/Crispin should prioritize finding or attaching Water. Lightning Energy must stay off Palafin ex and the rest of the Palafin line.
- Switch or retreat mainly in Palafin loop windows: active normal Palafin can move to Bench for Zero to Hero, active Palafin ex is attack-locked after Giga Impact, or active Tatsugiri has Air Balloon and can retreat for free into a ready attacker.
- Treat Mega Dragonite ex's Sky Transport as the primary reusable movement effect. Before spending Switch, Kieran as a switch, or a paid retreat, check whether Sky Transport reaches the same final board while saving a card or Energy.
- One switching effect is only one exchange. Active Palafin usually needs one movement to transform and another movement to bring Palafin ex Active that same turn. A Benched Palafin route can need three separate movements if it must transform and attack immediately.
- For the Palafin ex recharge route, prefer a fresh powered Benched Palafin ex when available. Otherwise, Tatsugiri with Air Balloon is a strong Dragonite pivot because Dragonite can push Tatsugiri Active, then Tatsugiri can retreat back into the reset Palafin ex.
- If active Palafin ex can currently use Giga Impact, Mega Dragonite ex switch Ability should stay low priority. If normal Palafin needs Zero to Hero, or Palafin ex cannot use Giga Impact and needs reset/recharge, Mega Dragonite ex switch Ability becomes high priority.
- Mega Dragonite ex should not pay a two-Energy retreat cost. Its switch Ability is for Palafin reset/recharge lines, not random pivoting.
- After our Active is Knocked Out, if no attacker is ready on board, promote Finizen so the next Palafin line can develop.
- Lone Finizen/Dratini/Dragonair/Palafin pieces and next-turn evolution pieces get extra protection. Do not throw the only evolving board piece Active unless there is no attacker and Finizen is the best rebuild route.
- Avoid retreating if it discards Energy unless the move is one of the approved Palafin reset windows.
- Prefer going first: the log showed going first gives a strong Poffin, Poké Pad, Tatsugiri, and Energy setup turn.
- Before Lillie's Determination, use a staged check: usable Items first, then legal evolution and Basics from hand, then useful abilities/Energy attachment, then Lillie if the hand still needs a reset.
- If Lillie would shuffle away a live evolution chain, use another legal Supporter first when possible: Hilda, Petrel, Crispin, or Kieran depending on the board.
- If cabt exposes main-turn legal actions, treat that as our actionable turn even when raw turn parity is ambiguous. Direct current-player fields override parity when available.
- Before any non-KO attack or end turn, re-check evolution, useful Items, Energy attachment, and legal Supporters. Because cabt calls the agent after every action, this checklist reruns after each resolved card. The checklist now ignores low-value playable cards so the agent can pass instead of spending resources with no meaningful gain.
- Generic attachment-effect prompts, including `CTX_ATTACH_FROM`, are routed through attachment-target scoring. This prevents effect attachments from falling back to the first legal target and piling Energy onto an already powered Pokémon.
- When the Bench is empty or nearly empty, use Buddy-Buddy Poffin first if legal. If no Poffin/playable Basic/setup Ability/exact setup Supporter is available, Lillie's Determination becomes the reset button for dead evolution-heavy hands.
- Do not bench every Basic merely because it is legal. Bench Finizen for the Palafin chain, Dratini for the Dragonite chain, and Tatsugiri when support access or a pivot matters; hold extras when they crowd the Bench, reveal too much, or weaken the switch loop.
- The card-by-card analysis layer lives in `core/card_analysis.py`, `core/card_relationships.py`, `core/deck_synergy_graph.py`, and `core/policy_rules_from_analysis.py`. It exports `docs/CARD_BY_CARD_ANALYSIS.md`, `docs/SYNERGY_MAP.md`, and `data/deck_synergy_graph.json`, and adds a light cached scoring adjustment on top of the tested Palaking planners.
- Air Balloon is not a random Tool. The analysis and scoring rules reserve it for active Palafin Zero to Hero and active attack-locked Palafin ex reset/recharge lines.
- If Finizen can legally evolve and normal Palafin is in hand, evolve before Secret Box, Lillie, or discard-cost cards. Do not discard the only normal Palafin in that window.
- Secret Box and Petrel route to Buddy-Buddy Poffin only when Poffin is missing and the Bench still needs setup Basics. If Poffin is already in hand, play Poffin instead of searching for it.
- Secret Box discard prompts protect Poffin when the Bench is low. If Secret Box is resolving and hand size is low, Lillie's Determination is a high-priority Supporter target for the next hand rebuild.
- Boss's Orders and Kieran are held unless they create visible Giga Impact KO math, a real prize route, or a switch/reset line. They are not generic setup Supporters.
- Poké Pad prioritizes normal Palafin when Finizen is ready. Once Finizen setup is stable or Palafin is already available, Poké Pad can shift toward Dratini/Dragonair and Tatsugiri.
- Giga Impact should be used aggressively. Its drawback belongs to the specific Palafin ex that attacked, and switching/reset resources can manage the next-turn restriction.
- Do not pass or spend random setup actions when Giga Impact creates a KO, major pressure, or a strong Boss/Kieran prize route.
- Do not expose Mega Dragonite ex just for convenience if the opponent is close enough on Prizes that a return knockout creates a losing trade.
- Palaking card-selection prompts are routed directly in root `policy.py`, so Secret Box, Petrel, Poké Pad, discard-cost, switch-target, attach-target, and evolution-selection windows apply deck-specific logic before generic scoring.

## Palafin Combo Line

- If Buddy-Buddy Poffin is legal and the board still needs Finizen or Tatsugiri, use it to establish those pieces. If the board is already developed, preserve Poffin and Bench space.
- If Finizen is ready and normal Palafin is missing, use Poké Pad to find Palafin.
- Petrel can directly get Poké Pad when that Poké Pad leads to Palafin evolving this turn.
- If normal Palafin is already handled and the Dragonite line is absent, prioritize Poké Pad for Dratini before treating the setup as complete.
- If active Finizen plus another Water Pokémon can start the chain, Secret Box may assemble Poké Pad, Air Balloon, Surfing Beach, and a Supporter.
- Petrel can fetch Secret Box instead of a single direct card when Secret Box safely assembles multiple pieces, including a next-turn Supporter after the current Supporter has been spent.
- Secret Box can spend Palafin ex / Mega Dragonite ex copies only when Sacred Ash or exact recovery is ready; recover those Pokémon before Lillie or another hand refresh.
- Evolve Finizen to Palafin, move Palafin from Active to Bench, use Zero to Hero into Palafin ex, then use Surfing Beach/Switch/Kieran/Air Balloon to bring the right attacker Active.
- If normal Palafin is already available and the Dragonite line is absent, Poké Pad should find Dratini. Dratini has 80 HP in local metadata, so Buddy-Buddy Poffin cannot fetch it.
- Poké Pad may not search Dragonair unless a real Dratini is already active or benched. Tatsugiri is only a support Basic and must never be treated as the Dragonite Basic.
- Petrel should only get Poké Pad for Dragonair when Dratini is actually in play. If Dratini is missing, the Poké Pad route is for Dratini first.
- Use Tatsugiri's Attract Customers before spending a Supporter when Tatsugiri is Active.
- In cabt, Tatsugiri's Attract Customers can appear as an attack-shaped option. Treat it as a setup Ability, not as a low-damage attack, and use it before Lillie's Determination or other Supporters when the Supporter slot is unused.
- Do not attach Energy to Tatsugiri for retreat setup. Use Air Balloon for Tatsugiri pivoting.
- If Dragonair has any Energy attached, check Evolutionary Guidance every turn. Use it before Supporters when the searched Evolution can be played immediately; use a hand-refresh Supporter first when the searched card would otherwise be shuffled away.
- Dragonair should not search Palafin ex; Palafin ex needs to stay in the deck for Palafin's Zero to Hero Ability.
- Once every Palafin ex in play has exactly one Water Energy and no extra Energy, spare Water Energy can be routed to Dratini/Dragonair/Mega Dragonite ex for the Dragonite plan.
- If more than one Palafin ex is stuck in hand, use Lillie's Determination after all useful Items, Basics, evolutions, Abilities, and Energy attachments are checked, so Palafin ex can return to the deck for Zero to Hero.
- Tatsugiri's Active Spot Ability should choose the best visible Supporter, usually Lillie's Determination for hand rebuild, Petrel for setup Trainer access, Hilda/Crispin for evolution/Energy, Kieran for switch/reset, or Boss only for prize route.

## Mapping Notes

- `Palafin SVALT 81` is local ID `106` by player confirmation.
- `Palafin ex PRE 151` uses the available same-name local ID `107`.
- `Mega Dragonite ex ASC 290` uses the available same-name local ID `904`.
- `Tatsugiri TWM 186` uses the available same-name local ID `122`.

## Next Logic Work

- Tune Palafin Ability sequencing from real cabt logs if the Zero to Hero prompt shape differs from current metadata assumptions.
- Tune Surfing Beach target selection from mirror visualizer logs.
- Add matchup-specific Boss/Kieran prize mapping.
- Run mirror games and sample-agent games, then tune from logs.
