from __future__ import annotations

import unittest

from agent import agent
from card_db import get_db
from core.round_plan import EARLY, LATE, MID, build_round_plan
from policy import debug_scores
from state_eval import AREA_ACTIVE, AREA_BENCH, AREA_DECK, AREA_HAND, CTX_MAIN, CTX_TO_HAND, OPT_ABILITY, OPT_ATTACK, OPT_CARD, OPT_END, OPT_EVOLVE, OPT_PLAY, normalize_state


def card(cid, player=0):
    return {"id": cid, "serial": cid, "playerIndex": player}


def pokemon(cid, hp=None, max_hp=None, energies=None, player=0):
    info = get_db().get_card(cid)
    max_hp = max_hp if max_hp is not None else (info.hp if info else 100)
    hp = hp if hp is not None else max_hp
    return {
        "id": cid,
        "serial": cid,
        "playerIndex": player,
        "hp": hp,
        "maxHp": max_hp,
        "appearThisTurn": False,
        "energies": energies or [],
        "energyCards": [],
        "tools": [],
        "preEvolution": [],
    }


def player(active=None, bench=None, hand=None, prizes=6, player_index=0):
    return {
        "active": [active] if active is not None else [],
        "bench": bench or [],
        "benchMax": 5,
        "deckCount": 40,
        "discard": [],
        "prize": [None] * prizes,
        "handCount": len(hand or []),
        "hand": hand or [],
        "poisoned": False,
        "burned": False,
        "asleep": False,
        "paralyzed": False,
        "confused": False,
    }


def current(p0=None, p1=None, **overrides):
    data = {
        "turn": 5,
        "turnActionCount": 0,
        "yourIndex": 0,
        "firstPlayer": 0,
        "supporterPlayed": False,
        "stadiumPlayed": False,
        "energyAttached": False,
        "retreated": False,
        "result": -1,
        "stadium": [],
        "looking": None,
        "players": [
            p0 or player(pokemon(59), hand=[]),
            p1 or player(pokemon(227, player=1), hand=None, player_index=1),
        ],
    }
    data.update(overrides)
    return data


def obs_for(p0, options, p1=None, logs=None, prizes=6):
    return {
        "current": current(p0=p0, p1=p1 or player(pokemon(227, player=1), prizes=prizes, hand=None, player_index=1)),
        "logs": logs or [],
        "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": options},
    }


