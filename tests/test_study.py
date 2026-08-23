"""The retrospective harness, and the labelling that keeps it honest."""

from __future__ import annotations

import unittest

from discovery.study.arms import (
    AIAloneArm,
    RandomSearchArm,
    SimulatedHumanArm,
    SimulatedHumanPlusAIArm,
    all_arms,
)
from discovery.study.retrospective import SIMULATION_CAVEAT, run_arm, run_study

from support import challenge


class ArmLabellingTests(unittest.TestCase):
    def test_the_two_human_arms_are_marked_as_simulations(self):
        self.assertTrue(SimulatedHumanArm().simulated)
        self.assertTrue(SimulatedHumanPlusAIArm().simulated)
        self.assertIn("SIMULATED", SimulatedHumanArm().label)
        self.assertIn("SIMULATED", SimulatedHumanPlusAIArm().label)

    def test_the_automated_arms_are_not_marked_as_simulated_humans(self):
        self.assertFalse(AIAloneArm().simulated)
        self.assertFalse(RandomSearchArm().simulated)

    def test_all_four_arms_are_present_and_distinct(self):
        names = [arm.name for arm in all_arms()]
        self.assertEqual(sorted(names), ["A", "B", "C", "D"])


class ArmBehaviourTests(unittest.TestCase):
    def test_every_arm_proposes_only_legal_candidates(self):
        compiled = challenge()
        for arm in all_arms():
            with self.subTest(arm=arm.name):
                result = run_arm(compiled, arm, budget=25, seed=7)
                self.assertEqual(result.evaluations, 25)

    def test_an_arm_run_is_reproducible_from_its_seed(self):
        compiled = challenge()
        first = run_arm(compiled, AIAloneArm(), budget=30, seed=11)
        second = run_arm(compiled, AIAloneArm(), budget=30, seed=11)
        self.assertEqual(first.best_score, second.best_score)
        self.assertEqual(first.evaluations_to_first_hit, second.evaluations_to_first_hit)

    def test_search_beats_the_starting_point(self):
        compiled = challenge()
        result = run_arm(compiled, AIAloneArm(), budget=60, seed=3)
        self.assertGreater(result.best_score, 0.4)

    def test_hits_are_measured_against_the_hidden_threshold(self):
        compiled = challenge()
        result = run_arm(compiled, RandomSearchArm(), budget=40, seed=5)
        threshold = compiled.held_out_answer()["hit_threshold"]
        if result.hits:
            self.assertGreaterEqual(result.best_score, threshold)
            self.assertIsNotNone(result.evaluations_to_first_hit)
        else:
            self.assertIsNone(result.evaluations_to_first_hit)


class ReportTests(unittest.TestCase):
    def test_the_report_carries_the_simulation_caveat(self):
        report = run_study(challenge(), budget=20, seed=42)
        self.assertIn(SIMULATION_CAVEAT, report.render())

    def test_the_report_states_that_recovery_is_not_biological_meaning(self):
        text = run_study(challenge(), budget=20, seed=42).render()
        self.assertIn("does not establish that any candidate is biologically meaningful", text)

    def test_the_report_never_prints_a_held_out_solution(self):
        compiled = challenge()
        text = run_study(compiled, budget=40, seed=42).render()
        for solution in compiled.held_out_answer()["held_out_solutions"]:
            self.assertNotIn(solution, text)

    def test_every_arm_runs_under_the_same_budget_and_seed(self):
        report = run_study(challenge(), budget=20, seed=42)
        self.assertEqual(len(report.arms), 4)
        for arm in report.arms:
            self.assertEqual(arm.evaluations, 20)


if __name__ == "__main__":
    unittest.main()
