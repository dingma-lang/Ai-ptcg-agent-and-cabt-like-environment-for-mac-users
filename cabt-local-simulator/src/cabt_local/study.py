from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Iterable

from .replay_visualizer import parse_battle_log


STUDY_SCHEMA_VERSION = 1
DECISIONS = {"accepted", "rejected", "pending"}
USEFUL_BEFORE_TERMINAL = {
    "ATTACH_ENERGY",
    "EVOLVE",
    "PLAY_BASIC_TO_BENCH",
    "PLAY_ITEM",
    "PLAY_STADIUM",
    "PLAY_SUPPORTER",
    "RARE_CANDY_EVOLVE",
    "USE_ABILITY",
}
PROACTIVE_LOG_ACTIONS = {
    "ATTACH_ENERGY",
    "EVOLVE",
    "PLAY_ACTIVE",
    "PLAY_BENCH",
    "PLAY_CARD",
    "PLAY_STADIUM",
    "RETREAT",
    "USE_ATTACK_OR_ABILITY",
}
_STORE_LOCK = threading.RLock()


def synchronized(function: Any) -> Any:
    @wraps(function)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        with _STORE_LOCK:
            return function(*args, **kwargs)

    return wrapped


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class StudyFinding:
    id: str
    category: str
    title: str
    turn: str
    player: str
    evidence: str
    explanation: str
    severity: str
    confidence: str
    source: str
    actionable: bool
    proposed_rule: dict[str, Any]
    status: str = "pending"
    reviewer_note: str = ""
    checkpoint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@synchronized
def create_study(
    root: Path,
    *,
    log_text: str,
    agent_profile: dict[str, Any],
    episode_path: Path | None = None,
) -> dict[str, Any]:
    replay = parse_battle_log(log_text)
    findings = analyze_log_replay(replay)
    episode_rows: list[dict[str, Any]] = []
    if episode_path is not None:
        episode_rows = read_episode_rows(episode_path)
        findings.extend(analyze_episode_rows(episode_rows, str(agent_profile.get("spec") or "")))
    findings = apply_review_history(root, agent_profile, deduplicate_findings(findings))

    created = utc_now()
    digest = hashlib.sha256(
        (created + log_text + str(agent_profile.get("spec") or "")).encode("utf-8")
    ).hexdigest()[:12]
    study_id = f"study-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{digest}"
    profile = public_agent_profile(agent_profile)
    payload = {
        "schema_version": STUDY_SCHEMA_VERSION,
        "ok": True,
        "study_id": study_id,
        "created_at": created,
        "updated_at": created,
        "agent": profile,
        "log_text": log_text,
        "episode_path": str(episode_path.relative_to(root)) if episode_path is not None else "",
        "replay": replay,
        "findings": [finding.to_dict() for finding in findings],
        "summary": finding_summary(findings),
        "memory": memory_status(root, agent_profile),
        "limitations": study_limitations(bool(episode_rows)),
    }
    save_study(root, payload)
    return payload


