"""Scoring backends declare what they model. Everything honest follows from that.

The central rule of this platform: a scoring backend may not quietly imply it
understands more biology than it does. Each backend publishes the set of
`Capability` values it actually models; the limitations shown to the user are
*derived* from the complement of that set. Swapping a weaker backend in
automatically lengthens the limitations list and weakens reported evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, FrozenSet, Protocol


class Capability(Enum):
    """Something a scoring model may or may not account for."""

    BASE_PAIRING = "base_pairing"
    STACKING_ENERGETICS = "stacking_energetics"
    LOOP_ENTROPY = "loop_entropy"
    PSEUDOKNOTS = "pseudoknots"
    ENSEMBLE_DIVERSITY = "ensemble_diversity"
    ION_CONDITIONS = "ion_conditions"
    CELLULAR_ENVIRONMENT = "cellular_environment"
    METABOLISM = "metabolism"
    HUMAN_TOXICITY = "human_toxicity"
    CLINICAL_EFFECTIVENESS = "clinical_effectiveness"
    EXPERIMENTAL_CONFIRMATION = "experimental_confirmation"


# Canonical order, used so limitations lists read the same way every time:
# nearest-to-the-model concerns first, furthest-from-the-model concerns last.
CAPABILITY_ORDER = (
    Capability.BASE_PAIRING,
    Capability.STACKING_ENERGETICS,
    Capability.LOOP_ENTROPY,
    Capability.PSEUDOKNOTS,
    Capability.ENSEMBLE_DIVERSITY,
    Capability.ION_CONDITIONS,
    Capability.CELLULAR_ENVIRONMENT,
    Capability.METABOLISM,
    Capability.HUMAN_TOXICITY,
    Capability.CLINICAL_EFFECTIVENESS,
    Capability.EXPERIMENTAL_CONFIRMATION,
)

CAPABILITY_PHRASES = {
    Capability.BASE_PAIRING: "which bases can physically pair",
    Capability.STACKING_ENERGETICS: "stacking energetics between adjacent pairs",
    Capability.LOOP_ENTROPY: "the entropic cost of loops and bulges",
    Capability.PSEUDOKNOTS: "pseudoknotted (crossing) structures",
    Capability.ENSEMBLE_DIVERSITY: "competing alternative folds, not just one",
    Capability.ION_CONDITIONS: "ion concentration and buffer conditions",
    Capability.CELLULAR_ENVIRONMENT: "the full cellular environment",
    Capability.METABOLISM: "metabolism and degradation in a living system",
    Capability.HUMAN_TOXICITY: "toxicity in humans",
    Capability.CLINICAL_EFFECTIVENESS: "clinical effectiveness",
    Capability.EXPERIMENTAL_CONFIRMATION: "laboratory confirmation",
}

# Capabilities no purely computational backend in this platform can ever claim.
# Listing them explicitly keeps a future backend author from quietly asserting one.
NEVER_COMPUTATIONAL = frozenset(
    {
        Capability.CELLULAR_ENVIRONMENT,
        Capability.METABOLISM,
        Capability.HUMAN_TOXICITY,
        Capability.CLINICAL_EFFECTIVENESS,
        Capability.EXPERIMENTAL_CONFIRMATION,
    }
)


class Tier(Enum):
    """Which rung of the compute funnel a result came from."""

    FAST = "fast"
    DEEP = "deep"


@dataclass(frozen=True)
class ScoreResult:
    """The output of one scoring run.

    Deliberately has no `confidence` field, and never will. A single percentage
    implies a calibrated probability this platform does not have. Callers wanting
    to communicate certainty must use `evaluation.evidence`, which reports three
    separate axes and refuses to collapse them into one number.
    """

    candidate_id: str
    candidate: str
    raw_score: float
    tier: Tier
    backend: str
    modeled: FrozenSet[Capability]
    detail: Dict[str, Any] = field(default_factory=dict)

    @property
    def display_score(self) -> float:
        """The metric-native score on the 0-10 scale players see.

        This is a rescaling, not a probability, and it is only meaningful when
        compared against other candidates scored by the same backend on the same
        challenge.
        """
        return round(max(0.0, min(1.0, self.raw_score)) * 10.0, 1)

    @property
    def unmodeled(self) -> FrozenSet[Capability]:
        return frozenset(CAPABILITY_ORDER) - self.modeled


class Scorer(Protocol):
    """What every scoring backend must provide."""

    name: str
    tier: Tier
    capabilities: FrozenSet[Capability]

    def available(self) -> bool:
        """Whether this backend can run in the current deployment."""

    def score(self, compiled: Any, candidate: str) -> ScoreResult:
        """Score one candidate against a compiled challenge."""


class BackendUnavailable(RuntimeError):
    """Raised when a requested scoring tier has no usable backend installed."""


def validate_capabilities(name: str, capabilities: FrozenSet[Capability]) -> None:
    """Reject a backend that claims to model something no computation can.

    Called at registration time so an over-claiming backend fails loudly at
    import rather than silently shortening a user's limitations list.
    """
    overclaimed = capabilities & NEVER_COMPUTATIONAL
    if overclaimed:
        phrases = ", ".join(sorted(c.value for c in overclaimed))
        raise ValueError(
            f"backend {name!r} claims capabilities no computational model can have: {phrases}"
        )
