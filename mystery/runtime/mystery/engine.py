"""The /MYSTERY runtime.

    CASE CREATED -> SCOPE LOCKED -> RECON -> HYPOTHESES -> TEST PROPOSAL
      -> SCOPE + CONSTRAINT + RISK GATE -> INVESTIGATION
      -> APPEND-ONLY EVIDENCE -> FINDING -> CANDIDATE LESSON -> VALIDATION

The engine never executes anything itself. It gates a proposal, hands the
approved action to a caller-supplied executor, and records what came back. A
host that skips the gate cannot reach ``capture`` through this API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from . import knowledge
from .enums import (
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
from .errors import ValidationError
from .gate import DEFAULT_RISK_POLICY, GateDecision, RiskPolicy, TestProposal, evaluate
from .ids import child_id, utcnow
from .models import (
    AuthorizationBasis,
    Case,
    Evidence,
    Finding,
    Hypothesis,
    Lesson,
    OpenQuestion,
    Scope,
)
from .ranking import DEFAULT_PROFILE, Factors, WeightProfile, rank
from .store import CaseStore

#: What an executor must hand back for its output to become evidence.
ExecutorResult = dict


@dataclass
class TestOutcome:
    proposal: TestProposal
    decision: GateDecision
    evidence: Evidence | None = None

    @property
    def executed(self) -> bool:
        return self.decision.allowed and self.evidence is not None

    def to_dict(self) -> dict:
        return {
            "proposal": self.proposal.to_dict(),
            "decision": self.decision.to_dict(),
            "evidence_id": self.evidence.id if self.evidence else None,
        }


class MysteryEngine:
    def __init__(
        self,
        store: CaseStore,
        actor: str = "user",
        weight_profile: WeightProfile = DEFAULT_PROFILE,
        risk_policy: RiskPolicy = DEFAULT_RISK_POLICY,
    ):
        self.store = store
        self.actor = actor
        self.weight_profile = weight_profile
        self.risk_policy = risk_policy

    # -- stage 1: recon ------------------------------------------------------
    def open_case(
        self,
        problem_statement: str,
        primary_domain: PrimaryDomain | str,
        scope_statement: str,
        assets_in_scope: Sequence[str],
        assets_out_of_scope: Sequence[str] = (),
        *,
        case_alias: str | None = None,
        subdomain: Sequence[str] = (),
        authorization: AuthorizationBasis | None = None,
        known_facts: Sequence[str] = (),
        unknowns: Sequence[str] = (),
        open_questions: Sequence[str] = (),
    ) -> Case:
        """Create a case with its scope locked. There is no un-scoped case."""
        scope = Scope(
            statement=scope_statement,
            assets_in_scope=tuple(assets_in_scope),
            assets_out_of_scope=tuple(assets_out_of_scope),
            locked_by=self.actor,
        )
        domain = PrimaryDomain(primary_domain)
        case = Case(
            case_id=self.store.allocate_case_id(),
            problem_statement=problem_statement,
            primary_domain=domain,
            scope=scope,
            created_by=self.actor,
            case_alias=case_alias,
            subdomain=list(subdomain),
            constraint_floor=frozenset(Constraint),
            authorization_basis=authorization,
            known_facts=list(known_facts),
            unknowns=list(unknowns),
            case_status=CaseStatus.RECON,
            open_questions=[OpenQuestion(text=q) for q in open_questions],
        )
        case.log(
            "case_opened",
            self.actor,
            domain=str(domain),
            scope_hash=scope.scope_hash,
            locked_at=scope.locked_at,
        )
        self.store.save_case(case)
        self.store.audit(
            "case_opened",
            self.actor,
            case_id=case.case_id,
            domain=str(domain),
            scope_hash=scope.scope_hash,
        )
        return case

    def record_recon(
        self,
        case_id: str,
        *,
        known_facts: Iterable[str] = (),
        unknowns: Iterable[str] = (),
        open_questions: Iterable[str] = (),
    ) -> Case:
        case = self.store.load_case(case_id)
        self._reject_if_closed(case)
        case.known_facts.extend(known_facts)
        case.unknowns.extend(unknowns)
        case.open_questions.extend(OpenQuestion(text=q) for q in open_questions)
        case.case_status = CaseStatus.RECON
        case.log("recon_updated", self.actor)
        self.store.save_case(case)
        return case

    # -- stage 2: hypotheses -------------------------------------------------
    def add_hypothesis(
        self,
        case_id: str,
        statement: str,
        *,
        likelihood: int,
        evidence_support: int,
        information_gain: int,
        impact: int,
        test_cost: int,
        risk: int,
        supersedes: str | None = None,
    ) -> Hypothesis:
        case = self.store.load_case(case_id)
        self._reject_if_closed(case)
        hypotheses = self.store.load_hypotheses(case_id)
        hypothesis = Hypothesis(
            id=child_id("hypothesis", len(hypotheses) + 1),
            case_id=case_id,
            statement=statement,
            factors=Factors(
                likelihood=likelihood,
                evidence_support=evidence_support,
                information_gain=information_gain,
                impact=impact,
                test_cost=test_cost,
                risk=risk,
            ),
            created_by=self.actor,
            supersedes=supersedes,
        )
        hypothesis.rescore(self.weight_profile)
        if supersedes:
            for existing in hypotheses:
                if existing.id == supersedes:
                    existing.mark(HypothesisStatus.SUPERSEDED, successor=hypothesis.id)
        hypotheses.append(hypothesis)
        case.hypotheses.append(hypothesis.id)
        case.case_status = CaseStatus.HYPOTHESIS
        case.log("hypothesis_added", self.actor, hypothesis_id=hypothesis.id)
        self.store.save_hypotheses(case_id, hypotheses)
        self.store.save_case(case)
        return hypothesis

    def ranked_hypotheses(self, case_id: str) -> list[Hypothesis]:
        hypotheses = self.store.load_hypotheses(case_id)
        for hypothesis in hypotheses:
            hypothesis.rescore(self.weight_profile)
        return rank(hypotheses, self.weight_profile)

    # -- stage 3: investigation ---------------------------------------------
    def propose_test(
        self,
        case_id: str,
        hypothesis_id: str,
        description: str,
        *,
        target_assets: Sequence[str],
        actions: Sequence[str],
        risk: int,
        reversible: bool = True,
        declared_domain: PrimaryDomain | str | None = None,
        approval: str | None = None,
    ) -> tuple[TestProposal, GateDecision]:
        """Build a proposal and run it through the gate without executing."""
        case = self.store.load_case(case_id)
        self._reject_if_closed(case)
        ledger = self.store.load_ledger(case_id)
        proposal = TestProposal(
            test_id=child_id("test", len(ledger) + 1),
            case_id=case_id,
            hypothesis_id=hypothesis_id,
            description=description,
            target_assets=tuple(target_assets),
            actions=tuple(actions),
            risk=risk,
            reversible=reversible,
            declared_domain=PrimaryDomain(declared_domain) if declared_domain else None,
            approval=approval,
            proposed_by=self.actor,
        )
        return proposal, evaluate(proposal, case, self.risk_policy)

    def run_test(
        self,
        case_id: str,
        hypothesis_id: str,
        description: str,
        *,
        target_assets: Sequence[str],
        actions: Sequence[str],
        risk: int,
        executor: Callable[[TestProposal], ExecutorResult] | None = None,
        reversible: bool = True,
        declared_domain: PrimaryDomain | str | None = None,
        approval: str | None = None,
    ) -> TestOutcome:
        """Gate, then execute, then capture. Rejection is recorded, not swallowed."""
        proposal, decision = self.propose_test(
            case_id,
            hypothesis_id,
            description,
            target_assets=target_assets,
            actions=actions,
            risk=risk,
            reversible=reversible,
            declared_domain=declared_domain,
            approval=approval,
        )
        case = self.store.load_case(case_id)
        hypotheses = self.store.load_hypotheses(case_id)
        hypothesis = self._find_hypothesis(hypotheses, hypothesis_id)

        if not decision.allowed:
            hypothesis.mark(
                HypothesisStatus.UNTESTABLE,
                reason=decision.reason or RejectionReason.INFEASIBLE,
            )
            case.log(
                "test_rejected",
                self.actor,
                test_id=proposal.test_id,
                hypothesis_id=hypothesis_id,
                reason=str(decision.reason),
                violated=[str(c) for c in decision.violated_constraints],
                message=decision.message,
            )
            self.store.save_hypotheses(case_id, hypotheses)
            self.store.save_case(case)
            self.store.audit(
                "test_rejected",
                self.actor,
                case_id=case_id,
                test_id=proposal.test_id,
                reason=str(decision.reason),
                message=decision.message,
            )
            return TestOutcome(proposal=proposal, decision=decision)

        # A hypothesis previously blocked by the gate becomes testable again
        # once a proposal actually clears it (e.g. re-proposed with approval).
        hypothesis.mark(HypothesisStatus.TESTING)
        hypothesis.untestable_reason = None
        case.case_status = CaseStatus.INVESTIGATION
        case.log("test_approved", self.actor, test_id=proposal.test_id, hypothesis_id=hypothesis_id)
        self.store.audit("test_approved", self.actor, case_id=case_id, test_id=proposal.test_id)

        evidence = None
        if executor is not None:
            result = executor(proposal)
            evidence = self._capture(
                case,
                ledger=self.store.load_ledger(case_id),
                type=result.get("type", EvidenceType.TERMINAL_OUTPUT),
                source=result.get("source", "executor"),
                description=result.get("description", description),
                content=result.get("content"),
                content_hash=result.get("content_hash"),
                original_reference=result.get(
                    "original_reference", f"artifact://{case_id}/{proposal.test_id}"
                ),
                related_hypotheses=[hypothesis_id],
                classification=result.get("classification", Classification.INTERNAL),
                retention=result.get("retention"),
                produced_by_test=proposal.test_id,
            )
            if result.get("supports") is True:
                hypothesis.link_evidence(evidence.id, supports=True)
            elif result.get("supports") is False:
                hypothesis.link_evidence(evidence.id, supports=False)

        self.store.save_hypotheses(case_id, hypotheses)
        self.store.save_case(case)
        return TestOutcome(proposal=proposal, decision=decision, evidence=evidence)

    def record_evidence(
        self,
        case_id: str,
        *,
        type: EvidenceType | str,
        source: str,
        description: str,
        content: bytes | None = None,
        content_hash: str | None = None,
        original_reference: str,
        related_hypotheses: Sequence[str] = (),
        classification: Classification | str = Classification.INTERNAL,
        retention: Retention | str | None = None,
        produced_by_test: str | None = None,
    ) -> Evidence:
        """Record evidence captured outside a gated test (a user paste, a handover)."""
        case = self.store.load_case(case_id)
        self._reject_if_closed(case)
        evidence = self._capture(
            case,
            ledger=self.store.load_ledger(case_id),
            type=type,
            source=source,
            description=description,
            content=content,
            content_hash=content_hash,
            original_reference=original_reference,
            related_hypotheses=related_hypotheses,
            classification=classification,
            retention=retention,
            produced_by_test=produced_by_test,
        )
        self.store.save_case(case)
        return evidence

    def derive_evidence(
        self,
        case_id: str,
        parent_id: str,
        *,
        description: str,
        method: str,
        content: bytes | None = None,
        content_hash: str | None = None,
        tool: str | None = None,
        parameters: dict | None = None,
    ) -> Evidence:
        """Transformations create a new object; the original is preserved."""
        case = self.store.load_case(case_id)
        self._reject_if_closed(case)
        ledger = self.store.load_ledger(case_id)
        child = ledger.derive(
            parent_id,
            description=description,
            method=method,
            content=content,
            content_hash=content_hash,
            performed_by=self.actor,
            tool=tool,
            parameters=parameters,
        )
        self.store.append_evidence(child)
        case.evidence.append(child.id)
        case.log("evidence_derived", self.actor, evidence_id=child.id, derived_from=parent_id)
        self.store.save_case(case)
        self.store.audit(
            "evidence_derived", self.actor, case_id=case_id, evidence_id=child.id, parent=parent_id
        )
        return child

    def link_evidence(
        self, case_id: str, hypothesis_id: str, evidence_id: str, *, supports: bool
    ) -> Hypothesis:
        hypotheses = self.store.load_hypotheses(case_id)
        hypothesis = self._find_hypothesis(hypotheses, hypothesis_id)
        self.store.load_ledger(case_id).get(evidence_id)  # existence check
        hypothesis.link_evidence(evidence_id, supports=supports)
        self.store.save_hypotheses(case_id, hypotheses)
        return hypothesis

    def set_hypothesis_status(
        self, case_id: str, hypothesis_id: str, status: HypothesisStatus | str, **kwargs
    ) -> Hypothesis:
        hypotheses = self.store.load_hypotheses(case_id)
        hypothesis = self._find_hypothesis(hypotheses, hypothesis_id)
        hypothesis.mark(HypothesisStatus(status), **kwargs)
        self.store.save_hypotheses(case_id, hypotheses)
        return hypothesis

    # -- stage 4: finding ----------------------------------------------------
    def conclude(
        self,
        case_id: str,
        status: FindingStatus | str,
        summary: str,
        *,
        confidence: float,
        supported_hypotheses: Sequence[str] = (),
        rejected_hypotheses: Sequence[str] = (),
        competing_hypotheses: Sequence[str] = (),
        evidence: Sequence[str] = (),
        missing_evidence: Sequence[str] = (),
        next_best_test: str | None = None,
        blockers: Sequence[str] = (),
        recommendations: Sequence[str] = (),
    ) -> Finding:
        """Write a finding. ``inconclusive`` is a legitimate ending, and the
        schema forces it to carry what is still competing and what to test next
        rather than rounding uncertainty up to an answer."""
        case = self.store.load_case(case_id)
        self._reject_if_closed(case)
        findings = self.store.load_findings(case_id)
        finding = Finding(
            id=child_id("finding", len(findings) + 1),
            case_id=case_id,
            status=FindingStatus(status),
            summary=summary,
            confidence=confidence,
            created_by=self.actor,
            supported_hypotheses=list(supported_hypotheses),
            rejected_hypotheses=list(rejected_hypotheses),
            competing_hypotheses=list(competing_hypotheses),
            evidence=list(evidence),
            missing_evidence=list(missing_evidence),
            next_best_test=next_best_test,
            blockers=list(blockers),
            recommendations=list(recommendations),
        )
        findings.append(finding)
        case.findings.append(finding.id)
        case.case_status = CaseStatus(finding.status.value)
        case.closed_at = utcnow()
        case.log("finding_recorded", self.actor, finding_id=finding.id, status=str(finding.status))
        self.store.save_findings(case_id, findings)
        self.store.save_case(case)
        self.store.audit(
            "finding_recorded", self.actor, case_id=case_id, finding_id=finding.id, status=str(finding.status)
        )
        return finding

    def suspend(self, case_id: str, reason: str) -> Case:
        case = self.store.load_case(case_id)
        case.case_status = CaseStatus.SUSPENDED
        case.log("case_suspended", self.actor, reason=reason)
        self.store.save_case(case)
        return case

    # -- stage 5: knowledge --------------------------------------------------
    def draft_lesson(
        self,
        case_id: str,
        statement: str,
        scope_of_applicability: str,
        *,
        domain_tags: Sequence[str] = (),
        evidence_id: str | None = None,
    ) -> Lesson:
        """A finished case yields a *candidate*. Nothing is validated by one case."""
        case = self.store.load_case(case_id)
        lesson = Lesson(
            lesson_id=self.store.allocate_lesson_id(),
            statement=statement,
            scope_of_applicability=scope_of_applicability,
            source_case_ids=[case_id],
            primary_domain=case.primary_domain,
            domain_tags=list(domain_tags or case.subdomain),
            status=LessonStatus.CANDIDATE,
        )
        lesson.confidence = knowledge.compute_confidence(lesson)
        lesson.log("drafted", self.actor, case_id=case_id, evidence_id=evidence_id)
        self.store.upsert_lesson(lesson)
        self.store.audit("lesson_drafted", self.actor, lesson_id=lesson.lesson_id, case_id=case_id)
        return lesson

    def confirm_lesson(self, lesson_id: str, case_id: str, **kwargs) -> Lesson:
        lesson = self._find_lesson(lesson_id)
        knowledge.confirm(lesson, case_id, actor=self.actor, **kwargs)
        self.store.upsert_lesson(lesson)
        self.store.audit(
            "lesson_confirmed", self.actor, lesson_id=lesson_id, case_id=case_id, status=str(lesson.status)
        )
        return lesson

    def contradict_lesson(self, lesson_id: str, case_id: str, **kwargs) -> Lesson:
        lesson = self._find_lesson(lesson_id)
        knowledge.contradict(lesson, case_id, actor=self.actor, **kwargs)
        self.store.upsert_lesson(lesson)
        self.store.audit("lesson_contradicted", self.actor, lesson_id=lesson_id, case_id=case_id)
        return lesson

    def reusable_knowledge(self, domain=None, tags=()) -> list[Lesson]:
        return knowledge.reusable(self.store.load_lessons(), domain=domain, tags=tags)

    # -- helpers -------------------------------------------------------------
    def _capture(self, case: Case, *, ledger, **kwargs) -> Evidence:
        evidence = ledger.capture(captured_by=self.actor, **kwargs)
        self.store.append_evidence(evidence)
        case.evidence.append(evidence.id)
        case.log("evidence_captured", self.actor, evidence_id=evidence.id, hash=evidence.hash)
        self.store.audit(
            "evidence_captured",
            self.actor,
            case_id=case.case_id,
            evidence_id=evidence.id,
            hash=evidence.hash,
        )
        return evidence

    @staticmethod
    def _find_hypothesis(hypotheses: list[Hypothesis], hypothesis_id: str) -> Hypothesis:
        for hypothesis in hypotheses:
            if hypothesis.id == hypothesis_id:
                return hypothesis
        raise ValidationError(f"unknown hypothesis {hypothesis_id!r}", code="unknown_hypothesis")

    def _find_lesson(self, lesson_id: str) -> Lesson:
        for lesson in self.store.load_lessons():
            if lesson.lesson_id == lesson_id:
                return lesson
        raise ValidationError(f"unknown lesson {lesson_id!r}", code="unknown_lesson")

    @staticmethod
    def _reject_if_closed(case: Case) -> None:
        if case.case_status in TERMINAL_CASE_STATUSES:
            raise ValidationError(
                f"case {case.case_id} is {case.case_status}; reopen or open a new case",
                code="case_closed",
            )


def authorization(
    type: AuthorizationType | str,
    reference: str | None = None,
    granted_by: str | None = None,
    expires_at: str | None = None,
) -> AuthorizationBasis:
    return AuthorizationBasis(
        type=AuthorizationType(type),
        reference=reference,
        granted_by=granted_by,
        expires_at=expires_at,
    )
