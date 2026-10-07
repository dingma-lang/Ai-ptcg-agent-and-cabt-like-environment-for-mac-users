from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .card_catalog import CardCatalog, discover_csv_catalog
from .deck import DeckError, convert_ptcglive_text, deck_report, load_deck, validate_deck
from .engine import CabtUnavailable
from .local_runtime import effective_environment_report
from .recorder import EpisodeReader, jsonl_to_parquet, split_episodes
from .runner import TwoDeckRunner
from .webapp import DEFAULT_HOST, DEFAULT_PORT, run_app


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except (DeckError, CabtUnavailable, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cabt-local", description="Local tooling around the official cabt Pokemon TCG engine.")
    sub = parser.add_subparsers(dest="command", required=True)

    env = sub.add_parser("env", help="Inspect local OS/Python/cabt availability.")
    env.set_defaults(func=cmd_env)

    app = sub.add_parser("app", help="Start the browser app.")
    app.add_argument("--host", default=DEFAULT_HOST)
    app.add_argument("--port", type=int, default=DEFAULT_PORT)
    app.add_argument("--no-browser", action="store_true")
    app.set_defaults(func=cmd_app)

    cards = sub.add_parser("cards", help="Supported-card catalog commands.")
    card_sub = cards.add_subparsers(dest="cards_command", required=True)
    export = card_sub.add_parser("export", help="Export supported card catalog as JSON and CSV.")
    export.add_argument("--out-dir", default="data/catalog")
    export.add_argument("--csv-fallback", default="")
    export.add_argument("--cg-path", default="")
    export.set_defaults(func=cmd_cards_export)

    deck = sub.add_parser("deck", help="Deck validation/conversion commands.")
    deck_sub = deck.add_subparsers(dest="deck_command", required=True)
    validate = deck_sub.add_parser("validate")
    validate.add_argument("path")
    validate.add_argument("--catalog-csv", default="")
    validate.add_argument("--cg-path", default="")
    validate.set_defaults(func=cmd_deck_validate)
    report = deck_sub.add_parser("report")
    report.add_argument("path")
    report.add_argument("--catalog-csv", default="")
    report.set_defaults(func=cmd_deck_report)
    convert = deck_sub.add_parser("convert")
    convert.add_argument("input")
    convert.add_argument("output")
    convert.add_argument("--catalog-csv", default="")
    convert.set_defaults(func=cmd_deck_convert)
    palaking = deck_sub.add_parser("check-palaking", help="Check whether the Palafin/Mega Dragonite deck IDs are in the available card pool.")
    palaking.add_argument("--deck", default="../Palaking/deck.csv")
    palaking.add_argument("--catalog-csv", default="")
    palaking.add_argument("--cg-path", default="")
    palaking.set_defaults(func=cmd_deck_validate)

    play = sub.add_parser("play", help="Run one two-deck match.")
    add_play_args(play)
    play.set_defaults(func=cmd_play)

    self_play = sub.add_parser("self-play", help="Run repeated sequential self-play.")
    add_play_args(self_play)
    self_play.add_argument("--games", type=int, default=10)
    self_play.set_defaults(func=cmd_self_play)

    episodes = sub.add_parser("episodes", help="Episode dataset commands.")
    ep_sub = episodes.add_subparsers(dest="episodes_command", required=True)
    stats = ep_sub.add_parser("stats")
    stats.add_argument("episode_dir", default="data/episodes")
    stats.set_defaults(func=cmd_episode_stats)
    split = ep_sub.add_parser("split")
    split.add_argument("episode_dir")
    split.add_argument("--train-fraction", type=float, default=0.8)
    split.add_argument("--seed", type=int, default=1)
    split.set_defaults(func=cmd_episode_split)
    parquet = ep_sub.add_parser("to-parquet")
    parquet.add_argument("episode_dir")
    parquet.add_argument("output")
    parquet.set_defaults(func=cmd_episode_parquet)
    return parser


def add_play_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--deck-a", required=True)
    parser.add_argument("--deck-b", required=True)
    parser.add_argument("--agent-a", default="random")
    parser.add_argument("--agent-b", default="random")
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--out-dir", default="data")
    parser.add_argument("--cg-path", default="")
    parser.add_argument("--direct-cg", action="store_true", help="Skip kaggle_environments and use cg.game directly.")
    parser.add_argument("--timeout-s", type=float, default=5.0)


def cmd_env(args: argparse.Namespace) -> int:
    print(json.dumps(effective_environment_report(Path.cwd()), indent=2, sort_keys=True))
    return 0


def cmd_app(args: argparse.Namespace) -> int:
    return run_app(Path.cwd(), host=args.host, port=args.port, open_browser=not args.no_browser)


def load_catalog_for_args(args: argparse.Namespace, prefer_engine: bool = True) -> CardCatalog | None:
    if prefer_engine:
        try:
            return CardCatalog.from_cabt(getattr(args, "cg_path", "") or None)
        except CabtUnavailable:
            pass
        except Exception:
            pass
    csv_path = getattr(args, "catalog_csv", "") or getattr(args, "csv_fallback", "")
    if not csv_path:
        found = discover_csv_catalog(Path.cwd())
        csv_path = str(found) if found else ""
    return CardCatalog.from_csv(csv_path) if csv_path else None


def cmd_cards_export(args: argparse.Namespace) -> int:
    catalog = load_catalog_for_args(args, prefer_engine=True)
    if catalog is None:
        raise CabtUnavailable("No cabt engine or CSV catalog was available.")
    out = Path(args.out_dir)
    print(f"Catalog source: {catalog.source}")
    print(catalog.export_json(out / "cards.json"))
    print(catalog.export_csv(out / "cards.csv"))
    return 0


def cmd_deck_validate(args: argparse.Namespace) -> int:
    catalog = load_catalog_for_args(args, prefer_engine=True)
    ids = load_deck(args.deck if hasattr(args, "deck") else args.path)
    errors = validate_deck(ids, catalog)
    if errors:
        for error in errors:
            print("ERROR:", error)
        return 1
    print(f"OK: {len(ids)} cards. Catalog: {catalog.source if catalog else 'not checked against catalog'}")
    return 0


def cmd_deck_report(args: argparse.Namespace) -> int:
    catalog = load_catalog_for_args(args, prefer_engine=False)
    report = deck_report(args.path, catalog)
    print(json.dumps(report.__dict__, indent=2, sort_keys=True))
    return 0


def cmd_deck_convert(args: argparse.Namespace) -> int:
    catalog = load_catalog_for_args(args, prefer_engine=False)
    if catalog is None:
        raise CabtUnavailable("Deck conversion requires a cabt or CSV catalog.")
    report = convert_ptcglive_text(args.input, args.output, catalog)
    print(json.dumps({"output_path": report.output_path, "converted_count": report.converted_count, "issues": [issue.__dict__ for issue in report.issues]}, indent=2))
    return 1 if report.issues or report.converted_count != 60 else 0


def cmd_play(args: argparse.Namespace) -> int:
    runner = TwoDeckRunner(args.out_dir, cg_path=args.cg_path or None, timeout_s=args.timeout_s)
    result = runner.play_paths(args.deck_a, args.deck_b, args.agent_a, args.agent_b, record=args.record, prefer_kaggle_env=not args.direct_cg)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


def cmd_self_play(args: argparse.Namespace) -> int:
    runner = TwoDeckRunner(args.out_dir, cg_path=args.cg_path or None, timeout_s=args.timeout_s)
    results = []
    for game_idx in range(args.games):
        result = runner.play_paths(args.deck_a, args.deck_b, args.agent_a, args.agent_b, record=args.record, prefer_kaggle_env=not args.direct_cg)
        results.append(result.to_dict())
        print(f"game {game_idx + 1}/{args.games}: {result.termination_reason}")
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


def cmd_episode_stats(args: argparse.Namespace) -> int:
    print(json.dumps(EpisodeReader(args.episode_dir).stats(), indent=2, sort_keys=True))
    return 0


def cmd_episode_split(args: argparse.Namespace) -> int:
    print(json.dumps(split_episodes(args.episode_dir, args.train_fraction, args.seed), indent=2, sort_keys=True))
    return 0


def cmd_episode_parquet(args: argparse.Namespace) -> int:
    print(jsonl_to_parquet(args.episode_dir, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
