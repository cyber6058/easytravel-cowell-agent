from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .capabilities import (
    hanhan_registered,
    list_calibration_check,
    tool_check,
    word_com_registered,
    yating_registered,
)
from .errors import (
    BriefingCliError,
    BriefingInputError,
    CalibrationContractConflictError,
)
from .exit_codes import INTERNAL_ERROR, NEEDS_REVIEW, SUCCESS
from .config import load_config
from .list_calibration import (
    CalibrationContractError,
    calibrate_list_templates,
    diagnose_calibration_conflicts,
    diagnose_list_components,
)
from .adapters.windows_word import WindowsWordAdapter
from .models import BriefingDraft, DraftStatus
from .workflow import (
    LocalRenderBackend,
    check_briefing_script,
    prepare_briefing,
    render_briefing,
)


SCHEMA_VERSION = 1
_HANHAN_VOICE = "Microsoft Hanhan Desktop"
_YATING_VOICE = "Microsoft Yating"
_YATING_LANGUAGE = "zh-TW"
_RUN_TIMESTAMP = re.compile(r"[0-9]{8}T[0-9]{6}(?:Z|[+-][0-9]{4})")
_PRODUCT_CODE = re.compile(r"[A-Z0-9](?:[A-Z0-9-]{3,30})[A-Z0-9]")


class BriefingArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        del message
        raise BriefingInputError("Invalid briefing command arguments")


