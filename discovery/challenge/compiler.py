"""The Challenge Compiler.

Researchers should not have to design games. They state a scientific problem;
this turns it into a beginner-friendly objective, an interactive sandbox schema,
scoring rules, a copilot curriculum, and researcher analytics keys.

Without this layer every new disease becomes a custom software project.

The compiler is also the security boundary for the retrospective study design:
`ChallengeSpec.validation` holds the hidden answer, and nothing reachable from
`player_facing()` may contain it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from .spec import ChallengeSpec, SpecError


class CompilerError(ValueError):
    """The spec cannot be turned into a playable challenge."""


@dataclass(frozen=True)
class TeachingPoint:
    """One thing the copilot may explain, generated from the metric, not authored."""

    topic: str
    explanation: str


@dataclass(frozen=True)
class ScoringRules:
    metric_id: str
    params: Dict[str, Any]
    promotion_threshold: float
    """Fast-tier score above which a candidate earns deep compute."""


@dataclass(frozen=True)
class SandboxSchema:
    alphabet: str
    length: int
    starting_point: str
    editable_positions: Tuple[int, ...]
    constraints: Tuple[Dict[str, Any], ...]


@dataclass(frozen=True)
class GovernanceNotice:
    tier: str
    license: str
    attribution: str
    publication_policy: str

    def as_banner(self) -> str:
        lines = [f"GOVERNANCE: {self.tier.upper()} CHALLENGE"]
        if self.license:
            lines.append(f"  License: {self.license}")
        if self.attribution:
            lines.append(f"  Attribution: {self.attribution}")
        if self.publication_policy:
            lines.append(f"  Publication: {self.publication_policy}")
        return "\n".join(lines)


@dataclass(frozen=True)
class CompiledChallenge:
    challenge_id: str
    domain: str
    brief: str
    sandbox: SandboxSchema
    scoring: ScoringRules
    curriculum: Tuple[TeachingPoint, ...]
    analytics_keys: Tuple[str, ...]
    governance: GovernanceNotice
    experimental_records: int = 0
    _validation: Dict[str, Any] = field(default_factory=dict, repr=False)
    _spec: ChallengeSpec | None = field(default=None, repr=False)

    def player_facing(self) -> Dict[str, Any]:
        """Everything a participant is allowed to see. Never includes validation."""
        return {
            "challenge_id": self.challenge_id,
            "domain": self.domain,
            "brief": self.brief,
            "sandbox": {
                "alphabet": self.sandbox.alphabet,
                "length": self.sandbox.length,
                "starting_point": self.sandbox.starting_point,
                "editable_positions": list(self.sandbox.editable_positions),
                "constraints": [dict(c) for c in self.sandbox.constraints],
            },
            "scoring": {
                "metric_id": self.scoring.metric_id,
                "params": dict(self.scoring.params),
            },
            "curriculum": [
                {"topic": t.topic, "explanation": t.explanation} for t in self.curriculum
            ],
            "governance": {
                "tier": self.governance.tier,
                "license": self.governance.license,
                "attribution": self.governance.attribution,
                "publication_policy": self.governance.publication_policy,
            },
        }

    def held_out_answer(self) -> Dict[str, Any]:
        """The hidden solution. Study harness and researcher dashboard only.

        Named deliberately awkwardly: any call site is easy to find in review,
        and no player-facing code path should ever contain one.
        """
        return dict(self._validation)

    def validate_candidate(self, candidate: str) -> str:
        if self._spec is None:  # pragma: no cover - compiled specs always carry one
            raise CompilerError("compiled challenge lost its spec")
        return self._spec.validate_candidate(candidate)


# Brief and curriculum generation is per-metric, which is what makes a new
# challenge a data file rather than a software project. Adding a metric here
# adds a challenge type to the whole platform.
_METRIC_BRIEFS = {
    "rna_structure_match": (
        "You are designing an RNA sequence {length} letters long, using only "
        "{alphabet}.\n"
        "RNA folds back on itself: some letters pair up, and the pattern of pairs "
        "is its shape.\n"
        "Your goal is to find a sequence that folds into this target shape:\n"
        "    {target}\n"
        "'(' and ')' mark a paired position; '.' marks an unpaired one.\n"
        "You score higher the more positions fold the way the target says they should."
    ),
}

_METRIC_CURRICULUM = {
    "rna_structure_match": (
        TeachingPoint(
            "what you are optimizing",
            "Agreement between the shape the scoring model predicts for your sequence "
            "and the target shape. Nothing else is being measured.",
        ),
        TeachingPoint(
            "which letters pair",
            "G pairs with C, A pairs with U, and G can also pair weakly with U. "
            "A '(' at one position needs a partner ')' further along.",
        ),
        TeachingPoint(
            "why loops matter",
            "A hairpin needs a few unpaired letters at its turn; pairs cannot close "
            "a loop that is too tight for the backbone to bend around.",
        ),
        TeachingPoint(
            "what the score is not",
            "A high score means your sequence matched this model's prediction of the "
            "target shape. It is not a measurement, and it is not a claim about how "
            "the molecule behaves in a cell.",
        ),
    ),
}

_METRIC_ANALYTICS = {
    "rna_structure_match": (
        "edit_distance_from_start",
        "region_preservation_signature",
        "gc_fraction",
        "score_trajectory",
        "evaluations_to_best",
    ),
}


def compile_challenge(spec: ChallengeSpec) -> CompiledChallenge:
    metric_id = spec.metric["id"]
    if metric_id not in _METRIC_BRIEFS:
        raise CompilerError(
            f"no compiler support for metric {metric_id!r}; "
            f"known metrics: {', '.join(sorted(_METRIC_BRIEFS))}"
        )

    params = {k: v for k, v in spec.metric.items() if k != "id"}
    if metric_id == "rna_structure_match":
        target = params.get("target_structure")
        if not target:
            raise CompilerError("rna_structure_match requires metric.target_structure")
        if len(target) != spec.length:
            raise CompilerError(
                f"target_structure is {len(target)} long but variables.length is {spec.length}"
            )
        _check_balanced(target)

    starting_point = spec.variables.get("starting_point") or spec.alphabet[0] * spec.length
    if len(starting_point) != spec.length:
        raise CompilerError("variables.starting_point must match variables.length")
    # The sandbox hands this sequence to every participant, and the study arms
    # build their first move from it. A starting point that breaks the
    # challenge's own constraints would make the first submission illegal.
    try:
        starting_point = spec.validate_candidate(starting_point)
    except SpecError as error:
        raise CompilerError(f"variables.starting_point is not a legal candidate: {error}") from error

    brief = _METRIC_BRIEFS[metric_id].format(
        length=spec.length,
        alphabet=", ".join(spec.alphabet),
        target=params.get("target_structure", ""),
    )

    sandbox = SandboxSchema(
        alphabet=spec.alphabet,
        length=spec.length,
        starting_point=starting_point.upper(),
        editable_positions=tuple(range(spec.length)),
        constraints=tuple(dict(c) for c in spec.constraints),
    )

    scoring = ScoringRules(
        metric_id=metric_id,
        params=params,
        promotion_threshold=float(spec.metric.get("promotion_threshold", 0.8)),
    )

    governance = GovernanceNotice(
        tier=spec.governance["tier"],
        license=spec.governance.get("license", ""),
        attribution=spec.governance.get("attribution", ""),
        publication_policy=spec.governance.get("publication_policy", ""),
    )

    compiled = CompiledChallenge(
        challenge_id=spec.challenge_id,
        domain=spec.domain,
        brief=brief,
        sandbox=sandbox,
        scoring=scoring,
        curriculum=_METRIC_CURRICULUM[metric_id],
        analytics_keys=_METRIC_ANALYTICS[metric_id],
        governance=governance,
        experimental_records=int(spec.known_data.get("experimental_records", 0) or 0),
        _validation=dict(spec.validation),
        _spec=spec,
    )
    _assert_no_leak(compiled, spec)
    return compiled


def _check_balanced(structure: str) -> None:
    depth = 0
    for index, char in enumerate(structure):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char != ".":
            raise CompilerError(
                f"target_structure position {index} has illegal character {char!r}; "
                "use only '(', ')' and '.'"
            )
        if depth < 0:
            raise CompilerError(f"target_structure closes an unopened pair at position {index}")
    if depth:
        raise CompilerError("target_structure has unclosed pairs")


def _assert_no_leak(compiled: CompiledChallenge, spec: ChallengeSpec) -> None:
    """Fail compilation if any held-out value is reachable from player-facing output.

    Belt and braces: the tests assert this too, but a leak should never survive
    even one call in production, and researchers add validation fields freely.
    """
    if not spec.validation:
        return
    rendered = json.dumps(compiled.player_facing()).upper()
    for value in _iter_strings(spec.validation):
        if len(value) >= 4 and value.upper() in rendered:
            raise CompilerError(
                f"held-out validation value {value!r} leaked into player-facing output"
            )


def _iter_strings(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _iter_strings(v)]
    if isinstance(value, (list, tuple)):
        return [s for v in value for s in _iter_strings(v)]
    return []
