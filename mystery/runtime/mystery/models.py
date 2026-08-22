"""Object model for MYSTERY v1.

Mirrors ``schema/json/*.schema.json``. Immutability that the architecture calls
for is expressed in the type system where possible: ``Scope`` and ``Evidence``
are frozen dataclasses, so "append-only" is not a convention someone has to
remember at 3am.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping

from .enums import (
    SCHEMA_VERSION,
    AuthorizationType,
    CaseStatus,
    Classification,
    Constraint,
    EvidenceType,
    FindingStatus,
    HypothesisStatus,
    LessonStatus,
    PrimaryDomain,
    RejectionReason,
    Retention,
    TERMINAL_CASE_STATUSES,
)
from .errors import ImmutabilityError, ValidationError
from .gate import DOMAIN_PROFILES, UNIVERSAL_CONSTRAINTS, DomainProfile
from .ids import is_case_alias, is_case_id, utcnow
from .ranking import Factors, PriorityScore, WeightProfile, score

HASH_ALGORITHM = "sha256"


def canonical_json(payload: Any) -> bytes:
    """Stable serialisation, so a hash of the same content is the same hash."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def digest(data: bytes, algorithm: str = HASH_ALGORITHM) -> str:
    if algorithm not in ("sha256", "sha512", "blake2b512"):
        raise ValidationError(f"unsupported hash algorithm: {algorithm}", code="hash_algorithm")
    hasher = hashlib.blake2b(digest_size=64) if algorithm == "blake2b512" else hashlib.new(algorithm)
    hasher.update(data)
    return f"{algorithm}:{hasher.hexdigest()}"


def _text(value: Any, field_name: str, *, maximum: int = 8192) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} is required and must be non-empty", code="required")
    if len(value) > maximum:
        raise ValidationError(f"{field_name} exceeds {maximum} characters", code="too_long")
    return value


@dataclass(frozen=True)
class AuthorizationBasis:
    type: AuthorizationType
    reference: str | None = None
    granted_by: str | None = None
    recorded_at: str = field(default_factory=utcnow)
    expires_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "type", AuthorizationType(self.type))

    def to_dict(self) -> dict:
        data = {"type": str(self.type), "recorded_at": self.recorded_at}
        for key in ("reference", "granted_by", "expires_at"):
            value = getattr(self, key)
            if value:
                data[key] = value
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AuthorizationBasis":
        return cls(
            type=AuthorizationType(data["type"]),
            reference=data.get("reference"),
            granted_by=data.get("granted_by"),
            recorded_at=data.get("recorded_at") or utcnow(),
            expires_at=data.get("expires_at"),
        )


