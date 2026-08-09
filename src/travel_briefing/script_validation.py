from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from dataclasses import dataclass

from .script_policy import NarrationInput, extract_critical_values


ESTIMATED_CHARS_PER_SECOND = 3.6
TARGET_AUDIO_MIN_SECONDS = 360.0
TARGET_AUDIO_MAX_SECONDS = 480.0

_SECTION_MARKER_PATTERN = re.compile(
    r"(?m)^[ \t]*<!--\s*section:([a-z0-9_]+)\s*-->[ \t]*$"
)

_CONTRADICTION_PATTERNS = {
    "no_leaving_group": (
        re.compile(r"(?<!不)(?:可以|允許|准許|可)(?:自行|擅自)?脫隊"),
        re.compile(r"(?:不必|不用|無須).{0,6}(?:跟團|隨團)"),
    ),
    "passport_validity": (
        re.compile(r"護照.{0,8}(?:不必|不用|無須).{0,6}(?:效期|有效)"),
    ),
    "vegetarian": (
        re.compile(r"素食.{0,8}(?:不必|不用|無須).{0,6}(?:告知|通知)"),
    ),
    "weather_reminder": (
        re.compile(r"天氣.{0,8}(?:保證|一定).{0,6}(?:準確|不變|相同)"),
    ),
}


@dataclass(frozen=True, slots=True)
class ScriptIssue:
    code: str
    severity: str
    message: str
    section_id: str = ""
    fact_id: str = ""


@dataclass(frozen=True, slots=True)
class ScriptValidationResult:
    schema_version: int
    draft_id: str
    status: str
    ready: bool
    issues: tuple[ScriptIssue, ...]
    section_order: tuple[str, ...]
    character_count: int
    estimated_chars_per_second: float
    estimated_duration_seconds: float
    estimated_length_status: str
    target_audio_min_seconds: float
    target_audio_max_seconds: float
    script_sha256: str
    narration_text_sha256: str


@dataclass(frozen=True, slots=True)
class AudioDurationValidation:
    schema_version: int
    duration_seconds: float
    revision_count: int
    target_min_seconds: float
    target_max_seconds: float
    status: str
    action: str
    can_revise: bool
    revision_rule: str


