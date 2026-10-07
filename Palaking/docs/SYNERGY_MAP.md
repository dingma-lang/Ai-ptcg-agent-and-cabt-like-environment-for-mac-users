# Palaking Synergy Map

## Main Combo Lines

### Combo 1: Palafin ex setup
Buddy-Buddy Poffin -> Finizen -> Poke Pad/Hilda -> Palafin -> Surfing Beach/Switch/Kieran/Air Balloon -> Zero to Hero -> Palafin ex -> Basic Water Energy -> attack.

### Combo 2: Palafin reset
Palafin ex attacks with Giga Impact, then Surfing Beach/Switch/Kieran/Mega Dragonite ex ability rotates or resets the attacker before the next attack.

### Combo 3: Dragonite setup
Dratini -> Dragonair -> attach Water/Lightning -> Hilda/Crispin -> Mega Dragonite ex -> use switch ability or attack for 330 when it matters.

### Combo 4: Secret Box setup
Secret Box discards 3 safe cards and finds an Item, Tool, Supporter, and Stadium package such as Poffin/Poke Pad/Switch + Air Balloon + Hilda/Lillie/Petrel/Crispin + Surfing Beach.

### Combo 5: Final prize math
Boss's Orders or Kieran plus Palafin ex 250/280 or Mega Dragonite ex 330/360 creates closing prize routes.

## Search Relationships

- Buddy-Buddy Poffin -> Finizen (searches, 100): Finizen is the required Basic for the Palafin ex engine.
- Buddy-Buddy Poffin -> Tatsugiri (searches, 75): Tatsugiri provides Supporter access and pivot value.
- Poke Pad -> Finizen (searches, 65): Poke Pad can find non-Rule Box Pokemon such as Finizen.
- Poke Pad -> Palafin (searches, 78): Poke Pad can find non-Rule Box Pokemon such as Palafin.
- Poke Pad -> Dragonair (searches, 65): Poke Pad can find non-Rule Box Pokemon such as Dragonair.
- Poke Pad -> Tatsugiri (searches, 65): Poke Pad can find non-Rule Box Pokemon such as Tatsugiri.
- Poke Pad -> Dratini (finds_evolution_piece, 72): Poke Pad is the route to Dratini because Dratini is not Poffin-eligible when HP is 80.
- Hilda -> Palafin (finds_evolution_piece, 88): Hilda can find Palafin when Finizen is ready.
- Hilda -> Dragonair (finds_evolution_piece, 82): Hilda can find Dragonair when Dratini is in play.
- Hilda -> Mega Dragonite ex (finds_evolution_piece, 88): Hilda can find Mega Dragonite ex when Dragonair is ready.
- Team Rocket's Petrel -> Buddy-Buddy Poffin (finds_exact_trainer, 82): Petrel can get exact Trainer Buddy-Buddy Poffin when that card solves the turn.
- Team Rocket's Petrel -> Poke Pad (finds_exact_trainer, 82): Petrel can get exact Trainer Poke Pad when that card solves the turn.
- Team Rocket's Petrel -> Surfing Beach (finds_exact_trainer, 82): Petrel can get exact Trainer Surfing Beach when that card solves the turn.
- Team Rocket's Petrel -> Switch (finds_exact_trainer, 82): Petrel can get exact Trainer Switch when that card solves the turn.
- Team Rocket's Petrel -> Secret Box (finds_exact_trainer, 82): Petrel can get exact Trainer Secret Box when that card solves the turn.
- Team Rocket's Petrel -> Air Balloon (finds_exact_trainer, 82): Petrel can get exact Trainer Air Balloon when that card solves the turn.
- Team Rocket's Petrel -> Energy Retrieval (finds_exact_trainer, 82): Petrel can get exact Trainer Energy Retrieval when that card solves the turn.
- Team Rocket's Petrel -> Night Stretcher (finds_exact_trainer, 82): Petrel can get exact Trainer Night Stretcher when that card solves the turn.
- Team Rocket's Petrel -> Sacred Ash (finds_exact_trainer, 82): Petrel can get exact Trainer Sacred Ash when that card solves the turn.
- Team Rocket's Petrel -> Boss's Orders (finds_exact_trainer, 82): Petrel can get exact Trainer Boss's Orders when that card solves the turn.
- Team Rocket's Petrel -> Kieran (finds_exact_trainer, 82): Petrel can get exact Trainer Kieran when that card solves the turn.
- Secret Box -> Buddy-Buddy Poffin (finds_exact_trainer, 76): Secret Box builds Item + Tool + Supporter + Stadium setup packages.
- Secret Box -> Poke Pad (finds_exact_trainer, 76): Secret Box builds Item + Tool + Supporter + Stadium setup packages.
- Secret Box -> Switch (finds_exact_trainer, 76): Secret Box builds Item + Tool + Supporter + Stadium setup packages.
- Secret Box -> Air Balloon (finds_tool, 76): Secret Box builds Item + Tool + Supporter + Stadium setup packages.
- Secret Box -> Hilda (finds_supporter, 76): Secret Box builds Item + Tool + Supporter + Stadium setup packages.
- Secret Box -> Lillie's Determination (finds_supporter, 76): Secret Box builds Item + Tool + Supporter + Stadium setup packages.
- Secret Box -> Team Rocket's Petrel (finds_supporter, 76): Secret Box builds Item + Tool + Supporter + Stadium setup packages.
- Secret Box -> Crispin (finds_supporter, 76): Secret Box builds Item + Tool + Supporter + Stadium setup packages.
- Secret Box -> Surfing Beach (finds_stadium, 76): Secret Box builds Item + Tool + Supporter + Stadium setup packages.