def analyze_log_replay(replay: dict[str, Any]) -> list[StudyFinding]:
    events = list(replay.get("events") or [])
    findings: list[StudyFinding] = []
    turn_events: list[dict[str, Any]] = []

    def finish_turn() -> None:
        if not turn_events:
            return
        end = next((event for event in reversed(turn_events) if event.get("action") == "TURN_END"), None)
        if end is None:
            return
        proactive = [event for event in turn_events if event.get("action") in PROACTIVE_LOG_ACTIONS]
        if proactive:
            return
        player = str(end.get("player") or "")
        turn = str(end.get("turn") or "")
        findings.append(
            make_finding(
                category="empty_turn_review",
                title="Turn ended without a proactive action",
                turn=turn,
                player=player,
                evidence=str(end.get("raw") or "Turn ended."),
                explanation="The public log shows no play, evolution, attachment, Ability, retreat, or attack. Review the decision trace before treating this as a mistake.",
                severity="medium",
                confidence="medium",
                source="battle_log",
                proposed_rule=rule(
                    "pre_end_action_check",
                    "Before ending, recheck useful legal setup, evolution, attachment, Ability, and Supporter actions.",
                    "END_TURN",
                    "avoid",
                    -2500,
                    {"useful_legal_action_exists": True},
                ),
            )
        )

    for event in events:
        action = str(event.get("action") or "")
        if action == "TURN_START":
            finish_turn()
            turn_events = [event]
        elif turn_events:
            turn_events.append(event)

        if action == "TIMEOUT":
            findings.append(
                make_finding(
                    category="timeout",
                    title="Agent failed to act before the deadline",
                    turn=str(event.get("turn") or ""),
                    player=str(event.get("player") or ""),
                    evidence=str(event.get("raw") or "Timeout"),
                    explanation="A deterministic emergency fallback should return a legal selection before the decision deadline.",
                    severity="critical",
                    confidence="high",
                    source="battle_log",
                    proposed_rule=rule(
                        "deadline_legal_fallback",
                        "Use a fast legal fallback when the normal policy approaches its decision deadline.",
                        "UNKNOWN",
                        "prefer",
                        10000,
                        {"deadline_risk": True},
                    ),
                )
            )
        elif action == "RETREAT" and "discard" in str(event.get("detail") or "").lower():
            findings.append(
                make_finding(
                    category="paid_retreat_review",
                    title="Retreat discarded an attached resource",
                    turn=str(event.get("turn") or ""),
                    player=str(event.get("player") or ""),
                    evidence="\n".join(filter(None, [str(event.get("raw") or ""), str(event.get("detail") or "")])),
                    explanation="Paid retreat can be correct, but free switching and the resulting attacker should be checked first.",
                    severity="medium",
                    confidence="low",
                    source="battle_log",
                    proposed_rule=rule(
                        "avoid_unnecessary_paid_retreat",
                        "Prefer a free switch and avoid discarding Energy unless retreat creates an immediate tactical benefit.",
                        "RETREAT",
                        "avoid",
                        -1500,
                        {"retreat_discards_energy": True, "urgent_switch": False},
                    ),
                )
            )
    finish_turn()

    unknown = list(replay.get("unparsed_lines") or [])
    if unknown:
        sample = "; ".join(f"line {row.get('line')}: {row.get('text')}" for row in unknown[:3])
        findings.append(
            make_finding(
                category="parser_coverage",
                title=f"{len(unknown)} log line(s) need parser coverage",
                turn="",
                player="",
                evidence=sample,
                explanation="These lines were preserved but cannot safely produce strategy advice until the parser understands them.",
                severity="low",
                confidence="high",
                source="system",
                actionable=False,
                proposed_rule={},
            )
        )
    return findings


