from __future__ import annotations

from typing import Any, Optional, Sequence, Set

from state_eval import (
    OPT_PLAY,
    bench_space,
    card_id,
    card_id_from_option,
    getv,
    hand_cards,
    iter_in_play,
    option_type,
)
from core.priority_tables import (
    CARD_IDS,
    canonical_name_from_id,
    count_in_play,
    has_in_hand,
    has_in_play,
)


ENERGY_NAMES = {"Basic Darkness Energy", "Basic Metal Energy", "Basic Psychic Energy"}


def present_names(state: Any) -> Set[str]:
    names = set()
    for card in hand_cards(state):
        name = canonical_name_from_id(card_id(card))
        if name:
            names.add(name)
    for _, _, pokemon in iter_in_play(state):
        name = canonical_name_from_id(card_id(pokemon))
        if name:
            names.add(name)
    return names


def hand_name_count(state: Any, name: str) -> int:
    wanted = CARD_IDS.get(name)
    return sum(1 for card in hand_cards(state) if wanted is not None and card_id(card) == wanted)


def hand_energy_count(state: Any) -> int:
    return sum(1 for card in hand_cards(state) if canonical_name_from_id(card_id(card)) in ENERGY_NAMES)


def has_any_bridge_enabler_in_hand(state: Any) -> bool:
    return any(
        has_in_hand(state, name)
        for name in (
            "Rare Candy",
            "Zweilous",
            "Haunter",
            "Poke Pad",
            "Ultra Ball",
            "Dawn",
            "Team Rocket's Petrel",
            "Secret Box",
        )
    )


def hydreigon_bridge_needed(state: Any) -> bool:
    return (
        has_in_play(state, "Deino")
        and has_in_hand(state, "Hydreigon ex")
        and not has_in_hand(state, "Rare Candy")
        and not has_in_hand(state, "Zweilous")
        and not has_in_play(state, "Zweilous")
        and count_in_play(state, "Hydreigon ex") < 2
    )


def hydreigon_rare_candy_path_needed(state: Any) -> bool:
    return (
        has_in_play(state, "Deino")
        and has_in_hand(state, "Hydreigon ex")
        and not has_in_hand(state, "Rare Candy")
        and count_in_play(state, "Hydreigon ex") < 2
    )


def gengar_bridge_needed(state: Any) -> bool:
    return (
        has_in_play(state, "Gastly")
        and has_in_hand(state, "Mega Gengar ex")
        and not has_in_hand(state, "Haunter")
        and not has_in_play(state, "Haunter")
        and count_in_play(state, "Mega Gengar ex") < 2
    )


def evolution_bridge_needed(state: Any) -> bool:
    return hydreigon_bridge_needed(state) or gengar_bridge_needed(state)


def secret_box_energy_recycler_combo(state: Any, require_secret_box_in_hand: bool = True) -> bool:
    if require_secret_box_in_hand and not has_in_hand(state, "Secret Box"):
        return False
    return has_in_hand(state, "Energy Recycler") and hand_energy_count(state) >= 3


def score_combo_play_option(state: Any, option: Any) -> float:
    if option_type(option) != OPT_PLAY:
        return 0.0
    name = canonical_name_from_id(card_id_from_option(state, option))
    if not name:
        return 0.0

    hydreigon_bridge = hydreigon_bridge_needed(state)
    gengar_bridge = gengar_bridge_needed(state)
    bridge = hydreigon_bridge or gengar_bridge

    if name == "Poke Pad" and bridge:
        return 7600.0 if hydreigon_bridge else 7200.0
    if name == "Dawn" and bridge:
        return 7400.0 if hydreigon_bridge else 7000.0
    if name == "Ultra Ball" and bridge:
        try:
            from core.discard_cost_guard import score_discard_cost_play_safety

            if score_discard_cost_play_safety(state, "Ultra Ball", 2) <= -3000.0:
                return 0.0
        except Exception:
            pass
        return 7350.0 if hydreigon_bridge else 7050.0
    if name == "Team Rocket's Petrel" and bridge:
        return 7200.0 if hydreigon_bridge else 6800.0
    if name == "Secret Box":
        try:
            from core.discard_cost_guard import score_discard_cost_play_safety

            if score_discard_cost_play_safety(state, "Secret Box", 3) <= -4500.0:
                return 0.0
        except Exception:
            pass
        if bridge:
            return 7800.0 if hydreigon_bridge else 7400.0
        if secret_box_energy_recycler_combo(state):
            return 5900.0
    if name == "Lillie's Determination" and bridge and not legal_bridge_enabler_exists(state):
        return 5200.0
    return 0.0


