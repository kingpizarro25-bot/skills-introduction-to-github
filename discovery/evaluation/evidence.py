"""Evidence strength: the replacement for a single confidence percentage.

`Confidence: 87%` asserts a calibrated probability. This platform does not have
one, and showing a number that looks like one is worse than showing nothing --
it borrows the authority of a measurement the platform never made.

So certainty is reported on three axes that are allowed to disagree, and there is
deliberately no function anywhere that collapses them into one figure.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, FrozenSet, Sequence

from ..scoring.base import Capability, ScoreResult


class Strength(Enum):
    NONE = "None"
    LIMITED = "Limited"
    MODERATE = "Moderate"
    STRONG = "Strong"


@dataclass(frozen=True)
class EvidenceStrength:
    """Three independent readings. Never averaged, never weighted together."""

    structural_fit: Strength
    comparison_evidence: Strength
    experimental_evidence: Strength
    notes: Dict[str, str]

    def rows(self) -> Sequence[tuple]:
        return (
            ("Structural fit", self.structural_fit, self.notes.get("structural_fit", "")),
            ("Comparison evidence", self.comparison_evidence, self.notes.get("comparison_evidence", "")),
            ("Experimental evidence", self.experimental_evidence, self.notes.get("experimental_evidence", "")),
        )


def assess(
    result: ScoreResult,
    cohort_size: int,
    experimental_records: int = 0,
) -> EvidenceStrength:
    """Derive evidence strength from what was modelled and what was compared.

    Structural fit is capped by the backend's declared capabilities before the
    score is even considered: a high score from a model that only counts base
    pairs is still weak evidence, and no amount of scoring well can lift it.
    """
    cap, cap_note = _structural_ceiling(result.modeled)
    fit = _min_strength(cap, _score_band(result.raw_score))
    if fit is cap and _score_band(result.raw_score).value != cap.value:
        cap_note = f"{cap_note} (capped by what {result.backend} models)"

    comparison, comparison_note = _comparison_band(cohort_size)
    experimental, experimental_note = _experimental_band(experimental_records)

    return EvidenceStrength(
        structural_fit=fit,
        comparison_evidence=comparison,
        experimental_evidence=experimental,
        notes={
            "structural_fit": cap_note,
            "comparison_evidence": comparison_note,
            "experimental_evidence": experimental_note,
        },
    )


_ORDER = (Strength.NONE, Strength.LIMITED, Strength.MODERATE, Strength.STRONG)


def _min_strength(a: Strength, b: Strength) -> Strength:
    return a if _ORDER.index(a) <= _ORDER.index(b) else b


def _structural_ceiling(modeled: FrozenSet[Capability]) -> tuple:
    energetics = Capability.STACKING_ENERGETICS in modeled
    entropy = Capability.LOOP_ENTROPY in modeled
    ensemble = Capability.ENSEMBLE_DIVERSITY in modeled

    if energetics and entropy and ensemble:
        return Strength.STRONG, "energy model with loop terms and fold ensemble"
    if energetics and entropy:
        return Strength.MODERATE, "energy model, single predicted fold only"
    if Capability.BASE_PAIRING in modeled:
        return Strength.LIMITED, "pair counting only, no energetics"
    return Strength.NONE, "backend models no structural physics"


def _score_band(raw: float) -> Strength:
    if raw >= 0.95:
        return Strength.STRONG
    if raw >= 0.75:
        return Strength.MODERATE
    if raw > 0.0:
        return Strength.LIMITED
    return Strength.NONE


def _comparison_band(cohort_size: int) -> tuple:
    if cohort_size >= 20:
        return Strength.STRONG, f"ranked against {cohort_size} other candidates"
    if cohort_size >= 5:
        return Strength.MODERATE, f"ranked against {cohort_size} other candidates"
    if cohort_size >= 1:
        return Strength.LIMITED, f"only {cohort_size} other candidate(s) to compare against"
    return Strength.NONE, "nothing to compare against yet"


def _experimental_band(records: int) -> tuple:
    if records == 0:
        return Strength.NONE, "no laboratory result exists for this candidate"
    if records < 3:
        return Strength.LIMITED, f"{records} linked laboratory record(s)"
    return Strength.MODERATE, f"{records} linked laboratory records"
