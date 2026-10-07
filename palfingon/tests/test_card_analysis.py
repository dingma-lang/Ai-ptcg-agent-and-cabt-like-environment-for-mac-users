from __future__ import annotations

import unittest

from core.card_analysis import build_all_card_analyses, render_card_analysis_markdown
from core.priority_tables import canonical_name_from_id
from deck_profile import load_deck_ids


class CardAnalysisTests(unittest.TestCase):
    def test_every_deck_card_has_analysis(self):
        analyses = build_all_card_analyses()
        deck_names = {canonical_name_from_id(cid) for cid in load_deck_ids()}
        deck_names.discard("")
        self.assertEqual(deck_names, set(analyses))
        for name in deck_names:
            analysis = analyses[name]
            self.assertEqual(analysis.card_name, name)
            self.assertGreaterEqual(analysis.count_in_deck, 1)
            self.assertIsInstance(analysis.search_targets, list)
            self.assertIsInstance(analysis.searched_by, list)
            self.assertIsInstance(analysis.enables_cards, list)
            self.assertIsInstance(analysis.enabled_by_cards, list)
            self.assertIsInstance(analysis.policy_rules, list)

    def test_core_card_roles_and_energy_rules_are_explicit(self):
        analyses = build_all_card_analyses()

        self.assertIn("setup_basic", analyses["Finizen"].role)
        self.assertIn("Poffin before Lillie", analyses["Finizen"].policy_rules)
        self.assertIn("evolution_bridge", analyses["Palafin"].role)
        self.assertIn("Zero to Hero", analyses["Palafin"].policy_rules)
        self.assertIn("main_attacker", analyses["Palafin ex"].role)
        self.assertIn("Water to Palafin ex", analyses["Palafin ex"].policy_rules)
        self.assertIn("secondary_attacker", analyses["Mega Dragonite ex"].role)
        self.assertIn("Protect Lightning", analyses["Mega Dragonite ex"].policy_rules)

        water = analyses["Basic Water Energy"]
        lightning = analyses["Basic Lightning Energy"]
        self.assertIn("Palafin ex", water.enables_cards)
        self.assertIn("Water to Palafin ex", water.policy_rules)
        self.assertIn("Mega Dragonite", lightning.energy_requirements)
        self.assertIn("Protect Lightning", lightning.policy_rules)
        self.assertIn("Palafin", lightning.when_not_to_play)

    def test_search_and_switch_cards_have_human_use_notes(self):
        analyses = build_all_card_analyses()

        poffin = analyses["Buddy-Buddy Poffin"]
        self.assertIn("search_card", poffin.role)
        self.assertGreaterEqual(poffin.early_game_value, 90)
        self.assertIn("Finizen", poffin.search_targets)
        self.assertIn("Dratini", poffin.when_not_to_play)

        pokepad = analyses["Poke Pad"]
        self.assertIn("Palafin", pokepad.search_targets)
        self.assertIn("Palafin ex", pokepad.when_not_to_play)

        beach = analyses["Surfing Beach"]
        self.assertIn("switch_engine", beach.role)
        self.assertIn("stadium", beach.role)
        self.assertIn("Zero to Hero", beach.primary_use)

        balloon = analyses["Air Balloon"]
        self.assertIn("active Palafin", balloon.when_to_play)
        self.assertIn("attack-locked Palafin ex", balloon.when_to_play)
        self.assertIn("random", balloon.when_not_to_play.lower())

    def test_markdown_export_contains_expected_sections(self):
        text = render_card_analysis_markdown(build_all_card_analyses())
        self.assertIn("# Palaking Card-By-Card Analysis", text)
        self.assertIn("## Palafin ex", text)
        self.assertIn("## Mega Dragonite ex", text)
        self.assertIn("Air Balloon", text)


if __name__ == "__main__":
    unittest.main()
