"""The four search arms of the retrospective study.

    A  AI alone
    B  Human alone            (SIMULATED)
    C  Human + AI copilot     (SIMULATED human)
    D  Random computational search

Arms B and C do not contain humans. They are scripted policies standing in for
one, so the harness can be exercised end to end before a single participant is
recruited. `simulated` is True on both, every report prints that flag, and no
output of this module may be described as a finding about people. The real
four-arm comparison is specified in docs/05-v1-retrospective-study.md and
requires actual participants.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Protocol, Sequence, Tuple

from ..challenge.compiler import CompiledChallenge
from ..challenge.spec import SpecError
from ..scoring.structure import CAN_PAIR, parse_pairs

Attempt = Tuple[str, float]
"""(candidate, raw_score) -- what an arm remembers about its own history."""


class Arm(Protocol):
    name: str
    label: str
    simulated: bool

    def propose(
        self, compiled: CompiledChallenge, history: Sequence[Attempt], rng: random.Random
    ) -> str: ...


@dataclass
class _BaseArm:
    name: str
    label: str
    simulated: bool

    def _repair(
        self, compiled: CompiledChallenge, candidate: str, rng: random.Random
    ) -> str:
        """Resample until the candidate satisfies the challenge's declared constraints."""
        alphabet = compiled.sandbox.alphabet
        for _ in range(64):
            try:
                return compiled.validate_candidate(candidate)
            except SpecError:
                index = rng.randrange(compiled.sandbox.length)
                candidate = (
                    candidate[:index] + rng.choice(alphabet) + candidate[index + 1 :]
                )
        return compiled.sandbox.starting_point


class RandomSearchArm(_BaseArm):
    """Arm D. Uniform sampling -- the floor any other arm must beat."""

    def __init__(self) -> None:
        super().__init__("D", "Random computational search", simulated=False)

    def propose(self, compiled, history, rng):
        candidate = "".join(
            rng.choice(compiled.sandbox.alphabet) for _ in range(compiled.sandbox.length)
        )
        return self._repair(compiled, candidate, rng)


class AIAloneArm(_BaseArm):
    """Arm A. Hill climbing on score feedback, with restarts when it stalls.

    Knows nothing about RNA. It only knows whether the number went up, which is
    precisely the automated-search baseline the platform claims humans complement.
    """

    def __init__(self, stall_limit: int = 12) -> None:
        super().__init__("A", "AI alone", simulated=False)
        self.stall_limit = stall_limit

    def propose(self, compiled, history, rng):
        if not history:
            return compiled.sandbox.starting_point
        best = max(history, key=lambda a: a[1])
        since_improvement = _attempts_since_best(history)
        if since_improvement > self.stall_limit:
            candidate = "".join(
                rng.choice(compiled.sandbox.alphabet)
                for _ in range(compiled.sandbox.length)
            )
        else:
            index = rng.randrange(compiled.sandbox.length)
            candidate = best[0][:index] + rng.choice(compiled.sandbox.alphabet) + best[0][index + 1 :]
        return self._repair(compiled, candidate, rng)


class SimulatedHumanArm(_BaseArm):
    """Arm B. A scripted stand-in for a person reasoning about shape.

    Its move is structural rather than positional: it picks a pair the target
    asks for and writes a complementary base pair into those two positions. It
    also forgets -- with some probability it builds on a recent attempt instead
    of its best one, standing in for imperfect recall of the search so far.

    This is a caricature of a participant, not a model of one.
    """

    def __init__(self, forget_probability: float = 0.25) -> None:
        super().__init__("B", "Human alone (SIMULATED)", simulated=True)
        self.forget_probability = forget_probability

    def propose(self, compiled, history, rng):
        if not history:
            return compiled.sandbox.starting_point
        source = (
            rng.choice(history[-5:])
            if rng.random() < self.forget_probability
            else max(history, key=lambda a: a[1])
        )
        target_pairs = sorted(parse_pairs(compiled.scoring.params["target_structure"]))
        if not target_pairs:
            return self._repair(compiled, source[0], rng)
        i, j = rng.choice(target_pairs)
        left, right = rng.choice(sorted(CAN_PAIR))
        candidate = list(source[0])
        candidate[i], candidate[j] = left, right
        return self._repair(compiled, "".join(candidate), rng)


class SimulatedHumanPlusAIArm(_BaseArm):
    """Arm C. The scripted human makes a structural move; the AI polishes it.

    The division of labour is the hypothesis under test: the human-shaped policy
    chooses *where* in the problem to work, the AI-shaped policy tunes *what* to
    put there. Whether that division actually helps is the question, and this
    simulation cannot answer it.
    """

    def __init__(self) -> None:
        super().__init__("C", "Human + AI copilot (SIMULATED human)", simulated=True)
        self._human = SimulatedHumanArm()
        self._ai = AIAloneArm()

    def propose(self, compiled, history, rng):
        if not history:
            return compiled.sandbox.starting_point
        # Alternate: structural move, then a score-guided single-position tweak.
        if len(history) % 2 == 0:
            return self._human.propose(compiled, history, rng)
        return self._ai.propose(compiled, history, rng)


def all_arms() -> List[Arm]:
    return [AIAloneArm(), SimulatedHumanArm(), SimulatedHumanPlusAIArm(), RandomSearchArm()]


def _attempts_since_best(history: Sequence[Attempt]) -> int:
    best_index = max(range(len(history)), key=lambda i: history[i][1])
    return len(history) - 1 - best_index
