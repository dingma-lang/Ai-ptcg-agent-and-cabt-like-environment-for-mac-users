from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path
from typing import Any

from card_db import get_db
from core.priority_tables import CARD_IDS, canonical_name_from_id


OUT = Path("local_results/score_review.html")


BASE_SCORES = {
    "Deino": 8600,
    "Gastly": 7400,
    "Toxel": 7600,
    "Buddy-Buddy Poffin": 9800,
    "Poke Pad": 7200,
    "Lillie's Determination": 9400,
    "Rare Candy": 6800,
    "Ultra Ball": 6400,
    "Hydreigon ex": 6200,
    "Mega Gengar ex": 6100,
    "Haunter": 5200,
    "Zweilous": 4800,
    "Crispin": 5000,
    "Dawn": 4700,
    "Secret Box": 4300,
    "Toxtricity": 4200,
    "Fezandipiti ex": 3600,
    "Air Balloon": 3200,
    "Basic Metal Energy": 3100,
    "Basic Psychic Energy": 3100,
    "Basic Darkness Energy": 2800,
    "Night Stretcher": 2600,
    "Sacred Ash": 2500,
    "Team Rocket's Petrel": 2400,
    "Pecharunt ex": 1700,
    "Boss's Orders": 1600,
    "Energy Recycler": 1400,
    "Battle Cage": 1300,
    "Meddling Memo": 1000,
    "Special Red Card": 1000,
}


CARD_RULES = {
    "Deino": {
        "role": "Core Basic. Target two Deino in play, but avoid over-focusing on Deino when active is already Deino and Toxel/Gastly are missing.",
        "use": "Bench early. Protect if you hold Rare Candy or Hydreigon ex. Attach Metal/Psychic/Darkness only on the Deino chain.",
        "missing": "Find with Buddy-Buddy Poffin, Poke Pad, Dawn, or Call for Family.",
    },
    "Gastly": {
        "role": "Mega Gengar ex line Basic and backup damage dealer path.",
        "use": "Bench early, especially if Haunter/Mega Gengar ex are in hand.",
        "missing": "Find with Poffin/Poke Pad/Dawn/Call for Family.",
    },
    "Toxel": {
        "role": "Setup bridge. Call for Family matters when bench is low; Toxtricity is an Energy engine, not an attacker.",
        "use": "Bench early when bench is low or basics are missing. Use Call for Family in the first turns if it fills core Basics/ex support.",
        "missing": "Find with Poffin/Poke Pad/Dawn/Call for Family.",
    },
    "Zweilous": {
        "role": "Stage 1 bridge to Hydreigon ex.",
        "use": "Evolve Deino when Rare Candy line is not ready. Never attack with Stage 1 Deino line; protect it.",
        "missing": "Find with Poke Pad/Dawn if Hydreigon ex is already in hand or Deino needs a normal evolution route.",
    },
    "Hydreigon ex": {
        "role": "Main attacker. Needs Darkness, Metal, Psychic, plus one extra Energy for Obsidian.",
        "use": "Evolve the Deino/Zweilous with the highest chance to attack, usually the one with more correct Energy.",
        "missing": "Find with Ultra Ball/Dawn/Secret Box package when Deino plus Rare Candy/Zweilous is ready.",
    },
    "Haunter": {
        "role": "Stage 1 bridge to Mega Gengar ex.",
        "use": "Evolve Gastly when Mega Gengar ex is in hand or opponent is ex-heavy.",
        "missing": "Find with Poke Pad/Dawn.",
    },
    "Mega Gengar ex": {
        "role": "Co-primary damage dealer, especially into ex attackers.",
        "use": "Build alongside Hydreigon, not after Hydreigon only. Attach Darkness when Gengar line is live.",
        "missing": "Find with Ultra Ball/Dawn when Gastly/Haunter is live.",
    },
    "Toxtricity": {
        "role": "Energy acceleration engine. Not the secondary attacker.",
        "use": "Use Sinister Surge to attach to Hydreigon ex or Mega Gengar ex; avoid attaching Energy to Toxtricity itself.",
        "missing": "Find after Toxel is in play if Energy acceleration is needed.",
    },
    "Fezandipiti ex": {
        "role": "Post-KO draw stabilizer.",
        "use": "Bench/find after your Pokemon was KO'd, then use Flip the Script. Do not bench early without reason.",
        "missing": "After KO, find with Dawn, Ultra Ball, Toxel Call for Family, or Secret Box package.",
    },
    "Pecharunt ex": {
        "role": "Support pivot/liability.",
        "use": "Bench only when the support effect matters. Do not attach Energy to it.",
        "missing": "Usually lower priority than Deino/Gastly/Toxel/Fezandipiti.",
    },
    "Buddy-Buddy Poffin": {
        "role": "Best early setup Item.",
        "use": "Use when bench is not full to get two Basics with 70 HP or less, prioritizing one Deino, one Gastly, one Toxel.",
        "missing": "Find with Petrel or Secret Box if bench is low and no Basics are in hand.",
    },
    "Poke Pad": {
        "role": "Setup search for missing pieces.",
        "use": "Use before Lillie when it can find missing Basic/Stage 1 pieces.",
        "missing": "Petrel/Secret Box can find it when direct Basic access is missing.",
    },
    "Ultra Ball": {
        "role": "Stage 2 and Fezandipiti access.",
        "use": "Use only when discard cost is safe. Do not discard Poffin when bench is empty.",
        "missing": "Petrel/Secret Box can find it when Stage 2 or Fezandipiti is urgent.",
    },
    "Rare Candy": {
        "role": "Hydreigon ex acceleration.",
        "use": "Use when Deino is in play and Hydreigon ex is in hand/searchable. Use before Lillie if live.",
        "missing": "Find with Petrel/Secret Box when Deino plus Hydreigon ex is lined up.",
    },
    "Lillie's Determination": {
        "role": "Preferred Supporter after useful hand actions are checked.",
        "use": "Use if legal after benching Basics, using Poffin/Poke Pad/live evolution/recovery/Fezandipiti access.",
        "missing": "Secret Box can find it if no Supporter is available and discard is safe.",
    },
    "Crispin": {
        "role": "Energy fixer for Hydreigon ex and live Mega Gengar lines.",
        "use": "Use when Hydreigon/Gengar is missing attack Energy. Do not over-attach beyond attack needs.",
        "missing": "Find with Secret Box when Hydreigon ex is evolved and missing Energy.",
    },
    "Dawn": {
        "role": "Pokemon search, especially post-KO Fezandipiti and full-chain assembly.",
        "use": "After KO, Dawn can beat Lillie if it finds Fezandipiti ex. Otherwise Lillie is usually preferred as Supporter.",
        "missing": "Secret Box can find it as the Supporter slot.",
    },
    "Team Rocket's Petrel": {
        "role": "Trainer search/disruption utility.",
        "use": "Use for exact Trainer only when Lillie is not the better Supporter or Poffin is not already in hand.",
        "missing": "Lillie usually beats it under current preference.",
    },
    "Secret Box": {
        "role": "Powerful package search with a severe discard cost.",
        "use": "Use only with three safe discards. Never discard Lillie/Poffin/live evolution pieces if avoidable.",
        "missing": "Petrel can find it when no Supporter exists and a multi-card package is needed.",
    },
    "Night Stretcher": {
        "role": "Exact recovery.",
        "use": "Use before Lillie if key Pokemon/Energy exact recovery is live, especially after KO.",
        "missing": "Petrel can find it when discard recovery is urgent.",
    },
    "Sacred Ash": {
        "role": "Pokemon engine recovery.",
        "use": "Use before Lillie when Deino/Gengar/Toxel engine pieces are in discard after KO.",
        "missing": "Petrel can find it for broad Pokemon recovery.",
    },
    "Energy Recycler": {
        "role": "Energy recovery.",
        "use": "Use only when enough Energy is in discard or deck-out/energy exhaustion matters.",
        "missing": "Petrel can find it when 4+ Energy are in discard.",
    },
    "Battle Cage": {
        "role": "Stadium protection.",
        "use": "Play if it protects bench setup or replaces opponent Stadium. Extra copies are discardable.",
        "missing": "Secret Box can take it as the Stadium slot.",
    },
    "Air Balloon": {
        "role": "Retreat/pivot tool.",
        "use": "Attach to a pivot or retreat target when it enables Hydreigon/Gengar attack. Extra copies are discardable.",
        "missing": "Secret Box can take it as Tool slot.",
    },
    "Boss's Orders": {
        "role": "Gust closer.",
        "use": "Use only for KO, prize route, or opponent block. Usually do not use during setup.",
        "missing": "Protected, but not a setup priority.",
    },
    "Meddling Memo": {
        "role": "Disruption / hand information card.",
        "use": "Use after setup is stable or when the opponent's next response is more important than building your board.",
        "missing": "Low setup priority.",
    },
    "Special Red Card": {
        "role": "Disruption.",
        "use": "Use after setup is stable or when opponent hand is clearly dangerous.",
        "missing": "Low setup priority.",
    },
    "Basic Darkness Energy": {
        "role": "Main flexible Energy.",
        "use": "Attach to Hydreigon/Gengar lines. Extra Darkness is usually the fourth Hydreigon Energy.",
        "missing": "Crispin/Toxtricity can find/attach it.",
    },
    "Basic Metal Energy": {
        "role": "Hydreigon required Energy.",
        "use": "Attach only to Deino/Zweilous/Hydreigon ex chain.",
        "missing": "Crispin can fetch it.",
    },
    "Basic Psychic Energy": {
        "role": "Hydreigon required Energy.",
        "use": "Attach only to Deino/Zweilous/Hydreigon ex chain.",
        "missing": "Crispin can fetch it.",
    },
}


