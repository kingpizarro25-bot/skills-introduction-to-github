"""The fast tier: what it computes, and what it refuses to pretend."""

from __future__ import annotations

import unittest

from discovery.scoring.base import Capability, Tier
from discovery.scoring.nussinov import NussinovScorer, fold
from discovery.scoring.registry import deep_backend, deployment_report, fast_backend
from discovery.scoring.structure import agreement, parse_pairs, render_pairs

from support import FLAT, PARTIAL, PERFECT, challenge


class FoldingTests(unittest.TestCase):
    def test_a_complementary_stem_folds_into_the_expected_hairpin(self):
        self.assertEqual(fold("GGGGAAAACCCC"), "((((....))))")

    def test_a_sequence_with_no_complementary_partners_forms_no_pairs(self):
        self.assertEqual(fold("ACACACACACAC"), "............")

    def test_a_loop_shorter_than_the_minimum_turn_cannot_close(self):
        # G and C are complementary but only two bases separate them.
        self.assertEqual(fold("GAAC"), "....")

    def test_folding_is_deterministic(self):
        sequence = "GCGUAAGCUACG"
        self.assertEqual(fold(sequence), fold(sequence))


class AgreementTests(unittest.TestCase):
    def test_matching_the_target_exactly_scores_one(self):
        self.assertEqual(agreement("((((....))))", "((((....))))")["fraction"], 1.0)

    def test_pairing_with_the_wrong_partner_does_not_count_as_correct(self):
        # Same bracket count, entirely different partners.
        stats = agreement("....((....))", "((....))....")
        self.assertEqual(stats["correct_pairs"], 0)
        self.assertLess(stats["fraction"], 0.5)

    def test_counts_are_reported_alongside_the_fraction(self):
        stats = agreement("((((....))))", "((((....))))")
        self.assertEqual(stats["correct_pairs"], 4)
        self.assertEqual(stats["positions_correct"], 12)
        self.assertEqual(stats["positions_total"], 12)

    def test_pairs_round_trip_through_dot_bracket(self):
        structure = "((((....))))"
        self.assertEqual(render_pairs(parse_pairs(structure), len(structure)), structure)

    def test_unbalanced_structures_are_rejected(self):
        with self.assertRaises(ValueError):
            parse_pairs("(((")


class ScorerTests(unittest.TestCase):
    def test_the_target_sequence_scores_ten_and_the_flat_one_does_not(self):
        compiled = challenge()
        scorer = NussinovScorer()
        self.assertEqual(scorer.score(compiled, PERFECT).display_score, 10.0)
        self.assertLess(scorer.score(compiled, FLAT).display_score, 5.0)

    def test_scores_are_ordered_the_way_the_structures_are(self):
        compiled = challenge()
        scorer = NussinovScorer()
        flat = scorer.score(compiled, FLAT).raw_score
        partial = scorer.score(compiled, PARTIAL).raw_score
        perfect = scorer.score(compiled, PERFECT).raw_score
        self.assertLess(flat, partial)
        self.assertLess(partial, perfect)

    def test_the_fast_scorer_declares_only_what_it_actually_models(self):
        self.assertEqual(NussinovScorer().capabilities, frozenset({Capability.BASE_PAIRING}))

    def test_the_result_carries_the_counts_the_copilot_explains_scores_with(self):
        detail = NussinovScorer().score(challenge(), PERFECT).detail
        self.assertEqual(detail["predicted_structure"], "((((....))))")
        self.assertEqual(detail["correct_pairs"], 4)


class RegistryTests(unittest.TestCase):
    def test_a_fast_backend_is_always_available(self):
        self.assertIs(fast_backend().tier, Tier.FAST)

    def test_the_deep_tier_reports_absence_rather_than_falling_back(self):
        # This environment ships no energy model. The registry must say so
        # instead of quietly returning the fast scorer under a deep label.
        backend = deep_backend()
        if backend is None:
            self.assertFalse(deployment_report()["deep_tier_available"])
        else:  # pragma: no cover - only when ViennaRNA is installed
            self.assertIs(backend.tier, Tier.DEEP)

    def test_unmodelled_capabilities_are_the_complement_of_what_is_installed(self):
        report = deployment_report()
        self.assertEqual(report["modeled"] & report["unmodeled"], frozenset())
        self.assertIn(Capability.HUMAN_TOXICITY, report["unmodeled"])


if __name__ == "__main__":
    unittest.main()
