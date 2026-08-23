"""The rules that make the docs' claims structural rather than aspirational.

Each test here corresponds to a promise made in docs/03-evidence-and-limitations.md
and docs/04-comparative-scoring.md. If one of these fails, the platform has
started making claims it cannot support.
"""

from __future__ import annotations

import dataclasses
import unittest

from discovery.copilot import assert_comparative
from discovery.evaluation.comparative import NoComparatorError, render
from discovery.evaluation.evidence import Strength, assess
from discovery.evaluation.limitations import (
    NOT_VALIDATED_FOOTER,
    LIMITATIONS_HEADER,
    limitations_for,
)
from discovery.scoring.base import Capability, ScoreResult
from discovery.scoring.registry import fast_backend

from support import FLAT, PARTIAL, PERFECT, FakeEnergyScorer, challenge


def _score(compiled, candidate, backend=None):
    return (backend or fast_backend()).score(compiled, candidate)


class NoCalibratedConfidenceTests(unittest.TestCase):
    def test_score_result_has_no_confidence_field(self):
        names = {f.name for f in dataclasses.fields(ScoreResult)}
        for forbidden in ("confidence", "probability", "certainty", "p_value"):
            self.assertNotIn(forbidden, names)

    def test_evidence_exposes_three_axes_and_no_combined_figure(self):
        compiled = challenge()
        evidence = assess(_score(compiled, PERFECT), cohort_size=8)
        self.assertEqual(len(evidence.rows()), 3)
        names = {f.name for f in dataclasses.fields(type(evidence))}
        for forbidden in ("overall", "combined", "confidence", "score"):
            self.assertNotIn(forbidden, names)

    def test_rendered_output_passes_the_claim_guard(self):
        compiled = challenge()
        cohort = [_score(compiled, c) for c in (FLAT, PARTIAL, PERFECT)]
        evidence = assess(cohort[-1], cohort_size=len(cohort))
        assert_comparative(render(cohort[-1], cohort, evidence))


class ComparisonRequiredTests(unittest.TestCase):
    def test_render_refuses_a_score_with_nothing_to_compare_against(self):
        compiled = challenge()
        lone = _score(compiled, PERFECT)
        evidence = assess(lone, cohort_size=0)
        with self.assertRaises(NoComparatorError):
            render(lone, [lone], evidence)

    def test_render_names_what_the_candidate_beat(self):
        compiled = challenge()
        cohort = [_score(compiled, c) for c in (FLAT, PARTIAL, PERFECT)]
        text = render(cohort[-1], cohort, assess(cohort[-1], cohort_size=3))
        self.assertIn("Ranked 1 of 3", text)
        self.assertIn("Scored higher than", text)
        self.assertIn("Within this challenge and scoring model", text)


class MandatoryBlocksTests(unittest.TestCase):
    def test_every_rendered_result_carries_limitations_and_the_footer(self):
        compiled = challenge()
        cohort = [_score(compiled, c) for c in (FLAT, PARTIAL, PERFECT)]
        for result in cohort[1:]:
            text = render(result, cohort, assess(result, cohort_size=3))
            self.assertIn(LIMITATIONS_HEADER, text)
            self.assertIn(NOT_VALIDATED_FOOTER, text)

    def test_limitations_always_include_what_no_computation_can_show(self):
        compiled = challenge()
        phrases = limitations_for(_score(compiled, PERFECT).modeled)
        self.assertIn("toxicity in humans", phrases)
        self.assertIn("clinical effectiveness", phrases)
        self.assertIn("laboratory confirmation", phrases)


class BackendDrivenHonestyTests(unittest.TestCase):
    """Removing a backend must weaken the platform's claims automatically."""

    def test_weaker_backend_produces_a_longer_limitations_list(self):
        compiled = challenge()
        weak = _score(compiled, PERFECT)
        strong = _score(compiled, PERFECT, backend=FakeEnergyScorer())
        self.assertGreater(
            len(limitations_for(weak.modeled)), len(limitations_for(strong.modeled))
        )
        self.assertIn("stacking energetics between adjacent pairs", limitations_for(weak.modeled))
        self.assertNotIn(
            "stacking energetics between adjacent pairs", limitations_for(strong.modeled)
        )

    def test_weaker_backend_produces_weaker_structural_evidence(self):
        compiled = challenge()
        weak = assess(_score(compiled, PERFECT), cohort_size=25)
        strong = assess(_score(compiled, PERFECT, backend=FakeEnergyScorer()), cohort_size=25)
        self.assertEqual(weak.structural_fit, Strength.LIMITED)
        self.assertEqual(strong.structural_fit, Strength.STRONG)

    def test_a_perfect_score_cannot_lift_evidence_above_what_the_model_supports(self):
        compiled = challenge()
        result = _score(compiled, PERFECT)
        self.assertEqual(result.display_score, 10.0)
        self.assertEqual(assess(result, cohort_size=50).structural_fit, Strength.LIMITED)

    def test_experimental_evidence_stays_none_without_laboratory_records(self):
        compiled = challenge()
        evidence = assess(_score(compiled, PERFECT), cohort_size=50, experimental_records=0)
        self.assertEqual(evidence.experimental_evidence, Strength.NONE)


class OverclaimTests(unittest.TestCase):
    def test_a_backend_cannot_declare_a_capability_no_computation_has(self):
        from discovery.scoring.base import validate_capabilities

        with self.assertRaises(ValueError) as caught:
            validate_capabilities(
                "wishful-backend", frozenset({Capability.CLINICAL_EFFECTIVENESS})
            )
        self.assertIn("no computational model can have", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