PAIR_RULES = [
    ("Buddy-Buddy Poffin", "Deino", 4200, "Poffin can establish Deino. Also seek Gastly/Toxel if missing."),
    ("Buddy-Buddy Poffin", "Gastly", 3600, "Poffin can establish Gengar line."),
    ("Buddy-Buddy Poffin", "Toxel", 3800, "Poffin can establish Call for Family / Toxtricity engine."),
    ("Poke Pad", "Deino", 2800, "Pad can find extra setup/evolution pieces once Deino exists."),
    ("Poke Pad", "Gastly", 2400, "Pad can find Haunter/Gengar line pieces."),
    ("Poke Pad", "Toxel", 2400, "Pad can find Toxtricity or missing setup Basic."),
    ("Rare Candy", "Deino", 6500, "Live Rare Candy path. Missing Hydreigon ex if not already held."),
    ("Hydreigon ex", "Rare Candy", 7000, "Hydreigon can enter through Deino. Missing Deino if none in play."),
    ("Hydreigon ex", "Zweilous", 8200, "Direct Stage 1 evolution path."),
    ("Hydreigon ex", "Deino", 5200, "Hydreigon target is valuable if Rare Candy/Zweilous is available."),
    ("Zweilous", "Deino", 4800, "Use normal evolution when Rare Candy line is not ready."),
    ("Mega Gengar ex", "Haunter", 9000, "Direct Gengar evolution path."),
    ("Mega Gengar ex", "Gastly", 5400, "Gengar line is live; find/evolve Haunter."),
    ("Haunter", "Gastly", 5200, "Stage 1 bridge for Mega Gengar ex."),
    ("Toxtricity", "Toxel", 5200, "Evolve for Sinister Surge engine, not attack plan."),
    ("Crispin", "Hydreigon ex", 7600, "Fix missing Hydreigon attack Energy."),
    ("Crispin", "Mega Gengar ex", 4600, "Can help Gengar attack when line is live."),
    ("Basic Metal Energy", "Deino", 5000, "Metal should go to Deino chain."),
    ("Basic Metal Energy", "Zweilous", 5400, "Metal should go to higher Hydreigon stage."),
    ("Basic Metal Energy", "Hydreigon ex", 6200, "Required Hydreigon Energy."),
    ("Basic Psychic Energy", "Deino", 5000, "Psychic should go to Deino chain."),
    ("Basic Psychic Energy", "Zweilous", 5400, "Psychic should go to higher Hydreigon stage."),
    ("Basic Psychic Energy", "Hydreigon ex", 6200, "Required Hydreigon Energy."),
    ("Basic Darkness Energy", "Deino", 3600, "Darkness can start Hydreigon chain."),
    ("Basic Darkness Energy", "Hydreigon ex", 5800, "Required plus extra Hydreigon Energy."),
    ("Basic Darkness Energy", "Gastly", 3600, "Darkness can prepare Gengar line."),
    ("Basic Darkness Energy", "Mega Gengar ex", 5800, "Gengar attack Energy."),
    ("Ultra Ball", "Hydreigon ex", 6200, "Search target if Deino/Rare Candy path is ready."),
    ("Ultra Ball", "Mega Gengar ex", 7000, "Search target when Gastly/Haunter is ready or opponent is ex-heavy."),
    ("Ultra Ball", "Fezandipiti ex", 6200, "Post-KO Fezandipiti access."),
    ("Ultra Ball", "Buddy-Buddy Poffin", -5200, "Use Poffin before Ultra Ball when bench is low."),
    ("Secret Box", "Lillie's Determination", -11000, "Do not discard Lillie to Secret Box."),
    ("Secret Box", "Buddy-Buddy Poffin", -12000, "Do not discard Poffin while bench is low."),
    ("Secret Box", "Battle Cage", 600, "Battle Cage is often a safe discard unless Stadium is needed."),
    ("Secret Box", "Air Balloon", 650, "Extra Air Balloon is often a safe discard."),
    ("Lillie's Determination", "Buddy-Buddy Poffin", -2600, "Use Poffin before Lillie."),
    ("Lillie's Determination", "Poke Pad", -1800, "Use live Pad before Lillie."),
    ("Lillie's Determination", "Rare Candy", -2600, "Use live evolution before Lillie."),
    ("Lillie's Determination", "Night Stretcher", -2600, "Use urgent recovery before Lillie."),
    ("Lillie's Determination", "Sacred Ash", -2600, "Use urgent recovery before Lillie."),
    ("Dawn", "Fezandipiti ex", 8200, "After KO, Dawn can find Fezandipiti ex before Lillie."),
    ("Toxel", "Fezandipiti ex", 7300, "Call for Family can find Fezandipiti after KO."),
    ("Fezandipiti ex", "Lillie's Determination", 7000, "After KO, use Flip the Script before ordinary Supporter."),
    ("Night Stretcher", "Deino", 7600, "Recover exact Deino/Hydreigon line pieces when discarded."),
    ("Sacred Ash", "Hydreigon ex", 9000, "Recover lost Hydreigon line after KO."),
    ("Energy Recycler", "Basic Darkness Energy", 4000, "Use only if several Energy are in discard."),
    ("Boss's Orders", "Mega Gengar ex", 2600, "Use if gust creates Gengar prize route/KO."),
]