def build_parser() -> argparse.ArgumentParser:
    parser = BriefingArgumentParser(
        prog="briefing",
        description="EasyTravel briefing document and audio drafts",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check local briefing capabilities")
    doctor.add_argument("--config", type=Path)
    doctor.add_argument("--format", choices=("text", "json"), default="text")
    doctor.set_defaults(handler=run_doctor)

    calibrate = subparsers.add_parser(
        "calibrate-list",
        help="Create one private calibrated LIST master",
    )
    calibrate.add_argument(
        "--sample",
        action="append",
        type=Path,
        required=True,
    )
    calibrate.add_argument("--private-dir", type=Path, required=True)
    calibrate.add_argument("--pdftoppm", type=Path, required=True)
    calibrate.add_argument("--generated-at")
    calibrate.add_argument("--format", choices=("text", "json"), default="text")
    calibrate.set_defaults(handler=run_calibrate_list)

    diagnose = subparsers.add_parser(
        "diagnose-list-conflicts",
        help="Inspect three LIST samples without calibrating a master",
    )
    diagnose.add_argument(
        "--sample",
        action="append",
        type=Path,
        required=True,
    )
    diagnose.add_argument("--private-dir", type=Path, required=True)
    diagnose.add_argument(
        "--format", choices=("text", "json"), default="text"
    )
    diagnose.set_defaults(handler=run_diagnose_list_conflicts)

    components = subparsers.add_parser(
        "diagnose-list-components",
        help="Read allowlisted LIST formatting components without calibration",
    )
    components.add_argument(
        "--sample", action="append", type=Path, required=True
    )
    components.add_argument("--private-dir", type=Path, required=True)
    components.add_argument(
        "--format", choices=("text", "json"), default="text"
    )
    components.set_defaults(handler=run_diagnose_list_components)

    prepare = subparsers.add_parser("prepare", help="Create a reviewable manifest")
    prepare.add_argument("--url")
    prepare.add_argument("--pdf", type=Path)
    prepare.add_argument("--previous-manifest", type=Path)
    prepare.add_argument("--op-values", type=Path)
    prepare.add_argument("--conflict-decisions", type=Path)
    prepare.add_argument("--output-dir", type=Path, required=True)
    prepare.add_argument("--generated-at")
    prepare.add_argument("--format", choices=("text", "json"), default="text")
    prepare.set_defaults(handler=run_prepare)

    check = subparsers.add_parser(
        "check-script",
        help="Validate an agent narration script against a manifest",
    )
    check.add_argument("--manifest", type=Path, required=True)
    check.add_argument("--script", type=Path, required=True)
    check.add_argument("--output-dir", type=Path)
    check.add_argument("--format", choices=("text", "json"), default="text")
    check.set_defaults(handler=run_check_script)

    render = subparsers.add_parser(
        "render",
        help="Create DRAFT artifacts or confirm an exact verified DRAFT",
    )
    render.add_argument("--manifest", type=Path, required=True)
    render.add_argument("--script", type=Path, required=True)
    render.add_argument("--config", type=Path)
    render.add_argument("--output-dir", type=Path)
    render.add_argument("--tts", choices=("yating",), default="yating")
    render.add_argument("--confirm-draft-id")
    render.add_argument("--generated-at")
    render.add_argument("--format", choices=("text", "json"), default="text")
    render.set_defaults(handler=run_render)
    return parser


def run_doctor(args: argparse.Namespace) -> dict[str, Any]:
    yating_available = yating_registered()
    hanhan_available = hanhan_registered()
    word_registered = word_com_registered()
    config = None
    calibration_configured = False
    calibration_status = "missing"
    try:
        config = load_config(getattr(args, "config", None))
        calibration_configured = True
    except BriefingCliError as error:
        reported = error.details.get("status")
        if isinstance(reported, str):
            calibration_status = reported
    checks = {
        "python": {
            "status": "ok" if sys.version_info >= (3, 12) else "error",
            "version": platform.python_version(),
        },
        "platform": {
            "status": "ok" if sys.platform == "win32" else "warning",
            "windows": sys.platform == "win32",
        },
        "yating": {
            "status": "ok" if yating_available else "warning",
            "available": yating_available,
            "voice": _YATING_VOICE,
            "language": _YATING_LANGUAGE,
            "engine": "windows-media-speech",
            "role": "official_tts",
            "probe": "voice_enumeration_only",
        },
        "hanhan": {
            "status": "ok",
            "available": hanhan_available,
            "voice": _HANHAN_VOICE,
            "role": "legacy_comparison_only",
        },
        "ffmpeg": tool_check(
            "ffmpeg",
            os.environ.get("BRIEFING_FFMPEG"),
            require_configured=True,
        ),
        "word_com": {
            "status": "ok" if word_registered else "warning",
            "registered": word_registered,
            "probe": "registry_only",
        },
        "pdftoppm": tool_check(
            "pdftoppm",
            str(config.pdftoppm_path) if config else None,
        ),
        "list_calibration": list_calibration_check(
            config,
            configured=calibration_configured,
            failure_status=calibration_status,
        ),
    }
    statuses = {check["status"] for check in checks.values()}
    status = (
        "error"
        if "error" in statuses
        else "warning"
        if {"warning", "missing", "changed", "unsupported"} & statuses
        else "ok"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "command": "doctor",
        "checks": checks,
    }


def run_calibrate_list(args: argparse.Namespace) -> dict[str, Any]:
    samples = tuple(path.expanduser().resolve() for path in args.sample)
    if len(samples) != 3 or len(set(samples)) != 3:
        raise BriefingInputError(
            "calibrate-list requires exactly three unique samples"
        )
    if any(
        not path.is_file() or path.suffix.casefold() not in {".doc", ".docx"}
        for path in samples
    ):
        raise BriefingInputError(
            "calibrate-list samples must be existing DOC or DOCX files"
        )
    private = args.private_dir.expanduser().resolve()
    if private.exists():
        raise BriefingInputError(
            "calibrate-list private directory must not exist"
        )
    pdftoppm = args.pdftoppm.expanduser().resolve()
    if not pdftoppm.is_file():
        raise BriefingInputError(
            "calibrate-list pdftoppm must be an existing executable"
        )
    source_hashes = [_sha256_file(path) for path in samples]
    stage = "inspect-samples"

    def record_stage(value: str) -> None:
        nonlocal stage
        stage = value

    try:
        private.mkdir(parents=True)
        result = calibrate_list_templates(
            samples,
            master_path=private / "LIST-master.docx",
            manifest_path=private / "calibration-manifest.json",
            adapter=WindowsWordAdapter(
                script_path=(
                    _briefing_scripts_root()
                    / "patch_list_template.ps1"
                )
            ),
            created_at=_generated_at(args.generated_at),
            timeout_seconds=180,
            on_stage=record_stage,
        )
    except CalibrationContractError as error:
        review_path = private / "calibration-review.json"
        review_payload = {
            "schema_version": SCHEMA_VERSION,
            "status": "needs_review",
            "error_code": error.code,
            "stage": stage,
            "source_sha256": source_hashes,
            "field_paths": list(error.field_paths),
        }
        if error.conflict_matrix is not None:
            review_payload["conflict_matrix"] = error.conflict_matrix
        _write_json_exclusive(
            review_path,
            review_payload,
        )
        raise CalibrationContractConflictError(
            stage=stage,
            field_paths=error.field_paths,
            review_path=str(review_path),
        ) from error
    except Exception:
        try:
            if private.is_dir() and not any(private.iterdir()):
                private.rmdir()
        except OSError:
            pass
        raise
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "command": "calibrate-list",
        "master_path": str(result.master_path),
        "calibration_manifest": str(result.manifest_path),
        "master_sha256": result.master_sha256,
        "calibration_manifest_sha256": result.manifest_sha256,
        "samples": [
            {
                "sha256": item.source_sha256,
                "day_count": item.day_count,
            }
            for item in result.sample_evidence
        ],
        "word_version": result.word_version,
    }