## Switch Relationships

- Palafin -> Palafin ex (enables_zero_to_hero, 100): Moving Palafin from Active to Bench puts Palafin ex into play.
- Surfing Beach -> Palafin (enables_zero_to_hero, 100): Surfing Beach moves Palafin from Active to Bench.
- Surfing Beach -> Palafin ex (resets_attack_restriction, 92): Surfing Beach helps reset or rotate after Giga Impact.
- Switch -> Palafin (enables_zero_to_hero, 88): Switch moves Palafin from Active to Bench.
- Switch -> Palafin ex (resets_attack_restriction, 92): Switch helps reset or rotate after Giga Impact.
- Kieran -> Palafin (enables_zero_to_hero, 88): Kieran moves Palafin from Active to Bench.
- Kieran -> Palafin ex (resets_attack_restriction, 92): Kieran helps reset or rotate after Giga Impact.
- Air Balloon -> Palafin (enables_zero_to_hero, 88): Air Balloon moves Palafin from Active to Bench.
- Air Balloon -> Palafin ex (resets_attack_restriction, 92): Air Balloon helps reset or rotate after Giga Impact.
- Mega Dragonite ex -> Palafin (enables_zero_to_hero, 88): Mega Dragonite ex moves Palafin from Active to Bench.
- Mega Dragonite ex -> Palafin ex (resets_attack_restriction, 92): Mega Dragonite ex helps reset or rotate after Giga Impact.

## Energy Relationships

