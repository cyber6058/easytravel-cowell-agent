from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CowellCliError(Exception):
    code: str
    message: str
    exit_code: int
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


class ConfigurationError(CowellCliError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        from .exit_codes import INPUT_ERROR

        super().__init__(
            code="CONFIGURATION_ERROR",
            message=message,
            exit_code=INPUT_ERROR,
            details=details or {},
        )

class ReadOnlyPolicyError(CowellCliError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        from .exit_codes import SOURCE_ERROR

        super().__init__(
            code="READ_ONLY_POLICY_BLOCKED",
            message=message,
            exit_code=SOURCE_ERROR,
            details=details or {},
        )


class WritePolicyError(CowellCliError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        from .exit_codes import SOURCE_ERROR

        super().__init__(
            code="WRITE_POLICY_BLOCKED",
            message=message,
            exit_code=SOURCE_ERROR,
            details=details or {},
        )


class SourceUnavailableError(CowellCliError):
    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        from .exit_codes import SOURCE_ERROR

        super().__init__(
            code=code,
            message=message,
            exit_code=SOURCE_ERROR,
            details=details or {},
        )


class ParseContractError(CowellCliError):
    """A Cowell page did not match the structure the parser expects.

    Raised fail-closed on layout drift so a changed page surfaces loudly as
    PARSE_CONTRACT_CHANGED (exit 30) instead of silently yielding empty/wrong
    data (seat-spec §8).
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        from .exit_codes import SOURCE_ERROR

        super().__init__(
            code="PARSE_CONTRACT_CHANGED",
            message=message,
            exit_code=SOURCE_ERROR,
            details=details or {},
        )


class ValidationError(CowellCliError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        from .exit_codes import INPUT_ERROR

        super().__init__(
            code="VALIDATION_FAILED",
            message=message,
            exit_code=INPUT_ERROR,
            details=details or {},
        )
