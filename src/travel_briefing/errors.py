from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BriefingCliError(Exception):
    code: str
    message: str
    exit_code: int
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


class BriefingInputError(BriefingCliError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        from .exit_codes import INPUT_ERROR

        super().__init__(
            code="INPUT_ERROR",
            message=message,
            exit_code=INPUT_ERROR,
            details=details or {},
        )


class ListRecalibrationRequiredError(BriefingInputError):
    def __init__(self, *, status: str = "changed") -> None:
        if status not in {"missing", "changed", "unsupported"}:
            status = "changed"
        super().__init__(
            (
                "LIST_RECALIBRATION_REQUIRED: run briefing calibrate-list "
                "and update template.master_path plus "
                "template.calibration_manifest"
            ),
            {"status": status},
        )
        self.code = "LIST_RECALIBRATION_REQUIRED"


class CalibrationContractConflictError(BriefingCliError):
    def __init__(
        self,
        *,
        stage: str,
        field_paths: tuple[str, ...],
        review_path: str,
    ) -> None:
        from .exit_codes import NEEDS_REVIEW

        super().__init__(
            code="CALIBRATION_CONTRACT_CONFLICT",
            message="Calibration samples have conflicting structural fields",
            exit_code=NEEDS_REVIEW,
            details={
                "stage": stage,
                "field_paths": list(field_paths),
                "review": review_path,
            },
        )


class BriefingSourceError(BriefingCliError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        from .exit_codes import SOURCE_ERROR

        super().__init__(
            code="SOURCE_ERROR",
            message=message,
            exit_code=SOURCE_ERROR,
            details=details or {},
        )


class ParseContractChangedError(BriefingCliError):
    def __init__(self, anchor: str) -> None:
        from .exit_codes import SOURCE_ERROR

        super().__init__(
            code="PARSE_CONTRACT_CHANGED",
            message="Source structure no longer matches the approved parser contract",
            exit_code=SOURCE_ERROR,
            details={"anchor": anchor},
        )


class PdfOcrRequiredError(BriefingCliError):
    def __init__(self) -> None:
        from .exit_codes import NEEDS_REVIEW

        super().__init__(
            code="PDF_OCR_REQUIRED",
            message=(
                "Itinerary PDF contains no extractable text; OCR requires "
                "separate review"
            ),
            exit_code=NEEDS_REVIEW,
            details={},
        )


class StaleDraftDecisionError(BriefingCliError):
    def __init__(self, kind: str) -> None:
        from .exit_codes import INPUT_ERROR

        super().__init__(
            code="STALE_DRAFT_DECISION",
            message="Submitted OP data does not match the current draft ID",
            exit_code=INPUT_ERROR,
            details={"kind": kind},
        )


class LocalTtsUnavailableError(BriefingCliError):
    def __init__(self, message: str = "Local Hanhan TTS is unavailable") -> None:
        from .exit_codes import NEEDS_REVIEW

        super().__init__(
            code="LOCAL_TTS_UNAVAILABLE",
            message=message,
            exit_code=NEEDS_REVIEW,
        )


class AudioSynthesisError(BriefingCliError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        from .exit_codes import SOURCE_ERROR

        super().__init__(
            code="AUDIO_SYNTHESIS_FAILED",
            message=message,
            exit_code=SOURCE_ERROR,
            details=details or {},
        )


class UnknownAudioResultError(BriefingCliError):
    def __init__(
        self,
        message: str = (
            "Local speech synthesis timed out after one attempt; partial outputs "
            "were inspected and no retry was made"
        ),
    ) -> None:
        from .exit_codes import NEEDS_REVIEW

        super().__init__(
            code="AUDIO_RESULT_UNKNOWN",
            message=message,
            exit_code=NEEDS_REVIEW,
        )


class Mp3ConverterUnavailableError(BriefingCliError):
    def __init__(self) -> None:
        from .exit_codes import NEEDS_REVIEW

        super().__init__(
            code="MP3_CONVERTER_UNAVAILABLE",
            message="A configured ffmpeg executable is required for MP3 output",
            exit_code=NEEDS_REVIEW,
        )


class WordAutomationUnavailableError(BriefingCliError):
    def __init__(self, message: str = "Microsoft Word automation is unavailable") -> None:
        from .exit_codes import NEEDS_REVIEW

        super().__init__(
            code="WORD_AUTOMATION_UNAVAILABLE",
            message=message,
            exit_code=NEEDS_REVIEW,
        )


class WordGenerationError(BriefingCliError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        from .exit_codes import SOURCE_ERROR

        super().__init__(
            code="WORD_GENERATION_FAILED",
            message=message,
            exit_code=SOURCE_ERROR,
            details=details or {},
        )


class UnknownWordResultError(BriefingCliError):
    def __init__(
        self,
        message: str = (
            "Word automation timed out after one attempt; inspect current "
            "outputs before retry"
        ),
        details: dict[str, Any] | None = None,
    ) -> None:
        from .exit_codes import NEEDS_REVIEW

        super().__init__(
            code="WORD_RESULT_UNKNOWN",
            message=message,
            exit_code=NEEDS_REVIEW,
            details=details or {},
        )