def run_diagnose_list_conflicts(
    args: argparse.Namespace,
) -> dict[str, Any]:
    samples = tuple(path.expanduser().resolve() for path in args.sample)
    if len(samples) != 3 or len(set(samples)) != 3:
        raise BriefingInputError(
            "diagnose-list-conflicts requires exactly three unique samples"
        )
    if any(
        not path.is_file() or path.suffix.casefold() not in {".doc", ".docx"}
        for path in samples
    ):
        raise BriefingInputError(
            "diagnose-list-conflicts samples must be existing DOC or DOCX files"
        )
    private = args.private_dir.expanduser().resolve()
    if private.exists():
        raise BriefingInputError(
            "diagnose-list-conflicts private directory must not exist"
        )
    try:
        private.mkdir(parents=True)
        result = diagnose_calibration_conflicts(
            samples,
            adapter=WindowsWordAdapter(
                script_path=(
                    _briefing_scripts_root()
                    / "patch_list_template.ps1"
                )
            ),
            timeout_seconds=180,
        )
        status = (
            "needs_review"
            if result.classification == "TEMPLATE_CONTRACT_CONFLICT"
            else "ok"
        )
        report_path = private / "conflict-diagnosis.json"
        report_payload = {
            "schema_version": SCHEMA_VERSION,
            "status": status,
            "command": "diagnose-list-conflicts",
            "stage": "compare-samples",
            "classification": result.classification,
            "word_version": result.word_version,
            "source_sha256": list(result.source_sha256),
            "field_paths": list(result.field_paths),
        }
        if result.conflict_matrix is not None:
            report_payload["conflict_matrix"] = result.conflict_matrix
        _write_json_exclusive(report_path, report_payload)
    except Exception:
        try:
            if private.is_dir() and not any(private.iterdir()):
                private.rmdir()
        except OSError:
            pass
        raise
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "command": "diagnose-list-conflicts",
        "classification": result.classification,
        "field_paths": list(result.field_paths),
        "report": str(report_path),
    }


