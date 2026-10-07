from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from core.trajectory_lessons import ALL_LESSONS


@dataclass(frozen=True)
class ExpertTrajectoryEvent:
    phase: str
    observations: List[str]
    reusable_rules: List[str]


@dataclass(frozen=True)
class ExpertTrajectory:
    name: str
    source_path: str
    lessons: List[dict]
    events: List[ExpertTrajectoryEvent]


EXPERT_TRAJECTORY_EVENTS = [
    ExpertTrajectoryEvent(
        phase="opening",
        observations=[
            "Toxel Active, Deino benched immediately.",
            "Secret Box discarded expendable resources to find Poffin, Air Balloon, Lillie, and Battle Cage.",
            "Buddy-Buddy Poffin was used immediately for Deino plus Gastly.",
            "Psychic Energy went to the Hydreigon line.",
        ],
        reusable_rules=[
            "Use Poffin aggressively when Bench is weak.",
            "Secret Box may spend expendable resources when the payoff creates a strong setup package.",
            "Prioritize one each of Deino, Gastly, and Toxel before duplicate setup pieces.",
        ],
    ),
    ExpertTrajectoryEvent(
        phase="post_ko_rebuild",
        observations=[
            "Fezandipiti ex used Flip the Script immediately after our Pokemon was Knocked Out.",
            "Sacred Ash restored Toxel and Toxtricity after the Energy engine was lost.",
            "Supporter and disruption were used after board rebuilding began.",
        ],
        reusable_rules=[
            "Use Fezandipiti before Supporter on post-KO turns.",
            "Recover the Toxtricity support engine only when its ability matters; do not use it as an attacker.",
        ],
    ),
    ExpertTrajectoryEvent(
        phase="mega_gengar_transition",
        observations=[
            "Haunter evolved into Mega Gengar ex.",
            "Toxtricity used Sinister Surge to attach Darkness to Mega Gengar ex.",
            "Mega Gengar attacked with Void Gale and moved Energy to Hydreigon ex.",
        ],
        reusable_rules=[
            "Treat Mega Gengar ex as a main attacker, not a fallback.",
            "Use Toxtricity ability before pivoting into Mega Gengar when it enables Void Gale.",
            "Move Void Gale Energy to the next Hydreigon or backup attacker.",
        ],
    ),
    ExpertTrajectoryEvent(
        phase="hydreigon_closer",
        observations=[
            "Hydreigon ex used Obsidian to KO the Active and two Benched Pokemon.",
            "The multi-prize Obsidian turn created the decisive prize swing.",
        ],
        reusable_rules=[
            "Score Obsidian bench damage, not only Active damage.",
            "If Obsidian takes multiple prizes or wins, it overrides ordinary setup lines.",
        ],
    ),
    ExpertTrajectoryEvent(
        phase="late_rebuild",
        observations=[
            "After Hydreigon ex was Knocked Out, Fezandipiti, Rare Candy, Energy Recycler, Night Stretcher, Toxtricity, and manual attachment rebuilt the final attacker.",
            "The final Obsidian took the remaining prizes.",
        ],
        reusable_rules=[
            "Use Energy Recycler when several key Energy are in discard.",
            "Use Night Stretcher for exact Energy or Pokemon needed to attack.",
            "Rebuild Hydreigon through Rare Candy when it creates the next prize route.",
        ],
    ),
]


def load_expert_trajectory() -> ExpertTrajectory:
    root = Path(__file__).resolve().parents[1]
    path = root / "data" / "expert_logs" / "tristary_vs_komug_win.txt"
    return ExpertTrajectory(
        name="tristary_vs_komug_win",
        source_path=str(path),
        lessons=list(ALL_LESSONS),
        events=list(EXPERT_TRAJECTORY_EVENTS),
    )


def read_expert_log() -> str:
    trajectory = load_expert_trajectory()
    try:
        return Path(trajectory.source_path).read_text(encoding="utf-8")
    except OSError:
        return ""
