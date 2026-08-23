"""The research copilot: teach, interpret, compare, question.

What it must not do is generate authoritative biological claims. The moment it
says "this molecule binds strongly", the user stops searching and starts
believing, and the thing they were uniquely contributing -- search strategy and
intuition -- is what gets replaced.

So every string this module emits passes through `assert_comparative`, which
raises on absolute-claim and calibrated-confidence phrasing. The guard runs on
output, not on intent, so a future template cannot quietly opt out.
"""

from __future__ import annotations

import re
from typing import List, Optional, Sequence

from .challenge.compiler import CompiledChallenge
from .evaluation.comparative import explain_difference
from .scoring.base import ScoreResult


class AbsoluteClaimError(ValueError):
    """Copilot output asserted a biological fact the platform cannot support."""


# Phrasings that turn a model output into a claim about the world.
_FORBIDDEN_PATTERNS = (
    (r"\bbinds?\s+(?:strongly|tightly|well)\b", "asserts a binding outcome"),
    (r"\b(?:is|are|will be)\s+(?:safe|toxic|effective|therapeutic)\b", "asserts a clinical property"),
    (r"\bwill\s+(?:cure|treat|work|bind|fold)\b", "predicts a real-world outcome"),
    (r"\bproven\s+to\b", "claims proof"),
    (r"\b(?:this|the)\s+(?:molecule|sequence|candidate)\s+works\b", "asserts efficacy"),
    (r"\bin\s+(?:vivo|patients|humans)\b.{0,40}\b(?:will|does|shows)\b", "extrapolates beyond the model"),
    (r"\bconfidence\s*[:=]?\s*\d", "reports a calibrated confidence the platform does not have"),
    (r"\b\d{1,3}\s*%\s*(?:confiden|certain|sure|likel)", "reports a calibrated confidence"),
)


def assert_comparative(text: str) -> str:
    """Return `text`, or raise if it makes a claim the platform cannot support."""
    lowered = text.lower()
    for pattern, reason in _FORBIDDEN_PATTERNS:
        match = re.search(pattern, lowered)
        if match:
            raise AbsoluteClaimError(
                f"copilot output {reason}: {match.group(0)!r} in {text[:80]!r}"
            )
    return text


class Copilot:
    """Four jobs, and no fifth."""

    def __init__(self, compiled: CompiledChallenge) -> None:
        self.compiled = compiled

    # 1. TEACH -- "here is what you are trying to optimise"
    def teach(self, topic: Optional[str] = None) -> str:
        points = self.compiled.curriculum
        if topic:
            points = tuple(p for p in points if p.topic == topic)
            if not points:
                known = ", ".join(p.topic for p in self.compiled.curriculum)
                raise KeyError(f"no teaching point {topic!r}; available: {known}")
        lines = [f"{p.topic.upper()}\n  {p.explanation}" for p in points]
        return assert_comparative("\n\n".join(lines))

    # 2. INTERPRET -- "your last change did this, at this cost"
    def interpret(self, previous: ScoreResult, current: ScoreResult) -> str:
        before, after = previous.detail, current.detail
        changed = _changed_positions(previous.candidate, current.candidate)
        pair_delta = after.get("correct_pairs", 0) - before.get("correct_pairs", 0)
        extra_pairs = after.get("predicted_pairs", 0) - before.get("predicted_pairs", 0)

        parts = [f"You changed {len(changed)} position(s): {_format_positions(changed)}."]
        if pair_delta > 0:
            parts.append(f"That recovered {pair_delta} more of the target's pairs.")
        elif pair_delta < 0:
            parts.append(f"That lost {abs(pair_delta)} of the target's pairs.")
        else:
            parts.append("Target pair agreement did not move.")
        if extra_pairs > 0 and pair_delta <= 0:
            parts.append(
                f"The model now predicts {extra_pairs} more pair(s) overall, but they are "
                "not the pairs the target asks for -- the sequence is folding somewhere else."
            )
        parts.append(
            f"Score moved {previous.display_score} -> {current.display_score} under "
            f"{current.backend}."
        )
        return assert_comparative(" ".join(parts))

    # 3. COMPARE -- "this attempt against your others"
    def compare(self, current: ScoreResult, history: Sequence[ScoreResult]) -> str:
        others = [r for r in history if r.candidate_id != current.candidate_id]
        if not others:
            return assert_comparative(
                "This is your first scored attempt, so there is nothing to compare it "
                "against yet. Score the starting sequence to get a baseline."
            )
        beaten = [r for r in others if r.raw_score < current.raw_score]
        best_other = max(others, key=lambda r: r.raw_score)
        lead = (
            f"{current.candidate_id} outscored {len(beaten)} of your previous "
            f"{len(others)} attempt(s)."
        )
        return assert_comparative(f"{lead} {explain_difference(current, best_other)}")

    # 4. QUESTION -- "what happens if you..."
    def question(self, current: ScoreResult) -> str:
        target = self.compiled.scoring.params.get("target_structure", "")
        predicted = current.detail.get("predicted_structure", "")
        mismatches = [
            i for i, (t, p) in enumerate(zip(target, predicted)) if t != p
        ]
        if not mismatches:
            return assert_comparative(
                "This sequence already matches the target under the current model. "
                "What happens if you find a second sequence that reaches the same shape "
                "by a different route?"
            )
        region = _region_name(mismatches[0], self.compiled.sandbox.length)
        stable = _region_name(
            next(
                (i for i in range(len(target)) if i not in mismatches),
                0,
            ),
            self.compiled.sandbox.length,
        )
        return assert_comparative(
            f"The model disagrees with the target first at position {mismatches[0]} "
            f"(region {region}). What happens if you preserve region {stable} and "
            f"modify region {region}?"
        )


def _changed_positions(before: str, after: str) -> List[int]:
    return [i for i, (a, b) in enumerate(zip(before, after)) if a != b]


def _format_positions(positions: Sequence[int]) -> str:
    if not positions:
        return "none"
    if len(positions) <= 6:
        return ", ".join(str(p) for p in positions)
    return f"{', '.join(str(p) for p in positions[:6])}, ..."


def _region_name(index: int, length: int) -> str:
    """Split the sequence into three named regions so strategies can be described."""
    third = max(1, length // 3)
    return "ABC"[min(2, index // third)]