EXTRA_PAIR_RULES = [
    ("Poke Pad", "Hydreigon ex", 6800, "If Deino is in play and Hydreigon ex is in hand, Poke Pad can find Zweilous as the normal evolution path."),
    ("Poke Pad", "Mega Gengar ex", 6500, "If Gastly is in play and Mega Gengar ex is in hand, Poke Pad can find Haunter."),
    ("Poke Pad", "Zweilous", 6000, "Zweilous plus Deino/Hydreigon line makes Poke Pad a live chain-builder."),
    ("Poke Pad", "Haunter", 5800, "Haunter plus Gastly/Mega Gengar line makes Poke Pad a live chain-builder."),
    ("Poke Pad", "Toxtricity", 5200, "Poke Pad can find or complete the Toxel -> Toxtricity engine line."),
    ("Dawn", "Deino", 7600, "Dawn can search a Basic, Stage 1, and Stage 2; with Deino present it can assemble Zweilous + Hydreigon ex."),
    ("Dawn", "Hydreigon ex", 7200, "Hydreigon ex in hand/field makes Dawn useful for missing Deino/Zweilous chain pieces."),
    ("Dawn", "Gastly", 7000, "Dawn can assemble Gastly -> Haunter -> Mega Gengar ex pieces."),
    ("Dawn", "Mega Gengar ex", 7000, "Mega Gengar ex in hand/field makes Dawn useful for missing Gastly/Haunter."),
    ("Dawn", "Toxel", 6200, "Dawn can assemble Toxel -> Toxtricity while also taking other Pokemon pieces."),
    ("Dawn", "Toxtricity", 6200, "Toxtricity in hand/field makes Dawn useful for missing Toxel or broader setup Pokemon."),
    ("Ultra Ball", "Deino", 7200, "With Deino in play, Ultra Ball can find Hydreigon ex or Zweilous, but only if discard cost is safe."),
    ("Ultra Ball", "Rare Candy", 7800, "Rare Candy plus Ultra Ball can become Hydreigon ex if Deino is in play."),
    ("Ultra Ball", "Zweilous", 7200, "Zweilous in play makes Ultra Ball a direct Hydreigon ex finder."),
    ("Ultra Ball", "Gastly", 6500, "With Gastly in play, Ultra Ball can find Mega Gengar ex or Haunter."),
    ("Ultra Ball", "Haunter", 8200, "Haunter in play makes Ultra Ball a direct Mega Gengar ex finder."),
    ("Ultra Ball", "Toxel", 5200, "Ultra Ball can find Toxtricity if the Energy engine is needed."),
    ("Team Rocket's Petrel", "Deino", 6800, "With Deino/Hydreigon path present, Petrel can find Rare Candy, Poke Pad, Ultra Ball, or Secret Box."),
    ("Team Rocket's Petrel", "Hydreigon ex", 6800, "With Hydreigon ex present, Petrel can find Rare Candy or a Pokemon-search Item to complete evolution."),
    ("Team Rocket's Petrel", "Gastly", 5800, "With Gastly/Gengar path present, Petrel can find Poke Pad or Ultra Ball."),
    ("Team Rocket's Petrel", "Mega Gengar ex", 5800, "With Mega Gengar ex present, Petrel can find Poke Pad or Ultra Ball to complete the line."),
    ("Team Rocket's Petrel", "Secret Box", 4200, "Petrel can find Secret Box only when a multi-card package is worth the discard cost."),
    ("Team Rocket's Petrel", "Energy Recycler", 5200, "Petrel can find Energy Recycler once enough Energy is in discard."),
    ("Team Rocket's Petrel", "Sacred Ash", 5200, "Petrel can find Sacred Ash when Pokemon engine recovery is urgent."),
    ("Team Rocket's Petrel", "Night Stretcher", 5200, "Petrel can find Night Stretcher when exact recovery is urgent."),
    ("Secret Box", "Deino", 7600, "With Deino/Hydreigon path present, Secret Box can get Rare Candy or Ultra Ball plus Lillie/Crispin/Tool/Stadium."),
    ("Secret Box", "Hydreigon ex", 7600, "With Hydreigon ex present, Secret Box can get Rare Candy or Ultra Ball if discard cost is safe."),
    ("Secret Box", "Rare Candy", 7000, "Rare Candy present lets Secret Box take Ultra Ball or Supporter pieces for Hydreigon line."),
    ("Secret Box", "Mega Gengar ex", 6200, "With Gengar path present, Secret Box can get Ultra Ball/Poke Pad package if discard is safe."),
    ("Secret Box", "Energy Recycler", 8600, "Energy Recycler makes Secret Box plus three Energy discards safer because Recycler can shuffle Energy back."),
    ("Secret Box", "Basic Darkness Energy", 1800, "Energy can be a Secret Box discard only when enough Energy/Recycler/recovery is available."),
    ("Secret Box", "Basic Metal Energy", -2200, "Metal is protected for Hydreigon; discard only with strong payoff and recovery."),
    ("Secret Box", "Basic Psychic Energy", -2200, "Psychic is protected for Hydreigon; discard only with strong payoff and recovery."),
    ("Energy Recycler", "Secret Box", 8600, "If Secret Box discards multiple Energy, Recycler can restore them to deck afterward."),
    ("Energy Recycler", "Basic Metal Energy", 4600, "Recycler becomes live after protected Hydreigon Energy is discarded."),
    ("Energy Recycler", "Basic Psychic Energy", 4600, "Recycler becomes live after protected Hydreigon Energy is discarded."),
    ("Energy Recycler", "Basic Darkness Energy", 4200, "Recycler becomes live after several Darkness Energy are discarded."),
    ("Lillie's Determination", "Deino", 5400, "If no Poffin/Pad/Dawn/Ultra Ball/Petrel/Secret Box path exists, Lillie is the fallback refresh after usage check."),
    ("Lillie's Determination", "Hydreigon ex", 5200, "If Hydreigon ex is stranded without Rare Candy/Zweilous/search path, Lillie can refresh after checking usable cards."),
    ("Lillie's Determination", "Gastly", 5000, "If Gengar path lacks Haunter/search, Lillie can refresh after checking usable cards."),
    ("Lillie's Determination", "Mega Gengar ex", 5000, "If Mega Gengar ex is stranded without Gastly/Haunter/search path, Lillie can refresh after checking usable cards."),
    ("Lillie's Determination", "Ultra Ball", -2600, "Use safe Ultra Ball before Lillie when it completes an evolution/search path."),
    ("Lillie's Determination", "Dawn", -1800, "Use Dawn before Lillie only when it gets urgent Pokemon pieces, especially post-KO Fezandipiti."),
    ("Lillie's Determination", "Secret Box", -2200, "Use safe Secret Box before Lillie only when it creates a strong package; otherwise Lillie wins."),
    ("Lillie's Determination", "Fezandipiti ex", -2600, "After KO, use Flip the Script / Fezandipiti access before ordinary Lillie."),
    ("Crispin", "Basic Metal Energy", 3600, "Crispin can fetch/attach one needed Energy and put the other into hand."),
    ("Crispin", "Basic Psychic Energy", 3600, "Crispin can fetch/attach one needed Energy and put the other into hand."),
    ("Crispin", "Basic Darkness Energy", 3400, "Crispin can provide Darkness while fixing Hydreigon/Gengar attack costs."),
    ("Toxtricity", "Hydreigon ex", 7600, "Sinister Surge should attach Darkness to Hydreigon ex if it helps attack; avoid Toxtricity as attacker."),
    ("Toxtricity", "Mega Gengar ex", 7000, "Sinister Surge should attach Darkness to Mega Gengar ex if it helps attack."),
    ("Toxtricity", "Basic Darkness Energy", 5200, "Toxtricity searches/attaches Darkness Energy from deck."),
    ("Toxtricity", "Pecharunt ex", -2800, "Do not use Toxtricity Energy acceleration on Pecharunt ex."),
    ("Toxtricity", "Fezandipiti ex", -2600, "Do not use Toxtricity Energy acceleration on Fezandipiti ex."),
    ("Air Balloon", "Deino", 2600, "Air Balloon can let a disposable Active pivot into the built attacker later."),
    ("Air Balloon", "Gastly", 3600, "Air Balloon on Gastly/Haunter can enable pivot into Hydreigon or Mega Gengar."),
    ("Air Balloon", "Toxel", 3400, "Air Balloon can help Toxel use Call for Family then retreat/pivot."),
    ("Air Balloon", "Mega Gengar ex", 4200, "Air Balloon can make the Gengar line easier to move Active."),
    ("Pecharunt ex", "Hydreigon ex", 2400, "Pecharunt can pivot Darkness Pokemon, but use only when it improves attack/survival."),
    ("Pecharunt ex", "Mega Gengar ex", 2400, "Pecharunt can pivot Darkness Pokemon, but use only when it improves attack/survival."),
    ("Basic Metal Energy", "Pecharunt ex", -9000, "Never attach Metal Energy to Pecharunt ex."),
    ("Basic Psychic Energy", "Pecharunt ex", -9000, "Never attach Psychic Energy to Pecharunt ex."),
    ("Basic Darkness Energy", "Pecharunt ex", -2600, "Avoid attaching Darkness to Pecharunt ex unless a rare pivot line demands it."),
    ("Basic Metal Energy", "Fezandipiti ex", -9000, "Never attach Metal Energy to Fezandipiti ex."),
    ("Basic Psychic Energy", "Fezandipiti ex", -9000, "Never attach Psychic Energy to Fezandipiti ex."),
    ("Basic Darkness Energy", "Fezandipiti ex", -2600, "Avoid attaching Darkness to Fezandipiti ex; it is a support liability."),
    ("Boss's Orders", "Hydreigon ex", 2800, "Boss can matter when Hydreigon creates a clean KO or prize route."),
    ("Meddling Memo", "Hydreigon ex", 1600, "Disruption is better once the attacking board is already built."),
    ("Meddling Memo", "Mega Gengar ex", 1600, "Disruption is better once the attacking board is already built."),
    ("Battle Cage", "Hydreigon ex", 1800, "Battle Cage can protect bench setup from damage-counter effects while attackers develop."),
    ("Battle Cage", "Mega Gengar ex", 1600, "Battle Cage can protect bench setup from damage-counter effects while attackers develop."),
]


