"""Knowledge-base hygiene.

    Case lesson -> candidate -> repeated confirmation -> validated -> reusable

One investigation produces a candidate, never a universal truth. Everything a
lesson claims carries the cases it came from and the limits it holds within, so
that a stale entry can be found and retired instead of quietly misleading the
next case.
"""

from __future__ import annotations

from dataclasses import dataclass

from .enums import LessonStatus
from .errors import ValidationError
from .ids import utcnow
from .models import EvidenceRef, Lesson


@dataclass(frozen=True)
class PromotionPolicy:
    """Default: two independent cases and no unresolved contradiction."""

    distinct_cases_required: int = 2
    base_confidence: float = 0.3
    confidence_per_case: float = 0.2
    max_confidence: float = 0.95
    contradiction_penalty: float = 0.25
    min_confidence: float = 0.05
    revalidation_days: int = 180


DEFAULT_POLICY = PromotionPolicy()


def unresolved_contradictions(lesson: Lesson) -> list[EvidenceRef]:
    return [ref for ref in lesson.contradicting_evidence if not ref.resolved]


def compute_confidence(lesson: Lesson, policy: PromotionPolicy = DEFAULT_POLICY) -> float:
    cases = len(set(lesson.source_case_ids))
    value = policy.base_confidence + policy.confidence_per_case * max(cases - 1, 0)
    value -= policy.contradiction_penalty * len(unresolved_contradictions(lesson))
    return round(max(policy.min_confidence, min(policy.max_confidence, value)), 4)


def confirm(
    lesson: Lesson,
    case_id: str,
    *,
    evidence_id: str | None = None,
    note: str | None = None,
    actor: str = "agent",
    policy: PromotionPolicy = DEFAULT_POLICY,
) -> Lesson:
    """Record a confirming case and promote if the threshold is met."""
    if lesson.status in (LessonStatus.RETIRED, LessonStatus.DEPRECATED):
        raise ValidationError(
            f"cannot confirm a {lesson.status} lesson", code="lesson_status"
        )
    if case_id not in lesson.source_case_ids:
        lesson.source_case_ids.append(case_id)
    lesson.supporting_evidence.append(
        EvidenceRef(case_id=case_id, evidence_id=evidence_id, note=note)
    )
    lesson.confidence = compute_confidence(lesson, policy)
    lesson.log("confirmed", actor, case_id=case_id, evidence_id=evidence_id)

    distinct = len(set(lesson.source_case_ids))
    if unresolved_contradictions(lesson):
        lesson.status = LessonStatus.CONFLICTED
    elif distinct >= policy.distinct_cases_required:
        if lesson.status is not LessonStatus.VALIDATED:
            lesson.log("promoted", actor, from_status=str(lesson.status), distinct_cases=distinct)
        lesson.status = LessonStatus.VALIDATED
        lesson.last_validated_at = utcnow()
    return lesson


def contradict(
    lesson: Lesson,
    case_id: str,
    *,
    evidence_id: str | None = None,
    note: str | None = None,
    actor: str = "agent",
    policy: PromotionPolicy = DEFAULT_POLICY,
) -> Lesson:
    """A contradiction demotes a lesson to conflicted, whatever its status was.

    A validated lesson is not privileged: contradicting evidence outranks
    accumulated confidence, which is the whole point of tracking both.
    """
    lesson.contradicting_evidence.append(
        EvidenceRef(case_id=case_id, evidence_id=evidence_id, note=note)
    )
    lesson.status = LessonStatus.CONFLICTED
    lesson.confidence = compute_confidence(lesson, policy)
    lesson.log("contradicted", actor, case_id=case_id, evidence_id=evidence_id)
    return lesson


def resolve_contradiction(
    lesson: Lesson,
    index: int,
    *,
    actor: str = "agent",
    policy: PromotionPolicy = DEFAULT_POLICY,
) -> Lesson:
    """Mark one contradiction resolved and recompute the lesson's standing."""
    try:
        ref = lesson.contradicting_evidence[index]
    except IndexError:
        raise ValidationError(f"no contradiction at index {index}", code="unknown_contradiction") from None
    ref.resolved = True
    lesson.confidence = compute_confidence(lesson, policy)
    if not unresolved_contradictions(lesson):
        distinct = len(set(lesson.source_case_ids))
        if distinct >= policy.distinct_cases_required:
            lesson.status = LessonStatus.VALIDATED
            lesson.last_validated_at = utcnow()
        else:
            lesson.status = LessonStatus.CANDIDATE
    lesson.log("contradiction_resolved", actor, index=index, status=str(lesson.status))
    return lesson


def deprecate(lesson: Lesson, reason: str, *, actor: str = "agent") -> Lesson:
    lesson.status = LessonStatus.DEPRECATED
    lesson.log("deprecated", actor, reason=reason)
    return lesson


def retire(lesson: Lesson, successor_id: str, *, actor: str = "agent") -> Lesson:
    if not successor_id:
        raise ValidationError("retiring a lesson requires a successor", code="successor_required")
    lesson.status = LessonStatus.RETIRED
    lesson.superseded_by = successor_id
    lesson.log("retired", actor, superseded_by=successor_id)
    return lesson


def reusable(lessons, *, domain=None, tags=()) -> list[Lesson]:
    """Only validated lessons are handed back to a new investigation."""
    tags = set(tags)
    out = []
    for lesson in lessons:
        if lesson.status is not LessonStatus.VALIDATED:
            continue
        if domain and lesson.primary_domain and lesson.primary_domain != domain:
            continue
        if tags and not tags & set(lesson.domain_tags):
            continue
        out.append(lesson)
    return sorted(out, key=lambda l: (-l.confidence, l.lesson_id))
