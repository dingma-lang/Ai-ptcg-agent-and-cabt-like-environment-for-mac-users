from __future__ import annotations

import unittest
from unittest.mock import patch

import deck_profile
from core.strategy_scope import deck_matches_hydreigon_gengar


class StrategyScopeTests(unittest.TestCase):
    def tearDown(self):
        deck_profile.reset_profile_cache()

    def test_hydreigon_signature_matches_current_deck_shape(self):
        deck_ids = [227, 227, 227, 228, 229, 229, 229, 59, 59, 771, 772, 772, 833, 834, 834] + [7] * 45
        self.assertTrue(deck_matches_hydreigon_gengar(deck_ids))

    def test_hydreigon_profile_is_ignored_for_non_matching_deck(self):
        old_profile = {
            "strategy_id": "hydreigon_mega_gengar",
            "archetype": "Hydreigon ex / Mega Gengar ex setup",
            "primary_attackers": [772, 229],
            "setup_pokemon": [227, 59, 833],
        }
        with patch("deck_profile._deck_ids_without_profile", return_value=[1] * 60), patch("deck_profile._read_json_profile", return_value=old_profile):
            deck_profile.reset_profile_cache()
            profile = deck_profile.load_profile()
            self.assertEqual(profile["strategy_id"], "generic")
            self.assertEqual(deck_profile.list_value("primary_attackers"), [])
            self.assertEqual(deck_profile.list_value("setup_pokemon"), [])

    def test_generic_profile_can_supply_new_deck_priorities(self):
        new_profile = {
            "strategy_id": "generic",
            "archetype": "Next deck",
            "primary_attackers": [999],
            "setup_pokemon": [111],
            "preferred_going": "first",
        }
        with patch("deck_profile._deck_ids_without_profile", return_value=[1] * 60), patch("deck_profile._read_json_profile", return_value=new_profile):
            deck_profile.reset_profile_cache()
            profile = deck_profile.load_profile()
            self.assertEqual(profile["archetype"], "Next deck")
            self.assertEqual(profile["preferred_going"], "first")
            self.assertEqual(deck_profile.list_value("primary_attackers"), [999])
            self.assertEqual(deck_profile.list_value("setup_pokemon"), [111])


if __name__ == "__main__":
    unittest.main()
