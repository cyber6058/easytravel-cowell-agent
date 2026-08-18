from __future__ import annotations

import os
import hashlib
import json
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import BriefingInputError, ListRecalibrationRequiredError
from .list_calibration import ListCalibrationManifest


_SECTIONS = frozenset({"output", "template", "tools"})
_FIELDS = {
    "output": frozenset({"root"}),
    "template": frozenset({"master_path", "calibration_manifest"}),
    "tools": frozenset({"ffmpeg", "pdftoppm"}),
}


@dataclass(frozen=True, slots=True)
class BriefingConfig:
    output_root: Path
    master_path: Path
    calibration_manifest_path: Path
    master_sha256: str
    calibration_manifest_sha256: str
    master_structure_fingerprint: str
    source_header_qr_candidate_count: int
    layout_profiles: tuple[dict[str, Any], ...]
    calibration_manifest: ListCalibrationManifest
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
    if isinstance(raw, Mapping) and isinstance(
        raw.get("template"), Mapping
    ):
        legacy = {"path", "layout_fingerprint"} & set(raw["template"])
        if legacy:
            raise ListRecalibrationRequiredError(status="unsupported")
    _validate_shape(raw)
    output = _section(raw, "output")
    template = _section(raw, "template")
    tools = _section(raw, "tools")
    output_root = _path(output, "root", must_exist=False)
    if output_root.exists() and not output_root.is_dir():
        raise BriefingInputError("Briefing output root must be a directory")
    master_path = _calibration_path(
        template, "master_path", suffix=".docx"
    )
    manifest_path = _calibration_path(
        template, "calibration_manifest", suffix=".json"
    )
    if master_path.parent != manifest_path.parent or _paths_overlap(
        output_root, master_path.parent
    ):
        raise BriefingInputError(
            "LIST master and calibration manifest must share a private "
            "directory outside the output root"
        )
    manifest, manifest_hash = _load_calibration_manifest(manifest_path)
    master_hash = _sha256_file(master_path)
    if master_hash != manifest.master_sha256:
        raise ListRecalibrationRequiredError(status="changed")
    normalized_layout = manifest.to_dict()["normalized_layout"]
    normalized_hash = hashlib.sha256(
        json.dumps(
            normalized_layout,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if normalized_hash != manifest.master_structure_fingerprint:
        raise ListRecalibrationRequiredError(status="changed")
    pdftoppm = _path(tools, "pdftoppm", must_exist=True)
    ffmpeg_value = tools.get("ffmpeg")
    ffmpeg = None
    if ffmpeg_value is not None:
        ffmpeg = _path(tools, "ffmpeg", must_exist=True)
    return BriefingConfig(
        output_root=output_root,
        master_path=master_path,
        calibration_manifest_path=manifest_path,
        master_sha256=master_hash,
        calibration_manifest_sha256=manifest_hash,
        master_structure_fingerprint=(
            manifest.master_structure_fingerprint
        ),
        source_header_qr_candidate_count=(
            manifest.source_header_qr_candidate_count
        ),
        layout_profiles=tuple(
            item.to_dict() for item in manifest.layout_profiles
        ),
        calibration_manifest=manifest,
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


def _calibration_path(
    section: Mapping[str, Any], field: str, *, suffix: str
) -> Path:
    value = os.path.expandvars(_text(section, field))
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise ListRecalibrationRequiredError(status="missing")
    if path.suffix.casefold() != suffix:
        raise ListRecalibrationRequiredError(status="unsupported")
    return path


def _load_calibration_manifest(
    path: Path,
) -> tuple[ListCalibrationManifest, str]:
    try:
        raw_text = path.read_text(encoding="utf-8")
        payload = json.loads(raw_text)
        manifest = ListCalibrationManifest.from_dict(payload)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise ListRecalibrationRequiredError(status="unsupported") from error
    canonical = manifest.to_canonical_json()
    if raw_text not in {canonical, canonical + "\n"}:
        raise ListRecalibrationRequiredError(status="changed")
    return manifest, _sha256_file(path)


def _paths_overlap(first: Path, second: Path) -> bool:
    return (
        first == second
        or first.is_relative_to(second)
        or second.is_relative_to(first)
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
