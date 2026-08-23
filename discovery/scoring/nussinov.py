"""Fast tier: Nussinov base-pair maximisation.

This model counts pairs. That is all it does. It knows nothing about stacking
energy, loop entropy, or competing folds, which makes it a poor predictor of
real RNA structure -- and exactly the right demonstration case for this platform.
Its weakness is visible to the user because it declares what it does not model,
and `evaluation.limitations` turns that declaration into the list they read.
"""

from __future__ import annotations

from typing import Any, FrozenSet, List, Set, Tuple

from .base import Capability, ScoreResult, Tier, validate_capabilities
from .structure import CAN_PAIR, MIN_LOOP, agreement, render_pairs


def fold(sequence: str, min_loop: int = MIN_LOOP) -> str:
    """Return the dot-bracket structure maximising the number of base pairs."""
    sequence = sequence.upper()
    n = len(sequence)
    if n == 0:
        return ""

    # dp[i][j] = most pairs achievable in the subsequence i..j inclusive.
    dp = [[0] * n for _ in range(n)]
    for span in range(min_loop + 1, n):
        for i in range(n - span):
            j = i + span
            best = dp[i][j - 1]  # j left unpaired
            for k in range(i, j - min_loop):
                if (sequence[k], sequence[j]) in CAN_PAIR:
                    left = dp[i][k - 1] if k > i else 0
                    candidate = left + 1 + dp[k + 1][j - 1]
                    if candidate > best:
                        best = candidate
            dp[i][j] = best

    pairs: Set[Tuple[int, int]] = set()
    stack: List[Tuple[int, int]] = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j - i <= min_loop:
            continue
        if dp[i][j] == dp[i][j - 1]:
            stack.append((i, j - 1))
            continue
        # Fixed scan order keeps the fold deterministic across runs, which the
        # study harness relies on when comparing arms.
        for k in range(i, j - min_loop):
            if (sequence[k], sequence[j]) not in CAN_PAIR:
                continue
            left = dp[i][k - 1] if k > i else 0
            if dp[i][j] == left + 1 + dp[k + 1][j - 1]:
                pairs.add((k, j))
                if k > i:
                    stack.append((i, k - 1))
                stack.append((k + 1, j - 1))
                break
    return render_pairs(pairs, n)


class NussinovScorer:
    name = "nussinov-base-pair-maximisation"
    tier = Tier.FAST
    capabilities: FrozenSet[Capability] = frozenset({Capability.BASE_PAIRING})

    def __init__(self) -> None:
        validate_capabilities(self.name, self.capabilities)

    def available(self) -> bool:
        return True

    def score(self, compiled: Any, candidate: str) -> ScoreResult:
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
            detail={
                "predicted_structure": predicted,
                "target_structure": target,
                **stats,
            },
        )
