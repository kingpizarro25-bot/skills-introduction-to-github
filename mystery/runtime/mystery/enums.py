"""Closed vocabularies for MYSTERY v1.

These mirror ``schema/json/common.schema.json``. ``tests/test_schema_sync.py``
fails if the two drift apart, so the schema and the runtime cannot disagree
about what a legal value is.
"""

from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


class PrimaryDomain(StrEnum):
    DEBUGGING = "debugging"
    RESEARCH = "research"
    SECURITY = "security"
    FRAUD = "fraud"
    WORKFLOW = "workflow"
    ANALYSIS = "analysis"
    GENERAL = "general"


class CaseStatus(StrEnum):
    CREATED = "created"
    RECON = "recon"
    HYPOTHESIS = "hypothesis"
    INVESTIGATION = "investigation"
    ANALYSIS = "analysis"
    RESOLVED = "resolved"
    PARTIALLY_RESOLVED = "partially_resolved"
    BLOCKED = "blocked"
    INCONCLUSIVE = "inconclusive"
    SUSPENDED = "suspended"
    CLOSED = "closed"


#: Statuses that end a case. ``suspended`` is deliberately absent: it is a pause.
TERMINAL_CASE_STATUSES = frozenset(
    {
        CaseStatus.RESOLVED,
        CaseStatus.PARTIALLY_RESOLVED,
        CaseStatus.BLOCKED,
        CaseStatus.INCONCLUSIVE,
        CaseStatus.CLOSED,
    }
)


class HypothesisStatus(StrEnum):
    UNTESTED = "untested"
    TESTING = "testing"
    SUPPORTED = "supported"
    REJECTED = "rejected"
    UNCERTAIN = "uncertain"
    UNTESTABLE = "untestable"
    SUPERSEDED = "superseded"


class FindingStatus(StrEnum):
    RESOLVED = "resolved"
    PARTIALLY_RESOLVED = "partially_resolved"
    INCONCLUSIVE = "inconclusive"
    BLOCKED = "blocked"


class LessonStatus(StrEnum):
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    DEPRECATED = "deprecated"
    RETIRED = "retired"
    CONFLICTED = "conflicted"


class AuthorizationType(StrEnum):
    OWNER = "owner"
    WRITTEN_PERMISSION = "written_permission"
    LAB = "lab"
    TRAINING_ENVIRONMENT = "training_environment"


class EvidenceType(StrEnum):
    TERMINAL_OUTPUT = "terminal_output"
    LOG = "log"
    FILE = "file"
    SCREENSHOT = "screenshot"
    NETWORK_CAPTURE = "network_capture"
    DATABASE_RECORD = "database_record"
    DOCUMENT = "document"
    INTERVIEW = "interview"
    METRIC = "metric"
    CODE_ARTIFACT = "code_artifact"
    DERIVED_ANALYSIS = "derived_analysis"
    EXTERNAL_REPORT = "external_report"


class Classification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class Retention(StrEnum):
    EPHEMERAL = "ephemeral"
    CASE_LIFETIME = "case_lifetime"
    D30 = "30d"
    D90 = "90d"
    Y1 = "1y"
    Y7 = "7y"
    LEGAL_HOLD = "legal_hold"


class Constraint(StrEnum):
    """Universal MUST_NOT invariants, enforced by the gate at execution time."""

    SCOPE_ESCAPE = "scope_escape"
    EVIDENCE_ALTERATION = "evidence_alteration"
    ACTIVITY_CONCEALMENT = "activity_concealment"
    CREDENTIAL_GUESSING = "credential_guessing"
    AUTHENTICATION_BYPASS = "authentication_bypass"
    LATERAL_MOVEMENT = "lateral_movement"
    PERSISTENCE = "persistence"
    UNRELATED_EXFILTRATION = "unrelated_exfiltration"
    AVAILABILITY_DESTRUCTION = "availability_destruction"
    ANTI_FORENSICS = "anti_forensics"
    DOMAIN_RELABELING = "domain_relabeling"


class RejectionReason(StrEnum):
    OUT_OF_SCOPE = "out_of_scope"
    CONSTRAINT_VIOLATION = "constraint_violation"
    RISK_THRESHOLD_EXCEEDED = "risk_threshold_exceeded"
    MISSING_AUTHORIZATION = "missing_authorization"
    INFEASIBLE = "infeasible"


#: Canonical subdomain tags. Unknown tags are permitted (the vocabulary is open)
#: but they never relax a constraint - see gate.effective_constraints.
CANONICAL_SUBDOMAINS = frozenset(
    {
        "incident-response",
        "forensics",
        "compliance",
        "threat-intelligence",
        "data-integrity",
        "ai-behavior",
        "networking",
        "identity",
        "automation",
    }
)

SCHEMA_VERSION = "1.0.0"
