from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from action_classifier import classify_legal_option
from card_db import CardInfo, get_db
from decision_reason import build_decision_record
from deck_profile import load_deck_ids, load_profile
from policy import debug_scores
from state_eval import (
    AREA_ACTIVE,
    AREA_BENCH,
    AREA_DECK,
    AREA_HAND,
    CTX_MAIN,
    CTX_SETUP_ACTIVE,
    CTX_SETUP_BENCH,
    CTX_TO_ACTIVE,
    CTX_TO_BENCH,
    CTX_TO_HAND,
    OPT_ABILITY,
    OPT_ATTACH,
    OPT_CARD,
    OPT_END,
    OPT_PLAY,
    SELECT_CARD,
    SELECT_MAIN,
    active_pokemon,
    attached_card_ids,
    bench_pokemon,
    bench_space,
    card_id,
    deck_count,
    discard_cards,
    getv,
    hand_cards,
    hand_count,
    int_or,
    normalize_state,
    pokemon_damage,
    pokemon_energy_count,
    pokemon_hp,
    pokemon_max_hp,
    prize_count,
)


DEFAULT_OUT = "local_results/mirror_visualizer.html"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an offline HTML replay/decision visualizer.")
    parser.add_argument("--trace", help="Existing run_local.py .trace.jsonl file to visualize.")
    parser.add_argument("--mirror", action="store_true", help="Run our agent against itself first, then visualize it.")
    parser.add_argument("--demo", action="store_true", help="Build a synthetic mirror setup trace without using cabt.")
    parser.add_argument("--max-steps", type=int, default=200, help="Maximum cabt self-play steps for --mirror.")
    parser.add_argument("--result-dir", default="local_results", help="Directory for mirror traces and summaries.")
    parser.add_argument("--out", default=DEFAULT_OUT, help="HTML file to write.")
    parser.add_argument("--json-out", help="Optional enriched replay JSON output path.")
    args = parser.parse_args()

    result_dir = Path(args.result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)

    records: List[Dict[str, Any]] = []
    summary: Dict[str, Any] = {}
    source = ""

    if args.trace:
        trace_path = Path(args.trace)
        records = load_trace(trace_path)
        source = str(trace_path)
    elif args.mirror:
        trace_path, summary = run_mirror_self_play(result_dir, args.max_steps)
        if trace_path is not None:
            records = load_trace(trace_path)
            source = str(trace_path)
        if not records:
            records = synthetic_mirror_trace()
            demo_path = result_dir / "mirror_demo.trace.jsonl"
            write_trace(demo_path, records)
            summary = dict(summary)
            summary["demo_fallback"] = True
            source = str(demo_path)
    else:
        records = synthetic_mirror_trace()
        demo_path = result_dir / "mirror_demo.trace.jsonl"
        write_trace(demo_path, records)
        summary = {"label": "mirror_demo", "demo_fallback": True}
        source = str(demo_path)

    frames = build_frames(records)
    replay = {
        "title": "PTCG Mirror Replay Inspector",
        "source": source,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "frames": frames,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_html(replay), encoding="utf-8")
    if args.json_out:
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(replay, ensure_ascii=True, indent=2), encoding="utf-8")

    print(f"Wrote visualizer: {out_path}")
    print(f"Frames: {len(frames)}")
    if summary.get("engine_error"):
        print("cabt mirror run unavailable locally:", summary["engine_error"])
        print("Used synthetic mirror decision trace instead.")
    return 0


def run_mirror_self_play(result_dir: Path, max_steps: int) -> Tuple[Optional[Path], Dict[str, Any]]:
    try:
        from agent import agent as our_agent
        from run_local import run_game

        deck = load_deck_ids()
        summary = run_game(
            our_agent,
            our_agent,
            deck,
            deck,
            label="mirror",
            result_dir=result_dir,
            max_steps=max_steps,
            agent_labels=("mirror-0", "mirror-1"),
        )
        trace_path = result_dir / "mirror.trace.jsonl"
        if trace_path.exists() and trace_path.stat().st_size > 0:
            return trace_path, summary
        return None, summary
    except Exception as exc:
        return None, {"label": "mirror", "engine_error": repr(exc), "winner": None, "steps": 0}