def analyze_episode_rows(rows: Iterable[dict[str, Any]], selected_agent_spec: str) -> list[StudyFinding]:
    findings: list[StudyFinding] = []
    for row in rows:
        if selected_agent_spec and not same_agent_spec(str(row.get("agent_id") or ""), selected_agent_spec):
            continue
        observation = row.get("observation") if isinstance(row.get("observation"), dict) else {}
        select = observation.get("select") if isinstance(observation.get("select"), dict) else {}
        legal = row.get("legal_options") or select.get("option") or []
        selected = row.get("selected_indexes") or []
        turn = str(row.get("turn") or "")
        player = str(row.get("player") if row.get("player") is not None else "")
        min_count = nonnegative_int(select.get("minCount"), 0)
        max_count = min(len(legal), max(min_count, nonnegative_int(select.get("maxCount"), min_count)))
        legal_selection = (
            isinstance(selected, list)
            and len(selected) == len(set(index for index in selected if isinstance(index, int)))
            and min_count <= len(selected) <= max_count
            and all(isinstance(index, int) and 0 <= index < len(legal) for index in selected)
        )
        if not legal_selection:
            findings.append(
                make_finding(
                    category="illegal_selection",
                    title="Agent returned an invalid legal-option selection",
                    turn=turn,
                    player=player,
                    evidence=f"selected={selected}; option_count={len(legal)}; required={min_count}..{max_count}",
                    explanation="The safety wrapper must normalize the output to unique in-range indices and satisfy minCount/maxCount.",
                    severity="critical",
                    confidence="high",
                    source="decision_trace",
                    proposed_rule=rule(
                        "legal_selection_guard",
                        "Sanitize every result against the current option list and selection count bounds.",
                        "UNKNOWN",
                        "prefer",
                        20000,
                        {"before_return": True},
                    ),
                )
            )
            continue

        trace = row.get("agent_trace") if isinstance(row.get("agent_trace"), dict) else {}
        trace_options = trace.get("legal_options") if isinstance(trace.get("legal_options"), list) else []
        option_rows = normalize_trace_options(trace_options, legal)
        chosen_rows = [item for item in option_rows if item["index"] in selected]
        chosen_categories = {str(item.get("category") or "UNKNOWN") for item in chosen_rows}
        terminal = bool(chosen_categories & {"END_TURN", "ATTACK"})
        if terminal:
            useful = [
                item
                for item in option_rows
                if str(item.get("category") or "") in USEFUL_BEFORE_TERMINAL
                and item["index"] not in selected
                and float_or(item.get("score"), 0.0) >= 500.0
            ]
            if useful:
                top = max(useful, key=lambda item: float_or(item.get("score"), 0.0))
                chosen_label = "attack" if "ATTACK" in chosen_categories else "end turn"
                categories = sorted({str(item.get("category") or "UNKNOWN") for item in useful})
                findings.append(
                    make_finding(
                        category="terminal_checklist",
                        title=f"Useful action remained before {chosen_label}",
                        turn=turn,
                        player=player,
                        evidence=(
                            f"Chose {chosen_label}; available {', '.join(categories)}. "
                            f"Top alternative: index {top['index']} {top.get('label') or ''} "
                            f"(score {float_or(top.get('score'), 0.0):.0f})."
                        ),
                        explanation="The trace proves these options were legal, but tactical attacks may correctly override setup. Review the score and reason before accepting.",
                        severity="high" if "END_TURN" in chosen_categories else "medium",
                        confidence="high" if "END_TURN" in chosen_categories else "medium",
                        source="decision_trace",
                        proposed_rule=rule(
                            "repeat_pre_terminal_checklist",
                            "Before attack or End, re-evaluate useful evolution, Basic benching, Energy, Item, Ability, Stadium, and Supporter options.",
                            "END_TURN" if "END_TURN" in chosen_categories else "ATTACK",
                            "avoid",
                            -3000,
                            {"useful_categories": categories, "immediate_win_or_ko": False},
                        ),
                    )
                )

        scored = [item for item in option_rows if item.get("score") is not None]
        chosen_scored = [item for item in chosen_rows if item.get("score") is not None]
        if scored and chosen_scored:
            best = max(scored, key=lambda item: float_or(item.get("score"), 0.0))
            chosen_best = max(chosen_scored, key=lambda item: float_or(item.get("score"), 0.0))
            gap = float_or(best.get("score"), 0.0) - float_or(chosen_best.get("score"), 0.0)
            if gap >= 2500.0 and best["index"] not in selected:
                findings.append(
                    make_finding(
                        category="score_override_review",
                        title="Selection bypassed a much higher score",
                        turn=turn,
                        player=player,
                        evidence=(
                            f"Chosen index {chosen_best['index']} scored {float_or(chosen_best.get('score'), 0.0):.0f}; "
                            f"index {best['index']} scored {float_or(best.get('score'), 0.0):.0f}. "
                            f"Reason: {trace.get('reason') or chosen_best.get('reason') or 'not recorded'}"
                        ),
                        explanation="A sequencing override may be intentional. This finding asks for review and does not automatically force highest-score play.",
                        severity="medium",
                        confidence="medium",
                        source="decision_trace",
                        proposed_rule=rule(
                            "audit_large_score_override",
                            "Require an explicit sequencing reason when bypassing an option with a substantially higher score.",
                            str(chosen_best.get("category") or "UNKNOWN"),
                            "review",
                            0,
                            {"minimum_score_gap": 2500},
                        ),
                    )
                )
    return findings


@synchronized
def decide_finding(
    root: Path,
    *,
    study_id: str,
    finding_id: str,
    decision: str,
    agent_profile: dict[str, Any],
    edited_rule: dict[str, Any] | None = None,
    reviewer_note: str = "",
) -> dict[str, Any]:
    if decision not in {"accepted", "rejected"}:
        raise ValueError("Decision must be accepted or rejected.")
    study = load_study(root, study_id)
    stored_spec = str((study.get("agent") or {}).get("spec") or "")
    if stored_spec != str(agent_profile.get("spec") or ""):
        raise ValueError("The selected agent does not match this study session.")
    finding = next((item for item in study.get("findings", []) if item.get("id") == finding_id), None)
    if finding is None:
        raise ValueError("Finding does not exist in this study.")
    if not finding.get("actionable") and decision == "accepted":
        raise ValueError("System coverage findings cannot change an agent.")

    finding["status"] = decision
    finding["reviewer_note"] = reviewer_note.strip()[:1000]
    checkpoint: dict[str, Any] | None = None
    if decision == "accepted":
        candidate = edited_rule if edited_rule is not None else finding.get("proposed_rule")
        validated = validate_rule(candidate)
        finding["proposed_rule"] = validated
        checkpoint = accept_rule_checkpoint(root, agent_profile, study, finding, validated)
        finding["checkpoint"] = str(checkpoint.get("checkpoint_id") or "")
        remove_rejection(root, agent_profile, str(validated.get("id") or ""))
    else:
        record_rejection(root, agent_profile, study, finding)

    study["updated_at"] = utc_now()
    study["summary"] = finding_summary(study.get("findings") or [])
    study["memory"] = memory_status(root, agent_profile)
    save_study(root, study)
    return {"ok": True, "study": study, "checkpoint": checkpoint}


