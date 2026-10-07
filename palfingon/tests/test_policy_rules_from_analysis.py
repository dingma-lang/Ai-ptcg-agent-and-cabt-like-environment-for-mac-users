from __future__ import annotations

import unittest

from core.policy_rules_from_analysis import generate_policy_rules_from_card_analysis


class PolicyRulesFromAnalysisTests(unittest.TestCase):
    def test_required_policy_rules_are_generated(self):
        rules = generate_policy_rules_from_card_analysis()
        by_name = {rule.rule_name: rule for rule in rules}
        expected = {
            "Poffin before Lillie",
            "Poke Pad for Palafin",
            "Zero to Hero",
            "Water to Palafin ex",
            "Protect Lightning",
            "Surfing Beach switch loop",
            "Hilda package",
            "Crispin Dragonite energy",
            "Boss/Kieran KO math",
            "Bench Basic from hand",
            "Air Balloon active Palafin",
            "Lightning protected resource",
        }
        self.assertTrue(expected <= set(by_name))

    def test_rules_include_forbidden_bad_actions(self):
        rules = {rule.rule_name: rule for rule in generate_policy_rules_from_card_analysis()}

        self.assertIn("Play Lillie's Determination before Poffin", rules["Poffin before Lillie"].forbidden_actions)
        self.assertIn("Use Poke Pad for Palafin ex", rules["Poke Pad for Palafin"].forbidden_actions)
        self.assertIn("Attach Lightning to Palafin ex", rules["Water to Palafin ex"].forbidden_actions)
        self.assertIn("Lightning to Tatsugiri", rules["Protect Lightning"].forbidden_actions)
        self.assertIn("Attach Air Balloon randomly", rules["Air Balloon active Palafin"].forbidden_actions)

    def test_rule_priorities_preserve_combo_order(self):
        rules = {rule.rule_name: rule for rule in generate_policy_rules_from_card_analysis()}

        self.assertGreater(rules["Zero to Hero"].priority, rules["Poffin before Lillie"].priority)
        self.assertGreater(rules["Poffin before Lillie"].priority, rules["Poke Pad for Palafin"].priority)
        self.assertGreater(rules["Boss/Kieran KO math"].priority, rules["Protect Lightning"].priority)


if __name__ == "__main__":
    unittest.main()
