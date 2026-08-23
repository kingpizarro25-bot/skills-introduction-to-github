"""Comparative rendering. MODEL RESULT != BIOLOGICAL FACT.

A score on its own invites the reading "this molecule is good". A score in a
ranking invites the reading "this scored higher than those, under this model" --
which is the only claim the platform can actually support.

So the renderer *refuses* to produce output for a candidate with nothing to
compare against. That is not a stylistic preference; `render` raises.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

from ..scoring.base import ScoreResult
from .evidence import EvidenceStrength
from .limitations import NOT_VALIDATED_FOOTER, render_limitations


class NoComparatorError(ValueError):
    """Raised when asked to present a score with nothing to rank it against.

    The fix is never to relax this check. It is to score a baseline -- the
    challenge's own starting point always qualifies -- and rank against that.
    """


@dataclass(frozen=True)
class Comparison:
    rank: int
    cohort_size: int
    better_than: Tuple[Tuple[str, float], ...]
    worse_than: Tuple[Tuple[str, float], ...]

    @property
    def comparator_count(self) -> int:
        return len(self.better_than) + len(self.worse_than)


def compare(result: ScoreResult, cohort: Sequence[ScoreResult]) -> Comparison:
    """Rank one result against a cohort, excluding the result itself."""
    others = [r for r in cohort if r.candidate_id != result.candidate_id]
    if not others:
        raise NoComparatorError(
            f"candidate {result.candidate_id!r} has nothing to compare against; "
            "score at least the challenge starting point before presenting a result"
        )

    better = tuple(
        (r.candidate_id, r.display_score)
        for r in sorted(others, key=lambda r: -r.raw_score)
        if r.raw_score < result.raw_score
    )
    worse = tuple(
        (r.candidate_id, r.display_score)
        for r in sorted(others, key=lambda r: -r.raw_score)
        if r.raw_score >= result.raw_score
    )
    return Comparison(
        rank=len(worse) + 1,
        cohort_size=len(others) + 1,
        better_than=better,
        worse_than=worse,
    )


def explain_difference(result: ScoreResult, other: ScoreResult) -> str:
    """Say *why* one candidate outranked another, in counts, scoped to the model."""
    mine = result.detail
    theirs = other.detail
    if "correct_pairs" not in mine or "correct_pairs" not in theirs:
        return (
            f"Within this challenge and scoring model, {result.candidate_id} scored "
            f"{result.display_score} and {other.candidate_id} scored {other.display_score}."
        )

    pair_delta = mine["correct_pairs"] - theirs["correct_pairs"]
    position_delta = mine["positions_correct"] - theirs["positions_correct"]
    if pair_delta > 0:
        reason = f"it recreated {pair_delta} more of the target's base pairs"
    elif pair_delta < 0:
        reason = f"it recreated {abs(pair_delta)} fewer of the target's base pairs"
    elif position_delta:
        direction = "more" if position_delta > 0 else "fewer"
        reason = f"it placed {abs(position_delta)} {direction} positions as the target specifies"
    else:
        reason = "the two fold identically under this model despite differing in sequence"

    verb = "higher than" if result.raw_score > other.raw_score else "lower than"
    return (
        f"Within this challenge and scoring model, {result.candidate_id} scored {verb} "
        f"{other.candidate_id} primarily because {reason}."
    )


def render(
    result: ScoreResult,
    cohort: Sequence[ScoreResult],
    evidence: EvidenceStrength,
    metric_label: str = "Predicted structural agreement",
) -> str:
    """The full result view: prediction, comparison, evidence, limitations, footer.

    Every block is mandatory. There is no `render_score_only` and no flag that
    strips the limitations, because a caller in a hurry is exactly the caller who
    would strip them.
    """
    comparison = compare(result, cohort)

    lines: List[str] = []
    lines.append("PREDICTION")
    lines.append(f"  {metric_label}   {result.display_score} / 10")
    lines.append(
        "  Defined only within this challenge's scoring model "
        f"({result.backend}, {result.tier.value} tier)."
    )
    lines.append("")

    lines.append("COMPARISON")
    lines.append(f"  Ranked {comparison.rank} of {comparison.cohort_size} scored candidates.")
    if comparison.better_than:
        listed = ", ".join(f"{cid} ({score})" for cid, score in comparison.better_than[:3])
        lines.append(f"  Scored higher than: {listed}")
    if comparison.worse_than:
        listed = ", ".join(f"{cid} ({score})" for cid, score in comparison.worse_than[:3])
        lines.append(f"  Scored lower than:  {listed}")
    nearest = _nearest(result, cohort)
    if nearest is not None:
        lines.append(f"  {explain_difference(result, nearest)}")
    lines.append("")

    lines.append("EVIDENCE STRENGTH")
    for label, strength, note in evidence.rows():
        detail = f"  — {note}" if note else ""
        lines.append(f"  {label:<22}{strength.value}{detail}")
    lines.append("")

    lines.append(render_limitations(result.modeled))
    lines.append("")
    lines.append(NOT_VALIDATED_FOOTER)
    return "\n".join(lines)


def _nearest(result: ScoreResult, cohort: Sequence[ScoreResult]):
    others = [r for r in cohort if r.candidate_id != result.candidate_id]
    if not others:
        return None
    return min(others, key=lambda r: abs(r.raw_score - result.raw_score))
