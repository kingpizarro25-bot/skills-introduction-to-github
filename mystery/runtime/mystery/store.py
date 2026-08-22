"""Filesystem persistence.

Layout under the store root::

    counters.json                    id sequences
    audit.jsonl                      append-only, every engine action
    cases/<case_id>/case.json        materialised case state
    cases/<case_id>/hypotheses.json
    cases/<case_id>/findings.json
    cases/<case_id>/evidence.jsonl   append-only ledger
    knowledge/lessons.json

Evidence and audit are append-only files; everything else is a materialised
view that can be rebuilt from them.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .errors import ImmutabilityError, ValidationError
from .evidence import EvidenceLedger
from .ids import new_case_id, new_lesson_id, utcnow
from .models import Case, Evidence, Finding, Hypothesis, Lesson


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


class CaseStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # -- paths ---------------------------------------------------------------
    @property
    def counters_path(self) -> Path:
        return self.root / "counters.json"

    @property
    def audit_path(self) -> Path:
        return self.root / "audit.jsonl"

    @property
    def lessons_path(self) -> Path:
        return self.root / "knowledge" / "lessons.json"

    def case_dir(self, case_id: str) -> Path:
        return self.root / "cases" / case_id

    # -- ids -----------------------------------------------------------------
    def _next_sequence(self, key: str) -> int:
        counters = _read_json(self.counters_path, {})
        value = int(counters.get(key, 0)) + 1
        counters[key] = value
        _write_json(self.counters_path, counters)
        return value

    def allocate_case_id(self) -> str:
        today = datetime.now(timezone.utc).date()
        return new_case_id(self._next_sequence(f"case:{today.isoformat()}"), today)

    def allocate_lesson_id(self) -> str:
        today = datetime.now(timezone.utc).date()
        return new_lesson_id(self._next_sequence(f"lesson:{today.isoformat()}"), today)

    # -- audit ---------------------------------------------------------------
    def audit(self, action: str, actor: str, **detail) -> None:
        """Append-only. Concealing activity is a constraint violation, so the
        audit file is only ever opened for append."""
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        record = {"at": utcnow(), "actor": actor, "action": action, "detail": detail}
        with open(self.audit_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_audit(self) -> list[dict]:
        if not self.audit_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.audit_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    # -- cases ---------------------------------------------------------------
    def list_cases(self) -> list[str]:
        base = self.root / "cases"
        if not base.exists():
            return []
        return sorted(p.name for p in base.iterdir() if (p / "case.json").exists())

    def save_case(self, case: Case) -> None:
        path = self.case_dir(case.case_id) / "case.json"
        existing = _read_json(path, None)
        if existing is not None:
            for locked in ("case_id", "created_at", "primary_domain"):
                if existing.get(locked) != case.to_dict().get(locked):
                    raise ImmutabilityError(
                        f"{locked} changed after creation", code="immutable_field", field=locked
                    )
            if existing.get("scope") != case.scope.to_dict():
                raise ImmutabilityError(
                    "scope changed after lock", code="scope_immutable", case_id=case.case_id
                )
        _write_json(path, case.to_dict())

    def load_case(self, case_id: str) -> Case:
        data = _read_json(self.case_dir(case_id) / "case.json", None)
        if data is None:
            raise ValidationError(f"unknown case {case_id!r}", code="unknown_case")
        return Case.from_dict(data)

    # -- hypotheses ----------------------------------------------------------
    def save_hypotheses(self, case_id: str, hypotheses: list[Hypothesis]) -> None:
        _write_json(self.case_dir(case_id) / "hypotheses.json", [h.to_dict() for h in hypotheses])

    def load_hypotheses(self, case_id: str) -> list[Hypothesis]:
        return [
            Hypothesis.from_dict(d)
            for d in _read_json(self.case_dir(case_id) / "hypotheses.json", [])
        ]

    # -- findings ------------------------------------------------------------
    def save_findings(self, case_id: str, findings: list[Finding]) -> None:
        _write_json(self.case_dir(case_id) / "findings.json", [f.to_dict() for f in findings])

    def load_findings(self, case_id: str) -> list[Finding]:
        return [Finding.from_dict(d) for d in _read_json(self.case_dir(case_id) / "findings.json", [])]

    # -- evidence ------------------------------------------------------------
    def evidence_path(self, case_id: str) -> Path:
        return self.case_dir(case_id) / "evidence.jsonl"

    def append_evidence(self, evidence: Evidence) -> None:
        path = self.evidence_path(evidence.case_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        for existing in self.load_ledger(evidence.case_id):
            if existing.id == evidence.id:
                raise ImmutabilityError(
                    f"evidence {evidence.id} is already written", code="evidence_overwrite"
                )
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(evidence.to_dict(), ensure_ascii=False) + "\n")

    def load_ledger(self, case_id: str) -> EvidenceLedger:
        ledger = EvidenceLedger(case_id=case_id)
        path = self.evidence_path(case_id)
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    ledger.append(Evidence.from_dict(json.loads(line)))
        return ledger

    # -- knowledge base ------------------------------------------------------
    def load_lessons(self) -> list[Lesson]:
        return [Lesson.from_dict(d) for d in _read_json(self.lessons_path, [])]

    def save_lessons(self, lessons: list[Lesson]) -> None:
        _write_json(self.lessons_path, [l.to_dict() for l in lessons])

    def upsert_lesson(self, lesson: Lesson) -> None:
        lessons = self.load_lessons()
        for index, existing in enumerate(lessons):
            if existing.lesson_id == lesson.lesson_id:
                lessons[index] = lesson
                break
        else:
            lessons.append(lesson)
        self.save_lessons(lessons)
