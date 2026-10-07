"""Render an original aggregate-data figure; no game/card artwork is used."""

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


def main():
    base = Path(__file__).resolve().parent
    with (base / "data/turn_metrics.csv").open(encoding="utf-8", newline="") as stream:
        turns = list(csv.DictReader(stream))
    report = json.loads((base / "data/audit_summary.json").read_text(encoding="utf-8"))
    battle15 = {int(t["turn"]): t for t in turns if t["match_id"].startswith("battle15_")}
    comparison = report["imported_1_3_vs_1_2"]
    if not battle15 or not comparison["decided_games"]:
        raise ValueError("Figure requires battle 15 and the imported version comparison")

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    figure, axes = plt.subplots(2, 1, figsize=(11, 6.8), gridspec_kw={"height_ratios": [1.15, 1]})
    figure.subplots_adjust(left=0.1, right=0.97, bottom=0.17, top=0.89, hspace=0.8)
    figure.suptitle("Legal decisions do not guarantee productive play", x=0.1, ha="left", fontsize=17, weight="bold")

    ax = axes[0]
    for turn in range(12, 27):
        data = battle15.get(turn)
        if data is None:
            color, hatch = "#ececec", "//"
        elif data["pass_only"] == "True":
            color, hatch = "#ac394c", ""
        else:
            color, hatch = "#16867d", ""
        ax.barh(0, 0.9, left=turn - 0.45, height=0.65, color=color, hatch=hatch)
    ax.set_title("A. Battle 15: main-turn actions, engine turns 12-26", loc="left", fontsize=12, pad=15)
    ax.set_xticks(range(12, 27))
    ax.set_xlim(11.4, 26.6)
    ax.set_ylim(-0.6, 0.6)
    ax.set_yticks([])
    ax.set_xlabel("Engine turn (players alternate)")
    ax.legend(handles=[Patch(color="#ac394c", label="Only END selected"),
                       Patch(color="#16867d", label="Other main action(s), then END")],
              loc="upper left", bbox_to_anchor=(0, -0.4), ncol=2, frameon=False, fontsize=10)

    ax = axes[1]
    wins, games = comparison["wins_1_3"], comparison["decided_games"]
    estimate = 100 * wins / games
    lo, hi = [100 * value for value in comparison["wilson95"]]
    ax.errorbar(estimate, 0, xerr=[[estimate - lo], [hi - estimate]], fmt="o",
                color="#343a40", ecolor="#343a40", capsize=7, markersize=8, linewidth=2)
    ax.axvline(50, linestyle=":", color="#a0a0a0", linewidth=1)
    ax.text(estimate, 0.25, "{}/{} wins ({:.1f}%)".format(wins, games, estimate), ha="center", fontsize=11)
    ax.text(lo, -0.27, "{:.1f}%".format(lo), ha="center", fontsize=10)
    ax.text(hi, -0.27, "{:.1f}%".format(hi), ha="center", fontsize=10)
    ax.set_title("B. Imported palfingon 1.3 vs 1.2: small-sample uncertainty", loc="left", fontsize=12, pad=15)
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.5, 0.6)
    ax.set_yticks([])
    ax.set_xticks(range(0, 101, 20))
    ax.set_xlabel("Observed win percentage and illustrative 95% Wilson interval")
    for ax in axes:
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color("#d0d0d0")

    figure.text(0.1, 0.075,
                "Pass-only is descriptive, not a confirmed mistake. The three-game sample is not controlled;",
                fontsize=9, color="#555555")
    figure.text(0.1, 0.048,
                "1.3 went first in all three games. Wilson uncertainty assumes independent Bernoulli outcomes.",
                fontsize=9, color="#555555")
    output = base / "data/evidence_figure.png"
    figure.savefig(output, dpi=180, facecolor="white")
    plt.close(figure)
    print(output)


if __name__ == "__main__":
    main()