def run_diagnose_list_components(
    args: argparse.Namespace,
) -> dict[str, Any]:
    samples = tuple(path.expanduser().resolve() for path in args.sample)
    if len(samples) != 3 or len(set(samples)) != 3:
        raise BriefingInputError(
            "diagnose-list-components requires exactly three unique samples"
        )
    if any(
        not path.is_file() or path.suffix.casefold() not in {".doc", ".docx"}
        for path in samples
    ):
        raise BriefingInputError(
            "diagnose-list-components samples must be existing DOC or DOCX files"
        )
    private = args.private_dir.expanduser().resolve()
    if private.exists():
        raise BriefingInputError(
            "diagnose-list-components private directory must not exist"
        )
    try:
        private.mkdir(parents=True)
        result = diagnose_list_components(
            samples,
            adapter=WindowsWordAdapter(
                script_path=_briefing_scripts_root() / "patch_list_template.ps1"
            ),
            timeout_seconds=120,
        )
        report_path = private / "component-diagnosis.json"
        _write_json_exclusive(
            report_path,
            {
                "schema_version": SCHEMA_VERSION,
                "status": "ok",
                "command": "diagnose-list-components",
                "stage": "component-evidence",
                "word_version": result.word_version,
                "source_sha256": list(result.source_sha256),
                "samples": list(result.samples),
            },
        )
    except Exception:
        try:
            if private.is_dir() and not any(private.iterdir()):
                private.rmdir()
        except OSError:
            pass
        raise
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "command": "diagnose-list-components",
        "report": str(report_path),
    }


def run_prepare(args: argparse.Namespace) -> dict[str, Any]:
    result = prepare_briefing(
        output_root=args.output_dir,
        generated_at=_generated_at(args.generated_at),
        source_url=args.url,
        pdf_path=args.pdf,
        previous_manifest=args.previous_manifest,
        op_values=_read_json_object(args.op_values, label="OP values"),
        conflict_decisions=_read_json_object(
            args.conflict_decisions,
            label="Conflict decisions",
        ),
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "needs_review",
        "command": "prepare",
        "draft_status": result.draft.status.value,
        "draft_id": result.draft.draft_id,
        "run_directory": str(result.run_directory),
        "manifest": str(result.manifest_path),
        "review": str(result.review_path),
        "narration_input": str(result.narration_input_path),
    }


def run_check_script(args: argparse.Namespace) -> dict[str, Any]:
    output_root = args.output_dir or _output_root_from_manifest(args.manifest)
    result = check_briefing_script(
        output_root=output_root,
        manifest_path=args.manifest,
        script_path=args.script,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok" if result.ready else "needs_review",
        "command": "check-script",
        "ready": result.ready,
        "report": str(result.report_path),
        "issue_codes": sorted({issue.code for issue in result.validation.issues}),
        "estimated_duration_seconds": (
            result.validation.estimated_duration_seconds
        ),
        "script_sha256": result.validation.script_sha256,
    }


def run_render(args: argparse.Namespace) -> dict[str, Any]:
    generated_at = _generated_at(args.generated_at)
    if args.confirm_draft_id is not None:
        output_root = args.output_dir or _output_root_from_manifest(args.manifest)
        backend: Any = _ConfirmationOnlyBackend()
    else:
        config = load_config(args.config)
        if args.output_dir is not None:
            config = replace(config, output_root=args.output_dir.expanduser().resolve())
        output_root = config.output_root
        backend = LocalRenderBackend.from_config(
            config,
            scripts_root=_briefing_scripts_root(),
        )
    result = render_briefing(
        output_root=output_root,
        manifest_path=args.manifest,
        script_path=args.script,
        generated_at=generated_at,
        backend=backend,
        confirm_draft_id=args.confirm_draft_id,
    )
    confirmed = result.draft.status is DraftStatus.CONFIRMED
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok" if confirmed else "needs_review",
        "command": "render",
        "draft_status": result.draft.status.value,
        "draft_id": result.draft.draft_id,
        "run_directory": str(result.run_directory),
        "manifest": str(result.manifest_path),
        "delivery_paths": [str(path) for path in result.delivery_paths],
    }


