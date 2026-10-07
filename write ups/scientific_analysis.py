"""Exact deck combinatorics and descriptive policy diagnostics from saved data."""

import csv
import hashlib
import itertools
import json
import math
import zipfile
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

from analyze_writeup_data import agent_label, main_turns, selection_status, write_csv


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path(__file__).resolve().parent / "scientific_data"


def choose(n, k):
    return math.comb(n, k) if 0 <= k <= n else 0


def at_least_each(total, groups, draws):
    """Exact probability of >=1 in every disjoint group, by inclusion-exclusion."""
    if not 0 <= draws <= total or any(k < 0 for k in groups) or sum(groups) > total:
        raise ValueError("Invalid population, disjoint groups, or sample size")
    numerator = 0
    for size in range(len(groups) + 1):
        for subset in itertools.combinations(groups, size):
            numerator += (-1) ** size * choose(total - sum(subset), draws)
    return Fraction(numerator, choose(total, draws))


def target_count_given_basic(total, basics, targets, draws, at_least):
    """Targets and Basics are disjoint; condition on at least one Basic."""
    denominator = choose(total, draws) - choose(total - basics, draws)
    if not denominator or basics + targets > total:
        raise ValueError("Impossible conditioning event or overlapping groups")
    numerator = sum(choose(targets, k) * (
        choose(total - targets, draws - k) - choose(total - targets - basics, draws - k))
        for k in range(at_least, min(targets, draws) + 1))
    return Fraction(numerator, denominator)


def energy_deficit(required, attached):
    """Typed Basic Energy only; does not infer legal attacks or special effects."""
    counts = Counter(attached)
    return sum(max(0, need - counts[kind]) for kind, need in required.items())


def trace_comparison(row):
    select = (row.get("observation") or {}).get("select") or {}
    options = select.get("option", [])
    trace = row.get("agent_trace") or {}
    if (select.get("context") != 0 or len(options) < 2 or selection_status(row) != "valid"
            or len(row.get("selected_indexes", [])) != 1):
        return None
    entries = trace.get("legal_options")
    if not isinstance(entries, list) or len(entries) != len(options):
        return None
    scores = {}
    for entry in entries:
        index, score = entry.get("index"), entry.get("score")
        if (type(index) is not int or index in scores or type(score) not in (int, float)
                or not math.isfinite(score)):
            return None
        scores[index] = score
    if set(scores) != set(range(len(options))) or trace.get("chosen_index") != row["selected_indexes"]:
        return None
    selected = row["selected_indexes"][0]
    maximum = max(scores.values())
    best = min(i for i, value in scores.items() if value == maximum)
    by_index = {e["index"]: e for e in entries}

    def name(index):
        entry = by_index[index]
        return entry.get("card_name") or entry.get("attack_name") or entry.get("category", "unknown")

    return {
        "match_id": row["match_id"], "decision": row["decision_index"], "turn": row["turn"],
        "agent": agent_label(row["agent_id"]), "options": len(options),
        "selected": selected, "selected_name": name(selected), "selected_score": scores[selected],
        "selected_type": options[selected].get("type"),
        "top": best, "top_name": name(best), "top_score": maximum,
        "score_gap": maximum - scores[selected],
        "discordant": maximum - scores[selected] > 1e-9,
        "rank_loss": sum(value > scores[selected] + 1e-9 for value in scores.values()) / (len(options) - 1),
    }


def transition_counts(turns):
    grouped = defaultdict(list)
    for turn in turns:
        grouped[(turn["match_id"], turn["player"])].append(turn)
    counts = Counter({"00": 0, "01": 0, "10": 0, "11": 0})
    for group in grouped.values():
        group.sort(key=lambda t: t["turn"])
        for before, after in zip(group, group[1:]):
            if after["turn"] == before["turn"] + 2 and before["verified"] and after["verified"]:
                counts[str(int(before["pass_only"])) + str(int(after["pass_only"]))] += 1
    return dict(counts)