def check_script(
    narration_input: NarrationInput,
    script: str,
) -> ScriptValidationResult:
    if not isinstance(script, str):
        raise TypeError("script must be text")

    issues: list[ScriptIssue] = []
    if not narration_input.ready:
        issues.append(
            ScriptIssue(
                code="NARRATION_INPUT_NOT_READY",
                severity="error",
                message=(
                    "The narration input contains review items; do not fill or "
                    "infer the missing values."
                ),
            )
        )

    matches = list(_SECTION_MARKER_PATTERN.finditer(script))
    observed_order = tuple(match.group(1) for match in matches)
    expected_order = tuple(
        section.section_id for section in narration_input.sections
    )
    if observed_order != expected_order:
        issues.append(
            ScriptIssue(
                code="SECTION_ORDER_INVALID",
                severity="error",
                message=(
                    "Section markers must appear exactly once in the required order."
                ),
            )
        )

    bodies = _section_bodies(script, matches)
    if matches and script[: matches[0].start()].strip():
        issues.append(
            ScriptIssue(
                code="CONTENT_OUTSIDE_SECTIONS",
                severity="error",
                message="Narration content must be inside a declared section.",
            )
        )

    approved_values = {
        _semantic_text(value)
        for fact in narration_input.required_facts
        for value in fact.critical_values
        if value
    }
    approved_values.update(
        _semantic_text(entry.written)
        for entry in narration_input.pronunciation_entries
        if extract_critical_values(entry.written)
    )

    for fact in narration_input.required_facts:
        body = bodies.get(fact.section_id, "")
        normalized_body = _semantic_text(body)
        if _semantic_text(fact.protected_text) not in normalized_body:
            issues.append(
                ScriptIssue(
                    code="REQUIRED_FACT_NOT_PRESERVED",
                    severity="error",
                    message=(
                        "A source-bound fact is absent or was rewritten beyond "
                        "the approved wording."
                    ),
                    section_id=fact.section_id,
                    fact_id=fact.fact_id,
                )
            )
        for value in fact.critical_values:
            if _semantic_text(value) not in normalized_body:
                issues.append(
                    ScriptIssue(
                        code="CRITICAL_VALUE_MISSING",
                        severity="error",
                        message=(
                            "A protected number or value is missing from its section."
                        ),
                        section_id=fact.section_id,
                        fact_id=fact.fact_id,
                    )
                )
        for pattern in _CONTRADICTION_PATTERNS.get(fact.category, ()):
            if pattern.search(normalized_body):
                issues.append(
                    ScriptIssue(
                        code="CONTRADICTORY_CLAIM",
                        severity="error",
                        message=(
                            "The section contains wording with the opposite meaning "
                            "of a required fact."
                        ),
                        section_id=fact.section_id,
                        fact_id=fact.fact_id,
                    )
                )

    narration_text = narration_text_for_tts(script)
    normalized_narration = _semantic_text(narration_text)
    for prohibited in narration_input.prohibited_values:
        if prohibited and _semantic_text(prohibited) in normalized_narration:
            issues.append(
                ScriptIssue(
                    code="PROHIBITED_VALUE_PRESENT",
                    severity="error",
                    message="The script contains a disputed or unconfirmed value.",
                )
            )

    for value in extract_critical_values(narration_text):
        if _semantic_text(value) not in approved_values:
            issues.append(
                ScriptIssue(
                    code="UNAPPROVED_CRITICAL_VALUE",
                    severity="error",
                    message="The script contains a number not approved by the input.",
                )
            )

    character_count = _character_count(narration_text)
    estimated_duration = round(
        character_count / ESTIMATED_CHARS_PER_SECOND,
        1,
    )
    if estimated_duration < TARGET_AUDIO_MIN_SECONDS:
        estimated_length_status = "below_target"
        issues.append(
            ScriptIssue(
                code="ESTIMATED_AUDIO_TOO_SHORT",
                severity="warning",
                message=(
                    "The advisory character estimate is below six minutes; "
                    "actual synthesized audio remains authoritative."
                ),
            )
        )
    elif estimated_duration > TARGET_AUDIO_MAX_SECONDS:
        estimated_length_status = "above_target"
        issues.append(
            ScriptIssue(
                code="ESTIMATED_AUDIO_TOO_LONG",
                severity="warning",
                message=(
                    "The advisory character estimate is above eight minutes; "
                    "actual synthesized audio remains authoritative."
                ),
            )
        )
    else:
        estimated_length_status = "within_target"

    ready = not any(issue.severity == "error" for issue in issues)
    status = (
        "blocked"
        if not ready
        else "ready_with_warnings"
        if issues
        else "ready"
    )
    return ScriptValidationResult(
        schema_version=1,
        draft_id=narration_input.draft_id,
        status=status,
        ready=ready,
        issues=tuple(issues),
        section_order=observed_order,
        character_count=character_count,
        estimated_chars_per_second=ESTIMATED_CHARS_PER_SECOND,
        estimated_duration_seconds=estimated_duration,
        estimated_length_status=estimated_length_status,
        target_audio_min_seconds=TARGET_AUDIO_MIN_SECONDS,
        target_audio_max_seconds=TARGET_AUDIO_MAX_SECONDS,
        script_sha256=hashlib.sha256(script.encode("utf-8")).hexdigest(),
        narration_text_sha256=hashlib.sha256(
            narration_text.encode("utf-8")
        ).hexdigest(),
    )


def narration_text_for_tts(script: str) -> str:
    without_markers = _SECTION_MARKER_PATTERN.sub("", script)
    lines = [line.strip() for line in without_markers.splitlines() if line.strip()]
    return "\n".join(lines)