def accept_rule_checkpoint(
    root: Path,
    agent_profile: dict[str, Any],
    study: dict[str, Any],
    finding: dict[str, Any],
    accepted_rule: dict[str, Any],
) -> dict[str, Any]:
    key = agent_key(agent_profile)
    memory_root = root / "data" / "study_memory" / key
    checkpoint_root = memory_root / "checkpoints"
    checkpoint_root.mkdir(parents=True, exist_ok=True)
    current_path = memory_root / "current.json"
    current = read_json(current_path, default={})
    rules = list(current.get("accepted_rules") or [])
    rules = [item for item in rules if item.get("id") != accepted_rule.get("id")]
    rules.append(accepted_rule)
    version = nonnegative_int(current.get("version"), 0) + 1
    checkpoint_id = f"checkpoint_{version:04d}"
    now = utc_now()
    checkpoint = {
        "schema_version": STUDY_SCHEMA_VERSION,
        "checkpoint_id": checkpoint_id,
        "version": version,
        "created_at": now,
        "agent": public_agent_profile(agent_profile),
        "parent_checkpoint": str(current.get("checkpoint_id") or ""),
        "source_study": str(study.get("study_id") or ""),
        "source_finding": str(finding.get("id") or ""),
        "accepted_rule": accepted_rule,
        "accepted_rules": rules,
        "kind": "rule_acceptance",
        "validation": {"status": "not_run", "message": "Run local matches before submission export."},
    }
    atomic_write_json(checkpoint_root / f"{checkpoint_id}.json", checkpoint)
    atomic_write_json(current_path, checkpoint)

    target = agent_sidecar_path(agent_profile)
    if target is not None:
        sidecar = {
            "schema_version": STUDY_SCHEMA_VERSION,
            "agent_key": key,
            "checkpoint_id": checkpoint_id,
            "updated_at": now,
            "accepted_rules": rules,
        }
        atomic_write_json(target, sidecar)
    checkpoint["runtime_integration"] = runtime_integration(agent_profile)
    return checkpoint


def list_checkpoints(root: Path, agent_profile: dict[str, Any]) -> list[dict[str, Any]]:
    checkpoint_root = root / "data" / "study_memory" / agent_key(agent_profile) / "checkpoints"
    rows = []
    for path in sorted(checkpoint_root.glob("checkpoint_*.json"), reverse=True) if checkpoint_root.exists() else []:
        payload = read_json(path, default={})
        rows.append(
            {
                "checkpoint_id": payload.get("checkpoint_id", path.stem),
                "version": payload.get("version", 0),
                "created_at": payload.get("created_at", ""),
                "source_study": payload.get("source_study", ""),
                "rule": (payload.get("accepted_rule") or {}).get("description", ""),
                "kind": payload.get("kind", "rule_acceptance"),
                "validation": payload.get("validation", {"status": "unknown"}),
            }
        )
    return rows


@synchronized
def restore_checkpoint(root: Path, agent_profile: dict[str, Any], checkpoint_id: str) -> dict[str, Any]:
    if checkpoint_id != "baseline" and not re.fullmatch(r"checkpoint_\d{4}", checkpoint_id):
        raise ValueError("Invalid checkpoint id.")
    key = agent_key(agent_profile)
    memory_root = root / "data" / "study_memory" / key
    current_path = memory_root / "current.json"
    current = read_json(current_path, default={})
    if checkpoint_id == "baseline":
        restored_rules: list[dict[str, Any]] = []
    else:
        target = read_json(memory_root / "checkpoints" / f"{checkpoint_id}.json", default={})
        if not target:
            raise ValueError("Checkpoint does not exist for this agent.")
        restored_rules = list(target.get("accepted_rules") or [])

    version = nonnegative_int(current.get("version"), 0) + 1
    new_id = f"checkpoint_{version:04d}"
    now = utc_now()
    checkpoint = {
        "schema_version": STUDY_SCHEMA_VERSION,
        "checkpoint_id": new_id,
        "version": version,
        "created_at": now,
        "agent": public_agent_profile(agent_profile),
        "parent_checkpoint": str(current.get("checkpoint_id") or ""),
        "restored_checkpoint": checkpoint_id,
        "accepted_rule": {
            "id": "checkpoint_restore",
            "description": f"Restored strategy memory from {checkpoint_id}.",
        },
        "accepted_rules": restored_rules,
        "kind": "restore",
        "validation": {"status": "not_run", "message": "Run local matches before submission export."},
    }
    checkpoint_root = memory_root / "checkpoints"
    checkpoint_root.mkdir(parents=True, exist_ok=True)
    atomic_write_json(checkpoint_root / f"{new_id}.json", checkpoint)
    atomic_write_json(current_path, checkpoint)
    target_sidecar = agent_sidecar_path(agent_profile)
    if target_sidecar is not None:
        atomic_write_json(
            target_sidecar,
            {
                "schema_version": STUDY_SCHEMA_VERSION,
                "agent_key": key,
                "checkpoint_id": new_id,
                "updated_at": now,
                "accepted_rules": restored_rules,
            },
        )
    checkpoint["runtime_integration"] = runtime_integration(agent_profile)
    return checkpoint