def render_text(payload: dict[str, Any]) -> str:
    if payload.get("status") == "error" and "error" in payload:
        error = payload["error"]
        return f"error [{error.get('code')}]: {error.get('message')}"
    command = payload.get("command", "briefing")
    lines = [f"EasyTravel briefing {command}: {payload['status']}"]
    if command == "doctor":
        for name, result in payload["checks"].items():
            lines.append(f"- {name}: {result['status']}")
        return "\n".join(lines)
    for name in (
        "draft_status",
        "draft_id",
        "run_directory",
        "manifest",
        "review",
        "narration_input",
        "report",
        "master_path",
        "calibration_manifest",
    ):
        if name in payload:
            lines.append(f"- {name}: {payload[name]}")
    return "\n".join(lines)


def error_payload(error: BriefingCliError) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "error",
        "error": {
            "code": error.code,
            "message": error.message,
            "details": error.details,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass
    arguments = tuple(argv) if argv is not None else tuple(sys.argv[1:])
    output_format = _requested_format(arguments)
    try:
        args = build_parser().parse_args(arguments)
        output_format = args.format
        payload = args.handler(args)
        exit_code = (
            NEEDS_REVIEW
            if payload.get("status") == "needs_review"
            else SUCCESS
            if payload.get("status") != "error"
            else INTERNAL_ERROR
        )
    except BriefingCliError as error:
        payload = error_payload(error)
        exit_code = error.exit_code
    except Exception:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "status": "error",
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Unexpected internal error",
                "details": {},
            },
        }
        exit_code = INTERNAL_ERROR
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=True, indent=2))
    else:
        print(render_text(payload))
    return exit_code


def _generated_at(value: str | None) -> str:
    if value is not None:
        return value
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_exclusive(path: Path, payload: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def _read_json_object(path: Path | None, *, label: str) -> dict[str, object] | None:
    if path is None:
        return None
    source = path.expanduser().resolve()
    if not source.is_file():
        raise BriefingInputError(f"{label} JSON file was not found")
    try:
        value = json.loads(source.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise BriefingInputError(f"{label} must be valid UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise BriefingInputError(f"{label} must be a JSON object")
    return value


def _output_root_from_manifest(manifest_path: Path) -> Path:
    manifest = manifest_path.expanduser().resolve()
    if manifest.name != "manifest.json" or not manifest.is_file():
        raise BriefingInputError("Manifest must be an existing manifest.json")
    run = manifest.parent
    if (
        _RUN_TIMESTAMP.fullmatch(run.name) is None
        or _PRODUCT_CODE.fullmatch(run.parent.name) is None
        or "--" in run.parent.name
    ):
        raise BriefingInputError("Manifest path does not match a briefing run")
    return manifest.parents[2]


def _requested_format(arguments: Sequence[str]) -> str:
    for index, value in enumerate(arguments[:-1]):
        if value == "--format" and arguments[index + 1] == "json":
            return "json"
    return "text"


def _briefing_scripts_root() -> Path:
    configured = os.environ.get("EASYTRAVEL_BRIEFING_SCRIPTS")
    candidates = []
    if configured:
        candidates.append(Path(os.path.expandvars(configured)).expanduser())
    candidates.extend(
        (
            Path(__file__).resolve().parents[2] / "scripts" / "briefing",
            Path(sys.prefix).resolve().parent / "scripts" / "briefing",
        )
    )
    required = {
        "patch_list_template.ps1",
        "render_list_template.ps1",
        "synthesize_yating.ps1",
    }
    for candidate in candidates:
        root = candidate.resolve()
        if root.is_dir() and required <= {path.name for path in root.iterdir()}:
            return root
    return candidates[0].resolve()


class _ConfirmationOnlyBackend:
    def render_word(self, draft: BriefingDraft, **_: Any) -> None:
        del draft
        raise AssertionError("Confirmation must not rerun Word")

    def render_audio(self, draft: BriefingDraft, script: str, **_: Any) -> None:
        del draft, script
        raise AssertionError("Confirmation must not rerun TTS")


if __name__ == "__main__":
    raise SystemExit(main())
