"""Identifier generation.

Case identifiers are system-generated and opaque to the user; the readable
label lives in ``case_alias`` and is explicitly not an identifier. Child
identifiers (hypotheses, evidence, tests, findings) are sequential within a
case, so uniqueness is the pair (case_id, id).
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone

CASE_ID_RE = re.compile(r"^MYS-(\d{8})-(\d{6})$")
CASE_ALIAS_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,63}$")
LESSON_ID_RE = re.compile(r"^LSN-\d{8}-\d{6}$")

_CHILD_FORMATS = {
    "hypothesis": ("H", 3),
    "evidence": ("E", 4),
    "finding": ("F", 3),
    "test": ("T", 4),
}


def utcnow() -> str:
    """Timestamp in RFC 3339 with an explicit offset."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_case_id(sequence: int, on: date | None = None) -> str:
    """MYS-YYYYMMDD-NNNNNN. ``sequence`` is allocated by the store, per day."""
    if not 1 <= sequence <= 999999:
        raise ValueError(f"case sequence out of range: {sequence}")
    day = (on or datetime.now(timezone.utc).date()).strftime("%Y%m%d")
    return f"MYS-{day}-{sequence:06d}"


def new_lesson_id(sequence: int, on: date | None = None) -> str:
    if not 1 <= sequence <= 999999:
        raise ValueError(f"lesson sequence out of range: {sequence}")
    day = (on or datetime.now(timezone.utc).date()).strftime("%Y%m%d")
    return f"LSN-{day}-{sequence:06d}"


def child_id(kind: str, sequence: int) -> str:
    """Sequential id for a case-scoped object: child_id('evidence', 1) -> 'E-0001'."""
    try:
        prefix, width = _CHILD_FORMATS[kind]
    except KeyError:
        raise ValueError(f"unknown child id kind: {kind}") from None
    if sequence < 1:
        raise ValueError(f"{kind} sequence out of range: {sequence}")
    return f"{prefix}-{sequence:0{width}d}"


def is_case_id(value: str) -> bool:
    return bool(CASE_ID_RE.match(value or ""))


def is_case_alias(value: str) -> bool:
    return bool(CASE_ALIAS_RE.match(value or ""))
