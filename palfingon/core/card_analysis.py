from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from card_db import CardInfo, get_db
from deck_profile import load_deck_ids
from core.card_relationships import CardRelationship, build_card_relationships
from core.priority_tables import canonical_name, canonical_name_from_id, card_id_for_name


ROLE_OPTIONS = [
    "main_attacker",
    "secondary_attacker",
    "setup_basic",
    "evolution_bridge",
    "evolution_target",
    "switch_engine",
    "search_card",
    "exact_trainer_search",
    "broad_draw",
    "energy_acceleration",
    "energy_recovery",
    "pokemon_recovery",
    "pivot",
    "stadium",
    "gust",
    "damage_modifier",
    "ace_spec",
    "support_pokemon",
    "resource_card",
]


@dataclass(frozen=True)
class CardAnalysis:
    card_name: str
    count_in_deck: int = 0
    card_type: str = ""
    stage: str = ""
    rule_box_status: str = ""
    hp: int = 0
    retreat_cost: int = 0
    attack_costs: List[str] = field(default_factory=list)
    attack_damage: List[str] = field(default_factory=list)
    ability_text: str = ""
    effect_text: str = ""
    role: List[str] = field(default_factory=list)
    primary_use: str = ""
    secondary_use: str = ""
    early_game_value: int = 0
    mid_game_value: int = 0
    late_game_value: int = 0
    search_targets: List[str] = field(default_factory=list)
    searched_by: List[str] = field(default_factory=list)
    enables_cards: List[str] = field(default_factory=list)
    enabled_by_cards: List[str] = field(default_factory=list)
    protects_cards: List[str] = field(default_factory=list)
    protected_by_cards: List[str] = field(default_factory=list)
    energy_requirements: str = ""
    switch_synergy: str = ""
    recovery_synergy: str = ""
    discard_priority: str = ""
    protected_priority: str = ""
    when_to_play: str = ""
    when_to_hold: str = ""
    when_not_to_play: str = ""
    common_mistakes: List[str] = field(default_factory=list)
    policy_rules: List[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


BASE_STRATEGY: Dict[str, dict[str, Any]] = {
    "Finizen": {
        "role": ["setup_basic"],
        "primary_use": "Required Basic for the Palafin ex engine.",
        "secondary_use": "Early Active or Bench body that becomes Palafin.",
        "values": (100, 70, 25),
        "energy_requirements": "Usually none until it becomes Palafin ex; Water only if it must attack.",
        "switch_synergy": "Needs to evolve to Palafin, then Palafin must move Active to Bench.",
        "recovery_synergy": "Recover if all Finizen or multiple Palafin line pieces are lost.",
        "discard_priority": "Very low discard priority; protect early.",
        "protected_priority": "High while Palafin line is not established.",
        "when_to_play": "Bench immediately when legal and Bench has space.",
        "when_to_hold": "Only hold if Bench is full and a better line is already established.",
        "when_not_to_play": "Do not overbench if Bench is full of stronger setup and opponent punishes low HP.",
        "common_mistakes": ["Focusing Dragonite before establishing Finizen.", "Using Lillie before playing a legal Finizen."],
        "policy_rules": ["Bench Basic from hand", "Poffin before Lillie"],
    },
    "Palafin": {
        "role": ["evolution_bridge", "switch_engine"],
        "primary_use": "Zero to Hero bridge from Finizen into Palafin ex.",
        "secondary_use": "Can be a temporary pivot but is not the main attacker.",
        "values": (85, 100, 55),
        "energy_requirements": "Usually no Energy unless forced; conserve Water for Palafin ex.",
        "switch_synergy": "Must move from Active to Bench to trigger Zero to Hero.",
        "recovery_synergy": "Recover exact copy when Finizen is ready and Palafin is missing.",
        "discard_priority": "Protected if Finizen is in play.",
        "protected_priority": "High when Zero to Hero is not online.",
        "when_to_play": "Evolve Finizen when a switch route or setup route is available.",
        "when_to_hold": "Hold if evolving would strand the only Palafin without switch access and another action is stronger.",
        "when_not_to_play": "Do not treat it as ordinary attacker if Zero to Hero can be built.",
        "common_mistakes": ["Attacking with Palafin instead of enabling Zero to Hero."],
        "policy_rules": ["Zero to Hero", "Poke Pad for Palafin"],
    },
    "Palafin ex": {
        "role": ["main_attacker", "evolution_target"],
        "primary_use": "Main attacker that hits hard for one Water Energy.",
        "secondary_use": "Prize-route attacker that needs switching after Giga Impact.",
        "values": (45, 100, 90),
        "energy_requirements": "Exactly one useful Water Energy; do not overattach.",
        "switch_synergy": "Needs Surfing Beach, Switch, Kieran, Air Balloon, or Mega Dragonite to reset Giga Impact turns.",
        "recovery_synergy": "Recover only when Zero to Hero target count is low or discarded copies block setup.",
        "discard_priority": "Protected; only discard with Sacred Ash/Night Stretcher recovery ready.",
        "protected_priority": "Very high.",
        "when_to_play": "Only through Palafin's Zero to Hero effect.",
        "when_to_hold": "Keep in deck when possible so Zero to Hero can find it.",
        "when_not_to_play": "Do not manually evolve or attack after Giga Impact without reset if cabt tracks the restriction.",
        "common_mistakes": ["Overattaching Energy.", "Trying to attack with the same Palafin ex next turn without reset.", "Searching it with Poke Pad."],
        "policy_rules": ["Water to Palafin ex", "Palafin reset"],
    },
    "Dratini": {
        "role": ["setup_basic"],
        "primary_use": "Basic for Dragonair and Mega Dragonite ex.",
        "secondary_use": "Background setup after Finizen line starts.",
        "values": (70, 80, 65),
        "energy_requirements": "Lightning/Water only when building Dragonite line; not before Finizen plan is safe.",
        "switch_synergy": "Can become Dragonair, then Mega Dragonite switch engine.",
        "recovery_synergy": "Recover if Dragonite line is unavailable.",
        "discard_priority": "Protected if Dragonite line is absent.",
        "protected_priority": "Medium-high.",
        "when_to_play": "Bench when legal after Finizen basics are handled or when hand naturally supports Dragonite.",
        "when_to_hold": "Do not clog Bench if Finizen line is missing and Bench is nearly full.",
        "when_not_to_play": "Do not expect Buddy-Buddy Poffin to find it when local HP is 80.",
        "common_mistakes": ["Wasting Poffin plan on illegal Dratini target."],
        "policy_rules": ["Poke Pad for Dratini"],
    },
    "Dragonair": {
        "role": ["evolution_bridge", "search_card"],
        "primary_use": "Evolution bridge and Evolution-search Ability when it has Energy.",
        "secondary_use": "Finds Palafin or Mega Dragonite ex depending board needs.",
        "values": (45, 90, 80),
        "energy_requirements": "One Energy can turn on Evolutionary Guidance; Lightning is best if building Dragonite.",
        "switch_synergy": "Evolves toward Mega Dragonite switch ability.",
        "recovery_synergy": "Recover exact copy when Dratini is in play and Dragonite line is missing.",
        "discard_priority": "Protected when Dratini is in play.",
        "protected_priority": "High if it is the only bridge.",
        "when_to_play": "Evolve Dratini and use Ability before Supporters/end when Energy is attached.",
        "when_to_hold": "Hold if no Dratini is in play and it is not searchable/useful this turn.",
        "when_not_to_play": "Do not ignore Dragonair once Palafin is online.",
        "common_mistakes": ["Ignoring Evolutionary Guidance.", "Searching Palafin ex instead of normal Palafin."],
        "policy_rules": ["Dragonair evolution search"],
    },
    "Mega Dragonite ex": {
        "role": ["secondary_attacker", "switch_engine", "evolution_target"],
        "primary_use": "Switch engine through ability and late-game heavy attacker.",
        "secondary_use": "Closes games with 330 damage when Energy discard is worth it.",
        "values": (35, 85, 100),
        "energy_requirements": "Water + Lightning + Lightning; protect Lightning.",
        "switch_synergy": "Ability can move Active and support Palafin reset loops.",
        "recovery_synergy": "Recover if discarded before Dragonair is ready.",
        "discard_priority": "Protected unless Sacred Ash/Night Stretcher recovery is ready.",
        "protected_priority": "Very high after Dragonair is in play.",
        "when_to_play": "Build in background after Palafin line is started.",
        "when_to_hold": "Hold if Dragonair is not ready and discard costs are unsafe.",
        "when_not_to_play": "Do not attack casually if discarding Energy gives no prize-route gain.",
        "common_mistakes": ["Using Dragonite attack without a follow-up.", "Spending Lightning elsewhere."],
        "policy_rules": ["Crispin Dragonite energy", "Protect Lightning"],
    },
    "Tatsugiri": {
        "role": ["support_pokemon", "pivot", "setup_basic"],
        "primary_use": "Active Spot Supporter access through Attract Customers.",
        "secondary_use": "Poffin target when support access is needed.",
        "values": (75, 55, 30),
        "energy_requirements": "Avoid Energy except exact retreat exception.",
        "switch_synergy": "Can pivot if Air Balloon is reserved for it.",
        "recovery_synergy": "Low recovery priority unless Supporter access is otherwise dead.",
        "discard_priority": "Medium; do not discard if it is your only support access.",
        "protected_priority": "Medium.",
        "when_to_play": "Bench when Finizen line is not blocked and support access matters.",
        "when_to_hold": "Hold if Bench is nearly full and Finizen/Dragonite setup is missing.",
        "when_not_to_play": "Do not fill Bench with Tatsugiri over core setup pieces.",
        "common_mistakes": ["Attaching extra Energy to Tatsugiri.", "Benching it when Finizen lines are missing and Bench is tight."],
        "policy_rules": ["Tatsugiri before Supporter", "Bench Basic from hand"],
    },
    "Buddy-Buddy Poffin": {
        "role": ["search_card"],
        "primary_use": "Early setup for Finizen and Tatsugiri.",
        "secondary_use": "Bench filling before Lillie.",
        "values": (100, 70, 20),
        "when_to_play": "Use before Lillie when Bench has space and Finizen/Tatsugiri targets remain.",
        "when_to_hold": "Hold only if Bench is full or targets are gone.",
        "when_not_to_play": "Do not expect it to find 80 HP Dratini.",
        "common_mistakes": ["Lillie before Poffin.", "Planning Poffin for Dratini."],
        "policy_rules": ["Poffin before Lillie"],
    },
    "Poke Pad": {
        "role": ["search_card"],
        "primary_use": "Finds non-Rule Box bridge pieces such as Palafin or Dratini.",
        "secondary_use": "Finds Tatsugiri/Finizen if setup is thin.",
        "values": (85, 95, 50),
        "when_to_play": "Use for Palafin when Finizen is ready or for Dratini when Dragonite line is absent.",
        "when_to_hold": "Hold if no useful non-Rule Box target exists.",
        "when_not_to_play": "Do not target Palafin ex or Mega Dragonite ex.",
        "common_mistakes": ["Random target selection without checking missing bridge."],
        "policy_rules": ["Poke Pad for Palafin", "Poke Pad for Dratini"],
    },
    "Lillie's Determination": {
        "role": ["broad_draw"],
        "primary_use": "Broad hand refresh after exact setup actions.",
        "secondary_use": "Dead-hand reset when Bench is empty and no exact search is available.",
        "values": (75, 70, 35),
        "when_to_play": "Use after Poffin/Poke Pad/evolution/Basic bench/Ability checks are cleared.",
        "when_to_hold": "Hold when it would shuffle a ready combo or exact setup action.",
        "when_not_to_play": "Do not use before Poffin or Poke Pad that solves the board.",
        "common_mistakes": ["Using Lillie as replacement for exact combo pieces."],
        "policy_rules": ["Lillie after setup actions"],
    },
    "Team Rocket's Petrel": {
        "role": ["exact_trainer_search", "search_card"],
        "primary_use": "Find exact Trainer that solves this turn.",
        "secondary_use": "Find Secret Box package when multiple pieces are missing.",
        "values": (80, 90, 70),
        "when_to_play": "Use when exact Trainer beats random draw.",
        "when_to_hold": "Hold if Poffin or target Trainer is already in hand.",
        "when_not_to_play": "Do not Petrel for Poffin when Poffin is already in hand.",
        "common_mistakes": ["Fetching low-impact Poffin with developed Bench."],
        "policy_rules": ["Petrel exact Trainer"],
    },
    "Secret Box": {
        "role": ["ace_spec", "search_card"],
        "primary_use": "Multi-piece setup package: Item + Tool + Supporter + Stadium.",
        "secondary_use": "Finds next-turn Supporter after Supporter is spent.",
        "values": (85, 100, 65),
        "when_to_play": "Use only when discard cost is safe and package advances setup.",
        "when_to_hold": "Hold with protected cards and no recovery.",
        "when_not_to_play": "Do not use just to thin hand.",
        "common_mistakes": ["Discarding protected Palafin ex/Mega Dragonite pieces without recovery."],
        "policy_rules": ["Secret Box package"],
    },
    "Surfing Beach": {
        "role": ["switch_engine", "stadium"],
        "primary_use": "Main Stadium switch engine for Zero to Hero and Palafin reset.",
        "secondary_use": "Preferred Stadium unless opponent Stadium must be answered differently.",
        "values": (80, 100, 90),
        "when_to_play": "Play when Palafin/Palafin ex movement matters.",
        "when_to_hold": "Hold duplicate if your Surfing Beach is already in play.",
        "when_not_to_play": "Do not replace your own useful Stadium without reason.",
        "common_mistakes": ["Not playing Surfing Beach before trying Zero to Hero."],
        "policy_rules": ["Surfing Beach switch loop"],
    },
    "Switch": {
        "role": ["switch_engine"],
        "primary_use": "Direct switching for Zero to Hero and reset.",
        "secondary_use": "Escape stuck Active.",
        "values": (70, 90, 80),
        "when_to_play": "Use when the switch creates Palafin ex or resets Giga Impact.",
        "when_to_hold": "Hold if Surfing Beach already solves movement.",
        "when_not_to_play": "Do not waste it with no attack/setup gain.",
        "common_mistakes": ["Wasting Switch when Surfing Beach already handles movement."],
        "policy_rules": ["Zero to Hero"],
    },
    "Air Balloon": {
        "role": ["switch_engine", "pivot"],
        "primary_use": "Attach to active Palafin evolution chain to retreat for Zero to Hero.",
        "secondary_use": "Attach to Tatsugiri as a Dragonite reset pivot, especially when Tatsugiri is Active.",
        "values": (60, 85, 75),
        "when_to_play": "Attach to active Palafin for Zero to Hero, active attack-locked Palafin ex for reset/recharge, or Tatsugiri for the Dragonite pivot loop.",
        "when_to_hold": "Hold if target is random or retreat is not needed.",
        "when_not_to_play": "Do not attach randomly to non-pivot Pokemon.",
        "common_mistakes": ["Attaching Air Balloon to a random Bench Pokemon."],
        "policy_rules": ["Air Balloon active Palafin"],
    },
    "Kieran": {
        "role": ["switch_engine", "damage_modifier"],
        "primary_use": "Switch mode for Zero to Hero/reset.",
        "secondary_use": "+30 damage only when KO math changes.",
        "values": (45, 75, 90),
        "when_to_play": "Use when switching creates Palafin ex/reset or +30 creates KO.",
        "when_to_hold": "Hold if neither mode changes the turn.",
        "when_not_to_play": "Do not use randomly.",
        "common_mistakes": ["Using damage mode when it does not change KO math."],
        "policy_rules": ["Boss/Kieran KO math"],
    },
    "Boss's Orders": {
        "role": ["gust"],
        "primary_use": "Prize-route control.",
        "secondary_use": "Final prizes or low-HP ex targets.",
        "values": (35, 75, 100),
        "when_to_play": "Use only when it creates KO, blocks opponent, or improves prize route.",
        "when_to_hold": "Hold if no prize benefit.",
        "when_not_to_play": "Do not gust without KO/prize route gain.",
        "common_mistakes": ["Boss without damage/prize benefit."],
        "policy_rules": ["Boss/Kieran KO math"],
    },
    "Crispin": {
        "role": ["energy_acceleration"],
        "primary_use": "Mixed Energy fixing, mainly Dragonite.",
        "secondary_use": "Can fix Palafin + Dragonite board.",
        "values": (45, 85, 90),
        "when_to_play": "Use when Dragonite line needs Water/Lightning or mixed Energy fixes attack.",
        "when_to_hold": "Hold if no attacker can use the acceleration.",
        "when_not_to_play": "Do not spend it for low-impact Energy movement.",
        "common_mistakes": ["Not using Crispin when Dragonite needs mixed Energy."],
        "policy_rules": ["Crispin Dragonite energy"],
    },
    "Hilda": {
        "role": ["search_card", "energy_acceleration"],
        "primary_use": "Evolution Pokemon + Energy package.",
        "secondary_use": "Find Palafin + Water, Dragonair + Lightning, or Mega Dragonite + Lightning.",
        "values": (65, 90, 75),
        "when_to_play": "Use when both Evolution and Energy matter.",
        "when_to_hold": "Hold if the missing piece is a Basic.",
        "when_not_to_play": "Do not use to solve missing Finizen/Dratini.",
        "common_mistakes": ["Using Hilda when the missing piece is Basic."],
        "policy_rules": ["Hilda package"],
    },
    "Energy Retrieval": {
        "role": ["energy_recovery"],
        "primary_use": "Recover Water/Lightning when exact Energy enables attack.",
        "secondary_use": "Recover after Dragonite discards.",
        "values": (20, 65, 90),
        "when_to_play": "Use when recovered Energy affects current or next turn.",
        "when_to_hold": "Hold when no important Energy is in discard.",
        "when_not_to_play": "Do not use too early.",
        "common_mistakes": ["Recovering Energy with no attack plan."],
        "policy_rules": ["Timed recovery"],
    },
    "Night Stretcher": {
        "role": ["pokemon_recovery", "energy_recovery"],
        "primary_use": "Exact Pokemon or Basic Energy recovery.",
        "secondary_use": "Restore a missing bridge or Energy.",
        "values": (20, 70, 90),
        "when_to_play": "Use when exact recovery creates immediate play.",
        "when_to_hold": "Hold if discard has no key target.",
        "when_not_to_play": "Do not recover random cards.",
        "common_mistakes": ["Random recovery."],
        "policy_rules": ["Timed recovery"],
    },
    "Sacred Ash": {
        "role": ["pokemon_recovery"],
        "primary_use": "Mass Pokemon recovery.",
        "secondary_use": "Restore multiple lost line pieces.",
        "values": (15, 60, 95),
        "when_to_play": "Use when several Pokemon or key line pieces are in discard.",
        "when_to_hold": "Hold for meaningful recovery.",
        "when_not_to_play": "Do not use for one noncritical Pokemon.",
        "common_mistakes": ["Using Sacred Ash too early."],
        "policy_rules": ["Timed recovery"],
    },
    "Basic Water Energy": {
        "role": ["resource_card"],
        "primary_use": "Palafin ex attack fuel.",
        "secondary_use": "Mega Dragonite attack cost.",
        "values": (70, 95, 85),
        "energy_requirements": "Best target is Palafin ex with zero Energy.",
        "when_to_play": "Attach to Palafin ex that can attack, or Dragonite line when Dragonite plan needs Water.",
        "when_to_hold": "Hold if only bad targets exist.",
        "when_not_to_play": "Do not overattach to Palafin ex.",
        "common_mistakes": ["Overattaching to Palafin ex."],
        "policy_rules": ["Water to Palafin ex"],
    },
    "Basic Lightning Energy": {
        "role": ["resource_card"],
        "primary_use": "Mega Dragonite ex attack fuel.",
        "secondary_use": "Do not use for Tatsugiri retreat setup.",
        "values": (55, 90, 100),
        "energy_requirements": "Best target is Dragonite line; protected for Mega Dragonite ex.",
        "when_to_play": "Attach to Dratini/Dragonair/Mega Dragonite ex when Dragonite line is real.",
        "when_to_hold": "Hold if only Palafin/Finizen/Tatsugiri targets exist.",
        "when_not_to_play": "Do not attach to Palafin line or Tatsugiri.",
        "common_mistakes": ["Putting Lightning on Palafin or Tatsugiri."],
        "policy_rules": ["Protect Lightning"],
    },
}


BASE_STRATEGY.update({
    "Palafin TEF 49": {
        "role": ["secondary_attacker", "one_prize_attacker"], "values": (40, 75, 80),
        "primary_use": "Vanguard Punch for 130 with one Water; check self-damage before attacking.",
        "energy_requirements": "One Water for Vanguard Punch; no extra Energy investment.",
        "when_to_play": "Evolve an available Finizen when the one-prize attack improves the current route.",
        "when_not_to_play": "Do not confuse this printing with the Zero to Hero evolution.",
        "common_mistakes": ["Trying to trigger Zero to Hero.", "Ignoring self-KO from existing damage."],
    },
    "Judge": {
        "role": ["draw_supporter", "disruption"], "values": (55, 65, 65),
        "primary_use": "Each player shuffles their hand into the deck and draws four.",
        "when_to_play": "Dead hand or large visible opposing hand, after useful Items, evolution, Basics, and Energy.",
        "when_not_to_play": "Avoid shrinking a useful hand or consuming the Supporter needed for attack access.",
    },
    "Battle Cage": {
        "role": ["defensive_stadium"], "values": (25, 60, 65),
        "primary_use": "Protect Benched Pokemon from opposing attack/Ability effects that place damage counters.",
        "when_to_play": "Visible counter-placement threat and no necessary Surfing Beach route this turn.",
        "when_not_to_play": "Do not replace needed Surfing Beach or treat this as prevention of attack damage.",
    },
})


def analyze_card(card_name: str, card_metadata: Any = None, deck_context: Optional[dict[str, Any]] = None) -> CardAnalysis:
    deck_context = deck_context or build_deck_context()
    name = canonical_name(card_name)
    card = card_metadata or deck_context["metadata_by_name"].get(name)
    strategy = BASE_STRATEGY.get(name, {})
    relationships = deck_context.get("relationships") or build_card_relationships(deck_context)
    outgoing = [rel for rel in relationships if rel.source_card == name and rel.priority > 0]
    incoming = [rel for rel in relationships if rel.target_card == name and rel.priority > 0]
    protects = [rel.target_card for rel in relationships if rel.source_card == name and rel.relationship_type == "should_not_discard"]
    protected_by = [rel.source_card for rel in relationships if rel.target_card == name and rel.relationship_type in {"protects_resource", "recovers_pokemon", "recovers_energy"}]
    values = strategy.get("values", (0, 0, 0))

    return CardAnalysis(
        card_name=name,
        count_in_deck=deck_context["counts_by_name"].get(name, 0),
        card_type=str(getattr(card, "card_type", "") or ""),
        stage=str(getattr(card, "stage", "") or ""),
        rule_box_status=rule_box_status(card),
        hp=int(getattr(card, "hp", 0) or 0),
        retreat_cost=int(getattr(card, "retreat_cost", 0) or 0),
        attack_costs=attack_costs(card),
        attack_damage=attack_damage(card),
        ability_text=ability_text(card),
        effect_text=effect_text(card),
        role=list(strategy.get("role", [])),
        primary_use=strategy.get("primary_use", ""),
        secondary_use=strategy.get("secondary_use", ""),
        early_game_value=int(values[0]),
        mid_game_value=int(values[1]),
        late_game_value=int(values[2]),
        search_targets=unique(rel.target_card for rel in outgoing if rel.relationship_type in {"searches", "finds_exact_trainer", "finds_evolution_piece", "finds_stadium", "finds_tool", "finds_supporter"}),
        searched_by=unique(rel.source_card for rel in incoming if rel.relationship_type in {"searches", "finds_exact_trainer", "finds_evolution_piece", "finds_stadium", "finds_tool", "finds_supporter"}),
        enables_cards=unique(rel.target_card for rel in outgoing if rel.relationship_type.startswith("enables") or rel.relationship_type in {"provides_energy", "resets_attack_restriction", "improves_damage_math"}),
        enabled_by_cards=unique(rel.source_card for rel in incoming if rel.relationship_type.startswith("enables") or rel.relationship_type in {"provides_energy", "resets_attack_restriction", "improves_damage_math"}),
        protects_cards=unique(protects),
        protected_by_cards=unique(protected_by),
        energy_requirements=strategy.get("energy_requirements", ""),
        switch_synergy=strategy.get("switch_synergy", ""),
        recovery_synergy=strategy.get("recovery_synergy", ""),
        discard_priority=strategy.get("discard_priority", "Medium."),
        protected_priority=strategy.get("protected_priority", "Medium."),
        when_to_play=strategy.get("when_to_play", ""),
        when_to_hold=strategy.get("when_to_hold", ""),
        when_not_to_play=strategy.get("when_not_to_play", ""),
        common_mistakes=list(strategy.get("common_mistakes", [])),
        policy_rules=list(strategy.get("policy_rules", [])),
    )


def build_deck_context() -> dict[str, Any]:
    ids = load_deck_ids()
    counts_by_id = Counter(ids)
    counts_by_name: Counter[str] = Counter(canonical_name_from_id(cid) for cid in ids)
    metadata_by_name: dict[str, CardInfo] = {}
    for cid in counts_by_id:
        card = get_db().get_card(cid)
        name = canonical_name_from_id(cid)
        if card and name:
            metadata_by_name[name] = card
    context: dict[str, Any] = {
        "deck_ids": ids,
        "counts_by_id": counts_by_id,
        "counts_by_name": counts_by_name,
        "metadata_by_name": metadata_by_name,
    }
    context["relationships"] = build_card_relationships(context)
    return context


def build_all_card_analyses(deck_context: Optional[dict[str, Any]] = None) -> dict[str, CardAnalysis]:
    deck_context = deck_context or build_deck_context()
    result = {}
    for name in deck_context["counts_by_name"]:
        if name:
            result[name] = analyze_card(name, deck_context["metadata_by_name"].get(name), deck_context)
    return result


def analyses_to_dicts(analyses: dict[str, CardAnalysis]) -> list[dict[str, Any]]:
    return [analysis.to_dict() for analysis in analyses.values()]


def render_card_analysis_markdown(analyses: Optional[dict[str, CardAnalysis]] = None) -> str:
    analyses = analyses or build_all_card_analyses()
    lines = [
        "# Palaking Card-By-Card Analysis",
        "",
        "This document is generated from the deterministic Palafin ex / Mega Dragonite ex analysis layer.",
        "",
    ]
    for analysis in analyses.values():
        lines.extend(
            [
                f"## {analysis.card_name}",
                "",
                f"Count: {analysis.count_in_deck}",
                f"Card type: {analysis.card_type}",
                f"Main role: {', '.join(analysis.role) or 'resource'}",
                f"Secondary role: {analysis.secondary_use}",
                f"Best stage of game: {best_stage(analysis)}",
                f"What this card enables: {', '.join(analysis.enables_cards) or analysis.primary_use}",
                f"What enables this card: {', '.join(analysis.enabled_by_cards) or 'Natural draw/search sequencing.'}",
                f"Best targets: {', '.join(analysis.search_targets or analysis.enables_cards) or 'Context dependent.'}",
                f"Bad targets: {bad_targets_for(analysis)}",
                f"Searchable by: {', '.join(analysis.searched_by) or 'Natural draw only.'}",
                f"Searches: {', '.join(analysis.search_targets) or 'None.'}",
                f"Energy use: {analysis.energy_requirements or 'No Energy requirement.'}",
                f"Switch synergy: {analysis.switch_synergy or 'None.'}",
                f"Recovery synergy: {analysis.recovery_synergy or 'Low unless exact resource is missing.'}",
                f"Discard priority: {analysis.discard_priority}",
                f"Protected priority: {analysis.protected_priority}",
                f"When to play: {analysis.when_to_play}",
                f"When to hold: {analysis.when_to_hold}",
                f"When not to play: {analysis.when_not_to_play}",
                f"Common agent mistakes: {', '.join(analysis.common_mistakes) or 'None noted.'}",
                f"Policy rule: {', '.join(analysis.policy_rules) or 'Use normal legality and tactical score.'}",
                "",
            ]
        )
    return "\n".join(lines)


def best_stage(analysis: CardAnalysis) -> str:
    values = {
        "early": analysis.early_game_value,
        "mid": analysis.mid_game_value,
        "late": analysis.late_game_value,
    }
    return max(values, key=values.get)


def bad_targets_for(analysis: CardAnalysis) -> str:
    if analysis.card_name == "Buddy-Buddy Poffin":
        return "Dratini when local HP is above 70; Rule Box Pokemon."
    if analysis.card_name == "Poke Pad":
        return "Palafin ex and Mega Dragonite ex because they are Rule Box Pokemon."
    if analysis.card_name == "Basic Lightning Energy":
        return "Palafin, Finizen, Palafin ex, or Tatsugiri."
    if analysis.card_name == "Air Balloon":
        return "Random Bench Pokemon; prefer active Palafin Zero to Hero, locked Palafin ex reset, or Tatsugiri Dragonite pivot."
    if analysis.card_name == "Hilda":
        return "Missing Basic Pokemon such as Finizen or Dratini."
    return "Context dependent."


def rule_box_status(card: Any) -> str:
    if not card:
        return ""
    if getattr(card, "mega_ex", False):
        return "Mega Pokemon ex"
    if getattr(card, "ex", False):
        return "Pokemon ex"
    if getattr(card, "ace_spec", False):
        return "ACE SPEC"
    rule = str(getattr(card, "rule", "") or "")
    return "" if rule.lower() == "n/a" else rule


def attack_costs(card: Any) -> list[str]:
    if not card:
        return []
    return ["/".join(str(part) for part in getattr(attack, "cost", ()) or ()) for attack in getattr(card, "attacks", ()) or ()]


def attack_damage(card: Any) -> list[str]:
    if not card:
        return []
    values = []
    for attack in getattr(card, "attacks", ()) or ():
        damage = str(getattr(attack, "damage_text", "") or getattr(attack, "damage", "") or "")
        values.append(damage)
    return values


def ability_text(card: Any) -> str:
    if not card:
        return ""
    pieces = []
    for skill in getattr(card, "skills", ()) or ():
        pieces.append(str(getattr(skill, "text", "") or ""))
    for attack in getattr(card, "attacks", ()) or ():
        name = str(getattr(attack, "name", "") or "")
        text = str(getattr(attack, "text", "") or "")
        if name.startswith("[Ability]") or "once during your turn" in text.lower():
            pieces.append(text)
    return " ".join(piece for piece in pieces if piece)


def effect_text(card: Any) -> str:
    if not card:
        return ""
    pieces = [str(getattr(card, "text", "") or "")]
    for attack in getattr(card, "attacks", ()) or ():
        name = str(getattr(attack, "name", "") or "")
        text = str(getattr(attack, "text", "") or "")
        if text and not name.startswith("[Ability]"):
            pieces.append(text)
    return " ".join(piece for piece in pieces if piece)


def unique(values: Iterable[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result


__all__ = [
    "CardAnalysis",
    "ROLE_OPTIONS",
    "analyze_card",
    "build_deck_context",
    "build_all_card_analyses",
    "analyses_to_dicts",
    "render_card_analysis_markdown",
]
