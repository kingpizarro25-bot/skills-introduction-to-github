"""Deep tier: an energy-model backend, used only when one is installed.

This is the optional half of the honesty demonstration. When ViennaRNA is
present the platform models stacking energetics, loop entropy and the fold
ensemble, so reported evidence strengthens and the limitations list shortens.
When it is absent -- the default in a bare environment -- nothing silently
substitutes for it. The deep tier reports itself unavailable and the funnel
records that the candidate is queued rather than pretending it was refined.
"""

from __future__ import annotations

import os
from typing import Any, FrozenSet

from .base import Capability, ScoreResult, Tier, validate_capabilities
from .structure import agreement

try:  # pragma: no cover - depends on the deployment, not on the test run
    import RNA as _vienna
except ImportError:  # pragma: no cover
    _vienna = None


def _disabled_by_env() -> bool:
    return os.environ.get("DISCOVERY_DISABLE_VIENNA", "").strip() not in ("", "0", "false")


class ViennaScorer:
    name = "viennarna-mfe"
    tier = Tier.DEEP
    capabilities: FrozenSet[Capability] = frozenset(
        {
            Capability.BASE_PAIRING,
            Capability.STACKING_ENERGETICS,
            Capability.LOOP_ENTROPY,
            Capability.ENSEMBLE_DIVERSITY,
        }
    )

    def __init__(self) -> None:
        validate_capabilities(self.name, self.capabilities)

    def available(self) -> bool:
        return _vienna is not None and not _disabled_by_env()

    def score(self, compiled: Any, candidate: str) -> ScoreResult:  # pragma: no cover
        if not self.available():
            raise RuntimeError("ViennaRNA backend is not available in this deployment")
        target = compiled.scoring.params["target_structure"]
        predicted, free_energy = _vienna.fold(candidate)
        stats = agreement(predicted, target)
        return ScoreResult(
            candidate_id=candidate,
            candidate=candidate,
            raw_score=stats["fraction"],
            tier=self.tier,
            backend=self.name,
            modeled=self.capabilities,
            detail={
                "predicted_structure": predicted,
                "target_structure": target,
                "mfe_kcal_per_mol": free_energy,
                **stats,
            },
        )
