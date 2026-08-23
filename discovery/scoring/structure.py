"""Shared secondary-structure helpers: dot-bracket parsing and target agreement."""

from __future__ import annotations

from typing import Dict, FrozenSet, Set, Tuple

CAN_PAIR: FrozenSet[Tuple[str, str]] = frozenset(
    {("G", "C"), ("C", "G"), ("A", "U"), ("U", "A"), ("G", "U"), ("U", "G")}
)

MIN_LOOP = 3
"""Fewest unpaired bases a hairpin turn can contain."""


def parse_pairs(structure: str) -> Set[Tuple[int, int]]:
    """Dot-bracket string -> set of (i, j) index pairs."""
    stack, pairs = [], set()
    for index, char in enumerate(structure):
        if char == "(":
            stack.append(index)
        elif char == ")":
            if not stack:
                raise ValueError(f"unbalanced structure at position {index}")
            pairs.add((stack.pop(), index))
    if stack:
        raise ValueError("unbalanced structure: unclosed pairs")
    return pairs


def render_pairs(pairs: Set[Tuple[int, int]], length: int) -> str:
    """Set of pairs -> dot-bracket string."""
    chars = ["."] * length
    for i, j in pairs:
        chars[i], chars[j] = "(", ")"
    return "".join(chars)


def agreement(predicted: str, target: str) -> Dict[str, float]:
    """How much of the target shape the prediction reproduced.

    A paired position counts as correct only when it pairs with the *right*
    partner, so a sequence cannot score well by folding into an unrelated shape
    that happens to have brackets in similar places.

    Returns the fraction of positions correct plus the counts behind it, because
    the copilot explains scores by citing the counts, never the fraction alone.
    """
    if len(predicted) != len(target):
        raise ValueError("predicted and target structures must be the same length")

    target_pairs = parse_pairs(target)
    predicted_pairs = parse_pairs(predicted)
    correct_pairs = len(target_pairs & predicted_pairs)

    target_unpaired = _unpaired(target_pairs, len(target))
    predicted_unpaired = _unpaired(predicted_pairs, len(predicted))
    correct_unpaired = len(target_unpaired & predicted_unpaired)

    positions_correct = 2 * correct_pairs + correct_unpaired
    return {
        "fraction": positions_correct / len(target) if target else 0.0,
        "positions_correct": positions_correct,
        "positions_total": len(target),
        "correct_pairs": correct_pairs,
        "target_pairs": len(target_pairs),
        "predicted_pairs": len(predicted_pairs),
    }


def _unpaired(pairs: Set[Tuple[int, int]], length: int) -> Set[int]:
    paired = {i for pair in pairs for i in pair}
    return set(range(length)) - paired