@synchronized
def validate_current_checkpoint(root: Path, agent_profile: dict[str, Any]) -> dict[str, Any]:
    key = agent_key(agent_profile)
    memory_root = root / "data" / "study_memory" / key
    current_path = memory_root / "current.json"
    current = read_json(current_path, default={})
    has_checkpoint = bool(current.get("checkpoint_id"))

    errors: list[str] = []
    warnings: list[str] = []
    rules = list(current.get("accepted_rules") or [])
    for index, candidate in enumerate(rules):
        try:
            validate_rule(candidate)
        except ValueError as exc:
            errors.append(f"rule {index + 1}: {exc}")

    sidecar = agent_sidecar_path(agent_profile)
    if has_checkpoint and (sidecar is None or not sidecar.is_file()):
        errors.append("Agent study_rules.json sidecar is missing.")
    elif sidecar is not None and sidecar.is_file():
        sidecar_payload = read_json(sidecar, default={})
        if has_checkpoint and sidecar_payload.get("checkpoint_id") != current.get("checkpoint_id"):
            errors.append("Agent sidecar does not match the current checkpoint id.")
        if has_checkpoint and sidecar_payload.get("accepted_rules") != rules:
            errors.append("Agent sidecar rules do not match checkpoint memory.")

    integration = runtime_integration(agent_profile)
    if has_checkpoint and not integration.get("active"):
        errors.append(str(integration.get("status") or "Runtime rule hook is unavailable."))
    elif not integration.get("active"):
        warnings.append(str(integration.get("status") or "Runtime rule hook is unavailable."))

    agent_path = agent_file_path(agent_profile)
    if agent_path is None:
        errors.append("Agent source file is unavailable.")
    else:
        syntax_paths = [agent_path, agent_path.parent / "policy.py", agent_path.parent / "study_rule_runtime.py"]
        for path in syntax_paths:
            if not path.is_file():
                warnings.append(f"Optional syntax target is missing: {path.name}")
                continue
            try:
                compile(path.read_text(encoding="utf-8"), str(path), "exec")
            except (OSError, SyntaxError, UnicodeError) as exc:
                errors.append(f"{path.name}: {exc}")

    validation = {
        "status": ("structural_pass" if has_checkpoint else "baseline_pass") if not errors else "failed",
        "checked_at": utc_now(),
        "errors": errors,
        "warnings": warnings,
        "match_validation": "not_run",
        "message": (
            "Baseline agent checks passed; accept a takeaway to create the first checkpoint."
            if not errors and not has_checkpoint
            else "Structural checks passed; run local A/B matches before submission."
            if not errors
            else "Structural validation failed."
        ),
    }
    if has_checkpoint:
        current["validation"] = validation
        atomic_write_json(current_path, current)
        checkpoint_id = str(current.get("checkpoint_id") or "")
        checkpoint_path = memory_root / "checkpoints" / f"{checkpoint_id}.json"
        if checkpoint_path.is_file():
            checkpoint = read_json(checkpoint_path, default={})
            checkpoint["validation"] = validation
            atomic_write_json(checkpoint_path, checkpoint)
    return validation


def memory_status(root: Path, agent_profile: dict[str, Any]) -> dict[str, Any]:
    key = agent_key(agent_profile)
    current = read_json(root / "data" / "study_memory" / key / "current.json", default={})
    rejections = read_json(root / "data" / "study_memory" / key / "rejections.json", default={})
    sidecar = agent_sidecar_path(agent_profile)
    return {
        "agent_key": key,
        "checkpoint_id": current.get("checkpoint_id", ""),
        "version": current.get("version", 0),
        "accepted_rule_count": len(current.get("accepted_rules") or []),
        "rejected_rule_count": len(rejections.get("rejected_rules") or []),
        "sidecar_path": str(sidecar) if sidecar else "",
        "runtime_integration": runtime_integration(agent_profile),
        "hook_install_supported": hook_install_supported(root, agent_profile),
    }


