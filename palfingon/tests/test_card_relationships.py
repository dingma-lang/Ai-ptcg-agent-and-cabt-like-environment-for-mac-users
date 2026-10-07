from __future__ import annotations

import unittest

from core.card_relationships import build_card_relationships


class CardRelationshipTests(unittest.TestCase):
    def setUp(self):
        self.relationships = build_card_relationships()

    def has_relationship(self, source: str, target: str, rel_type: str) -> bool:
        return any(
            rel.source_card == source and rel.target_card == target and rel.relationship_type == rel_type
            for rel in self.relationships
        )

    def test_evolution_and_zero_to_hero_relationships(self):
        self.assertTrue(self.has_relationship("Finizen", "Palafin", "evolves_into"))
        self.assertTrue(self.has_relationship("Palafin", "Palafin ex", "enables_zero_to_hero"))
        self.assertTrue(self.has_relationship("Dratini", "Dragonair", "evolves_into"))
        self.assertTrue(self.has_relationship("Dragonair", "Mega Dragonite ex", "evolves_into"))

    def test_search_cards_use_correct_targets(self):
        self.assertTrue(self.has_relationship("Buddy-Buddy Poffin", "Finizen", "searches"))
        self.assertTrue(self.has_relationship("Buddy-Buddy Poffin", "Tatsugiri", "searches"))
        self.assertTrue(self.has_relationship("Buddy-Buddy Poffin", "Dratini", "should_not_target"))

        self.assertTrue(self.has_relationship("Poke Pad", "Palafin", "searches"))
        self.assertTrue(self.has_relationship("Poke Pad", "Dratini", "finds_evolution_piece"))
        self.assertTrue(self.has_relationship("Poke Pad", "Palafin ex", "should_not_target"))

        self.assertTrue(self.has_relationship("Hilda", "Palafin", "finds_evolution_piece"))
        self.assertTrue(self.has_relationship("Hilda", "Basic Water Energy", "provides_energy"))
        self.assertTrue(self.has_relationship("Hilda", "Mega Dragonite ex", "finds_evolution_piece"))
        self.assertTrue(self.has_relationship("Hilda", "Basic Lightning Energy", "provides_energy"))

    def test_secret_box_and_petrel_relationships(self):
        self.assertTrue(self.has_relationship("Team Rocket's Petrel", "Poke Pad", "finds_exact_trainer"))
        self.assertTrue(self.has_relationship("Team Rocket's Petrel", "Secret Box", "finds_exact_trainer"))
        self.assertTrue(self.has_relationship("Team Rocket's Petrel", "Buddy-Buddy Poffin", "should_not_target"))

        self.assertTrue(self.has_relationship("Secret Box", "Poke Pad", "finds_exact_trainer"))
        self.assertTrue(self.has_relationship("Secret Box", "Air Balloon", "finds_tool"))
        self.assertTrue(self.has_relationship("Secret Box", "Hilda", "finds_supporter"))
        self.assertTrue(self.has_relationship("Secret Box", "Surfing Beach", "finds_stadium"))

    def test_switch_energy_and_recovery_relationships(self):
        for source in ("Surfing Beach", "Switch", "Air Balloon", "Mega Dragonite ex"):
            self.assertTrue(self.has_relationship(source, "Palafin", "enables_zero_to_hero"))
            self.assertTrue(self.has_relationship(source, "Palafin ex", "resets_attack_restriction"))

        self.assertTrue(self.has_relationship("Basic Water Energy", "Palafin ex", "enables_attack"))
        self.assertTrue(self.has_relationship("Basic Lightning Energy", "Mega Dragonite ex", "enables_attack"))
        self.assertTrue(self.has_relationship("Basic Lightning Energy", "Palafin ex", "should_not_target"))
        self.assertTrue(self.has_relationship("Crispin", "Mega Dragonite ex", "provides_energy"))
        self.assertTrue(self.has_relationship("Night Stretcher", "Basic Lightning Energy", "recovers_energy"))


if __name__ == "__main__":
    unittest.main()
