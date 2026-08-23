"""The copilot teaches, interprets, compares and questions -- and nothing else."""

from __future__ import annotations

import unittest

from discovery.copilot import AbsoluteClaimError, Copilot, assert_comparative
from discovery.scoring.registry import fast_backend

from support import FLAT, PARTIAL, PERFECT, challenge


class ClaimGuardTests(unittest.TestCase):
    def test_absolute_biological_claims_are_blocked(self):
        for claim in (
            "This molecule binds strongly to the target protein.",
            "The candidate is effective against the disease.",
            "This sequence will cure the condition.",
            "The design is proven to work in vivo.",
            "This molecule works.",
        ):
            with self.subTest(claim=claim):
                with self.assertRaises(AbsoluteClaimError):
                    assert_comparative(claim)

    def test_calibrated_confidence_phrasing_is_blocked(self):
        for claim in ("Confidence: 87%", "confidence = 0.87", "We are 92% confident in this fold."):
            with self.subTest(claim=claim):
                with self.assertRaises(AbsoluteClaimError):
                    assert_comparative(claim)

    def test_comparative_phrasing_is_allowed(self):
        text = (
            "Within this challenge and scoring model, candidate B scored higher than "
            "candidates A and C because it recreated two more of the target's pairs."
        )
        self.assertEqual(assert_comparative(text), text)


class FourJobsTests(unittest.TestCase):
    def setUp(self):
        self.compiled = challenge()
        scorer = fast_backend()
        self.flat = scorer.score(self.compiled, FLAT)
        self.partial = scorer.score(self.compiled, PARTIAL)
        self.perfect = scorer.score(self.compiled, PERFECT)
        self.copilot = Copilot(self.compiled)

    def test_teach_explains_what_is_being_optimised(self):
        text = self.copilot.teach()
        self.assertIn("WHAT YOU ARE OPTIMIZING", text.upper())
        self.assertIn("WHAT THE SCORE IS NOT", text.upper())

    def test_teach_rejects_an_unknown_topic_rather_than_improvising(self):
        with self.assertRaises(KeyError):
            self.copilot.teach("binding kinetics")

    def test_interpret_reports_the_change_and_its_effect(self):
        text = self.copilot.interpret(self.partial, self.perfect)
        self.assertIn("changed 2 position(s)", text)
        self.assertIn("recovered 2 more of the target's pairs", text)

    def test_interpret_flags_a_fold_that_moved_somewhere_else(self):
        text = self.copilot.interpret(self.perfect, self.flat)
        self.assertIn("lost", text)

    def test_compare_ranks_against_the_participants_own_history(self):
        text = self.copilot.compare(self.perfect, [self.flat, self.partial])
        self.assertIn("outscored 2 of your previous 2 attempt(s)", text)

    def test_compare_asks_for_a_baseline_when_there_is_no_history(self):
        text = self.copilot.compare(self.perfect, [])
        self.assertIn("nothing to compare it against", text)

    def test_question_points_at_a_region_rather_than_giving_the_answer(self):
        text = self.copilot.question(self.flat)
        self.assertIn("What happens if you preserve region", text)
        for solution in self.compiled.held_out_answer()["held_out_solutions"]:
            self.assertNotIn(solution, text)

    def test_every_job_survives_the_claim_guard(self):
        assert_comparative(self.copilot.teach())
        assert_comparative(self.copilot.interpret(self.flat, self.perfect))
        assert_comparative(self.copilot.compare(self.perfect, [self.flat, self.partial]))
        assert_comparative(self.copilot.question(self.partial))


if __name__ == "__main__":
    unittest.main()