MULTI_CARD_COMBOS = [
    {
        "name": "Hydreigon hand + Deino field, no bridge",
        "cards": ["Deino", "Hydreigon ex"],
        "missing": ["Rare Candy", "Zweilous"],
        "use_if_present": ["Poke Pad", "Dawn", "Ultra Ball", "Team Rocket's Petrel", "Secret Box", "Lillie's Determination"],
        "rule": "If Deino is in play and Hydreigon ex is in hand, first use any live path to get Rare Candy or Zweilous. Poke Pad/Dawn/Ultra Ball can get Zweilous; Petrel/Secret Box can get Rare Candy/Poke Pad/Ultra Ball. If none exists, use Lillie after the permanent usage check.",
        "score": 9800,
    },
    {
        "name": "Rare Candy + Deino, missing Hydreigon ex",
        "cards": ["Deino", "Rare Candy"],
        "missing": ["Hydreigon ex"],
        "use_if_present": ["Ultra Ball", "Dawn", "Secret Box", "Team Rocket's Petrel", "Lillie's Determination"],
        "rule": "Rare Candy is live only if Hydreigon ex is found. Ultra Ball/Dawn find Hydreigon ex; Secret Box/Petrel can find the search Item; Lillie is fallback after checking live actions.",
        "score": 9200,
    },
    {
        "name": "Mega Gengar hand + Gastly field, no Haunter",
        "cards": ["Gastly", "Mega Gengar ex"],
        "missing": ["Haunter"],
        "use_if_present": ["Poke Pad", "Dawn", "Ultra Ball", "Team Rocket's Petrel", "Secret Box", "Lillie's Determination"],
        "rule": "Find Haunter first, then Mega Gengar ex becomes live. Poke Pad/Dawn/Ultra Ball are direct paths; Petrel/Secret Box can get those Items.",
        "score": 9000,
    },
    {
        "name": "Secret Box + Energy Recycler + expendable Energy",
        "cards": ["Secret Box", "Energy Recycler", "Basic Darkness Energy"],
        "missing": [],
        "use_if_present": ["Basic Darkness Energy", "Basic Metal Energy", "Basic Psychic Energy"],
        "rule": "Secret Box can be safer if it discards multiple Energy and Energy Recycler is available to restore them. Still protect Metal/Psychic unless the package is important.",
        "score": 8600,
    },
    {
        "name": "Post-KO Fezandipiti access",
        "cards": ["Fezandipiti ex"],
        "missing": [],
        "use_if_present": ["Dawn", "Ultra Ball", "Toxel", "Secret Box", "Lillie's Determination"],
        "rule": "After your Pokemon was KO'd, Fezandipiti access/Flip the Script happens before ordinary Lillie.",
        "score": 8400,
    },
    {
        "name": "Toxtricity engine supports attackers",
        "cards": ["Toxtricity", "Basic Darkness Energy"],
        "missing": ["Hydreigon ex", "Mega Gengar ex"],
        "use_if_present": ["Hydreigon ex", "Mega Gengar ex"],
        "rule": "Use Sinister Surge to attach Darkness to Hydreigon ex or Mega Gengar ex. Avoid attaching to Toxtricity, Fezandipiti ex, or Pecharunt ex.",
        "score": 7600,
    },
    {
        "name": "Lillie permanent usage check",
        "cards": ["Lillie's Determination"],
        "missing": [],
        "use_if_present": ["Buddy-Buddy Poffin", "Poke Pad", "Rare Candy", "Ultra Ball", "Secret Box", "Dawn", "Night Stretcher", "Sacred Ash", "Fezandipiti ex"],
        "rule": "Before Lillie, always check if any useful hand/field action should be used first. If no useful action exists, Lillie is the preferred Supporter refresh.",
        "score": 9400,
    },
]


def load_deck_ids() -> list[int]:
    text = Path("deck.csv").read_text()
    return [int(part.strip()) for part in text.replace("\n", ",").split(",") if part.strip()]


def card_name(cid: int) -> str:
    return canonical_name_from_id(cid) or f"Card {cid}"


def build_cards(deck_ids: list[int]) -> list[dict[str, Any]]:
    counts = Counter(deck_ids)
    cards = []
    for cid, count in sorted(counts.items(), key=lambda item: (-item[1], card_name(item[0]))):
        db_card = get_db().get_card(cid)
        name = card_name(cid)
        rules = CARD_RULES.get(name, {})
        cards.append(
            {
                "id": cid,
                "name": name,
                "count": count,
                "type": db_card.card_type if db_card else "",
                "hp": db_card.hp if db_card else 0,
                "basic": bool(db_card.basic) if db_card else False,
                "stage1": bool(db_card.stage1) if db_card else False,
                "stage2": bool(db_card.stage2) if db_card else False,
                "ex": bool(db_card.ex or db_card.mega_ex) if db_card else False,
                "baseScore": BASE_SCORES.get(name, 0),
                "role": rules.get("role", ""),
                "use": rules.get("use", ""),
                "missing": rules.get("missing", ""),
            }
        )
    return cards