def script_validation_to_dict(
    value: ScriptValidationResult,
) -> dict[str, object]:
    return {
        "schema_version": value.schema_version,
        "type": "briefing_script_validation",
        "draft_id": value.draft_id,
        "status": value.status,
        "ready": value.ready,
        "issues": [
            {
                "code": issue.code,
                "severity": issue.severity,
                "message": issue.message,
                "section_id": issue.section_id,
                "fact_id": issue.fact_id,
            }
            for issue in value.issues
        ],
        "section_order": list(value.section_order),
        "character_count": value.character_count,
        "estimated_chars_per_second": value.estimated_chars_per_second,
        "estimated_duration_seconds": value.estimated_duration_seconds,
        "estimated_length_status": value.estimated_length_status,
        "target_audio_seconds": {
            "minimum": value.target_audio_min_seconds,
            "maximum": value.target_audio_max_seconds,
        },
        "script_sha256": value.script_sha256,
        "narration_text_sha256": value.narration_text_sha256,
    }


def dumps_script_validation(value: ScriptValidationResult) -> str:
    return json.dumps(
        script_validation_to_dict(value),
        ensure_ascii=False,
        indent=2,
    )


def validate_audio_duration(
    duration_seconds: float,
    *,
    revision_count: int,
) -> AudioDurationValidation:
    duration = float(duration_seconds)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("duration_seconds must be a positive finite number")
    if revision_count not in (0, 1):
        raise ValueError("revision_count must be 0 or 1")

    if TARGET_AUDIO_MIN_SECONDS <= duration <= TARGET_AUDIO_MAX_SECONDS:
        status = "accepted"
        action = "none"
        can_revise = False
        revision_rule = ""
    elif revision_count == 1:
        status = "blocked"
        action = "manual_review"
        can_revise = False
        revision_rule = (
            "Do not revise automatically again; keep the draft and request review."
        )
    elif duration < TARGET_AUDIO_MIN_SECONDS:
        status = "revise_once"
        action = "supplement_once"
        can_revise = True
        revision_rule = (
            "Expand only supplied, noncritical context while preserving all "
            "protected facts and critical values; add no external facts."
        )
    else:
        status = "revise_once"
        action = "compress_once"
        can_revise = True
        revision_rule = (
            "Remove repetition and transition-only wording while preserving all "
            "protected facts and critical values."
        )

    return AudioDurationValidation(
        schema_version=1,
        duration_seconds=duration,
        revision_count=revision_count,
        target_min_seconds=TARGET_AUDIO_MIN_SECONDS,
        target_max_seconds=TARGET_AUDIO_MAX_SECONDS,
        status=status,
        action=action,
        can_revise=can_revise,
        revision_rule=revision_rule,
    )


def audio_duration_validation_to_dict(
    value: AudioDurationValidation,
) -> dict[str, object]:
    return {
        "schema_version": value.schema_version,
        "type": "briefing_audio_duration_validation",
        "duration_seconds": value.duration_seconds,
        "revision_count": value.revision_count,
        "target_seconds": {
            "minimum": value.target_min_seconds,
            "maximum": value.target_max_seconds,
        },
        "status": value.status,
        "action": value.action,
        "can_revise": value.can_revise,
        "revision_rule": value.revision_rule,
    }


def dumps_audio_duration_validation(value: AudioDurationValidation) -> str:
    return json.dumps(
        audio_duration_validation_to_dict(value),
        ensure_ascii=False,
        indent=2,
    )


def _section_bodies(
    script: str,
    matches: list[re.Match[str]],
) -> dict[str, str]:
    bodies: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(script)
        section_id = match.group(1)
        if section_id not in bodies:
            bodies[section_id] = script[match.end() : end]
    return bodies


def _semantic_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in normalized if character.isalnum())


def _character_count(value: str) -> int:
    normalized = unicodedata.normalize("NFKC", value)
    return sum(character.isalnum() for character in normalized)
