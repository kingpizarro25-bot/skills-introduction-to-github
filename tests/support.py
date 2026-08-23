"""Shared fixtures for the test suite."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, FrozenSet

from discovery.challenge.compiler import CompiledChallenge, compile_challenge
from discovery.challenge.spec import ChallengeSpec
from discovery.scoring.base import Capability, ScoreResult, Tier, validate_capabilities
from discovery.scoring.structure import agreement
from discovery.scoring.nussinov import fold

REPO_ROOT = Path(__file__).resolve().parent.parent
CHALLENGE_PATH = REPO_ROOT / "challenges" / "rna-hairpin-v1.json"

PERFECT = "GGGGAAAACCCC"
"""Folds exactly to the V1 target under the fast backend."""

PARTIAL = "GGCGAAAAACCC"
FLAT = "ACACACACACAC"
"""The challenge starting point; forms no pairs at all."""


def raw_spec() -> Dict[str, Any]:
    with open(CHALLENGE_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def spec_with(**overrides: Any) -> ChallengeSpec:
    data = copy.deepcopy(raw_spec())
    for key, value in overrides.items():
        data[key] = value
    return ChallengeSpec.from_dict(data)


def challenge() -> CompiledChallenge:
    return compile_challenge(ChallengeSpec.load(CHALLENGE_PATH))


class FakeEnergyScorer:
    """Stands in for an installed energy-model backend.

    Folds identically to the fast backend -- the point is not better prediction
    but a richer capability declaration, so tests can show that limitations and
    evidence strength track what is installed.
    """

    name = "fake-energy-model"
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
        return True

    def score(self, compiled: CompiledChallenge, candidate: str) -> ScoreResult:
        target = compiled.scoring.params["target_structure"]
        predicted = fold(candidate)
        stats = agreement(predicted, target)
        return ScoreResult(
            candidate_id=candidate,
            candidate=candidate,
            raw_score=stats["fraction"],
            tier=self.tier,
            backend=self.name,
            modeled=self.capabilities,
            detail={"predicted_structure": predicted, "target_structure": target, **stats},
        )