@dataclass(frozen=True)
class Scope:
    """Locked at case creation. There is no supported path to edit one."""

    statement: str
    assets_in_scope: tuple[str, ...]
    assets_out_of_scope: tuple[str, ...] = ()
    locked_at: str = field(default_factory=utcnow)
    locked_by: str = "user"
    scope_hash: str = ""

    def __post_init__(self) -> None:
        _text(self.statement, "scope.statement", maximum=4096)
        if not self.assets_in_scope:
            raise ValidationError(
                "scope.assets_in_scope must list at least one asset", code="scope_empty"
            )
        object.__setattr__(self, "assets_in_scope", tuple(self.assets_in_scope))
        object.__setattr__(self, "assets_out_of_scope", tuple(self.assets_out_of_scope))
        overlap = set(self.assets_in_scope) & set(self.assets_out_of_scope)
        if overlap:
            raise ValidationError(
                f"assets declared both in and out of scope: {', '.join(sorted(overlap))}",
                code="scope_contradiction",
            )
        if not self.scope_hash:
            object.__setattr__(self, "scope_hash", self.compute_hash())

    def compute_hash(self) -> str:
        return digest(
            canonical_json(
                {
                    "statement": self.statement,
                    "assets_in_scope": sorted(self.assets_in_scope),
                    "assets_out_of_scope": sorted(self.assets_out_of_scope),
                }
            )
        )

    def verify(self) -> bool:
        return self.scope_hash == self.compute_hash()

    def to_dict(self) -> dict:
        return {
            "statement": self.statement,
            "assets_in_scope": list(self.assets_in_scope),
            "assets_out_of_scope": list(self.assets_out_of_scope),
            "locked_at": self.locked_at,
            "locked_by": self.locked_by,
            "scope_hash": self.scope_hash,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Scope":
        return cls(
            statement=data["statement"],
            assets_in_scope=tuple(data["assets_in_scope"]),
            assets_out_of_scope=tuple(data.get("assets_out_of_scope", ())),
            locked_at=data.get("locked_at") or utcnow(),
            locked_by=data.get("locked_by", "user"),
            scope_hash=data.get("scope_hash", ""),
        )


@dataclass(frozen=True)
class OpenQuestion:
    text: str
    raised_at: str = field(default_factory=utcnow)
    blocking: bool = False
    answered_at: str | None = None
    answer: str | None = None

    def to_dict(self) -> dict:
        data = {"text": self.text, "raised_at": self.raised_at, "blocking": self.blocking}
        if self.answered_at:
            data["answered_at"] = self.answered_at
        if self.answer:
            data["answer"] = self.answer
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OpenQuestion":
        return cls(
            text=data["text"],
            raised_at=data.get("raised_at") or utcnow(),
            blocking=bool(data.get("blocking", False)),
            answered_at=data.get("answered_at"),
            answer=data.get("answer"),
        )


@dataclass(frozen=True)
class JournalEntry:
    at: str
    actor: str
    action: str
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = {"at": self.at, "actor": self.actor, "action": self.action}
        if self.detail:
            data["detail"] = self.detail
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "JournalEntry":
        return cls(
            at=data["at"], actor=data["actor"], action=data["action"], detail=dict(data.get("detail", {}))
        )


@dataclass
class Case:
    case_id: str
    problem_statement: str
    primary_domain: PrimaryDomain
    scope: Scope
    created_by: str = "user"
    created_at: str = field(default_factory=utcnow)
    case_alias: str | None = None
    subdomain: list[str] = field(default_factory=list)
    constraint_floor: frozenset[Constraint] = UNIVERSAL_CONSTRAINTS
    authorization_basis: AuthorizationBasis | None = None
    known_facts: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    case_status: CaseStatus = CaseStatus.CREATED
    open_questions: list[OpenQuestion] = field(default_factory=list)
    hypotheses: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    closed_at: str | None = None
    journal: list[JournalEntry] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not is_case_id(self.case_id):
            raise ValidationError(
                f"case_id {self.case_id!r} is not system-generated (MYS-YYYYMMDD-NNNNNN)",
                code="case_id_format",
            )
        if self.case_alias is not None and not is_case_alias(self.case_alias):
            raise ValidationError(
                f"case_alias {self.case_alias!r} must be A-Z 0-9 _ - and 3-64 chars",
                code="case_alias_format",
            )
        _text(self.problem_statement, "problem_statement")
        object.__setattr__(self, "primary_domain", PrimaryDomain(self.primary_domain))
        self.case_status = CaseStatus(self.case_status)
        if not isinstance(self.scope, Scope):
            raise ValidationError("scope must be a locked Scope object", code="scope_required")
        if not self.scope.verify():
            raise ImmutabilityError(
                "scope hash does not match its contents; scope was altered after lock",
                code="scope_tampered",
            )
        object.__setattr__(
            self, "constraint_floor", frozenset(Constraint(c) for c in self.constraint_floor)
        )
        profile = DOMAIN_PROFILES.get(self.primary_domain)
        if profile and profile.requires_authorization and self.authorization_basis is None:
            raise ValidationError(
                f"domain {self.primary_domain} requires an authorization_basis",
                code="authorization_required",
            )
        if self.case_status in TERMINAL_CASE_STATUSES and not self.closed_at:
            raise ValidationError(
                f"terminal status {self.case_status} requires closed_at", code="closed_at_required"
            )

    # -- immutable-field guard ------------------------------------------------
    _LOCKED_FIELDS = ("case_id", "created_at", "scope", "primary_domain", "constraint_floor")

    def __setattr__(self, name: str, value: Any) -> None:
        if name in self._LOCKED_FIELDS and getattr(self, name, None) is not None:
            current = getattr(self, name)
            if current != value:
                raise ImmutabilityError(
                    f"{name} is locked at case creation and cannot be changed",
                    code="immutable_field",
                    field=name,
                )
        object.__setattr__(self, name, value)

    def constraint_floor_profile(self) -> DomainProfile:
        base = DOMAIN_PROFILES.get(self.primary_domain, DomainProfile(self.primary_domain))
        return DomainProfile(
            domain=self.primary_domain,
            requires_authorization=base.requires_authorization,
            max_auto_risk=base.max_auto_risk,
            constraints=self.constraint_floor,
        )

    def log(self, action: str, actor: str = "agent", **detail) -> JournalEntry:
        entry = JournalEntry(at=utcnow(), actor=actor, action=action, detail=detail)
        self.journal.append(entry)
        return entry

    def add_subdomain(self, tag: str, actor: str = "agent") -> None:
        """Tags may be added (they can only tighten) but never removed."""
        if tag not in self.subdomain:
            self.subdomain.append(tag)
            self.log("subdomain_added", actor, tag=tag)

    def to_dict(self) -> dict:
        data = {
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "problem_statement": self.problem_statement,
            "primary_domain": str(self.primary_domain),
            "subdomain": list(self.subdomain),
            "constraint_floor": sorted(str(c) for c in self.constraint_floor),
            "scope": self.scope.to_dict(),
            "known_facts": list(self.known_facts),
            "unknowns": list(self.unknowns),
            "case_status": str(self.case_status),
            "open_questions": [q.to_dict() for q in self.open_questions],
            "hypotheses": list(self.hypotheses),
            "evidence": list(self.evidence),
            "findings": list(self.findings),
            "journal": [j.to_dict() for j in self.journal],
        }
        if self.case_alias:
            data["case_alias"] = self.case_alias
        if self.authorization_basis:
            data["authorization_basis"] = self.authorization_basis.to_dict()
        if self.closed_at:
            data["closed_at"] = self.closed_at
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Case":
        auth = data.get("authorization_basis")
        return cls(
            case_id=data["case_id"],
            problem_statement=data["problem_statement"],
            primary_domain=PrimaryDomain(data["primary_domain"]),
            scope=Scope.from_dict(data["scope"]),
            created_by=data.get("created_by", "user"),
            created_at=data.get("created_at") or utcnow(),
            case_alias=data.get("case_alias"),
            subdomain=list(data.get("subdomain", [])),
            constraint_floor=frozenset(Constraint(c) for c in data.get("constraint_floor", [])),
            authorization_basis=AuthorizationBasis.from_dict(auth) if auth else None,
            known_facts=list(data.get("known_facts", [])),
            unknowns=list(data.get("unknowns", [])),
            case_status=CaseStatus(data.get("case_status", "created")),
            open_questions=[OpenQuestion.from_dict(q) for q in data.get("open_questions", [])],
            hypotheses=list(data.get("hypotheses", [])),
            evidence=list(data.get("evidence", [])),
            findings=list(data.get("findings", [])),
            closed_at=data.get("closed_at"),
            journal=[JournalEntry.from_dict(j) for j in data.get("journal", [])],
            schema_version=data.get("schema_version", SCHEMA_VERSION),
        )


@dataclass
class Hypothesis:
    id: str
    case_id: str
    statement: str
    factors: Factors
    created_by: str = "agent"
    created_at: str = field(default_factory=utcnow)
    status: HypothesisStatus = HypothesisStatus.UNTESTED
    priority_score: PriorityScore | None = None
    supporting_evidence: list[str] = field(default_factory=list)
    contradicting_evidence: list[str] = field(default_factory=list)
    open_questions: list[OpenQuestion] = field(default_factory=list)
    untestable_reason: RejectionReason | None = None
    supersedes: str | None = None
    superseded_by: str | None = None
    updated_at: str | None = None
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _text(self.statement, "hypothesis.statement", maximum=4096)
        self.status = HypothesisStatus(self.status)
        if isinstance(self.factors, Mapping):
            self.factors = Factors.from_dict(self.factors)
        if self.priority_score is None:
            self.priority_score = score(self.factors)
        self._validate_status()

    def _validate_status(self) -> None:
        if self.status is HypothesisStatus.UNTESTABLE and self.untestable_reason is None:
            raise ValidationError(
                "an untestable hypothesis must record untestable_reason", code="untestable_reason"
            )
        if self.status is HypothesisStatus.SUPERSEDED and not self.superseded_by:
            raise ValidationError(
                "a superseded hypothesis must name superseded_by", code="superseded_by"
            )

    def rescore(self, profile: WeightProfile | None = None) -> PriorityScore:
        self.priority_score = score(self.factors, profile)
        self.updated_at = utcnow()
        return self.priority_score

    def set_factors(self, **changes: int) -> PriorityScore:
        merged = self.factors.to_dict() | changes
        self.factors = Factors.from_dict(merged)
        return self.rescore()

    def link_evidence(self, evidence_id: str, *, supports: bool) -> None:
        bucket = self.supporting_evidence if supports else self.contradicting_evidence
        if evidence_id not in bucket:
            bucket.append(evidence_id)
        self.updated_at = utcnow()

    def mark(
        self, status: HypothesisStatus, *, reason: RejectionReason | None = None, successor: str | None = None
    ) -> None:
        self.status = HypothesisStatus(status)
        if reason is not None:
            self.untestable_reason = RejectionReason(reason)
        if successor is not None:
            self.superseded_by = successor
        self._validate_status()
        self.updated_at = utcnow()

    def to_dict(self) -> dict:
        data = {
            "schema_version": self.schema_version,
            "id": self.id,
            "case_id": self.case_id,
            "statement": self.statement,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "status": str(self.status),
            "factors": self.factors.to_dict(),
            "priority_score": self.priority_score.to_dict(),
            "supporting_evidence": list(self.supporting_evidence),
            "contradicting_evidence": list(self.contradicting_evidence),
            "open_questions": [q.to_dict() for q in self.open_questions],
        }
        if self.untestable_reason:
            data["untestable_reason"] = str(self.untestable_reason)
        if self.supersedes:
            data["supersedes"] = self.supersedes
        if self.superseded_by:
            data["superseded_by"] = self.superseded_by
        if self.updated_at:
            data["updated_at"] = self.updated_at
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Hypothesis":
        ps = data.get("priority_score")
        return cls(
            id=data["id"],
            case_id=data["case_id"],
            statement=data["statement"],
            factors=Factors.from_dict(data["factors"]),
            created_by=data.get("created_by", "agent"),
            created_at=data.get("created_at") or utcnow(),
            status=HypothesisStatus(data.get("status", "untested")),
            priority_score=PriorityScore(**ps) if ps else None,
            supporting_evidence=list(data.get("supporting_evidence", [])),
            contradicting_evidence=list(data.get("contradicting_evidence", [])),
            open_questions=[OpenQuestion.from_dict(q) for q in data.get("open_questions", [])],
            untestable_reason=(
                RejectionReason(data["untestable_reason"]) if data.get("untestable_reason") else None
            ),
            supersedes=data.get("supersedes"),
            superseded_by=data.get("superseded_by"),
            updated_at=data.get("updated_at"),
            schema_version=data.get("schema_version", SCHEMA_VERSION),
        )


@dataclass(frozen=True)
class Derivation:
    method: str
    performed_at: str = field(default_factory=utcnow)
    performed_by: str = "agent"
    tool: str | None = None
    parameters: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = {
            "method": self.method,
            "performed_at": self.performed_at,
            "performed_by": self.performed_by,
        }
        if self.tool:
            data["tool"] = self.tool
        if self.parameters:
            data["parameters"] = dict(self.parameters)
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Derivation":
        return cls(
            method=data["method"],
            performed_at=data.get("performed_at") or utcnow(),
            performed_by=data.get("performed_by", "agent"),
            tool=data.get("tool"),
            parameters=dict(data.get("parameters", {})),
        )


@dataclass(frozen=True)
class Evidence:
    """Frozen by construction. Processing an artifact produces a *new* Evidence
    linked by ``derived_from`` - the original is never edited."""

    id: str
    case_id: str
    type: EvidenceType
    source: str
    description: str
    hash: str
    original_reference: str
    captured_by: str = "user"
    captured_at: str = field(default_factory=utcnow)
    related_hypotheses: tuple[str, ...] = ()
    produced_by_test: str | None = None
    classification: Classification = Classification.INTERNAL
    retention: Retention = Retention.CASE_LIFETIME
    derived_from: str | None = None
    derivation: Derivation | None = None
    verified: bool = True
    verified_at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "type", EvidenceType(self.type))
        object.__setattr__(self, "classification", Classification(self.classification))
        object.__setattr__(self, "retention", Retention(self.retention))
        object.__setattr__(self, "related_hypotheses", tuple(self.related_hypotheses))
        _text(self.description, "evidence.description", maximum=4096)
        _text(self.source, "evidence.source", maximum=512)
        _text(self.original_reference, "evidence.original_reference", maximum=2048)
        algorithm = self.hash.split(":", 1)[0] if ":" in self.hash else ""
        if algorithm not in ("sha256", "sha512", "blake2b512"):
            raise ValidationError(
                f"evidence.hash must be algorithm-prefixed, got {self.hash!r}", code="hash_format"
            )
        if self.derived_from and self.derivation is None:
            raise ValidationError(
                "derived evidence must describe its derivation", code="derivation_required"
            )
        if self.derivation is not None and not self.derived_from:
            raise ValidationError(
                "derivation recorded without derived_from parent", code="derived_from_required"
            )
        if self.classification is Classification.RESTRICTED and self.retention is Retention.EPHEMERAL:
            raise ValidationError(
                "restricted evidence cannot be ephemeral", code="retention_conflict"
            )

    @property
    def hash_algorithm(self) -> str:
        return self.hash.split(":", 1)[0]

    @property
    def is_original(self) -> bool:
        return self.derived_from is None

    def to_dict(self) -> dict:
        data = {
            "schema_version": SCHEMA_VERSION,
            "id": self.id,
            "case_id": self.case_id,
            "type": str(self.type),
            "source": self.source,
            "captured_at": self.captured_at,
            "captured_by": self.captured_by,
            "description": self.description,
            "hash": self.hash,
            "original_reference": self.original_reference,
            "related_hypotheses": list(self.related_hypotheses),
            "classification": str(self.classification),
            "retention": str(self.retention),
            "integrity": {
                "append_only": True,
                "original_preserved": True,
                "verified": self.verified,
                "hash_algorithm": self.hash_algorithm,
            },
        }
        if self.verified_at:
            data["integrity"]["verified_at"] = self.verified_at
        if self.produced_by_test:
            data["produced_by_test"] = self.produced_by_test
        if self.derived_from:
            data["derived_from"] = self.derived_from
            data["derivation"] = self.derivation.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Evidence":
        integrity = data.get("integrity", {})
        derivation = data.get("derivation")
        return cls(
            id=data["id"],
            case_id=data["case_id"],
            type=EvidenceType(data["type"]),
            source=data["source"],
            description=data["description"],
            hash=data["hash"],
            original_reference=data["original_reference"],
            captured_by=data.get("captured_by", "user"),
            captured_at=data.get("captured_at") or utcnow(),
            related_hypotheses=tuple(data.get("related_hypotheses", ())),
            produced_by_test=data.get("produced_by_test"),
            classification=Classification(data.get("classification", "internal")),
            retention=Retention(data.get("retention", "case_lifetime")),
            derived_from=data.get("derived_from"),
            derivation=Derivation.from_dict(derivation) if derivation else None,
            verified=bool(integrity.get("verified", True)),
            verified_at=integrity.get("verified_at"),
        )