def load_trace(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        if isinstance(data, dict) and isinstance(data.get("frames"), list):
            return data["frames"]
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
        return []

    rows: List[Dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def write_trace(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in records:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")


def build_frames(records: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    frames: List[Dict[str, Any]] = []
    for offset, row in enumerate(records):
        obs = row.get("obs") or row.get("observation") or row.get("raw")
        if not isinstance(obs, dict):
            continue
        state = normalize_state(obs)
        trace_action = _clean_choice(row.get("action", []))
        policy_choice: List[int] = []
        scores: List[float] = [0.0] * len(state.options)
        labels: Dict[int, str] = {}
        try:
            policy_choice, score_rows = debug_scores(obs)
            scores = [0.0] * len(state.options)
            for idx, score, label in score_rows:
                if 0 <= idx < len(scores):
                    scores[idx] = float(score)
                    labels[idx] = str(label)
        except Exception as exc:
            labels[-1] = f"debug score unavailable: {exc!r}"
        if not trace_action:
            trace_action = list(policy_choice)

        try:
            decision = build_decision_record(state, scores, trace_action)
        except Exception as exc:
            decision = {"reason": f"Decision explanation unavailable: {exc!r}", "legal_options": []}

        option_rows = enrich_options(state, scores, trace_action, policy_choice, labels, decision)
        frame = {
            "step": int_or(row.get("step", offset), offset),
            "label": row.get("label", ""),
            "agent_label": row.get("agent_label", ""),
            "player_index": int_or(row.get("player_index", state.your_index), state.your_index),
            "elapsed_sec": row.get("elapsed_sec", 0),
            "legal": row.get("legal", True),
            "legal_error": row.get("legal_error", ""),
            "chosen": trace_action,
            "policy_choice": policy_choice,
            "reason": decision.get("reason", ""),
            "moment_type": decision.get("moment_type", ""),
            "thought_process": decision.get("thought_process", ""),
            "round_plan": decision.get("round_plan", {}),
            "turn": int_or(getv(state.current, "turn", 0), 0),
            "turn_player": current_turn_player_index(state.current),
            "context": int_or(getv(state.select, "context", -1), -1),
            "select_type": int_or(getv(state.select, "type", -1), -1),
            "min_count": int_or(getv(state.select, "minCount", 0), 0),
            "max_count": int_or(getv(state.select, "maxCount", 0), 0),
            "board": snapshot_board(state),
            "options": option_rows,
            "logs": normalize_logs(obs.get("logs", [])),
            "raw_obs": obs,
        }
        frames.append(frame)
    return frames


def enrich_options(
    state: Any,
    scores: Sequence[float],
    trace_action: Sequence[int],
    policy_choice: Sequence[int],
    labels: Dict[int, str],
    decision: Dict[str, Any],
) -> List[Dict[str, Any]]:
    chosen = {int(idx) for idx in trace_action if isinstance(idx, int)}
    policy_chosen = {int(idx) for idx in policy_choice if isinstance(idx, int)}
    reason_by_idx: Dict[int, str] = {}
    for item in decision.get("legal_options", []) or []:
        idx = int_or(getv(item, "index", -1), -1)
        if idx >= 0:
            reason_by_idx[idx] = str(getv(item, "reason", ""))

    rows: List[Dict[str, Any]] = []
    for idx, option in enumerate(state.options):
        classified = classify_legal_option(state, option, idx)
        score = float(scores[idx]) if idx < len(scores) else 0.0
        label = labels.get(idx) or classified.option_text or classified.card_name or classified.attack_name or f"Option {idx}"
        rows.append(
            {
                "index": idx,
                "score": round(score, 3),
                "label": label,
                "category": classified.category,
                "card_id": classified.card_id,
                "card_name": classified.card_name,
                "card_type": classified.card_type,
                "attack_id": classified.attack_id,
                "attack_name": classified.attack_name,
                "target_id": classified.target_id,
                "target_name": classified.target_name,
                "number": classified.number,
                "chosen": idx in chosen,
                "policy_chosen": idx in policy_chosen,
                "reason": reason_by_idx.get(idx, ""),
                "evidence": list(classified.evidence),
                "raw": option,
            }
        )
    return rows


def snapshot_board(state: Any) -> Dict[str, Any]:
    current = state.current or {}
    stadium = getv(current, "stadium", []) or []
    return {
        "your_index": state.your_index,
        "opponent_index": state.opponent_index,
        "first_player": int_or(getv(current, "firstPlayer", -1), -1),
        "turn_player": current_turn_player_index(current),
        "result": int_or(getv(current, "result", -1), -1),
        "bench_space": bench_space(state),
        "stadium": [compact_card(card) for card in stadium] if isinstance(stadium, list) else [],
        "players": [snapshot_player(state, 0), snapshot_player(state, 1)],
    }


def snapshot_player(state: Any, player_index: int) -> Dict[str, Any]:
    active = active_pokemon(state, player_index)
    bench = bench_pokemon(state, player_index)
    hand = hand_cards(state, player_index)
    discard = discard_cards(state, player_index)
    return {
        "index": player_index,
        "active": compact_pokemon(active) if active is not None else None,
        "bench": [compact_pokemon(pokemon) for pokemon in bench],
        "hand": [compact_card(card) for card in hand],
        "hand_count": hand_count(state, player_index),
        "deck_count": deck_count(state, player_index),
        "prize_count": prize_count(state, player_index),
        "discard": [compact_card(card) for card in discard[-12:]],
        "discard_count": len(discard) if isinstance(discard, list) else 0,
    }


def compact_pokemon(pokemon: Any) -> Dict[str, Any]:
    card = compact_card(pokemon)
    max_hp = pokemon_max_hp(pokemon) or int(card.get("max_hp", 0) or 0)
    hp = pokemon_hp(pokemon) or max_hp
    damage = pokemon_damage(pokemon)
    energy_ids = attached_card_ids(pokemon, "energyCards")
    energies = [compact_card(cid) for cid in energy_ids]
    raw_energies = getv(pokemon, "energies", [])
    if isinstance(raw_energies, list):
        for energy in raw_energies:
            if card_id(energy) is not None and card_id(energy) not in energy_ids:
                energies.append(compact_card(energy))
    tools = [compact_card(cid) for cid in attached_card_ids(pokemon, "tools")]
    return {
        **card,
        "hp": hp,
        "max_hp": max_hp,
        "damage": damage,
        "energy_count": pokemon_energy_count(pokemon),
        "energies": energies,
        "tools": tools,
        "special_conditions": special_conditions(pokemon),
    }


def compact_card(value: Any) -> Dict[str, Any]:
    cid = card_id(value)
    if cid is None:
        if value is None:
            return {"hidden": True, "name": "Hidden card", "id": None}
        return {"hidden": False, "name": str(value), "id": None}
    info = get_db().get_card(cid)
    return card_info_dict(info, cid)


def card_info_dict(info: Optional[CardInfo], cid: int) -> Dict[str, Any]:
    name = info.name if info else str(cid)
    return {
        "id": cid,
        "name": name,
        "type": info.card_type if info else "",
        "stage": info.stage if info else "",
        "max_hp": info.hp if info else 0,
        "ex": bool(info.ex) if info else False,
        "mega_ex": bool(info.mega_ex) if info else False,
        "prize_value": info.prize_value if info else 1,
        "energy_type": info.energy_type if info else "",
    }


def special_conditions(pokemon: Any) -> List[str]:
    names = []
    for key in ("asleep", "burned", "confused", "paralyzed", "poisoned"):
        if bool(getv(pokemon, key, False)):
            names.append(key)
    return names


def normalize_logs(logs: Any) -> List[str]:
    if not isinstance(logs, list):
        return []
    normalized = []
    for log in logs[-20:]:
        if isinstance(log, str):
            normalized.append(log)
        else:
            normalized.append(json.dumps(log, ensure_ascii=True, sort_keys=True))
    return normalized


def current_turn_player_index(current: Any) -> Optional[int]:
    turn = int_or(getv(current, "turn", 0), 0)
    first_player = int_or(getv(current, "firstPlayer", -1), -1)
    if turn <= 0 or first_player not in (0, 1):
        return None
    return first_player if turn % 2 == 1 else 1 - first_player


def _clean_choice(value: Any) -> List[int]:
    if not isinstance(value, list):
        return []
    clean: List[int] = []
    for item in value:
        try:
            clean.append(int(item))
        except (TypeError, ValueError):
            pass
    return clean


def synthetic_mirror_trace() -> List[Dict[str, Any]]:
    from agent import agent as our_agent
    from run_local import action_is_legal

    players = [
        make_player(active=[], bench=[], hand=[833, 59, 227, 1086, 1227, 1092, 7], deck_count=46),
        make_player(active=[make_pokemon(833)], bench=[make_pokemon(227)], hand=[], deck_count=46),
    ]
    rows: List[Dict[str, Any]] = []
    scenarios = [
        make_obs(
            0,
            0,
            players,
            CTX_SETUP_ACTIVE,
            SELECT_CARD,
            [card_option(AREA_HAND, 0, 833), card_option(AREA_HAND, 1, 59), card_option(AREA_HAND, 2, 227)],
            1,
            1,
            ["Setup: choose an Active Pokemon."],
        ),
        make_obs(
            1,
            0,
            replace_player(players, 0, active=[make_pokemon(833)], hand=[59, 227, 1086, 1227, 1092, 7]),
            CTX_SETUP_BENCH,
            SELECT_CARD,
            [card_option(AREA_HAND, 0, 59), card_option(AREA_HAND, 1, 227)],
            0,
            2,
            ["Setup: choose any Basic Pokemon for the Bench."],
        ),
        make_obs(
            2,
            1,
            replace_player(
                players,
                0,
                active=[make_pokemon(833)],
                bench=[make_pokemon(227), make_pokemon(59)],
                hand=[1086, 1227, 1092, 1231, 7],
            ),
            CTX_MAIN,
            SELECT_MAIN,
            [
                play_option(0, 1086),
                play_option(1, 1227),
                play_option(2, 1092),
                play_option(3, 1231),
                attach_option(4, 7, AREA_ACTIVE, 0),
                end_option(),
            ],
            1,
            1,
            ["Turn 1: Bench is not full. Buddy-Buddy Poffin should be a high-priority setup action."],
        ),
        make_search_obs(
            3,
            1,
            replace_player(
                players,
                0,
                active=[make_pokemon(833)],
                bench=[make_pokemon(227), make_pokemon(59)],
                hand=[1227, 1092, 1231, 7],
            ),
            source_id=1086,
            source_name="Buddy-Buddy Poffin",
            deck_cards=[227, 59, 833, 140, 141, 229],
            context=CTX_TO_BENCH,
            max_count=2,
            log="Buddy-Buddy Poffin: choose up to two Basic Pokemon with 70 HP or less to put on Bench.",
        ),
        make_obs(
            4,
            1,
            replace_player(
                players,
                0,
                active=[make_pokemon(833)],
                bench=[make_pokemon(227), make_pokemon(59), make_pokemon(227), make_pokemon(833)],
                hand=[1227, 1121, 1079, 7, 8, 5],
            ),
            CTX_MAIN,
            SELECT_MAIN,
            [
                play_option(0, 1227),
                play_option(1, 1121),
                play_option(2, 1079),
                attach_option(3, 7, AREA_BENCH, 0),
                attach_option(4, 8, AREA_BENCH, 0),
                attach_option(5, 5, AREA_BENCH, 0),
                end_option(),
            ],
            1,
            1,
            ["After Poffin: use Supporter/search or attach to the highest Hydreigon-line target before ending."],
        ),
        make_search_obs(
            5,
            1,
            replace_player(
                players,
                0,
                active=[make_pokemon(833)],
                bench=[make_pokemon(227, energy_cards=[7]), make_pokemon(59), make_pokemon(227), make_pokemon(833)],
                hand=[1079, 7, 8, 5],
            ),
            source_id=1227,
            source_name="Lillie's Determination",
            deck_cards=[229, 772, 1079, 1198, 1121, 1231],
            context=CTX_TO_HAND,
            max_count=1,
            log="Lillie's Determination: choose the setup card that advances the full board.",
        ),
        make_obs(
            6,
            5,
            [
                make_player(
                    active=[],
                    bench=[
                        make_pokemon(229, hp=210, energy_cards=[7, 8, 5]),
                        make_pokemon(772, hp=350, energy_cards=[7]),
                        make_pokemon(834),
                        make_pokemon(227),
                    ],
                    hand=[1231, 1121, 1092, 7],
                    deck_count=33,
                    prize_count=4,
                    discard=[833],
                ),
                make_player(active=[make_pokemon(229, energy_cards=[7, 8, 5])], bench=[make_pokemon(59), make_pokemon(227)], deck_count=35, prize_count=4),
            ],
            CTX_TO_ACTIVE,
            SELECT_CARD,
            [
                card_option(AREA_BENCH, 0, 229),
                card_option(AREA_BENCH, 1, 772),
                card_option(AREA_BENCH, 2, 834),
                card_option(AREA_BENCH, 3, 227),
            ],
            1,
            1,
            ["Our Active was Knocked Out. Promote the best attacker or pivot."],
        ),
        make_obs(
            7,
            5,
            [
                make_player(
                    active=[make_pokemon(229, hp=210, energy_cards=[7, 8, 5])],
                    bench=[make_pokemon(772, hp=350, energy_cards=[7]), make_pokemon(834), make_pokemon(227)],
                    hand=[1231, 1121, 1092, 7],
                    deck_count=33,
                    prize_count=4,
                    discard=[833],
                ),
                make_player(active=[make_pokemon(229, energy_cards=[7, 8, 5])], bench=[make_pokemon(59), make_pokemon(227)], deck_count=35, prize_count=4),
            ],
            CTX_MAIN,
            SELECT_MAIN,
            [play_option(0, 1231), play_option(1, 1121), play_option(2, 1092), attach_option(3, 7, AREA_ACTIVE, 0), end_option()],
            1,
            1,
            ["Your Pokemon was Knocked Out during opponent last turn. Prioritize finding Fezandipiti ex with Dawn, Ultra Ball, or Secret Box."],
        ),
        make_search_obs(
            8,
            5,
            [
                make_player(
                    active=[make_pokemon(229, hp=210, energy_cards=[7, 8, 5])],
                    bench=[make_pokemon(772, hp=350, energy_cards=[7]), make_pokemon(834), make_pokemon(227)],
                    hand=[1121, 1092, 7],
                    deck_count=33,
                    prize_count=4,
                    discard=[833, 1231],
                ),
                make_player(active=[make_pokemon(229, energy_cards=[7, 8, 5])], bench=[make_pokemon(59), make_pokemon(227)], deck_count=35, prize_count=4),
            ],
            source_id=1231,
            source_name="Dawn",
            deck_cards=[140, 141, 229, 772, 7],
            context=CTX_TO_HAND,
            max_count=1,
            log="Your Pokemon was Knocked Out during opponent last turn. Dawn: choose Fezandipiti ex.",
        ),
        make_obs(
            9,
            5,
            [
                make_player(
                    active=[make_pokemon(229, hp=210, energy_cards=[7, 8, 5])],
                    bench=[make_pokemon(772, hp=350, energy_cards=[7]), make_pokemon(834), make_pokemon(227)],
                    hand=[140, 1121, 1092, 7],
                    deck_count=32,
                    prize_count=4,
                    discard=[833, 1231],
                ),
                make_player(active=[make_pokemon(229, energy_cards=[7, 8, 5])], bench=[make_pokemon(59), make_pokemon(227)], deck_count=35, prize_count=4),
            ],
            CTX_MAIN,
            SELECT_MAIN,
            [play_option(0, 140), play_option(1, 1121), play_option(2, 1092), attach_option(3, 7, AREA_ACTIVE, 0), end_option()],
            1,
            1,
            ["Your Pokemon was Knocked Out during opponent last turn. Fezandipiti ex is in hand; put it down so Flip the Script is available."],
        ),
        make_obs(
            10,
            5,
            [
                make_player(
                    active=[make_pokemon(229, hp=210, energy_cards=[7, 8, 5])],
                    bench=[make_pokemon(772, hp=350, energy_cards=[7]), make_pokemon(834), make_pokemon(227), make_pokemon(140)],
                    hand=[1121, 1092, 7],
                    deck_count=32,
                    prize_count=4,
                    discard=[833, 1231],
                ),
                make_player(active=[make_pokemon(229, energy_cards=[7, 8, 5])], bench=[make_pokemon(59), make_pokemon(227)], deck_count=35, prize_count=4),
            ],
            CTX_MAIN,
            SELECT_MAIN,
            [ability_option(AREA_BENCH, 3, 140), play_option(0, 1121), play_option(1, 1092), attach_option(2, 7, AREA_ACTIVE, 0), end_option()],
            1,
            1,
            ["Your Pokemon was Knocked Out during opponent last turn. Use Fezandipiti ex Flip the Script before attacking or ending."],
        ),
    ]

    for step, obs in enumerate(scenarios):
        action = our_agent(obs)
        legal, legal_error = action_is_legal(obs, action)
        rows.append(
            {
                "label": "mirror_demo",
                "step": step,
                "player_index": int_or(getv(obs.get("current", {}), "yourIndex", 0), 0),
                "agent_label": "mirror-0",
                "elapsed_sec": 0,
                "action": action,
                "legal": legal,
                "legal_error": legal_error,
                "obs": obs,
                "demo": True,
            }
        )
    return rows


def make_obs(
    step: int,
    turn: int,
    players: List[Dict[str, Any]],
    context: int,
    select_type: int,
    options: List[Dict[str, Any]],
    min_count: int,
    max_count: int,
    logs: List[str],
) -> Dict[str, Any]:
    del step
    return {
        "logs": logs,
        "current": {
            "yourIndex": 0,
            "result": -1,
            "turn": turn,
            "firstPlayer": 0,
            "players": players,
            "stadium": [],
        },
        "select": {
            "type": select_type,
            "context": context,
            "option": options,
            "minCount": min_count,
            "maxCount": max_count,
        },
    }


def make_search_obs(
    step: int,
    turn: int,
    players: List[Dict[str, Any]],
    source_id: int,
    source_name: str,
    deck_cards: List[int],
    context: int,
    max_count: int,
    log: str,
) -> Dict[str, Any]:
    options = [card_option(AREA_DECK, idx, cid) for idx, cid in enumerate(deck_cards)]
    obs = make_obs(step, turn, players, context, SELECT_CARD, options, 0, max_count, [log])
    obs["select"]["sourceCardId"] = source_id
    obs["select"]["sourceName"] = source_name
    obs["select"]["deck"] = list(deck_cards)
    return obs


def make_player(
    active: Optional[List[Dict[str, Any]]] = None,
    bench: Optional[List[Dict[str, Any]]] = None,
    hand: Optional[List[int]] = None,
    deck_count: int = 40,
    prize_count: int = 6,
    discard: Optional[List[int]] = None,
) -> Dict[str, Any]:
    return {
        "active": active if active is not None else [],
        "bench": bench if bench is not None else [],
        "hand": list(hand or []),
        "handCount": len(hand or []),
        "deckCount": deck_count,
        "prize": [None] * prize_count,
        "discard": list(discard or []),
        "benchMax": 5,
    }


def replace_player(players: List[Dict[str, Any]], player_index: int, **updates: Any) -> List[Dict[str, Any]]:
    new_players = [dict(player) for player in players]
    player = dict(new_players[player_index])
    for key, value in updates.items():
        player[key] = value
    if "hand" in updates:
        player["handCount"] = len(updates["hand"])
    new_players[player_index] = player
    return new_players


def make_pokemon(card_id_value: int, hp: Optional[int] = None, energy_cards: Optional[List[int]] = None) -> Dict[str, Any]:
    info = get_db().get_card(card_id_value)
    max_hp = info.hp if info else 0
    return {
        "id": card_id_value,
        "cardId": card_id_value,
        "hp": hp if hp is not None else max_hp,
        "maxHp": max_hp,
        "energyCards": list(energy_cards or []),
        "tools": [],
        "preEvolution": [],
    }


def card_option(area: int, index: int, card_id_value: int) -> Dict[str, Any]:
    return {"type": OPT_CARD, "area": area, "index": index, "cardId": card_id_value}


def play_option(hand_index: int, card_id_value: int) -> Dict[str, Any]:
    return {"type": OPT_PLAY, "area": AREA_HAND, "index": hand_index, "cardId": card_id_value}


def attach_option(hand_index: int, card_id_value: int, target_area: int, target_index: int) -> Dict[str, Any]:
    return {
        "type": OPT_ATTACH,
        "area": AREA_HAND,
        "index": hand_index,
        "cardId": card_id_value,
        "inPlayArea": target_area,
        "inPlayIndex": target_index,
    }


def ability_option(area: int, index: int, card_id_value: int) -> Dict[str, Any]:
    return {"type": OPT_ABILITY, "area": area, "index": index, "cardId": card_id_value}


def end_option() -> Dict[str, Any]:
    return {"type": OPT_END, "label": "END"}


def render_html(replay: Dict[str, Any]) -> str:
    payload = json.dumps(replay, ensure_ascii=True).replace("</", "<\\/")
    template = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PTCG Replay Inspector</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f8;
      --ink: #202124;
      --muted: #68707a;
      --line: #d7dbe0;
      --card: #ffffff;
      --accent: #2e7d6b;
      --danger: #d84d32;
      --gold: #f2c14e;
      --violet: #6a5acd;
      --soft: #e8f2ef;
      --shadow: 0 1px 5px rgba(32, 33, 36, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: 0;
    }}
    button, select, input {{
      font: inherit;
    }}
    .app {{
      min-height: 100vh;
      display: grid;
      grid-template-rows: auto 1fr;
    }}
    .topbar {{
      display: flex;
      align-items: center;
      gap: 10px;
      min-height: 58px;
      padding: 10px 14px;
      border-bottom: 1px solid var(--line);
      background: #ffffff;
      position: sticky;
      top: 0;
      z-index: 5;
    }}
    .title {{
      font-weight: 760;
      white-space: nowrap;
      margin-right: 6px;
    }}
    .meta {{
      color: var(--muted);
      font-size: 12px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      flex: 1;
    }}
    .controls {{
      display: flex;
      gap: 6px;
      align-items: center;
      flex-wrap: wrap;
      justify-content: flex-end;
    }}
    .btn {{
      border: 1px solid var(--line);
      background: #ffffff;
      color: var(--ink);
      border-radius: 6px;
      padding: 6px 9px;
      min-width: 36px;
      cursor: pointer;
    }}
    .btn:hover {{ border-color: var(--accent); }}
    .btn.primary {{
      color: #ffffff;
      background: var(--accent);
      border-color: var(--accent);
    }}
    .speed {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 6px 8px;
      background: #ffffff;
    }}
    .layout {{
      display: grid;
      grid-template-columns: minmax(160px, 220px) minmax(520px, 1fr) minmax(330px, 440px);
      gap: 10px;
      padding: 10px;
      min-height: 0;
    }}
    .panel {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 8px;
      min-height: 0;
      box-shadow: var(--shadow);
      overflow: hidden;
    }}
    .timeline {{
      display: flex;
      flex-direction: column;
      min-height: 0;
    }}
    .panel-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      padding: 9px 10px;
      border-bottom: 1px solid var(--line);
      font-size: 13px;
      font-weight: 720;
    }}
    .timeline-list {{
      overflow: auto;
      padding: 6px;
    }}
    .step-row {{
      width: 100%;
      border: 1px solid transparent;
      background: transparent;
      text-align: left;
      border-radius: 6px;
      padding: 7px;
      margin-bottom: 4px;
      cursor: pointer;
      display: grid;
      gap: 2px;
    }}
    .step-row.active {{
      border-color: var(--accent);
      background: var(--soft);
    }}
    .step-row.bad {{
      border-color: var(--danger);
    }}
    .step-main {{
      font-size: 13px;
      font-weight: 690;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .step-sub {{
      color: var(--muted);
      font-size: 11px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .board-panel {{
      min-height: 0;
      display: flex;
      flex-direction: column;
    }}
    .board {{
      display: grid;
      grid-template-rows: minmax(220px, 1fr) auto minmax(250px, 1.12fr);
      gap: 8px;
      min-height: 0;
      padding: 10px;
      overflow: auto;
    }}
    .player-zone {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px;
      background: #fbfcfd;
      display: grid;
      grid-template-rows: auto 1fr auto;
      gap: 8px;
      min-height: 210px;
    }}
    .player-zone.current {{
      border-color: var(--accent);
      background: #f7fffc;
    }}
    .zone-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: var(--muted);
    }}
    .zone-title {{
      color: var(--ink);
      font-weight: 760;
    }}
    .counters {{
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }}
    .pill {{
      border: 1px solid var(--line);
      background: #ffffff;
      border-radius: 999px;
      padding: 2px 7px;
      font-size: 11px;
      color: var(--muted);
      white-space: nowrap;
    }}
    .field-row {{
      display: grid;
      grid-template-columns: minmax(130px, 170px) 1fr;
      gap: 10px;
      align-items: center;
    }}
    .active-slot {{
      min-height: 150px;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .bench {{
      display: grid;
      grid-template-columns: repeat(5, minmax(90px, 1fr));
      gap: 7px;
      align-items: stretch;
    }}
    .hand-row {{
      display: flex;
      gap: 6px;
      min-height: 56px;
      overflow-x: auto;
      padding-bottom: 2px;
    }}
    .center-strip {{
      min-height: 62px;
      display: flex;
      gap: 10px;
      align-items: center;
      justify-content: center;
      color: var(--muted);
      font-size: 12px;
    }}
    .slot-empty {{
      min-height: 92px;
      border: 1px dashed #c7ccd2;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #9198a1;
      font-size: 12px;
      background: #ffffff;
    }}
    .card {{
      min-width: 86px;
      min-height: 92px;
      border: 1px solid #cfd5dc;
      border-left: 5px solid var(--accent);
      border-radius: 8px;
      background: #ffffff;
      padding: 7px;
      display: grid;
      align-content: space-between;
      gap: 5px;
      box-shadow: 0 1px 2px rgba(32, 33, 36, 0.08);
    }}
    .card.small {{
      min-width: 86px;
      min-height: 52px;
      padding: 6px;
    }}
    .card.pokemon {{ border-left-color: var(--accent); }}
    .card.energy {{ border-left-color: var(--gold); }}
    .card.trainer {{ border-left-color: var(--violet); }}
    .card.hidden {{ border-left-color: #8e959d; color: var(--muted); }}
    .card-name {{
      font-weight: 760;
      font-size: 12px;
      line-height: 1.18;
      overflow-wrap: anywhere;
    }}
    .card-meta {{
      display: flex;
      gap: 4px;
      flex-wrap: wrap;
      font-size: 10px;
      color: var(--muted);
    }}
    .tag {{
      border-radius: 999px;
      padding: 1px 5px;
      background: #eef0f2;
      white-space: nowrap;
    }}
    .tag.ex {{
      background: #fff4c2;
      color: #6d5410;
      font-weight: 720;
    }}
    .hpbar {{
      height: 6px;
      background: #e9ecef;
      border-radius: 999px;
      overflow: hidden;
    }}
    .hpfill {{
      height: 100%;
      background: var(--accent);
      width: 100%;
    }}
    .inspector {{
      display: flex;
      flex-direction: column;
      min-height: 0;
    }}
    .inspector-scroll {{
      overflow: auto;
      padding: 10px;
      display: grid;
      gap: 10px;
    }}
    .decision-box {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px;
      background: #fbfcfd;
      display: grid;
      gap: 5px;
    }}
    .reason {{
      font-weight: 740;
      line-height: 1.28;
    }}
    .thought {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
      white-space: pre-wrap;
    }}
    .section-title {{
      font-size: 12px;
      font-weight: 780;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0;
    }}
    .options {{
      display: grid;
      gap: 6px;
    }}
    .option {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 7px;
      display: grid;
      gap: 5px;
      background: #ffffff;
    }}
    .option.chosen {{
      border-color: var(--accent);
      background: var(--soft);
    }}
    .option-head {{
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 7px;
      align-items: start;
      font-size: 12px;
    }}
    .idx {{
      width: 25px;
      height: 22px;
      border-radius: 6px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: #eef0f2;
      font-weight: 760;
    }}
    .cat {{
      color: var(--muted);
      font-size: 10px;
      overflow-wrap: anywhere;
    }}
    .score {{
      font-variant-numeric: tabular-nums;
      font-weight: 760;
      color: var(--accent);
    }}
    .bar {{
      height: 5px;
      border-radius: 999px;
      background: #eef0f2;
      overflow: hidden;
    }}
    .bar > span {{
      display: block;
      height: 100%;
      background: var(--accent);
      width: 0;
    }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      font-size: 11px;
      line-height: 1.35;
      color: #34383d;
      background: #f1f3f4;
      border-radius: 8px;
      padding: 9px;
      max-height: 360px;
      overflow: auto;
    }}
    .log-list {{
      display: grid;
      gap: 5px;
      font-size: 12px;
      color: #34383d;
    }}
    .log-line {{
      border-left: 3px solid var(--line);
      padding-left: 7px;
      line-height: 1.35;
    }}
    @media (max-width: 1100px) {{
      .layout {{
        grid-template-columns: 1fr;
      }}
      .timeline-list {{
        max-height: 190px;
      }}
      .board {{
        max-height: none;
      }}
    }}
    @media (max-width: 720px) {{
      .topbar {{
        align-items: flex-start;
        flex-direction: column;
      }}
      .controls {{
        justify-content: flex-start;
      }}
      .field-row {{
        grid-template-columns: 1fr;
      }}
      .bench {{
        grid-template-columns: repeat(2, minmax(120px, 1fr));
      }}
    }}
  </style>
</head>
<body>
  <div class="app">
    <header class="topbar">
      <div class="title">PTCG Replay Inspector</div>
      <div class="meta" id="meta"></div>
      <div class="controls">
        <button class="btn" id="first" title="First step">First</button>
        <button class="btn" id="prev" title="Previous step">Prev</button>
        <button class="btn primary" id="play" title="Play or pause">Play</button>
        <button class="btn" id="next" title="Next step">Next</button>
        <button class="btn" id="last" title="Last step">Last</button>
        <select class="speed" id="speed" title="Playback speed">
          <option value="1200">Slow</option>
          <option value="700" selected>Normal</option>
          <option value="300">Fast</option>
        </select>
      </div>
    </header>
    <main class="layout">
      <aside class="panel timeline">
        <div class="panel-head"><span>Timeline</span><span id="stepCount"></span></div>
        <div class="timeline-list" id="timeline"></div>
      </aside>
      <section class="panel board-panel">
        <div class="panel-head"><span id="boardTitle">Board</span><span id="boardStatus"></span></div>
        <div class="board" id="board"></div>
      </section>
      <aside class="panel inspector">
        <div class="panel-head"><span>Decision</span><span id="chosen"></span></div>
        <div class="inspector-scroll" id="inspector"></div>
      </aside>
    </main>
  </div>
  <script>
    window.REPLAY_DATA = __REPLAY_PAYLOAD__;
    const data = window.REPLAY_DATA;
    const frames = data.frames || [];
    let pos = 0;
    let timer = null;

    const $ = (id) => document.getElementById(id);
    const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
    const clamp = (value, lo, hi) => Math.max(lo, Math.min(hi, value));

    function cardClass(card) {{
      if (!card || card.hidden) return 'hidden';
      const type = String(card.type || '').toLowerCase();
      if (type.includes('energy')) return 'energy';
      if (type.includes('pokemon')) return 'pokemon';
      return 'trainer';
    }}

    function cardHtml(card, small=false) {{
      if (!card) return '<div class="slot-empty">Empty</div>';
      const maxHp = Number(card.max_hp || 0);
      const hp = Number(card.hp || maxHp || 0);
      const hpPct = maxHp ? clamp((hp / maxHp) * 100, 0, 100) : 100;
      const tags = [];
      if (card.stage) tags.push(`<span class="tag">${{esc(card.stage)}}</span>`);
      if (card.ex) tags.push('<span class="tag ex">ex</span>');
      if (card.mega_ex) tags.push('<span class="tag ex">Mega</span>');
      if (card.energy_count) tags.push(`<span class="tag">E ${{card.energy_count}}</span>`);
      const hpLine = maxHp ? `<span class="tag">${{hp}}/${{maxHp}} HP</span>` : '';
      const energies = (card.energies || []).map((e) => esc(e.name || e.id)).join(', ');
      return `<div class="card ${{small ? 'small' : ''}} ${{cardClass(card)}}" title="${{esc(energies)}}">` +
        `<div class="card-name">${{esc(card.name || 'Unknown')}}</div>` +
        `<div class="card-meta">${{hpLine}}${{tags.join('')}}</div>` +
        `${{maxHp ? `<div class="hpbar"><div class="hpfill" style="width:${{hpPct}}%"></div></div>` : ''}}` +
        `${{energies ? `<div class="card-meta"><span class="tag">${{energies}}</span></div>` : ''}}` +
      `</div>`;
    }}

    function playerHtml(player, frame, label) {{
      const isTurn = frame.board && frame.board.turn_player === player.index;
      const isYou = frame.board && frame.board.your_index === player.index;
      const bench = Array.from({{length: 5}}, (_, idx) => player.bench[idx] ? cardHtml(player.bench[idx]) : '<div class="slot-empty">Bench</div>').join('');
      const hand = (player.hand || []).length
        ? player.hand.map((card) => cardHtml(card, true)).join('')
        : '<span class="pill">hand hidden or empty</span>';
      return `<section class="player-zone ${{isTurn ? 'current' : ''}}">` +
        `<div class="zone-head"><div><span class="zone-title">${{esc(label)}}</span> ${{isYou ? '<span class="pill">obs view</span>' : ''}}</div>` +
        `<div class="counters"><span class="pill">Deck ${{player.deck_count}}</span><span class="pill">Prizes ${{player.prize_count}}</span><span class="pill">Hand ${{player.hand_count}}</span><span class="pill">Discard ${{player.discard_count}}</span></div></div>` +
        `<div class="field-row"><div class="active-slot">${{cardHtml(player.active)}}</div><div class="bench">${{bench}}</div></div>` +
        `<div class="hand-row">${{hand}}</div>` +
      `</section>`;
    }}

    function renderBoard(frame) {{
      const players = (frame.board && frame.board.players) || [];
      const p0 = players[0] || {{index:0, bench:[], hand:[]}};
      const p1 = players[1] || {{index:1, bench:[], hand:[]}};
      const stadium = ((frame.board && frame.board.stadium) || []).map((card) => cardHtml(card, true)).join('') || '<span class="pill">No Stadium</span>';
      $('boardTitle').textContent = `Turn ${{frame.turn}} / Step ${{frame.step}}`;
      $('boardStatus').textContent = `Player ${{frame.player_index}} acting`;
      $('board').innerHTML =
        playerHtml(p1, frame, 'Player 1 mirror') +
        `<div class="center-strip"><span class="pill">Stadium</span>${{stadium}}<span class="pill">Context ${{frame.context}}</span><span class="pill">Select ${{frame.select_type}}</span></div>` +
        playerHtml(p0, frame, 'Player 0 mirror');
    }}

    function renderTimeline() {{
      $('stepCount').textContent = `${{frames.length}} steps`;
      $('timeline').innerHTML = frames.map((frame, idx) => {{
        const chosen = (frame.chosen || []).join(', ');
        const best = (frame.options || []).find((option) => option.chosen) || (frame.options || [])[0] || {{}};
        return `<button class="step-row ${{idx === pos ? 'active' : ''}} ${{frame.legal === false ? 'bad' : ''}}" data-idx="${{idx}}">` +
          `<div class="step-main">#${{frame.step}} P${{frame.player_index}} ${{esc(best.category || '')}}</div>` +
          `<div class="step-sub">choice [${{esc(chosen)}}] ${{esc(best.card_name || best.attack_name || best.label || '')}}</div>` +
        `</button>`;
      }}).join('');
      document.querySelectorAll('.step-row').forEach((node) => node.addEventListener('click', () => go(Number(node.dataset.idx))));
    }}

    function renderOptions(frame) {{
      const scores = (frame.options || []).map((option) => Math.abs(Number(option.score || 0)));
      const maxScore = Math.max(1, ...scores);
      return `<div class="options">` + (frame.options || []).map((option) => {{
        const width = clamp((Math.abs(Number(option.score || 0)) / maxScore) * 100, 2, 100);
        const title = option.card_name || option.attack_name || option.label || '';
        return `<div class="option ${{option.chosen ? 'chosen' : ''}}">` +
          `<div class="option-head"><span class="idx">${{option.index}}</span><div><strong>${{esc(title)}}</strong><div class="cat">${{esc(option.category)}} / ${{esc(option.label)}}</div></div><span class="score">${{Number(option.score || 0).toFixed(1)}}</span></div>` +
          `<div class="bar"><span style="width:${{width}}%"></span></div>` +
          `${{option.reason ? `<div class="thought">${{esc(option.reason)}}</div>` : ''}}` +
        `</div>`;
      }}).join('') + `</div>`;
    }}

    function renderInspector(frame) {{
      $('chosen').textContent = `chosen [${{(frame.chosen || []).join(', ')}}]`;
      const logs = (frame.logs || []).length ? frame.logs.map((line) => `<div class="log-line">${{esc(line)}}</div>`).join('') : '<span class="pill">No logs</span>';
      const roundPlan = frame.round_plan && Object.keys(frame.round_plan).length ? JSON.stringify(frame.round_plan, null, 2) : '';
      $('inspector').innerHTML =
        `<div class="decision-box"><div class="section-title">Chosen Reason</div><div class="reason">${{esc(frame.reason || 'No reason')}}</div>${{frame.thought_process ? `<div class="thought">${{esc(frame.thought_process)}}</div>` : ''}}</div>` +
        `<div><div class="section-title">Legal Options</div>${{renderOptions(frame)}}</div>` +
        `<div><div class="section-title">Logs</div><div class="log-list">${{logs}}</div></div>` +
        `${{roundPlan ? `<div><div class="section-title">Round Plan</div><pre>${{esc(roundPlan)}}</pre></div>` : ''}}` +
        `<div><div class="section-title">Raw Observation</div><pre>${{esc(JSON.stringify(frame.raw_obs, null, 2))}}</pre></div>`;
    }}

    function render() {{
      if (!frames.length) {{
        $('meta').textContent = 'No frames found.';
        return;
      }}
      const frame = frames[pos];
      $('meta').textContent = `${{data.source || ''}} | generated ${{data.generated_at || ''}}`;
      renderTimeline();
      renderBoard(frame);
      renderInspector(frame);
    }}

    function go(nextPos) {{
      pos = clamp(nextPos, 0, Math.max(0, frames.length - 1));
      render();
    }}

    function playPause() {{
      if (timer) {{
        clearInterval(timer);
        timer = null;
        $('play').textContent = 'Play';
        return;
      }}
      $('play').textContent = 'Pause';
      timer = setInterval(() => {{
        if (pos >= frames.length - 1) {{
          playPause();
          return;
        }}
        go(pos + 1);
      }}, Number($('speed').value || 700));
    }}

    $('first').addEventListener('click', () => go(0));
    $('prev').addEventListener('click', () => go(pos - 1));
    $('next').addEventListener('click', () => go(pos + 1));
    $('last').addEventListener('click', () => go(frames.length - 1));
    $('play').addEventListener('click', playPause);
    document.addEventListener('keydown', (event) => {{
      if (event.key === 'ArrowLeft') go(pos - 1);
      if (event.key === 'ArrowRight') go(pos + 1);
      if (event.key === ' ') {{
        event.preventDefault();
        playPause();
      }}
    }});
    render();
  </script>
</body>
</html>
"""
    template = template.replace("{{", "{").replace("}}", "}")
    return template.replace("__REPLAY_PAYLOAD__", payload)


if __name__ == "__main__":
    raise SystemExit(main())
