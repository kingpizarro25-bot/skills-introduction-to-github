"""Typed failures for the MYSTERY engine.

Every refusal carries a machine-readable code so a rejection can be recorded on
the case rather than merely printed at a human.
"""


class MysteryError(Exception):
    """Base class. Carries a stable error code."""

    code = "mystery_error"

    def __init__(self, message: str, code: str | None = None, **detail):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.detail = detail

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "detail": self.detail}


class ValidationError(MysteryError):
    code = "validation_error"


class ImmutabilityError(MysteryError):
    """Raised on any attempt to mutate a locked field (scope, evidence, ids)."""

    code = "immutability_violation"


class ScopeViolation(MysteryError):
    code = "out_of_scope"


class ConstraintViolation(MysteryError):
    code = "constraint_violation"


class AuthorizationMissing(MysteryError):
    code = "missing_authorization"


class RiskThresholdExceeded(MysteryError):
    code = "risk_threshold_exceeded"