@dataclass
class Finding:
    id: str
    case_id: str
    status: FindingStatus
    summary: str
    confidence: float
    created_by: str = "agent"
    created_at: str = field(default_factory=utcnow)
    supported_hypotheses: list[str] = field(default_factory=list)
    rejected_hypotheses: list[str] = field(default_factory=list)
    competing_hypotheses: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    next_best_test: str | None = None
    blockers: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        self.status = FindingStatus(self.status)
        _text(self.summary, "finding.summary")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValidationError("finding.confidence must be within 0..1", code="confidence_range")
        if self.status is FindingStatus.INCONCLUSIVE:
            # Stage 4 must never manufacture certainty. An inconclusive finding
            # has to say what is still competing and how to settle it.
            if len(self.competing_hypotheses) < 2:
                raise ValidationError(
                    "an inconclusive finding must list at least two competing hypotheses",
                    code="competing_required",
                )
            if not self.missing_evidence:
                raise ValidationError(
                    "an inconclusive finding must list the missing evidence",
                    code="missing_evidence_required",
                )
            if not self.next_best_test:
                raise ValidationError(
                    "an inconclusive finding must name the next best test",
                    code="next_best_test_required",
                )
        if self.status is FindingStatus.BLOCKED and not self.blockers:
            raise ValidationError("a blocked finding must state its blockers", code="blockers_required")
        if self.status is FindingStatus.RESOLVED:
            if not self.supported_hypotheses:
                raise ValidationError(
                    "a resolved finding needs at least one supported hypothesis",
                    code="supported_required",
                )
            if not self.evidence:
                raise ValidationError(
                    "a resolved finding needs at least one piece of evidence", code="evidence_required"
                )

    def to_dict(self) -> dict:
        data = {
            "schema_version": self.schema_version,
            "id": self.id,
            "case_id": self.case_id,
            "status": str(self.status),
            "summary": self.summary,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "confidence": self.confidence,
            "supported_hypotheses": list(self.supported_hypotheses),
            "rejected_hypotheses": list(self.rejected_hypotheses),
            "competing_hypotheses": list(self.competing_hypotheses),
            "evidence": list(self.evidence),
            "missing_evidence": list(self.missing_evidence),
            "blockers": list(self.blockers),
            "recommendations": list(self.recommendations),
        }
        if self.next_best_test:
            data["next_best_test"] = self.next_best_test
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Finding":
        return cls(
            id=data["id"],
            case_id=data["case_id"],
            status=FindingStatus(data["status"]),
            summary=data["summary"],
            confidence=float(data["confidence"]),
            created_by=data.get("created_by", "agent"),
            created_at=data.get("created_at") or utcnow(),
            supported_hypotheses=list(data.get("supported_hypotheses", [])),
            rejected_hypotheses=list(data.get("rejected_hypotheses", [])),
            competing_hypotheses=list(data.get("competing_hypotheses", [])),
            evidence=list(data.get("evidence", [])),
            missing_evidence=list(data.get("missing_evidence", [])),
            next_best_test=data.get("next_best_test"),
            blockers=list(data.get("blockers", [])),
            recommendations=list(data.get("recommendations", [])),
            schema_version=data.get("schema_version", SCHEMA_VERSION),
        )