@synchronized
def install_runtime_hook(root: Path, agent_profile: dict[str, Any]) -> dict[str, Any]:
    if not hook_install_supported(root, agent_profile):
        raise ValueError("This agent does not have a compatible imported policy layout.")
    agent_path = agent_file_path(agent_profile)
    if agent_path is None:
        raise ValueError("Agent source file is unavailable.")
    agent_root = agent_path.parent
    policy_path = agent_root / "policy.py"
    runtime_path = agent_root / "study_rule_runtime.py"
    source = policy_path.read_text(encoding="utf-8")
    marker = "# STUDY_RULE_RUNTIME_HOOK"

    if marker not in source:
        tree = ast.parse(source, filename=str(policy_path))
        function = next(
            (node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "apply_action_reasoning"),
            None,
        )
        if function is None:
            raise ValueError("Compatible apply_action_reasoning function was not found.")
        returns = [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == "score"
        ]
        if len(returns) != 1:
            raise ValueError("Policy score return shape is not safe to patch automatically.")
        insertion_line = returns[0].lineno - 1
        hook = (
            "    # STUDY_RULE_RUNTIME_HOOK\n"
            "    try:\n"
            "        from study_rule_runtime import apply_study_rules\n\n"
            "        score = apply_study_rules(state, option, option_index, score)\n"
            "    except Exception:\n"
            "        pass\n"
        )
        lines = source.splitlines(keepends=True)
        lines.insert(insertion_line, hook)
        patched = "".join(lines)
        compile(patched, str(policy_path), "exec")

        backup_root = root / "data" / "study_memory" / agent_key(agent_profile) / "integration_backup"
        backup_root.mkdir(parents=True, exist_ok=True)
        backup_path = backup_root / "policy_before_study_hook.py"
        if not backup_path.exists():
            atomic_write_text(backup_path, source)
        atomic_write_text(policy_path, patched)

    template_path = Path(__file__).with_name("study_rule_runtime_template.py")
    runtime_source = template_path.read_text(encoding="utf-8")
    compile(runtime_source, str(runtime_path), "exec")
    atomic_write_text(runtime_path, runtime_source)
    integration = runtime_integration(agent_profile)
    if not integration.get("active"):
        raise ValueError("Runtime hook installation did not pass detection.")
    return {
        "ok": True,
        "agent": public_agent_profile(agent_profile),
        "runtime_integration": integration,
        "backup_path": str(root / "data" / "study_memory" / agent_key(agent_profile) / "integration_backup"),
    }


def hook_install_supported(root: Path, agent_profile: dict[str, Any]) -> bool:
    if str(agent_profile.get("source") or "") != "imported":
        return False
    agent_path = agent_file_path(agent_profile)
    if agent_path is None:
        return False
    imported_root = (root / "data" / "imported_agents").resolve()
    try:
        if not agent_path.resolve().is_relative_to(imported_root):
            return False
        source = (agent_path.parent / "policy.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, SyntaxError, UnicodeError):
        return False
    return any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "apply_action_reasoning"
        for node in tree.body
    )


def apply_review_history(
    root: Path,
    agent_profile: dict[str, Any],
    findings: list[StudyFinding],
) -> list[StudyFinding]:
    memory_root = root / "data" / "study_memory" / agent_key(agent_profile)
    current = read_json(memory_root / "current.json", default={})
    rejections = read_json(memory_root / "rejections.json", default={})
    accepted_ids = {str(item.get("id") or "") for item in current.get("accepted_rules") or []}
    rejected_ids = {str(item.get("rule_id") or "") for item in rejections.get("rejected_rules") or []}
    for finding in findings:
        rule_id = str(finding.proposed_rule.get("id") or "")
        if rule_id and rule_id in accepted_ids:
            finding.status = "accepted"
            finding.checkpoint = str(current.get("checkpoint_id") or "")
        elif rule_id and rule_id in rejected_ids:
            finding.status = "rejected"
    return findings


def record_rejection(
    root: Path,
    agent_profile: dict[str, Any],
    study: dict[str, Any],
    finding: dict[str, Any],
) -> None:
    path = root / "data" / "study_memory" / agent_key(agent_profile) / "rejections.json"
    payload = read_json(path, default={})
    rows = list(payload.get("rejected_rules") or [])
    rule_id = str((finding.get("proposed_rule") or {}).get("id") or finding.get("category") or "")
    rows = [item for item in rows if str(item.get("rule_id") or "") != rule_id]
    rows.append(
        {
            "rule_id": rule_id,
            "finding_id": finding.get("id", ""),
            "study_id": study.get("study_id", ""),
            "rejected_at": utc_now(),
            "reviewer_note": finding.get("reviewer_note", ""),
        }
    )
    atomic_write_json(
        path,
        {
            "schema_version": STUDY_SCHEMA_VERSION,
            "agent_key": agent_key(agent_profile),
            "rejected_rules": rows,
        },
    )