def run():
    deck_path = ROOT / "palfingon/deck.csv"
    deck = Counter(int(line[0]) for line in csv.reader(deck_path.open()) if line)
    if sum(deck.values()) != 60:
        raise ValueError("Expected the supplied 60-card list")
    sources = {deck_path, Path(__file__).resolve(), Path(__file__).with_name("analyze_writeup_data.py")}
    cards_path, attacks_path = ROOT / "palfingon/cabt_cards.json", ROOT / "palfingon/cabt_attacks.json"
    sources.update((cards_path, attacks_path))
    cards = {c["cardId"]: c for c in json.loads(cards_path.read_text())["cards"]}
    attacks = {a["attackId"]: a for a in json.loads(attacks_path.read_text())["attacks"]}
    if cards[3]["energyType"] != 3 or cards[4]["energyType"] != 4:
        raise ValueError("Energy ID/type mapping changed")
    if attacks[134]["energies"] != [3] or attacks[1302]["energies"] != [3, 4, 4]:
        raise ValueError("Audited attack costs changed")
    cross_deck = []
    for folder, focal in (("hydreigen", 227), ("Palaking", 105), ("NsZoroark", 292), ("palfingon", 105)):
        path = ROOT / folder / "deck.csv"
        sources.add(path)
        counts = Counter(int(row[0]) for row in csv.reader(path.open()) if row)
        total = sum(counts.values())
        basics = sum(count for cid, count in counts.items() if cards[cid]["basic"])
        if total != 60:
            raise ValueError("Cross-deck comparison requires 60 cards")
        legal_opening = at_least_each(total, [basics], 7)
        cross_deck.append({"workspace": folder, "cards": total, "basics": basics,
                           "focal_basic": cards[focal]["name"], "focal_copies": counts[focal],
                           "initial_mulligan_probability": float(1 - legal_opening),
                           "focal_given_valid_probability": float(at_least_each(total, [counts[focal]], 7) / legal_opening)})
    # Verify archived imported versions used for opening observations have this same list.
    for version in ("1.1", "1.2", "1.3"):
        archive = ROOT / "palfingon" / ("submission palfingon " + version + ".zip")
        sources.add(archive)
        with zipfile.ZipFile(archive) as handle:
            if Counter(map(int, handle.read("deck.csv").decode().splitlines())) != deck:
                raise ValueError("Archived deck composition differs")

    basic_count = sum(count for cid, count in deck.items() if cards[cid]["basic"])
    valid_hand = at_least_each(60, [basic_count], 7)
    probabilities = [
        ("Initial seven contain a Basic", valid_hand, "unconditional"),
        ("Initial seven require a mulligan", 1 - valid_hand, "unconditional"),
        ("Finizen in accepted seven", at_least_each(60, [deck[105]], 7) / valid_hand, "given Basic >=1"),
        ("Finizen and Dratini in accepted seven", at_least_each(60, [deck[105], deck[902]], 7) / valid_hand, "given Basic >=1"),
        ("Finizen and Water in accepted seven", at_least_each(60, [deck[105], deck[3]], 7) / valid_hand, "given Basic >=1"),
        ("Finizen, Dratini, Water in accepted seven", at_least_each(60, [deck[105], deck[902], deck[3]], 7) / valid_hand, "given Basic >=1"),
        ("Poffin in accepted seven", target_count_given_basic(60, basic_count, deck[1086], 7, 1), "given Basic >=1"),
        ("At least two Palafin ex in accepted seven", target_count_given_basic(60, basic_count, deck[107], 7, 2), "given Basic >=1"),
    ]
    probability_rows = [{"event": name, "probability": float(p), "numerator": p.numerator,
                         "denominator": p.denominator, "condition": condition} for name, p, condition in probabilities]

    traces, all_turns, snapshots, openings = [], [], [], []
    agent_summary = defaultdict(Counter)
    all_decisions = 0
    episodes = ROOT / "cabt-local-simulator/data/episodes"
    for summary_path in sorted((ROOT / "cabt-local-simulator/data/summaries").glob("*.json")):
        sources.add(summary_path)
        summary = json.loads(summary_path.read_text())
        path = episodes / (summary["match_id"] + ".jsonl")
        if not path.exists():
            continue
        sources.add(path)
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        all_decisions += len(rows)
        all_turns.extend(main_turns(summary["match_id"], rows))
        last_main, opening_seen = {}, set()
        for row in rows:
            label = agent_label(row.get("agent_id"))
            aggregate = agent_summary[label]
            aggregate["decisions"] += 1
            select = row["observation"].get("select") or {}
            current = row["observation"].get("current") or {}
            if select.get("context") == 0:
                aggregate["main_windows"] += 1
                last_main[(row["player"], row["turn"])] = row
            scored = trace_comparison(row)
            if scored is not None:
                traces.append(scored)
                aggregate["scorable_main_windows"] += 1
                aggregate["discordant"] += scored["discordant"]
                aggregate["discordant_end"] += scored["discordant"] and scored["selected_type"] == 14
                aggregate["discordant_attack"] += scored["discordant"] and scored["selected_type"] == 13
            player = row["player"]
            if (label.startswith("import:submission-palfingon-") and player not in opening_seen
                    and current.get("turn") == 0 and select.get("context") == 1):
                opening_seen.add(player)
                me = current["players"][player]
                hand = me.get("hand") or []
                if len(hand) == 7 and not me.get("active") and not me.get("bench"):
                    hand_counts = Counter(card["id"] for card in hand)
                    if any(hand_counts[cid] > deck[cid] for cid in hand_counts):
                        raise ValueError("Opening inconsistent with verified deck")
                    openings.append({
                        "match_id": row["match_id"], "player": player, "agent": label,
                        "finizen": hand_counts[105] > 0,
                        "finizen_dratini": hand_counts[105] > 0 and hand_counts[902] > 0,
                        "finizen_water": hand_counts[105] > 0 and hand_counts[3] > 0,
                        "finizen_dratini_water": all(hand_counts[i] > 0 for i in (105, 902, 3)),
                        "poffin": hand_counts[1086] > 0,
                        "multiple_palafin_ex": hand_counts[107] >= 2,
                    })
        for (player, turn), row in sorted(last_main.items()):
            me = row["observation"]["current"]["players"][player]
            label = agent_label(row["agent_id"])
            for pokemon in (me.get("active") or []) + (me.get("bench") or []):
                if pokemon.get("id") not in (107, 904):
                    continue
                energies = pokemon.get("energies")
                if not isinstance(energies, list) or not all(type(x) is int for x in energies):
                    raise ValueError("Unrecognized Energy representation in audited attacker")
                cid = pokemon["id"]
                required = {3: 1} if cid == 107 else {3: 1, 4: 2}
                snapshots.append({
                    "match_id": row["match_id"], "agent": label, "player": player, "turn": turn,
                    "card_id": cid, "instance": pokemon.get("serial"),
                    "water": energies.count(3), "lightning": energies.count(4),
                    "total_energy": len(energies), "typed_deficit": energy_deficit(required, energies),
                    "palafin_ex_overcap": cid == 107 and len(energies) > 1,
                    "palafin_ex_wrong_type": cid == 107 and any(e != 3 for e in energies),
                })
    # Keep statistical units explicit: repeated sightings of one Pokemon are not new subjects.
    battle15 = [t for t in all_turns if t["match_id"].startswith("battle15_")]
    aggregate_rows = []
    for label, counts in sorted(agent_summary.items()):
        aggregate_rows.append({"agent": label, **{key: counts[key] for key in (
            "decisions", "main_windows", "scorable_main_windows", "discordant", "discordant_end", "discordant_attack")}})
    energy_rows = []
    for label in sorted({row["agent"] for row in snapshots}):
        relevant = [r for r in snapshots if r["agent"] == label and r["card_id"] == 107]
        energy_rows.append({"agent": label, "palafin_ex_snapshots": len(relevant),
                            "overcap_snapshots": sum(r["palafin_ex_overcap"] for r in relevant),
                            "wrong_type_snapshots": sum(r["palafin_ex_wrong_type"] for r in relevant),
                            "energy_ready_snapshots": sum(r["typed_deficit"] == 0 for r in relevant)})
    result = {
        "design": "Descriptive historical analysis and exact deck combinatorics; no new games",
        "decisions": all_decisions, "deck_counts": dict(sorted(deck.items())), "basic_count": basic_count,
        "cross_deck_openings": cross_deck,
        "opening_probabilities": probability_rows, "opening_sample_size": len(openings),
        "observed_opening_events": {key: sum(row[key] for row in openings) for key in (
            "finizen", "finizen_dratini", "finizen_water", "finizen_dratini_water", "poffin", "multiple_palafin_ex")},
        "trace_aggregates": aggregate_rows,
        "battle15_transitions": transition_counts(battle15),
        "energy_aggregates": energy_rows,
        "source_manifest": [{"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                            for path in sorted(sources)],
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT / "cross_deck_openings.csv", cross_deck)
    write_csv(OUTPUT / "deck_counts.csv", [{"card_id": cid, "name": cards[cid]["name"],
                                           "count": count, "basic": cards[cid]["basic"],
                                           "hp": cards[cid]["hp"]} for cid, count in sorted(deck.items())])
    for filename, rows in [("opening_probabilities", probability_rows), ("opening_observations", openings),
                           ("score_discordance", traces), ("trace_aggregates", aggregate_rows),
                           ("attacker_snapshots", snapshots), ("energy_aggregates", energy_rows)]:
        write_csv(OUTPUT / (filename + ".csv"), rows)
    (OUTPUT / "scientific_summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "source_manifest"}, indent=2))


if __name__ == "__main__":
    run()
