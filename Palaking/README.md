# Palaking

Clean starting workspace for the Palafin ex / Mega Dragonite ex water-lightning deck.

## Current Deck

The active source list is in `palaking_deck_source.csv`. `build_deck_csv.py` resolves it against the local competition metadata and writes the final `deck.csv`.

Important local mapping notes:

- `Palafin SVALT 81` is forced to local card ID `106`, per player confirmation, because this is the Palafin with the Ability that supports the Palafin ex plan.
- `Palafin ex PRE 151` resolves to local same-name card ID `107`.
- `Mega Dragonite ex ASC 290` resolves to the available local Mega Dragonite ex card ID `904`.
- `Tatsugiri TWM 186` resolves to the available local Tatsugiri card ID `122`.

## Files

- `deck.csv`: generated 60-card Kaggle deck file.
- `submission Palaking 1.3.zip`: Palaking package with hard Palafin ex Energy cap.
- `submission Palaking 1.4.zip`: Palaking package with Tatsugiri retreat-Energy exception for ready Benched Palafin ex.
- `submission Palaking 1.5.zip`: Palaking package with stronger Poffin usage and Poké Pad Dratini routing.
- `submission Palaking 1.6.zip`: Palaking package with Supporter/Poffin/Pad pre-attack and pre-end checks.
- `submission Palaking 1.7.zip`: Palaking package with full evolution/item/Energy/Supporter checklist before non-KO attack or end turn.
- `submission Palaking 1.8.zip`: Palaking package with Petrel-to-Secret-Box package routing.
- `submission Palaking 1.9.zip`: Palaking package with Petrel-to-Poké Pad evolution routing, safer Energy-discard retreat logic, Lillie prechecks, and Water-only Palafin-line Energy.
- `submission Palaking 1.10.zip`: Palaking package with Dragonair Evolution-search Ability routing and stronger Tatsugiri Supporter-search usage.
- `submission Palaking 1.11.zip`: Palaking package with staged Lillie sequencing, alternate-Supporter handling for live evolution chains, and safer turn-window detection.
- `submission Palaking 1.12.zip`: Palaking package with generic effect-attachment target scoring, so attach-from-deck effects prefer underpowered targets instead of falling back to the first already-powered Pokémon.
- `submission Palaking 1.13.zip`: Palaking package with Tatsugiri Attract Customers treated as a setup Ability before Supporters, plus a hard block on extra Energy to already-powered Tatsugiri.
- `submission Palaking 1.14.zip`: Palaking package with explicit empty/nearly-empty Bench recovery: Poffin first, setup Abilities/exact setup Supporters next, then Lillie to reset dead hands.
- `submission Palaking 1.15.zip`: Palaking package with a hard Basic-from-hand bench guard before Ability, Supporter, attack, or end-turn choices.
- `submission Palaking 1.16.zip`: Palaking package with card-by-card analysis, relationship graph, generated policy rules, analysis-aware scoring notes, and exported strategy docs/data.
- `submission Palaking 1.17.zip`: Palaking package with stricter Palafin sequencing, Secret Box/Petrel/Poffin routing, Air Balloon/Switch waste guards, and aggressive Giga Impact planning.
- `submission Palaking 1.18.zip`: Palaking package with Palaking card-selection prompt routing applied directly in the live root policy, so Secret Box/Petrel/Poké Pad/discard prompts use deck logic before generic fallback.
- `submission Palaking 1.19.zip`: Palaking package with stricter Hilda targets, hard Lightning-to-Palafin-line blocks, Secret Box/Poffin discard safety, Petrel low-bench routing, hand-index Supporter resolution, and Tatsugiri reset-pivot support for Palafin ex after Giga Impact.
- `submission Palaking 1.20.zip`: Palaking package with stricter Dratini-before-Dragonair Poké Pad/Petrel routing, spare Water routing to Dragonite once Palafin ex attackers are exactly powered, stronger energized Dragonair Ability priority, and Lillie recovery for duplicate Palafin ex stuck in hand.
- `submission Palaking 1.21.zip`: Palaking package with Finizen opening-Active preference, strict switch/retreat gating to Zero to Hero or attack-locked Palafin ex reset lines, normal-Palafin recharge targeting over Tatsugiri pivots, and hard Mega Dragonite ex retreat-cost blocking.
- `submission Palaking 1.22.zip`: current Palaking package based on 1.21, restoring high Tatsugiri Air Balloon pivot value, Dragonite reset value only when Giga Impact is unavailable/locked, Finizen post-KO promotion when no attacker is ready, and stronger protection for lone/evolving board pieces.
- `palaking_deck_source.csv`: player-facing source decklist.
- `deck_mapping_report.md`: exact card-ID resolution report.
- `deck_profile.json`: Palaking-only starter strategy profile.
- `STRATEGY_NOTES.md`: Palaking planning notes.
- `docs/CARD_BY_CARD_ANALYSIS.md`: generated card-by-card role, timing, search, energy, discard, and mistake notes.
- `docs/SYNERGY_MAP.md`: generated map of setup/search/switch/energy/recovery relationships.
- `data/deck_synergy_graph.json`: machine-readable node/edge graph used by the analysis layer.
- `build_deck_csv.py`: Palaking-specific deck builder.

## Build Check

Run:

```bash
python3 build_deck_csv.py --deck-out deck.csv --report-out deck_mapping_report.md
python3 validate_deck.py
```
