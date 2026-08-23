"""The 'does not currently account for' list, derived rather than written.

Nobody hand-authors this per challenge. It is the complement of the capabilities
the active backends declare, which means the honest thing happens by default:
install a weaker backend and the list gets longer on its own.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List

from ..scoring.base import CAPABILITY_ORDER, CAPABILITY_PHRASES, Capability

LIMITATIONS_HEADER = "THIS MODEL DOES NOT CURRENTLY ACCOUNT FOR:"

NOT_VALIDATED_FOOTER = "Computational candidate. Not experimentally validated."
"""Appears on every rendered result. There is no code path that omits it."""


def limitations_for(modeled: FrozenSet[Capability]) -> List[str]:
    """Human-readable phrases for everything the active backends do not model."""
    return [
        CAPABILITY_PHRASES[capability]
        for capability in CAPABILITY_ORDER
        if capability not in modeled
    ]


def provenance_for(modeled: FrozenSet[Capability]) -> Dict[str, str]:
    """Which missing capability produced each limitation line.

    Surfaced by `cli run --show-limitations` so a user can see that the list is
    a property of the installed software, not editorial caution.
    """
    return {
        CAPABILITY_PHRASES[capability]: capability.value
        for capability in CAPABILITY_ORDER
        if capability not in modeled
    }


def render_limitations(modeled: FrozenSet[Capability], indent: str = "  ") -> str:
    lines = [LIMITATIONS_HEADER]
    lines += [f"{indent}• {phrase}" for phrase in limitations_for(modeled)]
    return "\n".join(lines)
