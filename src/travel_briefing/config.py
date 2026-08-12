from __future__ import annotations

import os
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import BriefingInputError


_SHA256 = re.compile(r"[0-9a-f]{64}")
_SECTIONS = frozenset({"output", "template", "tools"})
_FIELDS = {
    "output": frozenset({"root"}),
    "template": frozenset({"path", "layout_fingerprint"}),
    "tools": frozenset({"ffmpeg", "pdftoppm"}),
}


@dataclass(frozen=True, slots=True)
class BriefingConfig:
    output_root: Path
    template_path: Path
    template_layout_fingerprint: str
    ffmpeg_path: Path | None
    pdftoppm_path: Path


def default_config_path() -> Path:
    configured = os.environ.get("EASYTRAVEL_BRIEFING_CONFIG")
    if configured:
        return Path(os.path.expandvars(configured)).expanduser()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise BriefingInputError("LOCALAPPDATA is not configured")
    return Path(local_app_data) / "EasyTravelBriefing" / "config.toml"


def load_config(path: Path | None = None) -> BriefingConfig:
    config_path = (path or default_config_path()).expanduser()
    if not config_path.is_file():
        raise BriefingInputError(
            "EasyTravel briefing configuration file was not found",
            {"path": str(config_path)},
        )
    try:
        with config_path.open("rb") as stream:
            raw = tomllib.load(stream)
    except tomllib.TOMLDecodeError as error:
        raise BriefingInputError(
            "EasyTravel briefing configuration is invalid TOML",
            {"path": str(config_path), "reason": str(error)},
        ) from error
    return parse_config(raw)


def parse_config(raw: Mapping[str, Any]) -> BriefingConfig:
    _validate_shape(raw)
    output = _section(raw, "output")
    template = _section(raw, "template")
    tools = _section(raw, "tools")
    output_root = _path(output, "root", must_exist=False)
    if output_root.exists() and not output_root.is_dir():
        raise BriefingInputError("Briefing output root must be a directory")
    template_path = _path(template, "path", must_exist=True)
    if template_path.suffix.casefold() not in {".doc", ".docx"}:
        raise BriefingInputError("template.path must be an existing DOC or DOCX")
    fingerprint = _text(template, "layout_fingerprint").casefold()
    if _SHA256.fullmatch(fingerprint) is None:
        raise BriefingInputError("template.layout_fingerprint must be SHA-256")
    pdftoppm = _path(tools, "pdftoppm", must_exist=True)
    ffmpeg_value = tools.get("ffmpeg")
    ffmpeg = None
    if ffmpeg_value is not None:
        ffmpeg = _path(tools, "ffmpeg", must_exist=True)
    return BriefingConfig(
        output_root=output_root,
        template_path=template_path,
        template_layout_fingerprint=fingerprint,
        ffmpeg_path=ffmpeg,
        pdftoppm_path=pdftoppm,
    )


def _validate_shape(raw: Mapping[str, Any]) -> None:
    if not isinstance(raw, Mapping):
        raise BriefingInputError("Briefing configuration must be a TOML table")
    unknown_sections = sorted(set(raw) - _SECTIONS)
    if unknown_sections:
        raise BriefingInputError(
            "Briefing configuration contains unknown sections",
            {"sections": unknown_sections},
        )
    missing_sections = sorted(_SECTIONS - set(raw))
    if missing_sections:
        raise BriefingInputError(
            "Briefing configuration is missing required sections",
            {"sections": missing_sections},
        )
    for name in sorted(_SECTIONS):
        section = _section(raw, name)
        unknown_fields = sorted(set(section) - _FIELDS[name])
        if unknown_fields:
            raise BriefingInputError(
                "Briefing configuration contains unknown fields",
                {"section": name, "fields": unknown_fields},
            )


def _section(raw: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = raw.get(name)
    if not isinstance(value, Mapping):
        raise BriefingInputError(f"Briefing configuration section {name} is invalid")
    return value


def _text(section: Mapping[str, Any], field: str) -> str:
    value = section.get(field)
    if not isinstance(value, str) or not value.strip():
        raise BriefingInputError(f"Briefing configuration field {field} is required")
    return value.strip()


def _path(
    section: Mapping[str, Any],
    field: str,
    *,
    must_exist: bool,
) -> Path:
    value = os.path.expandvars(_text(section, field))
    path = Path(value).expanduser().resolve()
    if must_exist and not path.is_file():
        raise BriefingInputError(f"Briefing {field} path does not exist")
    return path
