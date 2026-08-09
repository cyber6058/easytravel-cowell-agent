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


class BriefingSourceError(BriefingCliError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        from .exit_codes import SOURCE_ERROR

        super().__init__(
            code="SOURCE_ERROR",
            message=message,
            exit_code=SOURCE_ERROR,
            details=details or {},
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
