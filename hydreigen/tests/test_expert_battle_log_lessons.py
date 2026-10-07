from __future__ import annotations

import unittest

from agent import agent
from core.expert_trajectory import load_expert_trajectory, read_expert_log
from core.sequence_planner import build_sequence_plans
from decision_reason import build_decision_record
from policy import debug_scores, score_options
from state_eval import (
    AREA_ACTIVE,
    AREA_BENCH,
    AREA_DECK,
    AREA_DISCARD,
    AREA_HAND,
    CTX_ATTACH_TO,
    CTX_DAMAGE,
    CTX_MAIN,
    CTX_TO_HAND,
    OPT_ABILITY,
    OPT_ATTACK,
    OPT_ATTACH,
    OPT_CARD,
    OPT_END,
    OPT_EVOLVE,
    OPT_PLAY,
    normalize_state,
)
from tests.test_round_plan import card, current, player, pokemon


KO_LOG = [{"type": "KNOCK_OUT", "playerIndex": 0, "text": "Our Pokemon was Knocked Out."}]


class ExpertBattleLogLessonTests(unittest.TestCase):
    def test_expert_trajectory_has_reusable_events(self):
        trajectory = load_expert_trajectory()
        self.assertTrue(read_expert_log())
        self.assertGreaterEqual(len(trajectory.events), 5)
        phases = {event.phase for event in trajectory.events}
        self.assertIn("opening", phases)
        self.assertIn("mega_gengar_transition", phases)
        self.assertIn("hydreigon_closer", phases)
        self.assertTrue(any("Use Poffin aggressively" in rule for event in trajectory.events for rule in event.reusable_rules))

    def test_opening_secret_box_package(self):
        p0 = player(pokemon(833), bench=[pokemon(227)], hand=[card(1092), card(7), card(834), card(1121)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])
        plans = build_sequence_plans(normalize_state(obs))
        self.assertTrue(any(plan.name == "Opening Secret Box into Poffin package" for plan in plans))

    def test_opening_poffin_after_secret_box(self):
        p0 = player(pokemon(833), bench=[pokemon(227)], hand=[card(1086), card(1227)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 1}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])

    def test_poffin_targets_deino_and_gastly(self):
        p0 = player(pokemon(833), hand=[])
        obs = poffin_prompt(p0, [card(227), card(59), card(833)])
        self.assertEqual(set(agent(obs)), {0, 1})

    def test_fezandipiti_after_ko_before_supporter(self):
        p0 = player(pokemon(59), bench=[pokemon(140)], hand=[card(1227)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_ABILITY, "area": AREA_BENCH, "index": 0, "playerIndex": 0}], logs=KO_LOG)
        self.assertEqual(agent(obs), [1])

    def test_sacred_ash_restores_toxtricity_engine(self):
        p0 = player(pokemon(59), hand=[card(1129)])
        p0["discard"] = [card(833), card(834)]
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}], logs=KO_LOG)
        self.assertEqual(agent(obs), [0])

    def test_sacred_ash_rebuilds_hydreigon_line_after_ko(self):
        p0 = player(pokemon(772), hand=[card(1129), card(1227)])
        p0["discard"] = [card(227), card(228), card(229)]
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 1}, {"type": OPT_END}], logs=KO_LOG)
        self.assertEqual(agent(obs), [0])

    def test_mega_gengar_attack_line_evolves_first(self):
        p0 = player(pokemon(771), hand=[card(772), card(7)], bench=[pokemon(834)])
        obs = obs_main(
            p0,
            [
                {"type": OPT_EVOLVE, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                {"type": OPT_ATTACH, "area": AREA_HAND, "index": 1, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
            ],
        )
        self.assertEqual(agent(obs), [0])

    def test_void_gale_energy_move_to_hydreigon(self):
        p0 = player(pokemon(772, energies=[card(7), card(7)]), bench=[pokemon(229)], hand=[])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_ATTACH_TO,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "effect": card(772),
                "option": [
                    {"type": OPT_CARD, "area": AREA_ACTIVE, "index": 0, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_BENCH, "index": 0, "playerIndex": 0},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_hydreigon_obsidian_multi_prize_attack(self):
        attacks = __import__("card_db").get_db().get_card(229).attacks
        obsidian = next(attack for attack in attacks if attack.name == "Obsidian")
        p0 = player(pokemon(229, energies=[card(5), card(7), card(8), card(7)]), hand=[])
        p1 = player(
            pokemon(140, hp=120, max_hp=210, player=1),
            bench=[pokemon(227, hp=70, max_hp=70, player=1), pokemon(833, hp=70, max_hp=70, player=1)],
            hand=None,
            player_index=1,
        )
        obs = obs_main(p0, [{"type": OPT_ATTACK, "attackId": obsidian.attack_id}, {"type": OPT_END}], p1=p1)
        self.assertEqual(agent(obs), [0])
        plans = build_sequence_plans(normalize_state(obs))
        self.assertTrue(any(plan.name == "Hydreigon Obsidian closer" for plan in plans))

    def test_hydreigon_obsidian_bench_targets(self):
        p0 = player(pokemon(229), hand=[])
        p1 = player(
            pokemon(227, player=1),
            bench=[pokemon(140, hp=120, max_hp=210, player=1), pokemon(833, hp=70, max_hp=70, player=1), pokemon(772, hp=350, max_hp=350, player=1)],
            hand=None,
            player_index=1,
        )
        obs = {
            "current": current(p0=p0, p1=p1),
            "logs": [],
            "select": {
                "context": CTX_DAMAGE,
                "type": 1,
                "minCount": 2,
                "maxCount": 2,
                "effect": card(229),
                "option": [
                    {"type": OPT_CARD, "area": AREA_BENCH, "index": 0, "playerIndex": 1},
                    {"type": OPT_CARD, "area": AREA_BENCH, "index": 1, "playerIndex": 1},
                    {"type": OPT_CARD, "area": AREA_BENCH, "index": 2, "playerIndex": 1},
                ],
            },
        }
        self.assertEqual(set(agent(obs)), {0, 1})

    def test_late_energy_recycler(self):
        p0 = player(pokemon(227), hand=[card(1139)], prizes=2)
        p0["discard"] = [card(7), card(7), card(5), card(8)]
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])
        plans = build_sequence_plans(normalize_state(obs))
        self.assertTrue(any(plan.name == "Late rebuild line" for plan in plans))

    def test_night_stretcher_exact_psychic_energy(self):
        p0 = player(pokemon(229), hand=[card(1097)], prizes=2)
        p0["discard"] = [card(5)]
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])

    def test_pecharunt_risk_avoids_exposure_without_gain(self):
        p0 = player(pokemon(227), bench=[pokemon(141), pokemon(772)], hand=[])
        p1 = player(pokemon(229, player=1), prizes=2, hand=None, player_index=1)
        obs = obs_main(p0, [{"type": OPT_ABILITY, "area": AREA_BENCH, "index": 0, "playerIndex": 0}, {"type": OPT_END}], p1=p1)
        self.assertEqual(agent(obs), [1])

    def test_toxtricity_ability_not_attack(self):
        attacks = __import__("card_db").get_db().get_card(834).attacks
        p0 = player(pokemon(834, energies=[card(7), card(7), card(7)]), bench=[pokemon(772)], hand=[])
        p1 = player(pokemon(229, hp=330, max_hp=330, player=1), hand=None, player_index=1)
        obs = obs_main(
            p0,
            [{"type": OPT_ATTACK, "attackId": attacks[1].attack_id}, {"type": OPT_ABILITY, "area": AREA_ACTIVE, "index": 0, "playerIndex": 0}],
            p1=p1,
        )
        self.assertEqual(agent(obs), [1])

    def test_debug_record_includes_expert_lesson(self):
        p0 = player(pokemon(833), bench=[pokemon(227)], hand=[card(1086)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}])
        state = normalize_state(obs)
        scores = score_options(state)
        record = build_decision_record(state, scores, [0])
        self.assertEqual(record["expert_lesson_status"], "matched")
        self.assertTrue(any(line.startswith("Expert lesson matched:") for line in record["expert_debug_lines"]))
        self.assertIn("expert_matches", record)
        self.assertTrue(any(match["lesson_id"] == "LESSON_OPENING_POFFIN" for match in record["expert_matches"]))


def obs_main(p0, options, p1=None, logs=None):
    return {
        "current": current(p0=p0, p1=p1),
        "logs": logs or [],
        "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": options},
    }


def poffin_prompt(p0, deck):
    return {
        "current": current(p0=p0),
        "logs": [],
        "select": {
            "context": CTX_TO_HAND,
            "type": 1,
            "minCount": 2,
            "maxCount": 2,
            "effect": card(1086),
            "deck": deck,
            "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": idx, "playerIndex": 0} for idx in range(len(deck))],
        },
    }


if __name__ == "__main__":
    unittest.main()
