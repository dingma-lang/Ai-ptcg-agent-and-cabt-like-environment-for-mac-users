from __future__ import annotations

import json
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace

from cabt_local.study import (
    analyze_episode_rows,
    create_study,
    decide_finding,
    install_runtime_hook,
    list_checkpoints,
    restore_checkpoint,
    validate_current_checkpoint,
)


LOG = """Setup
Alice played Finizen to the Active Spot.
Bob played Finizen to the Active Spot.
Alice's Turn
Alice drew Palafin.
Alice ended their turn.
Bob's Turn
Bob didn't take an action in time.
Alice wins.
"""


def make_agent(root: Path, name: str) -> dict:
    folder = root / name
    folder.mkdir(parents=True)
    agent_path = folder / "agent.py"
    agent_path.write_text("def agent(obs_dict):\n    return []\n", encoding="utf-8")
    return {
        "name": name,
        "spec": f"file:{agent_path}:agent",
        "deck": "",
        "source": "test",
        "ready": True,
    }


class StudyTests(unittest.TestCase):
    def test_log_analysis_preserves_uncertainty_and_finds_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = make_agent(root, "Palaking")
            study = create_study(root, log_text=LOG, agent_profile=profile)
        categories = {finding["category"] for finding in study["findings"]}
        self.assertIn("empty_turn_review", categories)
        self.assertIn("timeout", categories)
        empty = next(finding for finding in study["findings"] if finding["category"] == "empty_turn_review")
        self.assertEqual(empty["confidence"], "medium")
        self.assertIn("decision trace", empty["explanation"])

    def test_episode_analysis_detects_illegal_output_and_terminal_skip(self) -> None:
        profile_spec = "file:/tmp/agent.py:agent"
        base = {
            "agent_id": profile_spec,
            "player": 0,
            "turn": 4,
            "observation": {
                "select": {
                    "minCount": 1,
                    "maxCount": 1,
                    "option": [{"name": "End"}, {"name": "Attach Water Energy"}],
                }
            },
            "legal_options": [{"name": "End"}, {"name": "Attach Water Energy"}],
            "agent_trace": {
                "reason": "Pass",
                "legal_options": [
                    {"index": 0, "category": "END_TURN", "score": -1000, "reason": "Pass"},
                    {"index": 1, "category": "ATTACH_ENERGY", "score": 2200, "reason": "Prepare attacker"},
                ],
            },
        }
        valid = dict(base, selected_indexes=[0])
        invalid = dict(base, turn=5, selected_indexes=[9])
        findings = analyze_episode_rows([valid, invalid], profile_spec)
        categories = {finding.category for finding in findings}
        self.assertIn("terminal_checklist", categories)
        self.assertIn("score_override_review", categories)
        self.assertIn("illegal_selection", categories)

    def test_accept_creates_agent_specific_checkpoint_and_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = make_agent(root, "Palaking")
            study = create_study(root, log_text=LOG, agent_profile=profile)
            finding = next(item for item in study["findings"] if item["actionable"])
            result = decide_finding(
                root,
                study_id=study["study_id"],
                finding_id=finding["id"],
                decision="accepted",
                agent_profile=profile,
                reviewer_note="Confirmed from replay.",
            )
            sidecar = root / "Palaking" / "study_rules.json"
            sidecar_data = json.loads(sidecar.read_text(encoding="utf-8"))
            checkpoints = list_checkpoints(root, profile)
        self.assertEqual(result["checkpoint"]["checkpoint_id"], "checkpoint_0001")
        self.assertEqual(len(sidecar_data["accepted_rules"]), 1)
        self.assertEqual(len(checkpoints), 1)

    def test_rejection_does_not_change_agent_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = make_agent(root, "Palaking")
            study = create_study(root, log_text=LOG, agent_profile=profile)
            finding = next(item for item in study["findings"] if item["actionable"])
            result = decide_finding(
                root,
                study_id=study["study_id"],
                finding_id=finding["id"],
                decision="rejected",
                agent_profile=profile,
            )
            repeated = create_study(root, log_text=LOG, agent_profile=profile)
        saved = next(item for item in result["study"]["findings"] if item["id"] == finding["id"])
        self.assertEqual(saved["status"], "rejected")
        repeated_item = next(item for item in repeated["findings"] if item["category"] == finding["category"])
        self.assertEqual(repeated_item["status"], "rejected")
        self.assertFalse((root / "Palaking" / "study_rules.json").exists())

    def test_memory_is_isolated_between_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = make_agent(root, "Palaking")
            second = make_agent(root, "Zoroark")
            study = create_study(root, log_text=LOG, agent_profile=first)
            finding = next(item for item in study["findings"] if item["actionable"])
            decide_finding(
                root,
                study_id=study["study_id"],
                finding_id=finding["id"],
                decision="accepted",
                agent_profile=first,
            )
            self.assertEqual(len(list_checkpoints(root, first)), 1)
            self.assertEqual(list_checkpoints(root, second), [])

    def test_restore_creates_new_immutable_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = make_agent(root, "Palaking")
            study = create_study(root, log_text=LOG, agent_profile=profile)
            finding = next(item for item in study["findings"] if item["actionable"])
            decide_finding(
                root,
                study_id=study["study_id"],
                finding_id=finding["id"],
                decision="accepted",
                agent_profile=profile,
            )
            restored = restore_checkpoint(root, profile, "baseline")
            sidecar = json.loads((root / "Palaking" / "study_rules.json").read_text(encoding="utf-8"))
            checkpoints = list_checkpoints(root, profile)
        self.assertEqual(restored["checkpoint_id"], "checkpoint_0002")
        self.assertEqual(restored["restored_checkpoint"], "baseline")
        self.assertEqual(sidecar["accepted_rules"], [])
        self.assertEqual(len(checkpoints), 2)

    def test_workspace_runtime_applies_only_supported_rule_conditions(self) -> None:
        workspace = Path(__file__).resolve().parents[2]
        runtime_path = workspace / "Palaking" / "study_rule_runtime.py"
        module_spec = importlib.util.spec_from_file_location("palaking_study_rule_runtime_test", runtime_path)
        self.assertIsNotNone(module_spec)
        self.assertIsNotNone(module_spec.loader)
        runtime = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(runtime)

        classifier = ModuleType("action_classifier")
        classifier.classify_legal_option = lambda _state, _option, index: SimpleNamespace(
            category="END_TURN" if index == 0 else "ATTACH_ENERGY",
            card_name="",
            target_name="",
        )
        previous = sys.modules.get("action_classifier")
        sys.modules["action_classifier"] = classifier
        try:
            state = SimpleNamespace(options=["End", "Attach"])
            runtime.load_study_rules = lambda: [
                {
                    "target_category": "END_TURN",
                    "effect": "avoid",
                    "weight": -2500,
                    "conditions": {"useful_legal_action_exists": True},
                }
            ]
            self.assertEqual(runtime.apply_study_rules(state, "End", 0, 100.0), -2400.0)
            runtime.load_study_rules = lambda: [
                {
                    "target_category": "END_TURN",
                    "effect": "avoid",
                    "weight": -2500,
                    "conditions": {"unsupported_condition": True},
                }
            ]
            self.assertEqual(runtime.apply_study_rules(state, "End", 0, 100.0), 100.0)
        finally:
            if previous is None:
                sys.modules.pop("action_classifier", None)
            else:
                sys.modules["action_classifier"] = previous

    def test_structural_validation_checks_sidecar_hook_and_python_syntax(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = make_agent(root, "Palaking")
            agent_root = root / "Palaking"
            (agent_root / "policy.py").write_text('RULE_PATH = "study_rules.json"\n', encoding="utf-8")
            (agent_root / "study_rule_runtime.py").write_text("def load_study_rules():\n    return []\n", encoding="utf-8")
            study = create_study(root, log_text=LOG, agent_profile=profile)
            finding = next(item for item in study["findings"] if item["actionable"])
            decide_finding(
                root,
                study_id=study["study_id"],
                finding_id=finding["id"],
                decision="accepted",
                agent_profile=profile,
            )
            validation = validate_current_checkpoint(root, profile)
        self.assertEqual(validation["status"], "structural_pass")
        self.assertEqual(validation["match_validation"], "not_run")

    def test_new_agent_can_validate_before_first_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = make_agent(root, "NewAgent")
            validation = validate_current_checkpoint(root, profile)
        self.assertEqual(validation["status"], "baseline_pass")
        self.assertEqual(validation["errors"], [])
        self.assertIn("first checkpoint", validation["message"])

    def test_compatible_imported_agent_can_install_runtime_hook_safely(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agent_root = root / "data" / "imported_agents" / "ImportedAgent"
            agent_root.mkdir(parents=True)
            agent_path = agent_root / "agent.py"
            agent_path.write_text("def agent(obs_dict):\n    return []\n", encoding="utf-8")
            policy_path = agent_root / "policy.py"
            original = (
                "def apply_action_reasoning(state, option, option_index, base_score):\n"
                "    score = base_score\n"
                "    return score\n"
            )
            policy_path.write_text(original, encoding="utf-8")
            profile = {
                "name": "Imported Agent",
                "spec": f"file:{agent_path}:agent",
                "agent_path": str(agent_path),
                "deck": "",
                "source": "imported",
                "ready": True,
            }
            first = install_runtime_hook(root, profile)
            second = install_runtime_hook(root, profile)
            patched = policy_path.read_text(encoding="utf-8")
            backup = Path(first["backup_path"]) / "policy_before_study_hook.py"
            backup_text = backup.read_text(encoding="utf-8")
        self.assertTrue(first["runtime_integration"]["active"])
        self.assertTrue(second["runtime_integration"]["active"])
        self.assertEqual(patched.count("# STUDY_RULE_RUNTIME_HOOK"), 1)
        self.assertEqual(backup_text, original)


if __name__ == "__main__":
    unittest.main()