def build_matrix(cards: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    names = [card["name"] for card in cards]
    base_by_name = {card["name"]: int(card.get("baseScore") or 0) for card in cards}
    pair_lookup: dict[tuple[str, str], tuple[int, str]] = {}
    for row, col, score, note in PAIR_RULES + EXTRA_PAIR_RULES:
        old = pair_lookup.get((row, col))
        if old is None or abs(score) > abs(old[0]):
            pair_lookup[(row, col)] = (score, note)
    matrix = []
    for row_name in names:
        row = []
        for col_name in names:
            if row_name == col_name:
                row.append({"score": base_by_name.get(row_name, 0), "modifier": 0, "note": "Base presence score for this card."})
                continue
            modifier, note = pair_lookup.get((row_name, col_name), (0, ""))
            total = base_by_name.get(row_name, 0) + modifier if modifier else 0
            row.append({"score": total, "modifier": modifier, "note": note})
        matrix.append(row)
    return matrix


def build_strategy_notes() -> list[str]:
    return [
        "Opening board goal: get one Deino, one Gastly, and one Toxel first; then build toward Hydreigon ex plus Mega Gengar ex together.",
        "The matrix means co-presence: row card plus column card are in hand or on our field. Diagonal cells are base presence score; off-diagonal cells show row-card total score after the connection modifier.",
        "Buddy-Buddy Poffin is the highest early Item when bench has room. It should happen before Ultra Ball or Lillie when it fills missing Basics.",
        "Lillie's Determination is now the preferred Supporter, but only after useful hand actions are checked: bench Basics, Poffin, Poke Pad, live evolution, urgent recovery, Fezandipiti access, and strong Energy attach.",
        "Secret Box and Ultra Ball are discard-cost cards. They should not be played if their discard cost spends Poffin, Lillie, live evolution pieces, protected Energy, or unique key attackers.",
        "Metal and Psychic Energy should only attach to the Deino/Zweilous/Hydreigon ex line. Darkness attaches to Hydreigon or Mega Gengar lines, with extra Darkness usually being Hydreigon's fourth Energy.",
        "Toxtricity is an Energy engine, not a damage dealer. Its Energy acceleration should avoid attaching to itself.",
        "After your Pokemon is KO'd, Fezandipiti ex access can beat ordinary Lillie: use Dawn, Ultra Ball, Toxel Call for Family, or Fezandipiti's own ability when available.",
        "Recovery cards are normally held, but Sacred Ash/Night Stretcher/Energy Recycler can beat Lillie when key engine pieces or Energy are already in discard.",
    ]


def render_html(data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"""<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>PTCG Agent Score Review</title>
<style>
:root {{
  --bg: #f7f8fb;
  --panel: #ffffff;
  --ink: #1d2530;
  --muted: #657286;
  --line: #d9e0ea;
  --green: #167a4a;
  --red: #b42318;
  --blue: #2357c5;
  --gold: #8a5a00;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--bg);
  color: var(--ink);
}}
header {{
  padding: 18px 22px 12px;
  border-bottom: 1px solid var(--line);
  background: #fff;
  position: sticky;
  top: 0;
  z-index: 5;
}}
h1 {{ margin: 0; font-size: 22px; line-height: 1.2; }}
.sub {{ margin-top: 4px; color: var(--muted); font-size: 13px; }}
main {{ padding: 18px 22px 36px; max-width: 1600px; margin: 0 auto; }}
.toolbar {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0 18px; }}
button {{
  border: 1px solid #b9c4d4;
  background: #fff;
  color: var(--ink);
  border-radius: 6px;
  padding: 8px 11px;
  cursor: pointer;
  font-weight: 650;
}}
button.primary {{ background: #214ed3; border-color: #214ed3; color: #fff; }}
button.active {{ outline: 2px solid #214ed3; }}
.grid {{ display: grid; grid-template-columns: minmax(360px, 1.1fr) minmax(360px, .9fr); gap: 14px; align-items: start; }}
.panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }}
.panel h2 {{ margin: 0 0 10px; font-size: 16px; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(158px, 1fr)); gap: 9px; }}
.card {{
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px;
  min-height: 128px;
  background: #fff;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 6px;
}}
.card:hover {{ border-color: #8da3c8; }}
.card .name {{ font-weight: 750; font-size: 14px; }}
.card .meta {{ color: var(--muted); font-size: 12px; }}
.card .rating {{ margin-top: auto; font-size: 12px; color: var(--blue); font-weight: 700; }}
.card .score {{ display: none; font-size: 12px; }}
.card-actions {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 4px; }}
.mini-btn {{ padding: 4px 6px; border-radius: 5px; font-size: 11px; font-weight: 700; }}
.revealed .card .score {{ display: block; }}
.bench-row {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 8px; margin-top: 10px; }}
.pill {{ display: inline-flex; align-items: center; border: 1px solid var(--line); border-radius: 999px; padding: 2px 7px; font-size: 12px; margin: 2px 4px 2px 0; background: #fbfcff; }}
.active-slot {{ border-left: 4px solid var(--blue); }}
.bench-slot {{ border-left: 4px solid var(--green); min-height: 88px; }}
.prizes {{ display: grid; grid-template-columns: repeat(6, minmax(50px, 1fr)); gap: 8px; }}
.prize {{ border: 1px dashed #9aa8ba; border-radius: 6px; padding: 10px 6px; text-align: center; color: var(--muted); min-height: 54px; background: #fbfcff; font-size: 12px; }}
.prize.reveal {{ color: var(--ink); border-style: solid; }}
.summary-list {{ margin: 0; padding-left: 18px; color: #334155; font-size: 13px; }}
.summary-list li {{ margin: 6px 0; }}
.hidden {{ display: none; }}
.table-wrap {{ overflow: auto; max-height: 720px; border: 1px solid var(--line); border-radius: 8px; background: #fff; }}
table {{ border-collapse: collapse; width: max-content; min-width: 100%; }}
th, td {{ border: 1px solid #e5eaf1; padding: 6px 8px; font-size: 12px; vertical-align: top; }}
th {{ background: #f1f5fb; position: sticky; top: 0; z-index: 2; }}
th:first-child {{ left: 0; z-index: 3; }}
td:first-child {{ position: sticky; left: 0; background: #fff; font-weight: 700; }}
.cell-score.pos {{ color: var(--green); font-weight: 800; }}
.cell-score.neg {{ color: var(--red); font-weight: 800; }}
.cell-note {{ color: var(--muted); max-width: 180px; white-space: normal; }}
.delta.good {{ color: var(--green); }}
.delta.bad {{ color: var(--red); }}
.deck-list {{ columns: 2; font-size: 13px; }}
.rule-card {{ border-top: 1px solid var(--line); padding: 10px 0; }}
.rule-card:first-child {{ border-top: 0; padding-top: 0; }}
.rule-card b {{ display: block; margin-bottom: 3px; }}
.connection-list {{ display: grid; gap: 8px; }}
.connection-item {{ border: 1px solid var(--line); border-radius: 7px; padding: 8px; background: #fbfcff; font-size: 13px; }}
.connection-item b {{ display: block; margin-bottom: 2px; }}
@media (max-width: 980px) {{ .grid {{ grid-template-columns: 1fr; }} header {{ position: static; }} }}
</style>
</head>
<body>
<header>
  <h1>PTCG Agent Score Review</h1>
  <div class=\"sub\">Review opening-hand priorities against the current Hydreigon ex / Mega Gengar ex heuristic logic. Agent scores stay hidden until you reveal them.</div>
</header>
<main>
  <div class=\"toolbar\">
    <button class=\"primary\" id=\"dealBtn\">Random 7 + 6 Prizes</button>
    <button id=\"revealBtn\">Reveal Agent Scores</button>
    <button id=\"prizeBtn\">Reveal Prizes</button>
    <button id=\"chartBtn\">Score Chart</button>
    <button id=\"comboBtn\">Combo Rules</button>
    <button id=\"logicBtn\">Logic Notes</button>
  </div>
  <section class=\"grid\">
    <div class=\"panel\" id=\"scenarioPanel\">
      <h2>Opening Scenario</h2>
      <div id=\"scenarioMeta\"></div>
      <div id=\"activeArea\"></div>
      <h2 style=\"margin-top:14px\">Hand: click each card to set your importance</h2>
      <div class=\"cards\" id=\"handCards\"></div>
    </div>
    <div class=\"panel\">
      <h2>Comparison</h2>
      <div id=\"comparison\"></div>
      <h2 style=\"margin-top:14px\">Detected Present-Card Connections</h2>
      <div id=\"currentConnections\" class=\"connection-list\"></div>
      <h2 style=\"margin-top:14px\">Prize Cards</h2>
      <div class=\"prizes\" id=\"prizes\"></div>
      <h2 style=\"margin-top:14px\">Deck Counts</h2>
      <div class=\"deck-list\" id=\"deckList\"></div>
    </div>
  </section>
  <section class=\"panel hidden\" id=\"chartPanel\" style=\"margin-top:14px\">
    <h2>Presence Score Matrix</h2>
    <div class=\"sub\">Rows are cards being valued. Columns are cards co-present in hand, Active, or Bench. Diagonal cells are base presence score. Off-diagonal cells show the row card's total score after the connection modifier.</div>
    <div class=\"table-wrap\" id=\"matrixWrap\"></div>
  </section>
  <section class=\"panel hidden\" id=\"comboPanel\" style=\"margin-top:14px\">
    <h2>Multi-Card Connection Rules</h2>
    <div class=\"connection-list\" id=\"comboRules\"></div>
  </section>
  <section class=\"panel hidden\" id=\"logicPanel\" style=\"margin-top:14px\">
    <h2>Current Logic Notes</h2>
    <ul class=\"summary-list\" id=\"strategyNotes\"></ul>
    <div id=\"cardRules\"></div>
  </section>
</main>
<script>
const DATA = {payload};
let scenario = null;
let ratings = {{}};
let revealed = false;
let prizesRevealed = false;

function shuffle(arr) {{
  const out = arr.slice();
  for (let i = out.length - 1; i > 0; i--) {{
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }}
  return out;
}}

function cardById(id) {{ return DATA.cardsById[String(id)] || {{ id, name: `Card ${{id}}`, type: "" }}; }}
function countByName(ids) {{
  const c = {{}};
  ids.forEach(id => {{ const n = cardById(id).name; c[n] = (c[n] || 0) + 1; }});
  return c;
}}
function isBasic(id) {{
  const c = cardById(id);
  return c.basic || ["Deino","Gastly","Toxel","Fezandipiti ex","Pecharunt ex"].includes(c.name);
}}
function chooseActive(hand) {{
  const order = ["Deino", "Gastly", "Toxel", "Fezandipiti ex", "Pecharunt ex"];
  for (const name of order) {{
    const idx = hand.findIndex(id => cardById(id).name === name);
    if (idx >= 0) return idx;
  }}
  return hand.findIndex(isBasic);
}}
function deal() {{
  let deck, hand, activeIdx;
  for (let tries = 0; tries < 200; tries++) {{
    deck = shuffle(DATA.deck);
    hand = deck.slice(0, 7);
    activeIdx = chooseActive(hand);
    if (activeIdx >= 0) break;
  }}
  const active = hand.splice(activeIdx, 1)[0];
  scenario = {{
    deck,
    originalHand: deck.slice(0, 7),
    hand,
    active,
    prizes: deck.slice(7, 13),
    remainingDeck: deck.slice(13),
    bench: [],
  }};
  ratings = {{}};
  revealed = false;
  prizesRevealed = false;
  document.body.classList.remove("revealed");
  renderScenario();
}}

function missingCore(handNames) {{
  const inPlay = [cardById(scenario.active).name].concat(scenario.bench.map(id => cardById(id).name));
  return {{
    deino: inPlay.filter(n => n === "Deino").length < 2,
    gastly: !inPlay.some(n => ["Gastly","Haunter","Mega Gengar ex"].includes(n)),
    toxel: !inPlay.some(n => ["Toxel","Toxtricity"].includes(n)),
    handNames,
    inPlay,
  }};
}}
function presentIds() {{
  if (!scenario) return [];
  return [scenario.active].concat(scenario.bench).concat(scenario.hand);
}}
function presentNames() {{
  return presentIds().map(id => cardById(id).name);
}}
function fieldNames() {{
  if (!scenario) return [];
  return [cardById(scenario.active).name].concat(scenario.bench.map(id => cardById(id).name));
}}
function benchCard(handIndex) {{
  if (!scenario || scenario.bench.length >= 5) return;
  const id = scenario.hand[handIndex];
  if (!isBasic(id)) return;
  scenario.bench.push(id);
  scenario.hand.splice(handIndex, 1);
  ratings = {{}};
  renderScenario();
}}
function safeDiscardCount(handIds, sourceName) {{
  let safe = 0;
  handIds.forEach(id => {{
    const n = cardById(id).name;
    if (n === sourceName) return;
    if (["Battle Cage","Air Balloon","Team Rocket's Petrel","Dawn","Basic Darkness Energy"].includes(n)) safe += 1;
    if (handIds.filter(x => x === id).length >= 2) safe += 1;
  }});
  return safe;
}}
function preLillieAction(handNames, handIds) {{
  const miss = missingCore(handNames);
  if (handNames.includes("Buddy-Buddy Poffin") && (miss.deino || miss.gastly || miss.toxel)) return "Buddy-Buddy Poffin";
  if (handNames.includes("Poke Pad") && (miss.deino || miss.gastly || miss.toxel || hydreigonBridgeNeeded())) return "Poke Pad";
  if (handNames.includes("Rare Candy") && handNames.includes("Hydreigon ex") && miss.inPlay.includes("Deino")) return "Rare Candy";
  if (handNames.includes("Ultra Ball") && safeDiscardCount(handIds, "Ultra Ball") >= 2 && (handNames.includes("Rare Candy") || miss.inPlay.includes("Gastly") || hydreigonBridgeNeeded())) return "Ultra Ball";
  if (handNames.includes("Secret Box") && safeDiscardCount(handIds, "Secret Box") >= 3 && hydreigonBridgeNeeded()) return "Secret Box";
  return "";
}}
function hydreigonBridgeNeeded() {{
  const p = presentNames();
  const f = fieldNames();
  return f.includes("Deino") && p.includes("Hydreigon ex") && !p.includes("Rare Candy") && !p.includes("Zweilous");
}}
function gengarBridgeNeeded() {{
  const p = presentNames();
  const f = fieldNames();
  return f.includes("Gastly") && p.includes("Mega Gengar ex") && !p.includes("Haunter");
}}
function secretBoxEnergyRecyclerCombo() {{
  const names = presentNames();
  const handEnergy = scenario.hand.filter(id => ["Basic Darkness Energy","Basic Metal Energy","Basic Psychic Energy"].includes(cardById(id).name)).length;
  return names.includes("Secret Box") && names.includes("Energy Recycler") && handEnergy >= 3;
}}
function agentScoreFor(id, handIds) {{
  const card = cardById(id);
  const name = card.name;
  const handNames = handIds.map(x => cardById(x).name);
  const pNames = presentNames();
  const fNames = fieldNames();
  const counts = countByName(presentIds());
  const miss = missingCore(handNames);
  let score = card.baseScore || 0;
  const notes = [];

  if (["Deino","Gastly","Toxel"].includes(name)) {{
    if (name === "Deino" && (counts["Deino"] || 0) >= 2) {{ score -= 3600; notes.push("extra Deino lower after one active/one copy"); }}
    else {{ score += 4200; notes.push("bench setup Basic now"); }}
  }}
  if (name === "Buddy-Buddy Poffin") {{
    if (miss.deino || miss.gastly || miss.toxel) {{ score += 7200; notes.push("fills missing core Basics"); }}
    else score -= 1200;
  }}
  if (name === "Poke Pad") {{
    if (miss.deino || miss.gastly || miss.toxel || hydreigonBridgeNeeded() || gengarBridgeNeeded()) {{ score += 5200; notes.push("find missing Basic/Stage 1/evolution bridge before Lillie"); }}
  }}
  if (name === "Lillie's Determination") {{
    const wait = preLillieAction(handNames, handIds);
    if (wait) {{ score -= 2600; notes.push(`wait: use ${{wait}} first`); }}
    else {{ score += 7600; notes.push("preferred Supporter after hand-action check"); }}
  }}
  if (name === "Rare Candy") {{
    if (pNames.includes("Hydreigon ex") && fNames.includes("Deino")) {{ score += 7500; notes.push("live Hydreigon evolution"); }}
    else notes.push("needs Deino in play plus Hydreigon ex");
  }}
  if (name === "Hydreigon ex") {{
    if (pNames.includes("Rare Candy") && fNames.includes("Deino")) {{ score += 6900; notes.push("Rare Candy path live"); }}
    else if (hydreigonBridgeNeeded()) {{ score += 2600; notes.push("needs Rare Candy or Zweilous bridge; use Pad/Dawn/Ultra Ball/Petrel/Secret Box if present"); }}
    else notes.push("needs Rare Candy/Zweilous and protected Deino chain");
  }}
  if (name === "Ultra Ball") {{
    const safe = safeDiscardCount(handIds, "Ultra Ball");
    if (handNames.includes("Buddy-Buddy Poffin") && (miss.deino || miss.gastly || miss.toxel)) {{ score -= 5200; notes.push("use Poffin before Ultra Ball"); }}
    else if (safe >= 2 && (hydreigonBridgeNeeded() || gengarBridgeNeeded())) {{ score += 7200; notes.push("safe discard cost and evolution bridge/search target needed"); }}
    else if (safe >= 2) {{ score += 4200; notes.push("safe discard cost available"); }}
    else {{ score -= 3600; notes.push("discard cost unsafe"); }}
  }}
  if (name === "Secret Box") {{
    const safe = safeDiscardCount(handIds, "Secret Box");
    if (secretBoxEnergyRecyclerCombo()) {{ score += 8600; notes.push("Secret Box can discard Energy, then Energy Recycler can restore it"); }}
    else if (safe >= 3 && hydreigonBridgeNeeded()) {{ score += 6200; notes.push("safe package can find Rare Candy/Poke Pad/Ultra Ball for Hydreigon bridge"); }}
    else if (safe >= 3) {{ score += 3000; notes.push("safe 3-card discard package"); }}
    else {{ score -= 5200; notes.push("discard cost unsafe"); }}
  }}
  if (name === "Crispin" && (pNames.includes("Hydreigon ex") || pNames.includes("Mega Gengar ex"))) {{
    score += 2800; notes.push("energy fixer once attacker is live");
  }}
  if (["Basic Metal Energy","Basic Psychic Energy"].includes(name)) {{
    if (fieldNames().some(n => ["Deino","Zweilous","Hydreigon ex"].includes(n))) {{ score += 3100; notes.push("attach only to highest Hydreigon line in play"); }}
    else {{ score -= 1800; notes.push("hold unless Hydreigon line target exists"); }}
  }}
  if (name === "Basic Darkness Energy") {{
    if (fieldNames().some(n => ["Deino","Gastly","Haunter","Hydreigon ex","Mega Gengar ex"].includes(n))) {{ score += 2200; notes.push("main attacker Energy"); }}
  }}
  if (name === "Fezandipiti ex" || name === "Pecharunt ex") {{
    score -= 1600; notes.push("two-prize support liability unless effect matters");
  }}
  if (name === "Sacred Ash" || name === "Night Stretcher" || name === "Energy Recycler") {{
    score -= 1200; notes.push("hold until discard has real targets");
  }}
  return {{ score: Math.max(-12000, Math.round(score)), notes }};
}}
function normalizeScore(score) {{
  return Math.max(0, Math.min(5, Math.round(score / 2800)));
}}
function renderScenario() {{
  if (!scenario) return;
  const meta = document.getElementById("scenarioMeta");
  meta.innerHTML = `<span class="pill">Opening 7 dealt</span><span class="pill">Active auto-selected</span><span class="pill">Hand + Active + Bench count as present</span><span class="pill">Agent ignores hidden prize identities</span>`;
  const activeCard = cardById(scenario.active);
  const benchHtml = scenario.bench.length
    ? `<div class="bench-row">${{scenario.bench.map((id, i) => {{ const c = cardById(id); return `<div class="card bench-slot"><div class="name">Bench ${{i + 1}}: ${{escapeHtml(c.name)}}</div><div class="meta">${{escapeHtml(c.type)}} · ID ${{c.id}}</div></div>`; }}).join("")}}</div>`
    : `<div class="sub" style="margin-top:8px">Bench is empty. Use the Bench button on Basic Pokemon in hand to test field-present connections.</div>`;
  document.getElementById("activeArea").innerHTML = `<div class="card active-slot"><div class="name">Active: ${{escapeHtml(activeCard.name)}}</div><div class="meta">${{escapeHtml(activeCard.type)}} · ID ${{activeCard.id}}</div><div class="score">Auto-chosen setup Basic</div></div>${{benchHtml}}`;
  const hand = document.getElementById("handCards");
  hand.innerHTML = "";
  scenario.hand.forEach((id, idx) => {{
    const c = cardById(id);
    const rating = ratings[idx] || 0;
    const s = agentScoreFor(id, scenario.hand);
    const agentRating = normalizeScore(s.score);
    const benchButton = isBasic(id) && scenario.bench.length < 5 ? `<button class="mini-btn" onclick="event.stopPropagation(); benchCard(${{idx}})">Bench</button>` : "";
    const div = document.createElement("div");
    div.className = "card";
    div.onclick = () => {{ ratings[idx] = ((ratings[idx] || 0) + 1) % 6; renderScenario(); }};
    div.innerHTML = `<div class="name">${{escapeHtml(c.name)}}</div><div class="meta">${{escapeHtml(c.type)}} · ID ${{c.id}}</div><div class="card-actions">${{benchButton}}</div><div class="rating">Your importance: ${{rating}} / 5</div><div class="score">Agent: ${{agentRating}} / 5 · raw ${{s.score}}<br>${{escapeHtml(s.notes.join("; ") || "baseline role score")}}</div>`;
    hand.appendChild(div);
  }});
  renderPrizes();
  renderComparison();
  renderDeckList();
  renderCurrentConnections();
}}
function renderComparison() {{
  const box = document.getElementById("comparison");
  if (!scenario) {{ box.innerHTML = ""; return; }}
  if (!revealed) {{
    box.innerHTML = `<p class="sub">Set your importance by clicking hand cards, then reveal agent scores.</p>`;
    return;
  }}
  const rows = scenario.hand.map((id, idx) => {{
    const c = cardById(id);
    const s = agentScoreFor(id, scenario.hand);
    const agent = normalizeScore(s.score);
    const user = ratings[idx] || 0;
    const diff = user - agent;
    const cls = Math.abs(diff) <= 1 ? "good" : "bad";
    return `<tr><td>${{escapeHtml(c.name)}}</td><td>${{user}}</td><td>${{agent}}</td><td class="delta ${{cls}}">${{diff > 0 ? "+" : ""}}${{diff}}</td><td>${{escapeHtml(s.notes.join("; "))}}</td></tr>`;
  }}).join("");
  box.innerHTML = `<div class="table-wrap" style="max-height:340px"><table><thead><tr><th>Card</th><th>Your</th><th>Agent</th><th>Diff</th><th>Agent reason</th></tr></thead><tbody>${{rows}}</tbody></table></div>`;
}}
function renderPrizes() {{
  const box = document.getElementById("prizes");
  box.innerHTML = scenario.prizes.map((id, idx) => {{
    const c = cardById(id);
    return `<div class="prize ${{prizesRevealed ? "reveal" : ""}}">${{prizesRevealed ? escapeHtml(c.name) : `Prize ${{idx + 1}}`}}</div>`;
  }}).join("");
}}
function renderDeckList() {{
  const counts = {{}};
  DATA.deck.forEach(id => {{ const n = cardById(id).name; counts[n] = (counts[n] || 0) + 1; }});
  document.getElementById("deckList").innerHTML = Object.entries(counts).sort((a,b) => a[0].localeCompare(b[0])).map(([n,c]) => `<div>${{c}} · ${{escapeHtml(n)}}</div>`).join("");
}}
function detectedConnectionRules() {{
  if (!scenario) return [];
  const names = presentNames();
  const handNames = scenario.hand.map(id => cardById(id).name);
  const rules = [];
  const add = (title, score, text) => rules.push({{ title, score, text }});
  if (hydreigonBridgeNeeded()) {{
    const presentFinders = ["Poke Pad","Dawn","Ultra Ball","Team Rocket's Petrel","Secret Box","Lillie's Determination"].filter(n => names.includes(n));
    const direct = presentFinders.filter(n => n !== "Lillie's Determination");
    const text = direct.length
      ? `Deino is in play and Hydreigon ex is present, but Rare Candy/Zweilous is missing. Use: ${{direct.join(", ")}}. Lillie is fallback after usage check.`
      : "Deino is in play and Hydreigon ex is present, but Rare Candy/Zweilous and search paths are missing. Lillie can refresh after checking all useful actions.";
    add("Hydreigon bridge needed", 9800, text);
  }}
  if (gengarBridgeNeeded()) {{
    const direct = ["Poke Pad","Dawn","Ultra Ball","Team Rocket's Petrel","Secret Box"].filter(n => names.includes(n));
    add("Mega Gengar bridge needed", 9000, direct.length ? `Gastly and Mega Gengar ex are present. Find Haunter with ${{direct.join(", ")}}.` : "Gastly and Mega Gengar ex are present, but Haunter/search path is missing. Lillie can refresh after usage check.");
  }}
  if (secretBoxEnergyRecyclerCombo()) {{
    add("Secret Box + Energy Recycler", 8600, "Secret Box has Energy Recycler plus at least three Energy in hand. Discarding Energy can be safer because Recycler can restore it afterward; still protect Metal/Psychic unless payoff matters.");
  }}
  if (handNames.includes("Buddy-Buddy Poffin") && (missingCore(handNames).deino || missingCore(handNames).gastly || missingCore(handNames).toxel)) {{
    add("Use Poffin before draw/search costs", 9800, "Bench is missing core Basics. Use Buddy-Buddy Poffin before Lillie, Ultra Ball, or Secret Box.");
  }}
  const wait = preLillieAction(handNames, scenario.hand);
  if (handNames.includes("Lillie's Determination")) {{
    add("Lillie permanent usage check", wait ? 7600 : 9400, wait ? `Use ${{wait}} before Lillie's Determination, then reassess.` : "No obvious useful hand action blocks Lillie; Lillie is the preferred Supporter refresh.");
  }}
  if (names.includes("Toxtricity") && (names.includes("Hydreigon ex") || names.includes("Mega Gengar ex"))) {{
    add("Toxtricity Energy engine target", 7600, "Use Sinister Surge to attach Darkness to Hydreigon ex or Mega Gengar ex, not to Toxtricity/Fezandipiti/Pecharunt.");
  }}
  return rules.sort((a,b) => b.score - a.score);
}}
function renderCurrentConnections() {{
  const box = document.getElementById("currentConnections");
  const rules = detectedConnectionRules();
  if (!rules.length) {{
    box.innerHTML = `<div class="sub">No special multi-card path detected yet. Use Score Chart for static whole-deck relationships.</div>`;
    return;
  }}
  box.innerHTML = rules.map(r => `<div class="connection-item"><b>${{escapeHtml(r.title)}} <span class="sub">score ${{r.score}}</span></b>${{escapeHtml(r.text)}}</div>`).join("");
}}
function renderMatrix() {{
  const headers = DATA.cards.map(c => `<th>${{escapeHtml(c.name)}}</th>`).join("");
  const rows = DATA.cards.map((rowCard, r) => {{
    const cells = DATA.matrix[r].map(cell => {{
      const cls = cell.score > 0 ? "pos" : cell.score < 0 ? "neg" : "";
      const score = cell.score ? `<div class="cell-score ${{cls}}">${{cell.score > 0 ? "+" : ""}}${{cell.score}}</div>` : `<div class="cell-score">0</div>`;
      const modifier = cell.modifier ? `<div class="cell-note">modifier ${{cell.modifier > 0 ? "+" : ""}}${{cell.modifier}}</div>` : "";
      const note = cell.note ? `<div class="cell-note">${{escapeHtml(cell.note)}}</div>` : "";
      return `<td>${{score}}${{modifier}}${{note}}</td>`;
    }}).join("");
    return `<tr><td>${{escapeHtml(rowCard.name)}}</td>${{cells}}</tr>`;
  }}).join("");
  document.getElementById("matrixWrap").innerHTML = `<table><thead><tr><th>Valued card ↓ / Present card →</th>${{headers}}</tr></thead><tbody>${{rows}}</tbody></table>`;
}}
function renderComboRules() {{
  const box = document.getElementById("comboRules");
  box.innerHTML = DATA.combos.map(combo => {{
    const cards = combo.cards.concat(combo.use_if_present || []).join(" + ");
    const missing = combo.missing && combo.missing.length ? `<div class="sub">Missing/check: ${{escapeHtml(combo.missing.join(" or "))}}</div>` : "";
    return `<div class="connection-item"><b>${{escapeHtml(combo.name)}} <span class="sub">score ${{combo.score}}</span></b><div class="sub">${{escapeHtml(cards)}}</div>${{missing}}<div>${{escapeHtml(combo.rule)}}</div></div>`;
  }}).join("");
}}
function renderLogic() {{
  document.getElementById("strategyNotes").innerHTML = DATA.strategyNotes.map(x => `<li>${{escapeHtml(x)}}</li>`).join("");
  document.getElementById("cardRules").innerHTML = DATA.cards.map(c => `<div class="rule-card"><b>${{escapeHtml(c.name)}} <span class="sub">base ${{c.baseScore || 0}}</span></b><div>${{escapeHtml(c.role || "")}}</div><div class="sub">Use: ${{escapeHtml(c.use || "")}}</div><div class="sub">Missing: ${{escapeHtml(c.missing || "")}}</div></div>`).join("");
}}
function escapeHtml(s) {{
  return String(s || "").replace(/[&<>"']/g, ch => ({{"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}}[ch]));
}}
document.getElementById("dealBtn").onclick = deal;
document.getElementById("revealBtn").onclick = () => {{ revealed = !revealed; document.body.classList.toggle("revealed", revealed); renderComparison(); }};
document.getElementById("prizeBtn").onclick = () => {{ prizesRevealed = !prizesRevealed; renderPrizes(); }};
document.getElementById("chartBtn").onclick = () => document.getElementById("chartPanel").classList.toggle("hidden");
document.getElementById("comboBtn").onclick = () => document.getElementById("comboPanel").classList.toggle("hidden");
document.getElementById("logicBtn").onclick = () => document.getElementById("logicPanel").classList.toggle("hidden");
renderMatrix();
renderComboRules();
renderLogic();
deal();
</script>
</body>
</html>"""


def main() -> None:
    deck = load_deck_ids()
    cards = build_cards(deck)
    data = {
        "deck": deck,
        "cards": cards,
        "cardsById": {str(card["id"]): card for card in cards},
        "matrix": build_matrix(cards),
        "combos": MULTI_CARD_COMBOS,
        "strategyNotes": build_strategy_notes(),
        "cardIds": CARD_IDS,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render_html(data), encoding="utf-8")
    print(f"Wrote {OUT.resolve()}")


if __name__ == "__main__":
    main()
