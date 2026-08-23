"""The compute funnel: what earns expensive compute, and what gets recorded."""

from __future__ import annotations

import unittest

from discovery.funnel import FunnelLedger, evaluate, strategy_signature

from support import FLAT, PARTIAL, PERFECT, challenge


class PromotionTests(unittest.TestCase):
    def test_a_low_scoring_candidate_does_not_reach_the_expensive_tier(self):
        compiled = challenge()
        record = evaluate(compiled, FLAT)
        self.assertFalse(record.promoted)
        self.assertIn("below the promotion threshold", record.reason)
        self.assertIsNone(record.deep)

    def test_a_high_scoring_candidate_clears_the_threshold(self):
        record = evaluate(challenge(), PERFECT)
        self.assertTrue(record.promoted)
        self.assertIn("cleared the promotion threshold", record.reason)

    def test_promotion_without_a_deep_backend_queues_rather_than_pretends(self):
        record = evaluate(challenge(), PERFECT)
        if record.deep is None:
            self.assertIn("queued", record.deep_status)
            self.assertIn("no deep backend installed", record.deep_status)
        else:  # pragma: no cover - only when an energy model is installed
            self.assertIn("refined by", record.deep_status)

    def test_a_candidate_that_folds_identically_to_a_promoted_one_is_not_reprocessed(self):
        compiled = challenge()
        first = evaluate(compiled, PERFECT)
        # Different sequence, same predicted structure and same score.
        second = evaluate(compiled, "GCGCAAAAGCGC", cohort=[first.fast])
        self.assertFalse(second.promoted)
        self.assertIn("folds identically", second.reason)

    def test_an_illegal_candidate_is_rejected_before_any_compute_runs(self):
        from discovery.challenge.spec import SpecError

        with self.assertRaises(SpecError):
            evaluate(challenge(), "AAAAAAAAAAAA")


class StrategySignatureTests(unittest.TestCase):
    def test_an_untouched_sequence_reports_every_region_kept(self):
        compiled = challenge()
        signature = strategy_signature(compiled, compiled.sandbox.starting_point)
        self.assertEqual(signature, "A=kept B=kept C=kept")

    def test_editing_one_end_is_distinguishable_from_editing_the_other(self):
        compiled = challenge()
        start = compiled.sandbox.starting_point
        front = "GGGG" + start[4:]
        back = start[:8] + "CCCC"
        self.assertNotEqual(
            strategy_signature(compiled, front), strategy_signature(compiled, back)
        )
        self.assertTrue(strategy_signature(compiled, front).startswith("A=changed"))
        self.assertTrue(strategy_signature(compiled, back).endswith("C=changed"))


class LedgerTests(unittest.TestCase):
    def test_the_ledger_counts_evaluations_promotions_and_strategies(self):
        compiled = challenge()
        ledger = FunnelLedger()
        cohort = []
        for candidate in (compiled.sandbox.starting_point, FLAT, PARTIAL, PERFECT):
            record = evaluate(compiled, candidate, cohort=cohort, ledger=ledger)
            cohort.append(record.fast)

        summary = ledger.summary()
        self.assertEqual(summary["evaluations"], 4)
        self.assertEqual(summary["promoted"], 1)
        self.assertGreaterEqual(summary["distinct_strategy_clusters"], 2)
        self.assertEqual(summary["best_fast_score"], 10.0)

    def test_the_ledger_reports_which_strategy_was_most_common(self):
        compiled = challenge()
        ledger = FunnelLedger()
        for candidate in (PERFECT, "GCGCAAAAGCGC", FLAT):
            evaluate(compiled, candidate, ledger=ledger)
        name, count = ledger.summary()["largest_cluster"]
        self.assertIn("=", name)
        self.assertGreaterEqual(count, 1)

    def test_deep_tier_runs_are_counted_separately_from_promotions(self):
        compiled = challenge()
        ledger = FunnelLedger()
        evaluate(compiled, PERFECT, ledger=ledger)
        summary = ledger.summary()
        self.assertLessEqual(summary["deep_tier_runs"], summary["promoted"])


if __name__ == "__main__":
    unittest.main()