class RoundPlanTests(unittest.TestCase):
    def test_early_empty_bench_poffin_establishes_basics(self):
        p0 = player(pokemon(59), hand=[card(1086)])
        obs = obs_for(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}])
        plan = build_round_plan(normalize_state(obs), None, None)
        self.assertEqual(plan.game_stage, EARLY)
        self.assertEqual(plan.board_goal, "establish basics")
        self.assertEqual(agent(obs), [0])

    def test_early_rare_candy_hydreigon_available_is_first(self):
        p0 = player(pokemon(227), hand=[card(1079), card(229)])
        obs = obs_for(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}])
        plan = build_round_plan(normalize_state(obs), None, None)
        self.assertIn("Hydreigon", plan.primary_attacker_goal)
        self.assertEqual(agent(obs), [0])

    def test_ready_mega_gengar_line_can_beat_slower_hydreigon_setup(self):
        p0 = player(pokemon(771), bench=[pokemon(227)], hand=[card(772), card(1079), card(229)])
        obs = obs_for(
            p0,
            [
                {"type": OPT_EVOLVE, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                {"type": OPT_PLAY, "index": 1},
            ],
        )
        self.assertEqual(agent(obs), [0])

    def test_mid_hydreigon_online_haunter_ready_raises_mega_gengar(self):
        p0 = player(pokemon(229, energies=[card(7), card(8), card(5)]), bench=[pokemon(771)], hand=[card(772)], prizes=4)
        p1 = player(pokemon(229, player=1), prizes=4, hand=None, player_index=1)
        obs = obs_for(
            p0,
            [{"type": OPT_EVOLVE, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_BENCH, "inPlayIndex": 0}, {"type": OPT_END}],
            p1=p1,
        )
        plan = build_round_plan(normalize_state(obs), None, None)
        self.assertEqual(plan.game_stage, MID)
        self.assertEqual(agent(obs), [0])

    def test_mid_plan_names_mega_gengar_as_real_damage_dealer(self):
        p0 = player(pokemon(771), bench=[pokemon(227)], hand=[card(772), card(1079), card(229)], prizes=4)
        p1 = player(pokemon(229, player=1), prizes=4, hand=None, player_index=1)
        obs = obs_for(p0, [], p1=p1)
        plan = build_round_plan(normalize_state(obs), None, None)
        self.assertIn("Mega Gengar", plan.primary_attacker_goal + " " + plan.evolution_goal + " " + plan.energy_goal)
        self.assertNotIn("complete Hydreigon first", plan.energy_goal)

    def test_mid_after_ko_uses_fezandipiti_recovery(self):
        p0 = player(pokemon(59), bench=[pokemon(140)], hand=[card(1227)], prizes=4)
        p1 = player(pokemon(229, player=1), prizes=4, hand=None, player_index=1)
        obs = obs_for(
            p0,
            [{"type": OPT_PLAY, "index": 0}, {"type": OPT_ABILITY, "area": AREA_BENCH, "index": 0, "playerIndex": 0}],
            p1=p1,
            logs=[{"type": "KNOCK_OUT", "playerIndex": 0, "text": "Your Pokemon was Knocked Out."}],
        )
        self.assertEqual(agent(obs), [1])

    def test_mid_pecharunt_pivots_to_darkness_attacker(self):
        p0 = player(pokemon(59, hp=30, max_hp=70), bench=[pokemon(141), pokemon(229, energies=[card(7), card(7)])], hand=[], prizes=4)
        p1 = player(pokemon(229, player=1), prizes=4, hand=None, player_index=1)
        obs = obs_for(p0, [{"type": OPT_ABILITY, "area": AREA_BENCH, "index": 0, "playerIndex": 0}, {"type": OPT_END}], p1=p1)
        self.assertEqual(agent(obs), [0])

    def test_late_does_not_bench_fezandipiti_for_final_prize_liability(self):
        p0 = player(pokemon(229, energies=[card(7), card(8), card(5)]), bench=[pokemon(227), pokemon(59)], hand=[card(140)], prizes=2)
        p1 = player(pokemon(227, player=1), prizes=2, hand=None, player_index=1)
        obs = obs_for(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}], p1=p1)
        plan = build_round_plan(normalize_state(obs), None, None)
        self.assertEqual(plan.game_stage, LATE)
        self.assertEqual(agent(obs), [1])

    def test_opponent_ex_heavy_increases_mega_gengar_score(self):
        ex_obs = mega_gengar_score_obs(player(pokemon(229, player=1), bench=[pokemon(140, player=1)], prizes=4, hand=None, player_index=1))
        one_prize_obs = mega_gengar_score_obs(player(pokemon(227, player=1), bench=[pokemon(59, player=1)], prizes=4, hand=None, player_index=1))
        ex_score = score_for_option(ex_obs, 0)
        one_prize_score = score_for_option(one_prize_obs, 0)
        self.assertGreater(ex_score, one_prize_score)

    def test_opponent_one_prize_lowers_mega_gengar_priority(self):
        obs = mega_gengar_score_obs(player(pokemon(227, player=1), bench=[pokemon(59, player=1)], prizes=4, hand=None, player_index=1))
        plan = build_round_plan(normalize_state(obs), None, None)
        self.assertTrue(plan.opponent_model.likely_one_prize)
        self.assertLess(plan.weights["mega_gengar"], 700.0)

    def test_round_plan_blocks_pass_when_resources_and_danger_need_checks(self):
        p0 = player(pokemon(59, hp=30, max_hp=70), hand=[card(1227), card(1086)], prizes=6)
        p1 = player(pokemon(772, energies=[card(7), card(7)], player=1), prizes=6, hand=None, player_index=1)
        obs = obs_for(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 1}, {"type": OPT_END}], p1=p1)
        plan = build_round_plan(normalize_state(obs), None, None)
        self.assertFalse(plan.pass_allowed)
        self.assertTrue(plan.supporter_goal)
        self.assertTrue(plan.energy_goal)
        self.assertTrue(plan.evolution_goal)
        self.assertTrue(plan.search_goal)
        self.assertTrue(plan.danger_goal)
        self.assertTrue(plan.attack_goal)

    def test_supporter_unused_weak_hand_uses_lillie_before_pass(self):
        p0 = player(pokemon(59), hand=[card(1227), card(1182)])
        obs = obs_for(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])


def mega_gengar_score_obs(p1):
    p0 = player(pokemon(229, energies=[card(7), card(8), card(5)]), bench=[pokemon(771)], hand=[card(772)], prizes=4)
    return obs_for(
        p0,
        [{"type": OPT_EVOLVE, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_BENCH, "inPlayIndex": 0}, {"type": OPT_END}],
        p1=p1,
    )


def score_for_option(obs, index):
    _, rows = debug_scores(obs)
    for idx, score, _ in rows:
        if idx == index:
            return score
    raise AssertionError(f"missing option {index}")


if __name__ == "__main__":
    unittest.main()
