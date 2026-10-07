# NsZoroark

Separate workspace for the N's Zoroark ex / N's Zekrom toolbox deck.

This folder is intentionally isolated from `Palaking/` and `hydreigen/`. The profile is set to `strategy_id: ns_zoroark`, so old deck-specific combo rules do not affect this deck.

## Current Deck Status

The player-facing source list is in `nzoroark_deck_source.csv`.

`build_deck_csv.py` resolves the list against local cabt competition metadata. The current replacement list resolves successfully and `deck.csv` has 60 numeric card IDs.

Other mapping notes are recorded in `deck_mapping_report.md`:

- `Darkness Energy MEE 7` resolves to local `Basic {D} Energy`, ID `7`.
- `Tool Scrapper ASC 212` resolves to local same-name `Tool Scrapper WHT 85`, ID `1137`.
- `Air Balloon ASC 181` resolves to local same-name `Air Balloon BLK 79`, ID `1174`.
- `Fezandipiti ex ASC 142`, `Black Belt's Training JTG 143`, and `Binding Mochi PRE 95` use available same-name local competition IDs.

## Build Commands

```bash
python3 build_deck_csv.py --deck-out deck.csv --report-out deck_mapping_report.md
python3 validate_deck.py
python3 make_submission.py --out "submission NsZoroark 1.1.zip"
```

## Core Files

- `agent.py`: Kaggle entry wrapper.
- `main.py`: cabt/Kaggle import alias.
- `deck_profile.json`: N's Zoroark profile and strategy gate.
- `core/zoroark_planner.py`: top-level N's Zoroark action router.
- `core/night_joker_planner.py`: Night Joker copy-attack scoring.
- `core/energy_planner_zoroark.py`: exact Darkness Energy discipline and N's PP Up scoring.
- `core/search_planner_zoroark.py`: Poffin, Poké Pad, Cyrano, N's PP Up, Unfair Stamp, Tool Scrapper, Air Balloon, and Watchtower timing.
- `core/supporter_router_zoroark.py`: Boss, Black Belt, Cyrano, Ciphermaniac, and Lillie timing.
- `build_deck_csv.py`: deck source to numeric-ID resolver.
- `deck_mapping_report.md`: exact and fallback card-ID mapping report.
- `STRATEGY_NOTES.md`: deck concept and first-pass sequencing notes.