@dataclass
class EvidenceRef:
    case_id: str
    evidence_id: str | None = None
    note: str | None = None
    resolved: bool = False

    def to_dict(self, *, include_resolved: bool = False) -> dict:
        data: dict[str, Any] = {"case_id": self.case_id}
        if self.evidence_id:
            data["evidence_id"] = self.evidence_id
        if self.note:
            data["note"] = self.note
        if include_resolved:
            data["resolved"] = self.resolved
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EvidenceRef":
        return cls(
            case_id=data["case_id"],
            evidence_id=data.get("evidence_id"),
            note=data.get("note"),
            resolved=bool(data.get("resolved", False)),
        )


@dataclass
class Lesson:
    lesson_id: str
    statement: str
    scope_of_applicability: str
    source_case_ids: list[str]
    confidence: float = 0.3
    primary_domain: PrimaryDomain | None = None
    domain_tags: list[str] = field(default_factory=list)
    supporting_evidence: list[EvidenceRef] = field(default_factory=list)
    contradicting_evidence: list[EvidenceRef] = field(default_factory=list)
    created_at: str = field(default_factory=utcnow)
    last_validated_at: str | None = None
    status: LessonStatus = LessonStatus.CANDIDATE
    supersedes: str | None = None
    superseded_by: str | None = None
    journal: list[JournalEntry] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _text(self.statement, "lesson.statement", maximum=4096)
        _text(self.scope_of_applicability, "lesson.scope_of_applicability", maximum=4096)
        self.status = LessonStatus(self.status)
        if self.primary_domain is not None:
            self.primary_domain = PrimaryDomain(self.primary_domain)
        if not self.source_case_ids:
            raise ValidationError("a lesson needs at least one source case", code="source_required")

    def log(self, action: str, actor: str = "agent", **detail) -> None:
        self.journal.append(JournalEntry(at=utcnow(), actor=actor, action=action, detail=detail))

    def to_dict(self) -> dict:
        data = {
            "schema_version": self.schema_version,
            "lesson_id": self.lesson_id,
            "statement": self.statement,
            "source_case_ids": list(dict.fromkeys(self.source_case_ids)),
            "domain_tags": list(self.domain_tags),
            "scope_of_applicability": self.scope_of_applicability,
            "confidence": round(float(self.confidence), 4),
            "supporting_evidence": [e.to_dict() for e in self.supporting_evidence],
            "contradicting_evidence": [
                e.to_dict(include_resolved=True) for e in self.contradicting_evidence
            ],
            "created_at": self.created_at,
            "status": str(self.status),
            "journal": [j.to_dict() for j in self.journal],
        }
        if self.primary_domain:
            data["primary_domain"] = str(self.primary_domain)
        if self.last_validated_at:
            data["last_validated_at"] = self.last_validated_at
        if self.supersedes:
            data["supersedes"] = self.supersedes
        if self.superseded_by:
            data["superseded_by"] = self.superseded_by
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Lesson":
        return cls(
            lesson_id=data["lesson_id"],
            statement=data["statement"],
            scope_of_applicability=data["scope_of_applicability"],
            source_case_ids=list(data["source_case_ids"]),
            confidence=float(data.get("confidence", 0.3)),
            primary_domain=(
                PrimaryDomain(data["primary_domain"]) if data.get("primary_domain") else None
            ),
            domain_tags=list(data.get("domain_tags", [])),
            supporting_evidence=[EvidenceRef.from_dict(e) for e in data.get("supporting_evidence", [])],
            contradicting_evidence=[
                EvidenceRef.from_dict(e) for e in data.get("contradicting_evidence", [])
            ],
            created_at=data.get("created_at") or utcnow(),
            last_validated_at=data.get("last_validated_at"),
            status=LessonStatus(data.get("status", "candidate")),
            supersedes=data.get("supersedes"),
            superseded_by=data.get("superseded_by"),
            journal=[JournalEntry.from_dict(j) for j in data.get("journal", [])],
            schema_version=data.get("schema_version", SCHEMA_VERSION),
        )