def legal_bridge_enabler_exists(state: Any) -> bool:
    bridge_names = {"Poke Pad", "Dawn", "Ultra Ball", "Team Rocket's Petrel", "Secret Box", "Rare Candy"}
    for option in getattr(state, "options", []) or []:
        if option_type(option) != OPT_PLAY:
            continue
        name = canonical_name_from_id(card_id_from_option(state, option))
        if name in bridge_names:
            if name == "Secret Box":
                try:
                    from core.discard_cost_guard import score_discard_cost_play_safety

                    if score_discard_cost_play_safety(state, "Secret Box", 3) <= -4500.0:
                        continue
                except Exception:
                    pass
            if name == "Ultra Ball":
                try:
                    from core.discard_cost_guard import score_discard_cost_play_safety

                    if score_discard_cost_play_safety(state, "Ultra Ball", 2) <= -3000.0:
                        continue
                except Exception:
                    pass
            return True
    return False


def score_combo_search_target(state: Any, cid: Optional[int], source: str = "") -> float:
    name = canonical_name_from_id(cid)
    if not name:
        return 0.0

    if hydreigon_bridge_needed(state):
        if source in {"Poke Pad", "Dawn", "Ultra Ball"}:
            if name == "Zweilous":
                return 32000.0
            if name == "Deino":
                return 350.0
        if source == "Team Rocket's Petrel":
            if name == "Rare Candy":
                return 34000.0
            if name in {"Poke Pad", "Ultra Ball"}:
                return 26000.0
            if name == "Secret Box":
                return 22000.0
        if source == "Secret Box":
            if name == "Rare Candy":
                return 34000.0
            if name in {"Poke Pad", "Ultra Ball"}:
                return 26000.0
            if name == "Lillie's Determination":
                return 5400.0

    if hydreigon_rare_candy_path_needed(state):
        if source in {"Team Rocket's Petrel", "Secret Box"} and name == "Rare Candy":
            return 32000.0
        if source in {"Poke Pad", "Dawn", "Ultra Ball"} and name == "Zweilous":
            return 30000.0

    if gengar_bridge_needed(state):
        if source in {"Poke Pad", "Dawn", "Ultra Ball"}:
            if name == "Haunter":
                return 32000.0
            if name == "Gastly":
                return 350.0
        if source == "Team Rocket's Petrel":
            if name in {"Poke Pad", "Ultra Ball"}:
                return 26000.0
            if name == "Secret Box":
                return 22000.0
        if source == "Secret Box":
            if name in {"Poke Pad", "Ultra Ball"}:
                return 26000.0
            if name == "Dawn":
                return 22000.0

    if source in {"Team Rocket's Petrel", "Secret Box"} and secret_box_energy_recycler_combo(state):
        if name == "Energy Recycler":
            return 7000.0
    return 0.0


def score_before_lillie_combo(state: Any, option: Any) -> float:
    name = canonical_name_from_id(card_id_from_option(state, option))
    if name == "Lillie's Determination":
        return 0.0
    score = score_combo_play_option(state, option)
    if score:
        return score
    if evolution_bridge_needed(state) and option_type(option) == OPT_PLAY and name == "Rare Candy":
        return 8000.0
    return 0.0


def score_secret_box_energy_discard(state: Any, cid: Optional[int]) -> float:
    name = canonical_name_from_id(cid)
    if name not in ENERGY_NAMES:
        return 0.0
    if not secret_box_energy_recycler_combo(state, require_secret_box_in_hand=False):
        return 0.0
    if name == "Basic Darkness Energy":
        return 1250.0
    if name in {"Basic Metal Energy", "Basic Psychic Energy"}:
        if hand_name_count(state, name) >= 2:
            return 950.0
        return 760.0
    return 0.0


def describe_combo_need(state: Any) -> str:
    if hydreigon_bridge_needed(state):
        return "Deino is in play and Hydreigon ex is in hand, so find Zweilous or Rare Candy."
    if gengar_bridge_needed(state):
        return "Gastly is in play and Mega Gengar ex is in hand, so find Haunter."
    if secret_box_energy_recycler_combo(state):
        return "Secret Box can spend Energy because Energy Recycler can restore it later."
    if bench_space(state) > 0:
        return "Keep connecting setup pieces before passing."
    return ""
