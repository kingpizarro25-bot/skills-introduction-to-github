"""Multi-factor hypothesis prioritisation.

    Priority = Evidence Support + Information Gain + Impact + Likelihood
               - Test Cost - Risk

Each dimension is scored 0-5 independently. Information gain is first class:
without it the engine keeps re-testing whatever is cheapest rather than
whatever is most decisive.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping

from .errors import ValidationError
from .ids import utcnow

POSITIVE_FACTORS = ("likelihood", "evidence_support", "information_gain", "impact")
NEGATIVE_FACTORS = ("test_cost", "risk")
FACTORS = POSITIVE_FACTORS + NEGATIVE_FACTORS
FACTOR_MAX = 5


@dataclass(frozen=True)
class WeightProfile:
    """Per-dimension weights.

    Exact weights are a tuning policy, not an architectural invariant, so they
    live here as named profiles rather than as constants sprinkled through the
    engine. ``balanced-v1`` is the documented default: every dimension weighs 1.
    """

    name: str = "balanced-v1"
    likelihood: float = 1.0
    evidence_support: float = 1.0
    information_gain: float = 1.0
    impact: float = 1.0
    test_cost: float = 1.0
    risk: float = 1.0

    def weight(self, factor: str) -> float:
        return float(getattr(self, factor))

    @property
    def max_raw(self) -> float:
        return FACTOR_MAX * sum(self.weight(f) for f in POSITIVE_FACTORS)

    @property
    def min_raw(self) -> float:
        return -FACTOR_MAX * sum(self.weight(f) for f in NEGATIVE_FACTORS)


#: Shifts the engine toward decisive tests when a case is stalling.
INFORMATION_SEEKING = WeightProfile(
    name="information-seeking-v1", information_gain=2.0, test_cost=0.5
)

#: Used when execution capacity is the bottleneck rather than uncertainty.
COST_AVERSE = WeightProfile(name="cost-averse-v1", test_cost=2.0, risk=1.5)

PROFILES: dict[str, WeightProfile] = {
    p.name: p for p in (WeightProfile(), INFORMATION_SEEKING, COST_AVERSE)
}
DEFAULT_PROFILE = PROFILES["balanced-v1"]


@dataclass(frozen=True)
class Factors:
    likelihood: int
    evidence_support: int
    information_gain: int
    impact: int
    test_cost: int
    risk: int

    def __post_init__(self) -> None:
        for name in FACTORS:
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValidationError(
                    f"factor {name!r} must be an integer 0-{FACTOR_MAX}", code="factor_type"
                )
            if not 0 <= value <= FACTOR_MAX:
                raise ValidationError(
                    f"factor {name!r}={value} outside 0-{FACTOR_MAX}", code="factor_range"
                )

    @classmethod
    def from_dict(cls, data: Mapping[str, int]) -> "Factors":
        missing = [f for f in FACTORS if f not in data]
        if missing:
            raise ValidationError(
                f"missing hypothesis factors: {', '.join(missing)}", code="factor_missing"
            )
        extra = [k for k in data if k not in FACTORS]
        if extra:
            raise ValidationError(
                f"unknown hypothesis factors: {', '.join(sorted(extra))}", code="factor_unknown"
            )
        return cls(**{f: data[f] for f in FACTORS})

    def to_dict(self) -> dict[str, int]:
        return {f: getattr(self, f) for f in FACTORS}


@dataclass(frozen=True)
class PriorityScore:
    raw: float
    normalized: float
    weight_profile: str
    computed_at: str = field(default_factory=utcnow)

    def to_dict(self) -> dict:
        return {
            "raw": round(self.raw, 4),
            "normalized": round(self.normalized, 4),
            "weight_profile": self.weight_profile,
            "computed_at": self.computed_at,
        }


def score(factors: Factors, profile: WeightProfile | None = None) -> PriorityScore:
    profile = profile or DEFAULT_PROFILE
    raw = sum(profile.weight(f) * getattr(factors, f) for f in POSITIVE_FACTORS)
    raw -= sum(profile.weight(f) * getattr(factors, f) for f in NEGATIVE_FACTORS)
    span = profile.max_raw - profile.min_raw
    normalized = (raw - profile.min_raw) / span if span else 0.0
    return PriorityScore(raw=raw, normalized=normalized, weight_profile=profile.name)


def rank(hypotheses: Iterable, profile: WeightProfile | None = None) -> list:
    """Order hypotheses by priority, then by decisiveness, then by impact.

    Ties break on information gain so that, all else equal, the engine picks the
    test that removes the most uncertainty. Untestable and superseded
    hypotheses are excluded: they cannot be acted on.
    """
    from .enums import HypothesisStatus

    profile = profile or DEFAULT_PROFILE
    actionable = [
        h
        for h in hypotheses
        if h.status
        not in (HypothesisStatus.UNTESTABLE, HypothesisStatus.SUPERSEDED, HypothesisStatus.REJECTED)
    ]
    return sorted(
        actionable,
        key=lambda h: (
            -score(h.factors, profile).raw,
            -h.factors.information_gain,
            -h.factors.impact,
            h.id,
        ),
    )
