# N's Zoroark Strategy Notes

This folder is the isolated workspace for the N's Zoroark ex Night Joker toolbox list.

## Current State

- `nzoroark_deck_source.csv` contains the 60-card list supplied by the player.
- `deck_profile.json` is N's Zoroark-specific and uses `strategy_id: ns_zoroark` so rules from other deck folders stay inactive.
- `build_deck_csv.py` maps the source list against local cabt metadata.
- `deck.csv` is generated for the replacement list with N's Reshiram, Ciphermaniac, Unfair Stamp, Air Balloon, Tool Scrapper, and Team Rocket's Watchtower.

## Deck Concept

- Establish multiple N's Zorua early with Buddy-Buddy Poffin.
- Evolve into N's Zoroark ex as the main engine and attacker.
- Keep useful N's Pokemon on the Bench so Zoroark ex can copy attacks with Night Joker.
- Use N's Zekrom as the key copied-attack source only. Never manually power or attack with Zekrom.
- Use N's Reshiram as a second copy source. Powerful Rage scales from damage counters on the attacking Zoroark; Virtuous Flame is a stable 170 copy.
- Use N's PP Up to convert discarded Darkness Energy into acceleration only for Benched N's Zorua or N's Zoroark ex.
- Use N's Castle to remove retreat cost from N's Pokemon and keep the attacker chain flexible.
- Use Binding Mochi when a poisoned Darkness attacker can convert the damage boost into a clean KO.
- Use Fezandipiti ex for comeback draw after our Pokemon is Knocked Out; treat it and Pecharunt ex as two-prize liabilities.
- Use Lillie's Determination to reset weak hands or shuffle excess pieces back into deck.
- Use Ciphermaniac's Codebreaking when Trade or another draw effect can convert stacked cards into hand.
- Use Unfair Stamp after our Pokemon was Knocked Out when disruption matters.

## First-Pass Sequencing

- Opening setup prefers N's Zorua Active if available, with extra Zorua and a copy source on Bench.
- If Bench has room and Buddy-Buddy Poffin is legal, use it early for Zorua. In this replacement list, Poffin usually cannot get the other Basics because they are over 70 HP.
- If N's Zoroark ex is in hand and Zorua can evolve, evolve before discard-cost Items.
- Protect the only Zoroark ex, only Zorua, only Zekrom/Reshiram copy source, N's PP Up, N's Castle, Unfair Stamp, and scarce Darkness Energy.
- If Darkness Energy is in discard and a Benched Zorua/Zoroark line needs Energy, use N's PP Up before ending turn.
- If the Supporter slot is unused and the hand is weak, prefer Lillie's Determination.
- Boss's Orders is held for KO math or an important prize-map target.
- Black Belt is held unless +40 against Pokemon ex changes KO math.
- Tool Scrapper is used only when a Tool target matters.
- Team Rocket's Watchtower is avoided while our Abilities still matter.
- Pecharunt ex should not be benched just because it is legal; bench it when the switch/poison line or damage math matters.

## Mapping Notes

- `Darkness Energy MEE 7` maps to local `Basic {D} Energy`, ID `7`.
- `Fezandipiti ex ASC 142` maps to local same-name `Fezandipiti ex SFA 38`, ID `140`.
- `Black Belt's Training JTG 143` maps to local same-name `Black Belt's Training PRE 96`, ID `1211`.
- `Binding Mochi PRE 95` maps to local same-name `Binding Mochi SFA 55`, ID `1162`.
- `Tool Scrapper ASC 212` maps to local same-name `Tool Scrapper WHT 85`, ID `1137`.
- `Air Balloon ASC 181` maps to local same-name `Air Balloon BLK 79`, ID `1174`.

## Implemented Logic

- Target board evaluation tracks Zorua, Zoroark ex, ready 2-Darkness Zoroark, N's Zekrom, N's Reshiram, Darmanitan line, Pecharunt, Mochi, Fezandipiti, and Munkidori.
- Night Joker scores N's Zekrom Rampaging Thunder, N's Reshiram Powerful Rage/Virtuous Flame, N's Darmanitan Back Draft, and Flamebody Cannon with the correct drawbacks.
- Damage math explicitly handles 250, 290 with Mochi or Black Belt, and 330 with both against Pokemon ex.
- Energy planner blocks third Darkness on one Zoroark, blocks all non-Zorua/Zoroark Energy targets, and uses N's PP Up only with Darkness in discard plus a real Benched Zorua/Zoroark target.
- Search planner uses Poffin for eligible Zorua basics only, Poké Pad for non-rulebox Pokemon/copy sources, Cyrano for Zoroark ex, and Ciphermaniac when stacked cards can be drawn.
- Pass guard blocks ending while useful N's setup, evolution, Energy, search, Trade, recovery, or Night Joker action remains.
