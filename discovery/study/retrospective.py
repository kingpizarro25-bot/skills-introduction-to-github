"""The retrospective harness: hide a known answer, then measure the platform.

The point of a retrospective V1 is that "did this work?" becomes answerable now
rather than in two years. The challenge author already holds solutions; those are
withheld from every arm and used only to score the platform's own output.

What this module measures:

    hit rate @ k          did an arm's best candidates reach the known standard
    evaluations to hit    how much search that took
    rediscovery           did it recover the specific held-out solutions
    strategy clusters     how many distinct approaches the search explored
    improvement           did later attempts beat earlier ones

What it cannot measure is anything about real people -- see arms.py.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from ..challenge.compiler import CompiledChallenge
from ..funnel import FunnelLedger, evaluate
from ..scoring.base import ScoreResult
from .arms import Arm, Attempt, all_arms

SIMULATION_CAVEAT = (
    "Arms marked SIMULATED contain no human participants. They are scripted policies "
    "used to exercise this harness. No result below is evidence about how people search."
)


@dataclass(frozen=True)
class ArmResult:
    arm_name: str
    arm_label: str
    simulated: bool
    evaluations: int
    best_score: float
    hit_rate_at_k: float
    k: int
    hits: int
    evaluations_to_first_hit: Optional[int]
    rediscovered: Tuple[str, ...]
    distinct_strategy_clusters: int
    largest_cluster: Optional[Tuple[str, int]]
    early_best: float
    late_best: float

    @property
    def improvement(self) -> float:
        return round(self.late_best - self.early_best, 3)


@dataclass(frozen=True)
class StudyReport:
    challenge_id: str
    budget: int
    seed: int
    hit_threshold: float
    held_out_count: int
    arms: Tuple[ArmResult, ...]

    def render(self) -> str:
        lines = [
            f"RETROSPECTIVE STUDY — {self.challenge_id}",
            f"  budget {self.budget} evaluations per arm · seed {self.seed}",
            f"  {self.held_out_count} held-out solution(s), hidden from every arm",
            f"  a 'hit' is a candidate scoring >= {round(self.hit_threshold * 10, 1)} / 10",
            "",
            f"{'ARM':<38}{'BEST':>6}{'HITS':>6}{'HIT@k':>8}{'TO 1ST':>8}{'REDISC':>8}{'CLUST':>7}{'IMPRV':>7}",
        ]
        for arm in sorted(self.arms, key=lambda a: -a.best_score):
            first = arm.evaluations_to_first_hit
            lines.append(
                f"{arm.arm_label:<38}"
                f"{round(arm.best_score * 10, 1):>6}"
                f"{arm.hits:>6}"
                f"{arm.hit_rate_at_k:>8.2f}"
                f"{(first if first is not None else '—'):>8}"
                f"{len(arm.rediscovered):>8}"
                f"{arm.distinct_strategy_clusters:>7}"
                f"{arm.improvement * 10:>7.1f}"
            )
        lines.append("")
        lines.append(SIMULATION_CAVEAT)
        lines.append("")
        lines.append(
            "This harness measures whether the platform can recover a known answer. "
            "It does not establish that any candidate is biologically meaningful."
        )
        return "\n".join(lines)


def run_arm(
    compiled: CompiledChallenge,
    arm: Arm,
    budget: int,
    seed: int,
    k: int = 10,
) -> ArmResult:
    answer = compiled.held_out_answer()
    hit_threshold = float(answer.get("hit_threshold", 1.0))
    held_out = {s.upper() for s in answer.get("held_out_solutions", [])}

    rng = random.Random(seed)
    ledger = FunnelLedger()
    history: List[Attempt] = []
    scored: Dict[str, ScoreResult] = {}
    first_hit: Optional[int] = None
    rediscovered: List[str] = []

    for step in range(1, budget + 1):
        candidate = arm.propose(compiled, history, rng)
        record = evaluate(compiled, candidate, cohort=list(scored.values()), ledger=ledger)
        result = record.fast
        history.append((result.candidate, result.raw_score))
        scored.setdefault(result.candidate, result)

        if result.raw_score >= hit_threshold:
            if first_hit is None:
                first_hit = step
            if result.candidate in held_out and result.candidate not in rediscovered:
                rediscovered.append(result.candidate)

    ranked = sorted(scored.values(), key=lambda r: -r.raw_score)[:k]
    hits = sum(1 for r in ranked if r.raw_score >= hit_threshold)
    clusters = ledger.strategy_clusters()
    quartile = max(1, budget // 4)

    return ArmResult(
        arm_name=arm.name,
        arm_label=arm.label,
        simulated=arm.simulated,
        evaluations=ledger.evaluations,
        best_score=max((s for _, s in history), default=0.0),
        hit_rate_at_k=(hits / len(ranked)) if ranked else 0.0,
        k=len(ranked),
        hits=sum(1 for r in scored.values() if r.raw_score >= hit_threshold),
        evaluations_to_first_hit=first_hit,
        rediscovered=tuple(rediscovered),
        distinct_strategy_clusters=len(clusters),
        largest_cluster=next(iter(clusters.items()), None),
        early_best=max((s for _, s in history[:quartile]), default=0.0),
        late_best=max((s for _, s in history[-quartile:]), default=0.0),
    )


def run_study(
    compiled: CompiledChallenge,
    budget: int = 200,
    seed: int = 20260823,
    arms: Optional[Sequence[Arm]] = None,
) -> StudyReport:
    answer = compiled.held_out_answer()
    chosen = list(arms) if arms is not None else all_arms()
    # Same seed per arm so differences come from policy, not from luck of the draw.
    results = tuple(run_arm(compiled, arm, budget, seed) for arm in chosen)
    return StudyReport(
        challenge_id=compiled.challenge_id,
        budget=budget,
        seed=seed,
        hit_threshold=float(answer.get("hit_threshold", 1.0)),
        held_out_count=len(answer.get("held_out_solutions", [])),
        arms=results,
    )
