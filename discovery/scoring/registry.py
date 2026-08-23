"""Which backends this deployment actually has, and what they admit to modelling."""

from __future__ import annotations

from typing import Dict, List, Optional

from .base import BackendUnavailable, Capability, Scorer, Tier
from .nussinov import NussinovScorer
from .vienna import ViennaScorer

_BACKENDS: List[Scorer] = [NussinovScorer(), ViennaScorer()]


def backends(tier: Optional[Tier] = None) -> List[Scorer]:
    found = [b for b in _BACKENDS if b.available()]
    return [b for b in found if tier is None or b.tier is tier]


def fast_backend() -> Scorer:
    """The cheap scorer every keystroke runs through."""
    available = backends(Tier.FAST)
    if not available:
        raise BackendUnavailable("no fast scoring backend is installed")
    return available[0]


def deep_backend() -> Optional[Scorer]:
    """The expensive scorer, or None when this deployment has no deep tier.

    Returning None rather than falling back to the fast scorer is deliberate: a
    candidate that was never refined must not be recorded as though it were.
    """
    available = backends(Tier.DEEP)
    return available[0] if available else None


def deployment_report() -> Dict[str, object]:
    """What is installed and what it leaves unmodelled -- the input to limitations."""
    fast = fast_backend()
    deep = deep_backend()
    modeled = set(fast.capabilities)
    if deep is not None:
        modeled |= set(deep.capabilities)
    return {
        "fast_backend": fast.name,
        "deep_backend": deep.name if deep else None,
        "deep_tier_available": deep is not None,
        "modeled": frozenset(modeled),
        "unmodeled": frozenset(Capability) - frozenset(modeled),
    }