- Buddy-Buddy Poffin -> Dratini (should_not_target, -100): Dratini has more than 70 HP in local competition metadata.
- Poke Pad -> Palafin ex (should_not_target, -100): Palafin ex has a Rule Box and should stay in deck for Zero to Hero.
- Poke Pad -> Mega Dragonite ex (should_not_target, -80): Mega Dragonite ex has a Rule Box; use Hilda/Dragonair style evolution search instead.
- Hilda -> Basic Water Energy (provides_energy, 84): Hilda can pair Palafin with Water Energy.
- Hilda -> Basic Lightning Energy (provides_energy, 86): Hilda can pair Dragonite line evolution with Lightning Energy.
- Team Rocket's Petrel -> Buddy-Buddy Poffin (should_not_target, -40): Do not Petrel for Poffin when Poffin is already in hand.
- Basic Water Energy -> Palafin ex (enables_attack, 100): Palafin ex attacks for one Water Energy.
- Basic Water Energy -> Mega Dragonite ex (enables_attack, 55): Mega Dragonite also needs Water for its attack.
- Basic Lightning Energy -> Mega Dragonite ex (enables_attack, 100): Mega Dragonite needs scarce Lightning Energy.
- Basic Lightning Energy -> Palafin ex (should_not_target, -100): Lightning Energy is protected for Mega Dragonite ex.
- Crispin -> Mega Dragonite ex (provides_energy, 90): Crispin fixes Water + Lightning for Mega Dragonite ex.
- Crispin -> Palafin ex (provides_energy, 40): Crispin can provide Water, but Palafin usually needs only one manual Water.

## Recovery Relationships

- Energy Retrieval -> Basic Water Energy (recovers_energy, 70): Energy Retrieval recovers Palafin attack fuel.
- Energy Retrieval -> Basic Lightning Energy (recovers_energy, 78): Energy Retrieval recovers scarce Dragonite Energy.
- Night Stretcher -> Palafin (recovers_pokemon, 70): Night Stretcher gets exact missing Pokemon or Basic Energy from discard.
- Night Stretcher -> Basic Lightning Energy (recovers_energy, 75): Night Stretcher can recover exact Lightning Energy.
- Sacred Ash -> Finizen (recovers_pokemon, 68): Sacred Ash restores lost Pokemon lines when several pieces are in discard.
- Sacred Ash -> Palafin (recovers_pokemon, 68): Sacred Ash restores lost Pokemon lines when several pieces are in discard.
- Sacred Ash -> Palafin ex (recovers_pokemon, 68): Sacred Ash restores lost Pokemon lines when several pieces are in discard.
- Sacred Ash -> Dratini (recovers_pokemon, 68): Sacred Ash restores lost Pokemon lines when several pieces are in discard.
- Sacred Ash -> Dragonair (recovers_pokemon, 68): Sacred Ash restores lost Pokemon lines when several pieces are in discard.
- Sacred Ash -> Mega Dragonite ex (recovers_pokemon, 68): Sacred Ash restores lost Pokemon lines when several pieces are in discard.

## Supporter Decision Map

- Team Rocket's Petrel: exact Trainer search when one card solves the turn.
- Hilda: Evolution plus Energy package; not for missing Basics.
- Crispin: mixed Energy, especially Mega Dragonite ex.
- Lillie's Determination: broad refresh only after exact setup actions are checked.
- Boss's Orders and Kieran: use only for KO, final prize, switch reset, or exact damage math.

## Common Wrong Plays

- Lillie before legal Poffin, Poke Pad, evolution, Basic bench, or setup Ability.
- Expecting Poffin to find Dratini when local Dratini has 80 HP.
- Searching Palafin ex with Poke Pad instead of keeping it for Zero to Hero.
- Attaching Lightning Energy to Palafin line or Tatsugiri.
- Using Dragonite attack casually and discarding Energy without prize-route gain.
- Attaching Air Balloon randomly instead of active Palafin Zero to Hero or locked Palafin ex reset.

## Correct Sequencing Examples

1. Bench Basic Pokemon from hand before Supporter, Ability, attack, or end.
2. Use Poffin before Lillie when Bench has space and Finizen/Tatsugiri remain.
3. Use Poke Pad for Palafin when Finizen is ready; use Poke Pad for Dratini when Dragonite line is absent.
4. Move active Palafin to Bench with Surfing Beach/Switch/Kieran/Air Balloon to trigger Zero to Hero.
5. Attach Water to Palafin ex once, then preserve switch/reset cards for real Giga Impact lock turns.
