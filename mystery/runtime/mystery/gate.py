"""The execution gate.

    Proposed Test -> Scope Check -> Constraint Check -> Risk Check
                  -> Execute OR Reject -> Capture Evidence

Nothing reaches execution without passing all three checks. A rejected test is
not a silent no-op: it is recorded on the case and marks its hypothesis
``untestable`` with a reason, so the refusal is part of the evidence trail.

The gate denies by default. An action the registry cannot classify is rejected
as unclassified rather than waved through, because the failure mode of the
opposite choice is that every novel action becomes a hole.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Iterable, Sequence

from .enums import Constraint, PrimaryDomain, RejectionReason
from .ids import utcnow

#: Every constraint is universal. Domains tighten *requirements*, never the
#: MUST_NOT set - there is no domain in which lateral movement becomes fine.
UNIVERSAL_CONSTRAINTS: frozenset[Constraint] = frozenset(Constraint)


@dataclass(frozen=True)
class DomainProfile:
    """Domain-specific tightening applied on top of the universal constraints."""

    domain: PrimaryDomain
    requires_authorization: bool = False
    max_auto_risk: int = 3
    constraints: frozenset[Constraint] = UNIVERSAL_CONSTRAINTS

    def strictness(self) -> tuple[int, int, int]:
        """Comparable strictness vector. Larger is stricter on every axis."""
        return (
            len(self.constraints),
            int(self.requires_authorization),
            -self.max_auto_risk,
        )


DOMAIN_PROFILES: dict[PrimaryDomain, DomainProfile] = {
    PrimaryDomain.SECURITY: DomainProfile(
        PrimaryDomain.SECURITY, requires_authorization=True, max_auto_risk=2
    ),
    PrimaryDomain.FRAUD: DomainProfile(
        PrimaryDomain.FRAUD, requires_authorization=True, max_auto_risk=2
    ),
    PrimaryDomain.DEBUGGING: DomainProfile(PrimaryDomain.DEBUGGING),
    PrimaryDomain.RESEARCH: DomainProfile(PrimaryDomain.RESEARCH),
    PrimaryDomain.WORKFLOW: DomainProfile(PrimaryDomain.WORKFLOW),
    PrimaryDomain.ANALYSIS: DomainProfile(PrimaryDomain.ANALYSIS),
    PrimaryDomain.GENERAL: DomainProfile(PrimaryDomain.GENERAL),
}

#: Subdomain tags that tighten the profile regardless of the primary domain.
SUBDOMAIN_TIGHTENING: dict[str, dict] = {
    "incident-response": {"requires_authorization": True, "max_auto_risk": 2},
    "forensics": {"requires_authorization": True, "max_auto_risk": 1},
    "compliance": {"requires_authorization": True},
    "threat-intelligence": {"max_auto_risk": 2},
    "identity": {"requires_authorization": True, "max_auto_risk": 2},
}

#: Declared action vocabulary. Mapping an action to constraints is how a
#: proposal becomes checkable; unlisted actions are refused, not assumed benign.
ACTION_CONSTRAINTS: dict[str, frozenset[Constraint]] = {
    # Read-only / observational
    "read_file": frozenset(),
    "read_log": frozenset(),
    "run_readonly_command": frozenset(),
    "query_database_readonly": frozenset(),
    "capture_screenshot": frozenset(),
    "inspect_configuration": frozenset(),
    "passive_network_capture": frozenset(),
    "interview_person": frozenset(),
    "static_code_analysis": frozenset(),
    "reproduce_locally": frozenset(),
    "compute_derived_analysis": frozenset(),
    # Mutating but legitimate inside scope
    "write_scratch_file": frozenset(),
    "restart_owned_service": frozenset(),
    "apply_configuration_change": frozenset(),
    # Categorically forbidden
    "guess_credentials": frozenset({Constraint.CREDENTIAL_GUESSING}),
    "brute_force": frozenset({Constraint.CREDENTIAL_GUESSING}),
    "reuse_leaked_credentials": frozenset({Constraint.CREDENTIAL_GUESSING}),
    "bypass_authentication": frozenset({Constraint.AUTHENTICATION_BYPASS}),
    "escalate_privileges": frozenset({Constraint.AUTHENTICATION_BYPASS}),
    "pivot_to_host": frozenset({Constraint.LATERAL_MOVEMENT}),
    "install_agent": frozenset({Constraint.PERSISTENCE}),
    "create_account": frozenset({Constraint.PERSISTENCE}),
    "add_scheduled_task": frozenset({Constraint.PERSISTENCE}),
    "modify_evidence": frozenset({Constraint.EVIDENCE_ALTERATION}),
    "overwrite_original": frozenset({Constraint.EVIDENCE_ALTERATION}),
    "delete_logs": frozenset({Constraint.ANTI_FORENSICS, Constraint.EVIDENCE_ALTERATION}),
    "clear_shell_history": frozenset({Constraint.ANTI_FORENSICS}),
    "tamper_timestamps": frozenset({Constraint.ANTI_FORENSICS}),
    "disable_logging": frozenset({Constraint.ACTIVITY_CONCEALMENT}),
    "disable_monitoring": frozenset({Constraint.ACTIVITY_CONCEALMENT}),
    "suppress_alerting": frozenset({Constraint.ACTIVITY_CONCEALMENT}),
    "exfiltrate_data": frozenset({Constraint.UNRELATED_EXFILTRATION}),
    "bulk_download_unrelated": frozenset({Constraint.UNRELATED_EXFILTRATION}),
    "stop_production_service": frozenset({Constraint.AVAILABILITY_DESTRUCTION}),
    "delete_data": frozenset({Constraint.AVAILABILITY_DESTRUCTION}),
    "flood_target": frozenset({Constraint.AVAILABILITY_DESTRUCTION}),
}


@dataclass(frozen=True)
class RiskPolicy:
    """Risk ceilings.

    ``hard_ceiling`` is not an approval threshold: a test scored 5 is refused
    outright, since 'a human clicked yes' is exactly the mechanism that turns a
    ceiling into a formality.
    """

    hard_ceiling: int = 5
    default_max_auto_risk: int = 3
    irreversible_requires_approval: bool = True


DEFAULT_RISK_POLICY = RiskPolicy()


@dataclass(frozen=True)
class TestProposal:
    test_id: str
    case_id: str
    hypothesis_id: str
    description: str
    target_assets: Sequence[str]
    actions: Sequence[str]
    risk: int
    reversible: bool = True
    declared_domain: PrimaryDomain | None = None
    approval: str | None = None
    proposed_by: str = "agent"
    proposed_at: str = field(default_factory=utcnow)

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "case_id": self.case_id,
            "hypothesis_id": self.hypothesis_id,
            "description": self.description,
            "target_assets": list(self.target_assets),
            "actions": list(self.actions),
            "risk": self.risk,
            "reversible": self.reversible,
            "declared_domain": str(self.declared_domain) if self.declared_domain else None,
            "approval": self.approval,
            "proposed_by": self.proposed_by,
            "proposed_at": self.proposed_at,
        }


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    checks: tuple[CheckResult, ...]
    reason: RejectionReason | None = None
    violated_constraints: tuple[Constraint, ...] = ()
    message: str = ""
    decided_at: str = field(default_factory=utcnow)

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "reason": str(self.reason) if self.reason else None,
            "violated_constraints": [str(c) for c in self.violated_constraints],
            "message": self.message,
            "checks": [
                {"name": c.name, "passed": c.passed, "detail": c.detail} for c in self.checks
            ],
            "decided_at": self.decided_at,
        }


def effective_profile(
    primary_domain: PrimaryDomain,
    subdomains: Iterable[str] = (),
    floor: DomainProfile | None = None,
) -> DomainProfile:
    """Strictest profile of: the domain, its subdomains, and the case floor.

    Monotonic by construction. Adding a tag or reclassifying a case can only
    make the profile stricter, which is what closes the 'call it research'
    loophole at the data level rather than at the prose level.
    """
    profile = DOMAIN_PROFILES.get(primary_domain, DomainProfile(primary_domain))
    requires_auth = profile.requires_authorization
    max_auto_risk = profile.max_auto_risk
    constraints = set(profile.constraints) | set(UNIVERSAL_CONSTRAINTS)

    for tag in subdomains:
        tighten = SUBDOMAIN_TIGHTENING.get(tag, {})
        requires_auth = requires_auth or tighten.get("requires_authorization", False)
        max_auto_risk = min(max_auto_risk, tighten.get("max_auto_risk", max_auto_risk))

    if floor is not None:
        requires_auth = requires_auth or floor.requires_authorization
        max_auto_risk = min(max_auto_risk, floor.max_auto_risk)
        constraints |= set(floor.constraints)

    return DomainProfile(
        domain=primary_domain,
        requires_authorization=requires_auth,
        max_auto_risk=max_auto_risk,
        constraints=frozenset(constraints),
    )


def asset_in_scope(asset: str, in_scope: Sequence[str], out_of_scope: Sequence[str]) -> bool:
    """Glob match. Exclusion wins ties - deny precedence, always."""
    if any(fnmatch(asset, pattern) for pattern in out_of_scope):
        return False
    return any(fnmatch(asset, pattern) for pattern in in_scope)


def check_scope(proposal: TestProposal, case) -> tuple[CheckResult, list[str]]:
    if not proposal.target_assets:
        return (
            CheckResult("scope", False, "proposal declares no target assets"),
            [],
        )
    offending = [
        asset
        for asset in proposal.target_assets
        if not asset_in_scope(asset, case.scope.assets_in_scope, case.scope.assets_out_of_scope)
    ]
    if offending:
        return (
            CheckResult("scope", False, f"assets outside locked scope: {', '.join(offending)}"),
            offending,
        )
    return CheckResult("scope", True, f"{len(proposal.target_assets)} asset(s) in scope"), []


def check_constraints(
    proposal: TestProposal, case, profile: DomainProfile
) -> tuple[CheckResult, list[Constraint], RejectionReason | None]:
    if not proposal.actions:
        return (
            CheckResult("constraint", False, "proposal declares no actions"),
            [],
            RejectionReason.INFEASIBLE,
        )

    unknown = [a for a in proposal.actions if a not in ACTION_CONSTRAINTS]
    if unknown:
        return (
            CheckResult(
                "constraint",
                False,
                f"unclassified action(s), refused by default: {', '.join(sorted(unknown))}",
            ),
            [],
            RejectionReason.INFEASIBLE,
        )

    violated: list[Constraint] = []
    for action in proposal.actions:
        for constraint in ACTION_CONSTRAINTS[action]:
            if constraint in profile.constraints and constraint not in violated:
                violated.append(constraint)

    # Relabelling check: a proposal may declare a stricter domain than the case,
    # never a looser one.
    if proposal.declared_domain and proposal.declared_domain != case.primary_domain:
        declared = effective_profile(proposal.declared_domain)
        if declared.strictness() < profile.strictness():
            violated.append(Constraint.DOMAIN_RELABELING)
            return (
                CheckResult(
                    "constraint",
                    False,
                    f"declared domain {proposal.declared_domain} is looser than the case "
                    f"floor ({case.primary_domain}); relabelling cannot relax constraints",
                ),
                violated,
                RejectionReason.CONSTRAINT_VIOLATION,
            )

    if violated:
        return (
            CheckResult(
                "constraint",
                False,
                "forbidden action class: " + ", ".join(str(c) for c in violated),
            ),
            violated,
            RejectionReason.CONSTRAINT_VIOLATION,
        )

    if profile.requires_authorization and case.authorization_basis is None:
        return (
            CheckResult("constraint", False, "domain requires an authorization basis; none recorded"),
            [],
            RejectionReason.MISSING_AUTHORIZATION,
        )

    return CheckResult("constraint", True, f"{len(proposal.actions)} action(s) permitted"), [], None


def check_risk(
    proposal: TestProposal, profile: DomainProfile, policy: RiskPolicy = DEFAULT_RISK_POLICY
) -> CheckResult:
    if not 0 <= proposal.risk <= 5:
        return CheckResult("risk", False, f"risk {proposal.risk} outside 0-5")
    if proposal.risk >= policy.hard_ceiling:
        return CheckResult(
            "risk", False, f"risk {proposal.risk} meets the hard ceiling; not executable"
        )
    needs_approval = proposal.risk > profile.max_auto_risk or (
        policy.irreversible_requires_approval and not proposal.reversible
    )
    if needs_approval and not proposal.approval:
        why = (
            f"risk {proposal.risk} exceeds auto limit {profile.max_auto_risk}"
            if proposal.risk > profile.max_auto_risk
            else "irreversible test"
        )
        return CheckResult("risk", False, f"{why}; explicit approval required")
    detail = f"risk {proposal.risk} within auto limit {profile.max_auto_risk}"
    if needs_approval:
        detail = f"risk {proposal.risk} accepted under approval {proposal.approval!r}"
    return CheckResult("risk", True, detail)


def evaluate(
    proposal: TestProposal, case, policy: RiskPolicy = DEFAULT_RISK_POLICY
) -> GateDecision:
    """Run the full gate. Checks run in order; all results are recorded."""
    profile = effective_profile(case.primary_domain, case.subdomain, case.constraint_floor_profile())

    checks: list[CheckResult] = []
    scope_check, _offending = check_scope(proposal, case)
    checks.append(scope_check)
    if not scope_check.passed:
        return GateDecision(
            allowed=False,
            checks=tuple(checks),
            reason=RejectionReason.OUT_OF_SCOPE,
            violated_constraints=(Constraint.SCOPE_ESCAPE,),
            message=scope_check.detail,
        )

    constraint_check, violated, reason = check_constraints(proposal, case, profile)
    checks.append(constraint_check)
    if not constraint_check.passed:
        return GateDecision(
            allowed=False,
            checks=tuple(checks),
            reason=reason or RejectionReason.CONSTRAINT_VIOLATION,
            violated_constraints=tuple(violated),
            message=constraint_check.detail,
        )

    risk_check = check_risk(proposal, profile, policy)
    checks.append(risk_check)
    if not risk_check.passed:
        return GateDecision(
            allowed=False,
            checks=tuple(checks),
            reason=RejectionReason.RISK_THRESHOLD_EXCEEDED,
            message=risk_check.detail,
        )

    return GateDecision(allowed=True, checks=tuple(checks), message="all checks passed")
