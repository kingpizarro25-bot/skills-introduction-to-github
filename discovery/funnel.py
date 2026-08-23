"""The compute funnel.

Every edit runs the cheap scorer. Only interesting candidates earn expensive
compute, because firing a heavy workload every time somebody drags something
three pixels to the left is how a platform discovers that cloud providers enjoy
money more than it does.

The funnel is also where the researcher dashboard gets its raw material: it
records not just candidates but *how people moved through the search space*.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from .challenge.compiler import CompiledChallenge
from .scoring.base import ScoreResult
from .scoring.registry import deep_backend, fast_backend


@dataclass(frozen=True)
class FunnelRecord:
    fast: ScoreResult
    promoted: bool
    reason: str
    strategy_signature: str
    deep: Optional[ScoreResult] = None
    deep_status: str = "not attempted"


@dataclass
class FunnelLedger:
    """Aggregate view over every attempt, for the researcher dashboard."""

    records: List[FunnelRecord] = field(default_factory=list)

    def add(self, record: FunnelRecord) -> None:
        self.records.append(record)

    @property
    def evaluations(self) -> int:
        return len(self.records)

    @property
    def promoted(self) -> List[FunnelRecord]:
        return [r for r in self.records if r.promoted]

    def strategy_clusters(self) -> Dict[str, int]:
        """How many attempts fell into each region-preservation strategy.

        This is the signal researchers cannot get from candidates alone: not
        which sequences people submitted, but which parts of the problem they
        decided to hold still while they varied the rest.
        """
        return dict(Counter(r.strategy_signature for r in self.records).most_common())

    def summary(self) -> Dict[str, object]:
        clusters = self.strategy_clusters()
        best = max(self.records, key=lambda r: r.fast.raw_score, default=None)
        return {
            "evaluations": self.evaluations,
            "promoted": len(self.promoted),
            "distinct_strategy_clusters": len(clusters),
            "largest_cluster": next(iter(clusters.items()), None),
            "deep_tier_runs": sum(1 for r in self.records if r.deep is not None),
            "best_fast_score": best.fast.display_score if best else None,
        }


def evaluate(
    compiled: CompiledChallenge,
    candidate: str,
    cohort: Sequence[ScoreResult] = (),
    ledger: Optional[FunnelLedger] = None,
) -> FunnelRecord:
    """Score one candidate and decide whether it earns the expensive tier."""
    candidate = compiled.validate_candidate(candidate)
    fast = fast_backend().score(compiled, candidate)
    signature = strategy_signature(compiled, candidate)

    promoted, reason = _promotion_decision(compiled, fast, cohort)
    deep, deep_status = None, "not attempted"
    if promoted:
        backend = deep_backend()
        if backend is None:
            # No deep tier installed. The candidate is queued, not refined --
            # recording it as refined would be a lie the dashboard then repeats.
            deep_status = "queued: no deep backend installed in this deployment"
        else:
            deep = backend.score(compiled, candidate)
            deep_status = f"refined by {backend.name}"

    record = FunnelRecord(
        fast=fast,
        promoted=promoted,
        reason=reason,
        strategy_signature=signature,
        deep=deep,
        deep_status=deep_status,
    )
    if ledger is not None:
        ledger.add(record)
    return record


def _promotion_decision(
    compiled: CompiledChallenge,
    fast: ScoreResult,
    cohort: Sequence[ScoreResult],
) -> tuple:
    threshold = compiled.scoring.promotion_threshold
    if fast.raw_score < threshold:
        return False, (
            f"fast score {fast.display_score} is below the promotion threshold "
            f"{round(threshold * 10, 1)}"
        )
    duplicate = next(
        (r for r in cohort if r.detail.get("predicted_structure") == fast.detail.get("predicted_structure")
         and r.candidate != fast.candidate and r.raw_score >= fast.raw_score),
        None,
    )
    if duplicate is not None:
        return False, (
            f"folds identically to already-promoted candidate {duplicate.candidate_id}; "
            "deep compute would repeat work"
        )
    return True, f"fast score {fast.display_score} cleared the promotion threshold"


def strategy_signature(compiled: CompiledChallenge, candidate: str) -> str:
    """Which named regions the participant held still, and which they varied.

    Rendered as e.g. 'A=kept B=changed C=changed'. Counting these across
    thousands of attempts is what turns submissions into search strategies.
    """
    start = compiled.sandbox.starting_point
    length = compiled.sandbox.length
    third = max(1, length // 3)
    parts = []
    for region_index, name in enumerate("ABC"):
        lo = region_index * third
        hi = length if name == "C" else min(length, lo + third)
        if lo >= length:
            continue
        changed = any(start[i] != candidate[i] for i in range(lo, hi))
        parts.append(f"{name}={'changed' if changed else 'kept'}")
    return " ".join(parts)
