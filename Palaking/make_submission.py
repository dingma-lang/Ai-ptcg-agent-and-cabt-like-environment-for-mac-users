from __future__ import annotations

import argparse
import zipfile
from pathlib import Path
from typing import Iterable, List


FORBIDDEN_ARCHIVE_PARTS = [
    "memory/",
    "local_results/",
    "eval_results/",
    "__pycache__",
    ".DS_Store",
    ".ipynb_checkpoints",
]

FORBIDDEN_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".tiff",
    ".html",
    ".jsonl",
    ".log",
}

ROOT_SAFE_MODULES = [
    "action_classifier.py",
    "action_reasoner.py",
    "card_db.py",
    "decision_reason.py",
    "deck_profile.py",
    "memory.py",
    "option_scorer.py",
    "policy.py",
    "search_policy.py",
    "state_eval.py",
    "state_parser.py",
    "study_rule_runtime.py",
    "study_rules.json",
    "turn_sequencer.py",
]

CORE_SAFE_MODULES = {
    "__init__.py",
    "action_classifier.py",
    "action_intent.py",
    "agent_memory.py",
    "air_balloon_planner.py",
    "attack_choice_planner.py",
    "card_analysis.py",
    "card_relationships.py",
    "crispin_planner.py",
    "danger_evaluator.py",
    "decision_reason.py",
    "deck_profile.py",
    "deck_synergy_graph.py",
    "energy_planner.py",
    "finizen_setup_planner.py",
    "giga_impact_planner.py",
    "lillie_guard.py",
    "mega_dragonite_planner.py",
    "opponent_model.py",
    "option_scorer.py",
    "palafin_attack_state.py",
    "palafin_evolution_guard.py",
    "palafin_planner.py",
    "petrel_exact_search_planner.py",
    "poffin_planner.py",
    "pokepad_dragonite_planner.py",
    "pokepad_planner.py",
    "policy.py",
    "policy_rules_from_analysis.py",
    "priority_tables.py",
    "recovery_planner.py",
    "secret_box_palafin_guard.py",
    "state_parser.py",
    "strategy_scope.py",
    "stuck_recovery.py",
    "supporter_router.py",
    "switch_engine_planner.py",
    "switch_reset_planner.py",
    "switch_usage_guard.py",
    "target_board.py",
    "turn_plan.py",
    "zero_to_hero_planner.py",
}

REQUIRED_TOP_LEVEL = [
    "agent.py",
    "main.py",
    "deck.csv",
    "deck_profile.json",
    "config.py",
    "README.md",
    "STRATEGY_NOTES.md",
]


def build_file_list(root: Path) -> List[Path]:
    files: List[Path] = []
    for name in REQUIRED_TOP_LEVEL + ROOT_SAFE_MODULES:
        path = root / name
        if path.exists():
            files.append(path)
    core = root / "core"
    if core.exists():
        files.extend(core / name for name in CORE_SAFE_MODULES if (core / name).exists())
    for folder in [root / "adapters" / "cabt", root / "docs", root / "data"]:
        if folder.exists():
            files.extend(path for path in folder.rglob("*") if path.is_file())
    return sorted(set(files))


def is_forbidden(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        return True
    return any(part in rel for part in FORBIDDEN_ARCHIVE_PARTS)


def make_archive(out_path: Path, files: Iterable[Path], root: Path) -> None:
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            if is_forbidden(path, root):
                continue
            archive.write(path, path.relative_to(root).as_posix())


def validate_archive(path: Path) -> List[str]:
    errors: List[str] = []
    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()
    required = {"agent.py", "main.py", "deck.csv", "config.py", "adapters/cabt/submission_entry.py"}
    missing = sorted(required - set(names))
    if missing:
        errors.append("missing required files: " + ", ".join(missing))
    forbidden = [name for name in names if any(part in name for part in FORBIDDEN_ARCHIVE_PARTS) or Path(name).suffix.lower() in FORBIDDEN_SUFFIXES]
    if forbidden:
        errors.append("forbidden files included: " + ", ".join(sorted(forbidden)))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a cabt/Kaggle-safe submission archive.")
    parser.add_argument("--out", default="submission.zip")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    out_path = root / args.out
    files = build_file_list(root)
    make_archive(out_path, files, root)
    errors = validate_archive(out_path)
    if errors:
        for error in errors:
            print("ERROR:", error)
        return 1
    print(f"Wrote {out_path} with {len(zipfile.ZipFile(out_path).namelist())} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