def remove_rejection(root: Path, agent_profile: dict[str, Any], rule_id: str) -> None:
    path = root / "data" / "study_memory" / agent_key(agent_profile) / "rejections.json"
    payload = read_json(path, default={})
    rows = [item for item in payload.get("rejected_rules") or [] if str(item.get("rule_id") or "") != rule_id]
    if payload or rows:
        atomic_write_json(
            path,
            {
                "schema_version": STUDY_SCHEMA_VERSION,
                "agent_key": agent_key(agent_profile),
                "rejected_rules": rows,
            },
        )


def runtime_integration(agent_profile: dict[str, Any]) -> dict[str, Any]:
    sidecar = agent_sidecar_path(agent_profile)
    if sidecar is None:
        return {"active": False, "status": "No writable file-agent package is selected."}
    markers = ("study_rules.json", "load_study_rules", "apply_study_rules")
    paths = [sidecar.parent / "agent.py", sidecar.parent / "policy.py"]
    paths.extend((sidecar.parent / "core").glob("*.py") if (sidecar.parent / "core").exists() else [])
    for path in paths:
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if any(marker in source for marker in markers):
            return {"active": True, "status": f"Runtime rule hook detected in {path.name}."}
    return {
        "active": False,
        "status": "This agent does not yet load study_rules.json at runtime.",
    }


def validate_rule(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("The proposed rule must be a JSON object.")
    rule_id = str(value.get("id") or "").strip()
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,79}", rule_id):
        raise ValueError("Rule id must use 3-80 lowercase letters, numbers, or underscores.")
    description = str(value.get("description") or "").strip()
    if not description or len(description) > 800:
        raise ValueError("Rule description must contain 1-800 characters.")
    scope = str(value.get("scope") or "agent")
    if scope not in {"agent", "system"}:
        raise ValueError("Rule scope must be agent or system.")
    effect = str(value.get("effect") or "review")
    if effect not in {"prefer", "avoid", "review"}:
        raise ValueError("Rule effect must be prefer, avoid, or review.")
    weight = int(float_or(value.get("weight"), 0.0))
    if not -50000 <= weight <= 50000:
        raise ValueError("Rule weight must be between -50000 and 50000.")
    conditions = value.get("conditions") or {}
    if not isinstance(conditions, dict) or len(json.dumps(conditions)) > 4000:
        raise ValueError("Rule conditions must be a small JSON object.")
    return {
        "id": rule_id,
        "description": description,
        "scope": scope,
        "target_category": str(value.get("target_category") or "UNKNOWN")[:80],
        "effect": effect,
        "weight": weight,
        "conditions": conditions,
    }


def rule(
    rule_id: str,
    description: str,
    target_category: str,
    effect: str,
    weight: int,
    conditions: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": rule_id,
        "description": description,
        "scope": "agent",
        "target_category": target_category,
        "effect": effect,
        "weight": weight,
        "conditions": conditions,
    }


def make_finding(
    *,
    category: str,
    title: str,
    turn: str,
    player: str,
    evidence: str,
    explanation: str,
    severity: str,
    confidence: str,
    source: str,
    proposed_rule: dict[str, Any],
    actionable: bool = True,
) -> StudyFinding:
    digest = hashlib.sha256(
        "|".join([category, turn, player, evidence, str(proposed_rule.get("id") or "")]).encode("utf-8")
    ).hexdigest()[:12]
    return StudyFinding(
        id=f"finding-{digest}",
        category=category,
        title=title,
        turn=turn,
        player=player,
        evidence=evidence,
        explanation=explanation,
        severity=severity,
        confidence=confidence,
        source=source,
        actionable=actionable,
        proposed_rule=proposed_rule,
    )


def normalize_trace_options(trace_options: list[Any], legal_options: list[Any]) -> list[dict[str, Any]]:
    by_index: dict[int, dict[str, Any]] = {}
    for fallback_index, item in enumerate(trace_options):
        if not isinstance(item, dict):
            continue
        index = nonnegative_int(item.get("index"), fallback_index)
        by_index[index] = {
            "index": index,
            "category": str(item.get("category") or "UNKNOWN"),
            "score": item.get("score"),
            "reason": str(item.get("reason") or ""),
            "label": option_label(legal_options[index]) if 0 <= index < len(legal_options) else "",
        }
    for index, option in enumerate(legal_options):
        by_index.setdefault(
            index,
            {"index": index, "category": infer_option_category(option), "score": None, "reason": "", "label": option_label(option)},
        )
    return [by_index[index] for index in sorted(by_index)]


def infer_option_category(option: Any) -> str:
    text = option_label(option).lower()
    if "end" in text or "pass" in text:
        return "END_TURN"
    if "attack" in text or "damage" in text:
        return "ATTACK"
    if "attach" in text and "energy" in text:
        return "ATTACH_ENERGY"
    if "evolve" in text:
        return "EVOLVE"
    if "retreat" in text:
        return "RETREAT"
    return "UNKNOWN"


