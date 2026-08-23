"""What a researcher hands the platform.

A `ChallengeSpec` is the six things a scientist can state about their problem
without knowing anything about game design:

    objective, known data, allowed variables, constraints, evaluation metric,
    validation data

The compiler turns that into something a beginner can play. The researcher never
writes a game; they write this.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


class SpecError(ValueError):
    """The researcher's challenge definition is incomplete or self-contradictory."""


REQUIRED_FIELDS = (
    "challenge_id",
    "domain",
    "objective",
    "variables",
    "metric",
    "governance",
)

GOVERNANCE_TIERS = ("public", "sponsored", "private")


@dataclass(frozen=True)
class ChallengeSpec:
    challenge_id: str
    domain: str
    objective: str
    variables: Dict[str, Any]
    metric: Dict[str, Any]
    governance: Dict[str, Any]
    known_data: Dict[str, Any] = field(default_factory=dict)
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    validation: Dict[str, Any] = field(default_factory=dict)
    """Held-out answer. Never reaches a player. See compiler.CompiledChallenge."""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChallengeSpec":
        missing = [f for f in REQUIRED_FIELDS if not data.get(f)]
        if missing:
            raise SpecError(f"challenge is missing required field(s): {', '.join(missing)}")

        tier = data["governance"].get("tier")
        if tier not in GOVERNANCE_TIERS:
            raise SpecError(
                f"governance.tier must be one of {GOVERNANCE_TIERS}, got {tier!r}. "
                "Every challenge must state its IP and attribution terms up front."
            )
        if tier == "public" and not data["governance"].get("license"):
            raise SpecError("public challenges must name an open research license")

        variables = data["variables"]
        for key in ("alphabet", "length"):
            if key not in variables:
                raise SpecError(f"variables must declare {key!r}")
        if not variables["alphabet"]:
            raise SpecError("variables.alphabet cannot be empty")
        if int(variables["length"]) < 1:
            raise SpecError("variables.length must be positive")

        if "id" not in data["metric"]:
            raise SpecError("metric must declare an 'id' naming its scoring rule")

        known = dict(data.get("known_data") or {})
        return cls(
            challenge_id=data["challenge_id"],
            domain=data["domain"],
            objective=data["objective"],
            variables=dict(variables),
            metric=dict(data["metric"]),
            governance=dict(data["governance"]),
            known_data=known,
            constraints=list(data.get("constraints") or []),
            validation=dict(data.get("validation") or {}),
        )

    @classmethod
    def load(cls, path: str | Path) -> "ChallengeSpec":
        with open(path, "r", encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))

    @property
    def alphabet(self) -> str:
        return self.variables["alphabet"]

    @property
    def length(self) -> int:
        return int(self.variables["length"])

    def validate_candidate(self, candidate: str) -> str:
        """Check a submission against the declared variables and constraints."""
        candidate = candidate.strip().upper()
        if len(candidate) != self.length:
            raise SpecError(
                f"candidate must be {self.length} characters long, got {len(candidate)}"
            )
        illegal = sorted(set(candidate) - set(self.alphabet))
        if illegal:
            raise SpecError(
                f"candidate uses characters outside the allowed alphabet "
                f"{self.alphabet!r}: {', '.join(illegal)}"
            )
        for constraint in self.constraints:
            _apply_constraint(constraint, candidate)
        return candidate


def _apply_constraint(constraint: Dict[str, Any], candidate: str) -> None:
    kind = constraint.get("kind")
    if kind == "max_run_length":
        limit = int(constraint["value"])
        run, previous = 1, ""
        for char in candidate:
            run = run + 1 if char == previous else 1
            previous = char
            if run > limit:
                raise SpecError(
                    f"constraint {constraint.get('name', kind)!r} violated: "
                    f"no more than {limit} identical bases in a row"
                )
    elif kind == "required_prefix":
        prefix = str(constraint["value"]).upper()
        if not candidate.startswith(prefix):
            raise SpecError(
                f"constraint {constraint.get('name', kind)!r} violated: "
                f"candidate must start with {prefix}"
            )
    elif kind is not None:
        raise SpecError(f"unknown constraint kind {kind!r}")
