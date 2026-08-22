"""Append-only evidence ledger and chain of custody.

Two rules, both enforced here rather than trusted to discipline:

1. An evidence id is written once. Re-registering an id is a violation, not an
   update.
2. Processing produces a new object: ``E1 -> derived-from -> E2``. There is no
   code path that edits E1, because ``Evidence`` is frozen.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

from .enums import Classification, EvidenceType, Retention
from .errors import ImmutabilityError, ValidationError
from .ids import child_id, utcnow
from .models import Derivation, Evidence, digest

CHUNK = 1 << 20

#: Default retention by classification. Documented defaults, overridable per
#: capture; see docs/decisions.md.
DEFAULT_RETENTION: dict[Classification, Retention] = {
    Classification.PUBLIC: Retention.CASE_LIFETIME,
    Classification.INTERNAL: Retention.CASE_LIFETIME,
    Classification.CONFIDENTIAL: Retention.Y1,
    Classification.RESTRICTED: Retention.Y7,
}


def hash_bytes(data: bytes, algorithm: str = "sha256") -> str:
    return digest(data, algorithm)


def hash_text(text: str, algorithm: str = "sha256") -> str:
    return digest(text.encode("utf-8"), algorithm)


def hash_file(path: str | Path, algorithm: str = "sha256") -> str:
    hasher = hashlib.blake2b(digest_size=64) if algorithm == "blake2b512" else hashlib.new(algorithm)
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK), b""):
            hasher.update(chunk)
    return f"{algorithm}:{hasher.hexdigest()}"


@dataclass
class EvidenceLedger:
    """In-memory append-only ledger for one case."""

    case_id: str
    _items: dict[str, Evidence] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[Evidence]:
        return iter(self._items.values())

    def __contains__(self, evidence_id: object) -> bool:
        return evidence_id in self._items

    def get(self, evidence_id: str) -> Evidence:
        try:
            return self._items[evidence_id]
        except KeyError:
            raise ValidationError(f"unknown evidence {evidence_id!r}", code="unknown_evidence") from None

    def next_id(self) -> str:
        return child_id("evidence", len(self._items) + 1)

    def append(self, evidence: Evidence) -> Evidence:
        if evidence.case_id != self.case_id:
            raise ValidationError(
                f"evidence {evidence.id} belongs to {evidence.case_id}, not {self.case_id}",
                code="case_mismatch",
            )
        if evidence.id in self._items:
            raise ImmutabilityError(
                f"evidence {evidence.id} already exists; the ledger is append-only",
                code="evidence_overwrite",
            )
        if evidence.derived_from and evidence.derived_from not in self._items:
            raise ValidationError(
                f"derived_from {evidence.derived_from!r} is not in the ledger",
                code="unknown_parent",
            )
        self._items[evidence.id] = evidence
        return evidence

    def capture(
        self,
        *,
        type: EvidenceType | str,
        source: str,
        description: str,
        content: bytes | None = None,
        content_hash: str | None = None,
        original_reference: str,
        captured_by: str = "user",
        related_hypotheses: Iterable[str] = (),
        classification: Classification | str = Classification.INTERNAL,
        retention: Retention | str | None = None,
        produced_by_test: str | None = None,
        algorithm: str = "sha256",
    ) -> Evidence:
        """Record an original capture. Exactly one of content/content_hash."""
        if (content is None) == (content_hash is None):
            raise ValidationError(
                "provide either content or content_hash, not both", code="hash_source"
            )
        classification = Classification(classification)
        if retention is None:
            retention = DEFAULT_RETENTION[classification]
        return self.append(
            Evidence(
                id=self.next_id(),
                case_id=self.case_id,
                type=EvidenceType(type),
                source=source,
                description=description,
                hash=content_hash or hash_bytes(content, algorithm),
                original_reference=original_reference,
                captured_by=captured_by,
                related_hypotheses=tuple(related_hypotheses),
                classification=classification,
                retention=Retention(retention),
                produced_by_test=produced_by_test,
            )
        )

    def derive(
        self,
        parent_id: str,
        *,
        description: str,
        method: str,
        content: bytes | None = None,
        content_hash: str | None = None,
        original_reference: str | None = None,
        performed_by: str = "agent",
        tool: str | None = None,
        parameters: dict | None = None,
        type: EvidenceType | str = EvidenceType.DERIVED_ANALYSIS,
        algorithm: str = "sha256",
    ) -> Evidence:
        """Create the processed child of an existing object. The parent is untouched."""
        parent = self.get(parent_id)
        if (content is None) == (content_hash is None):
            raise ValidationError(
                "provide either content or content_hash, not both", code="hash_source"
            )
        child = Evidence(
            id=self.next_id(),
            case_id=self.case_id,
            type=EvidenceType(type),
            source=f"derived:{parent.id}",
            description=description,
            hash=content_hash or hash_bytes(content, algorithm),
            original_reference=original_reference or parent.original_reference,
            captured_by=performed_by,
            related_hypotheses=parent.related_hypotheses,
            # Derived material inherits the parent's handling rules; a
            # transformation must never launder a classification downward.
            classification=parent.classification,
            retention=parent.retention,
            derived_from=parent.id,
            derivation=Derivation(
                method=method,
                performed_at=utcnow(),
                performed_by=performed_by,
                tool=tool,
                parameters=parameters or {},
            ),
        )
        return self.append(child)

    def provenance(self, evidence_id: str) -> list[Evidence]:
        """Chain from the original capture down to the requested object."""
        chain: list[Evidence] = []
        seen: set[str] = set()
        current: Evidence | None = self.get(evidence_id)
        while current is not None:
            if current.id in seen:
                raise ValidationError(
                    f"derivation cycle at {current.id}", code="derivation_cycle"
                )
            seen.add(current.id)
            chain.append(current)
            current = self.get(current.derived_from) if current.derived_from else None
        return list(reversed(chain))

    def verify_against(self, evidence_id: str, content: bytes) -> bool:
        evidence = self.get(evidence_id)
        return hash_bytes(content, evidence.hash_algorithm) == evidence.hash