def option_label(option: Any) -> str:
    if option is None:
        return "hidden option"
    if isinstance(option, str):
        return option
    try:
        return json.dumps(option, sort_keys=True, ensure_ascii=False, separators=(",", ":"))[:500]
    except (TypeError, ValueError):
        return str(option)[:500]


def same_agent_spec(left: str, right: str) -> bool:
    if left == right:
        return True
    left_path = file_agent_path(left)
    right_path = file_agent_path(right)
    return left_path is not None and right_path is not None and left_path == right_path


def file_agent_path(spec: str) -> Path | None:
    if not spec.startswith("file:"):
        return None
    path_text, separator, _function = spec.removeprefix("file:").rpartition(":")
    if not separator:
        path_text = spec.removeprefix("file:")
    try:
        return Path(path_text).expanduser().resolve()
    except OSError:
        return None


def agent_sidecar_path(agent_profile: dict[str, Any]) -> Path | None:
    agent_path = agent_file_path(agent_profile)
    return agent_path.parent / "study_rules.json" if agent_path is not None and agent_path.is_file() else None


def agent_file_path(agent_profile: dict[str, Any]) -> Path | None:
    explicit_path = str(agent_profile.get("agent_path") or "").strip()
    return Path(explicit_path).expanduser().resolve() if explicit_path else file_agent_path(str(agent_profile.get("spec") or ""))


def agent_key(agent_profile: dict[str, Any]) -> str:
    name = re.sub(r"[^a-z0-9]+", "-", str(agent_profile.get("name") or "agent").lower()).strip("-") or "agent"
    digest = hashlib.sha256(str(agent_profile.get("spec") or name).encode("utf-8")).hexdigest()[:10]
    return f"{name[:48]}-{digest}"


def public_agent_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": str(profile.get("name") or ""),
        "spec": str(profile.get("spec") or ""),
        "deck": str(profile.get("deck") or ""),
        "source": str(profile.get("source") or ""),
        "ready": bool(profile.get("ready")),
    }


def study_limitations(has_episode: bool) -> list[str]:
    limits = [
        "Text logs contain only recorded public actions and cannot prove every action that was legal.",
        "Hidden hands, deck order, and face-down Prize identities are never inferred as known facts.",
    ]
    if not has_episode:
        limits.append("Attach the matching decision JSONL to audit legal options, scores, and missed actions.")
    return limits


def finding_summary(findings: Iterable[Any]) -> dict[str, Any]:
    rows = [item.to_dict() if isinstance(item, StudyFinding) else item for item in findings]
    by_status = {status: sum(1 for item in rows if item.get("status") == status) for status in DECISIONS}
    by_severity = {
        severity: sum(1 for item in rows if item.get("severity") == severity)
        for severity in ("critical", "high", "medium", "low")
    }
    return {"total": len(rows), "by_status": by_status, "by_severity": by_severity}


def deduplicate_findings(findings: Iterable[StudyFinding]) -> list[StudyFinding]:
    unique: dict[str, StudyFinding] = {}
    for finding in findings:
        unique.setdefault(finding.id, finding)
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return sorted(unique.values(), key=lambda item: (severity_order.get(item.severity, 4), item.turn, item.id))


def read_episode_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Decision trace line {line_number} is invalid JSON: {exc}") from exc
        if isinstance(value, dict):
            rows.append(value)
    return rows


def save_study(root: Path, payload: dict[str, Any]) -> None:
    study_id = validate_study_id(str(payload.get("study_id") or ""))
    atomic_write_json(root / "data" / "studies" / f"{study_id}.json", payload)


def load_study(root: Path, study_id: str) -> dict[str, Any]:
    study_id = validate_study_id(study_id)
    path = root / "data" / "studies" / f"{study_id}.json"
    if not path.is_file():
        raise ValueError("Study session does not exist.")
    payload = read_json(path, default={})
    if not payload:
        raise ValueError("Study session is unreadable.")
    return payload


def validate_study_id(value: str) -> str:
    if not re.fullmatch(r"study-[A-Za-z0-9-]{12,80}", value):
        raise ValueError("Invalid study id.")
    return value


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def atomic_write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    temporary.write_text(value, encoding="utf-8")
    os.replace(temporary, path)


def read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(default)
    return value if isinstance(value, dict) else dict(default)


def nonnegative_int(value: Any, default: int) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def float_or(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


__all__ = [
    "StudyFinding",
    "analyze_episode_rows",
    "analyze_log_replay",
    "create_study",
    "decide_finding",
    "list_checkpoints",
    "load_study",
    "install_runtime_hook",
    "memory_status",
    "restore_checkpoint",
    "validate_current_checkpoint",
    "validate_rule",
]
