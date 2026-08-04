from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import traceback
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .adapters.cowell.controlled_write_policy import ScopedTestWriteAuthorization
from .adapters.cowell.http_gateway import CowellHttpGateway
from .adapters.cowell.live_rooming import CowellLiveRooming
from .adapters.cowell.operation_registry import default_cowell_registry
from .adapters.cowell.read_only_policy import ReadOnlyPolicy
from .adapters.cowell.session_import import import_cdp_session
from .application.auth import auth_status
from .application.passenger_import import (
    build_cowell_roster_workbook,
    validate_cowell_roster_template,
)
from .application.passports import (
    load_passport_travelers,
    validate_passport_travelers,
)
from .application.rooming_workflow import build_rooming_plan
from .application.rooms import parse_rooming_list
from .application.serializers import (
    serialize_live_rooming_preview,
    serialize_live_rooming_result,
    serialize_rooming_list,
    serialize_rooming_plan,
)
from .config import load_config
from .errors import CowellCliError, ValidationError
from .exit_codes import INTERNAL_ERROR, SUCCESS
from .infrastructure.passport_images import prepare_passport_images
from .infrastructure.redaction import redact, redact_text
from .infrastructure.session_lock import SessionLock


SCHEMA_VERSION = 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cowell",
        description="EasyTravel passport roster and existing-order rooming",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check the local runtime")
    doctor.add_argument("--format", choices=("text", "json"), default="text")
    doctor.set_defaults(handler=run_doctor)

    auth = subparsers.add_parser("auth", help="Cowell session commands")
    auth_subparsers = auth.add_subparsers(dest="auth_command", required=True)
    auth_status_parser = auth_subparsers.add_parser("status", help="Check Cowell session")
    auth_status_parser.add_argument("--format", choices=("text", "json"), default="text")
    auth_status_parser.set_defaults(handler=run_auth_status)

    passports = subparsers.add_parser(
        "passports", help="Prepare and validate passport rosters"
    )
    passport_commands = passports.add_subparsers(
        dest="passports_command", required=True
    )
    prepare = passport_commands.add_parser(
        "prepare", help="Split sources into one upright image per passport"
    )
    prepare.add_argument("path", type=Path)
    prepare.add_argument("--output-dir", type=Path, required=True)
    prepare.add_argument(
        "--layout", choices=("auto", "single", "2x2", "2x1", "1x2"), default="auto"
    )
    prepare.add_argument(
        "--rotate", choices=("auto", "0", "90", "180", "270"), default="auto"
    )
    prepare.add_argument("--format", choices=("text", "json"), default=None)
    prepare.set_defaults(handler=run_passports_prepare)

    template = passport_commands.add_parser(
        "template", help="Download the current account's official Cowell XLSX template"
    )
    template.add_argument("--output", type=Path, required=True)
    template.add_argument("--format", choices=("text", "json"), default=None)
    template.set_defaults(handler=run_passports_template)

    validate = passport_commands.add_parser(
        "validate", help="Validate extracted fields against TD3 MRZ check digits"
    )
    validate.add_argument("path", type=Path)
    validate.add_argument("--format", choices=("text", "json"), default=None)
    validate.set_defaults(handler=run_passports_validate)

    export = passport_commands.add_parser(
        "export", help="Write a validated 19-column Cowell XLSX roster"
    )
    export.add_argument("path", type=Path)
    export.add_argument("--template", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--allow-unverified", action="store_true")
    export.add_argument("--format", choices=("text", "json"), default=None)
    export.set_defaults(handler=run_passports_export)

    rooms = subparsers.add_parser("rooms", help="Existing-order rooming workflows")
    room_commands = rooms.add_subparsers(dest="rooms_command", required=True)
    parse = room_commands.add_parser(
        "parse", help="Parse DOCX/XLSX without connecting to Cowell"
    )
    parse.add_argument("path", type=Path)
    parse.add_argument("--format", choices=("text", "json"), default=None)
    parse.set_defaults(handler=run_rooms_parse)
    plan = room_commands.add_parser(
        "plan", help="Build a deterministic plan without connecting to Cowell"
    )
    _add_rooming_target_arguments(plan)
    plan.add_argument("--format", choices=("text", "json"), default=None)
    plan.set_defaults(handler=run_rooms_plan)
    preview = room_commands.add_parser(
        "preview", help="Read Cowell and verify names, cabins, and room collisions"
    )
    _add_rooming_target_arguments(preview)
    preview.add_argument("--format", choices=("text", "json"), default=None)
    preview.set_defaults(handler=run_rooms_preview)
    apply = room_commands.add_parser(
        "apply", help="Apply one reviewed existing-order plan and verify read-back"
    )
    _add_rooming_target_arguments(apply)
    apply.add_argument("--confirm", required=True)
    apply.add_argument("--format", choices=("text", "json"), default=None)
    apply.set_defaults(handler=run_rooms_apply)
    return parser


def _add_rooming_target_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("path", type=Path)
    parser.add_argument("--group-code", required=True)
    parser.add_argument("--order-id", required=True)
    parser.add_argument("--room-offset", type=int, default=0)
    parser.add_argument("--cabin")
    parser.add_argument(
        "--cabin-map",
        type=Path,
        help="JSON object mapping source passenger sequence to Cowell cabin",
    )


def run_doctor(_: argparse.Namespace) -> dict[str, Any]:
    checks = {
        "python": {
            "status": "ok" if sys.version_info >= (3, 12) else "error",
            "version": platform.python_version(),
        },
        "platform": {
            "status": "ok" if sys.platform == "win32" else "warning",
            "name": platform.platform(),
        },
        "local_app_data": {"status": "ok", "configured": bool(_local_app_data())},
    }
    status = (
        "ok"
        if all(check["status"] in {"ok", "warning"} for check in checks.values())
        else "error"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "command": "doctor",
        "checks": checks,
    }


def run_auth_status(_: argparse.Namespace) -> dict[str, Any]:
    with _cowell_gateway() as gateway:
        session = auth_status(gateway)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "command": "auth status",
        "session": session,
    }


def run_rooms_parse(args: argparse.Namespace) -> dict[str, Any]:
    payload = serialize_rooming_list(parse_rooming_list(args.path))
    payload.update(status="ok", command="rooms parse")
    return payload


def _build_rooming_plan_from_args(args: argparse.Namespace):
    cabin_map = None
    if args.cabin_map:
        path = args.cabin_map.expanduser().resolve()
        if not path.is_file():
            raise ValidationError("cabin_map JSON does not exist", {"path": str(path)})
        try:
            cabin_map = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValidationError("cabin_map must be valid UTF-8 JSON") from error
        if not isinstance(cabin_map, dict):
            raise ValidationError("cabin_map must be a JSON object")
    return build_rooming_plan(
        args.path,
        group_code=args.group_code,
        order_id=args.order_id,
        room_offset=args.room_offset,
        cabin=args.cabin,
        cabin_map=cabin_map,
    )


def run_rooms_plan(args: argparse.Namespace) -> dict[str, Any]:
    payload = serialize_rooming_plan(_build_rooming_plan_from_args(args))
    payload.update(status="ok", command="rooms plan")
    return payload


def run_rooms_preview(args: argparse.Namespace) -> dict[str, Any]:
    plan = _build_rooming_plan_from_args(args)
    preview = _live_rooming(
        group_code=plan.target_group_code, order_id=plan.target_order_id
    ).preview(plan)
    payload = serialize_live_rooming_preview(preview)
    payload.update(
        status="ok",
        command="rooms preview",
        plan_hash=plan.plan_hash,
        confirmation=plan.confirmation,
    )
    return payload


def run_rooms_apply(args: argparse.Namespace) -> dict[str, Any]:
    plan = _build_rooming_plan_from_args(args)
    result = _live_rooming(
        group_code=plan.target_group_code, order_id=plan.target_order_id
    ).apply(plan, confirmation=args.confirm)
    payload = serialize_live_rooming_result(result)
    payload.update(status="ok", command="rooms apply")
    return payload


def run_passports_prepare(args: argparse.Namespace) -> dict[str, Any]:
    result = prepare_passport_images(
        args.path, args.output_dir, layout=args.layout, rotation=args.rotate
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "command": "passports prepare",
        "type": "passport_image_preparation",
        "data": {
            "source_sha256": result.source_sha256,
            "output_dir": str(result.output_dir),
            "page_count": result.page_count,
            "passport_count": result.passport_count,
            "artifacts": [
                {
                    "record_id": artifact.record_id,
                    "page_number": artifact.page_number,
                    "path": str(artifact.path),
                    "sha256": artifact.sha256,
                    "width": artifact.width,
                    "height": artifact.height,
                    "rotation_degrees": artifact.rotation_degrees,
                }
                for artifact in result.artifacts
            ],
            "warnings": list(result.warnings),
        },
    }


def run_passports_template(args: argparse.Namespace) -> dict[str, Any]:
    output = _new_xlsx_output(args.output, "Cowell template")
    with _cowell_gateway() as gateway:
        content = gateway.get("/Docu/rect_file.xlsx").content
    validate_cowell_roster_template(content)
    output.write_bytes(content)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "command": "passports template",
        "type": "passport_roster_template",
        "data": {
            "output": str(output),
            "sha256": hashlib.sha256(content).hexdigest(),
            "byte_count": len(content),
        },
    }


def run_passports_validate(args: argparse.Namespace) -> dict[str, Any]:
    report = validate_passport_travelers(load_passport_travelers(args.path))
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "command": "passports validate",
        "type": "passport_validation",
        "data": {
            "record_count": report.record_count,
            "ready_count": report.ready_count,
            "valid_mrz_count": report.valid_mrz_count,
            "ready_for_export": report.ready_for_export,
            "records": [
                {
                    "record_id": record.record_id,
                    "ready_for_export": record.ready_for_export,
                    "mrz_check_digits_valid": record.mrz_check_digits_valid,
                    "errors": list(record.errors),
                    "warnings": list(record.warnings),
                }
                for record in report.records
            ],
        },
    }


def run_passports_export(args: argparse.Namespace) -> dict[str, Any]:
    travelers = load_passport_travelers(args.path)
    report = validate_passport_travelers(travelers)
    if not report.ready_for_export and not args.allow_unverified:
        raise ValidationError(
            "Passport roster is not fully MRZ-verified",
            {
                "record_count": report.record_count,
                "ready_count": report.ready_count,
                "blocked_record_ids": [
                    record.record_id
                    for record in report.records
                    if not record.ready_for_export
                ],
            },
        )
    template = args.template.expanduser().resolve()
    if not template.is_file():
        raise ValidationError("Cowell XLSX template does not exist", {"path": str(template)})
    output = _new_xlsx_output(args.output, "Passport roster")
    workbook = build_cowell_roster_workbook(template.read_bytes(), travelers)
    output.write_bytes(workbook.content)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "command": "passports export",
        "type": "passport_roster_export",
        "data": {
            "output": str(output),
            "sha256": hashlib.sha256(workbook.content).hexdigest(),
            "passenger_count": workbook.passenger_count,
            "verified_count": report.ready_count,
            "unverified_export": not report.ready_for_export,
            "column_count": len(workbook.populated_columns),
        },
    }


def _new_xlsx_output(value: Path, label: str) -> Path:
    output = value.expanduser().resolve()
    if output.suffix.lower() != ".xlsx":
        raise ValidationError(f"{label} output must use .xlsx")
    if output.exists():
        raise ValidationError(
            f"{label} output already exists; choose a new filename",
            {"path": str(output)},
        )
    if not output.parent.is_dir():
        raise ValidationError(
            f"{label} output directory does not exist", {"path": str(output.parent)}
        )
    return output


def _live_rooming(*, group_code: str, order_id: str) -> CowellLiveRooming:
    config = load_config()
    return CowellLiveRooming(
        base_url=config.cowell_base_url,
        session_lock_path=_session_lock_path(),
        authorization=ScopedTestWriteAuthorization(
            group_code=group_code, order_id=order_id
        ),
    )


def _local_app_data() -> Path | None:
    import os

    value = os.environ.get("LOCALAPPDATA")
    return Path(value) if value else None


def _session_lock_path() -> Path:
    local_app_data = _local_app_data()
    if local_app_data is None:
        from .errors import ConfigurationError

        raise ConfigurationError("LOCALAPPDATA is not configured")
    return local_app_data / "CowellCLI" / "session.lock"


def _cowell_gateway() -> CowellHttpGateway:
    config = load_config()
    lock = SessionLock(_session_lock_path()).acquire()
    try:
        session = import_cdp_session()
        policy = ReadOnlyPolicy(default_cowell_registry(), config.cowell_base_url)
        return CowellHttpGateway(
            base_url=config.cowell_base_url,
            policy=policy,
            session=session,
            lock=lock,
        )
    except BaseException:
        lock.release()
        raise


def render_text(payload: dict[str, Any]) -> str:
    if payload.get("status") == "error":
        error = payload.get("error", {})
        return f"error [{error.get('code')}]: {error.get('message')}"
    if payload.get("command") == "doctor":
        lines = [f"EasyTravel Cowell doctor: {payload['status']}"]
        for name, result in payload["checks"].items():
            detail = result.get("version") or result.get("name") or ""
            lines.append(f"- {name}: {result['status']} {detail}".rstrip())
        return "\n".join(lines)
    if payload.get("command") == "auth status":
        session = payload.get("session", {})
        state = "valid" if session.get("valid") else "invalid"
        return f"auth status: {state} (probe {session.get('probe')})"
    return json.dumps(payload, ensure_ascii=False, indent=2)


def error_payload(error: CowellCliError) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "error",
        "error": {
            "code": error.code,
            "message": error.message,
            "details": redact(error.details),
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass
    args = build_parser().parse_args(argv)
    output_format = getattr(args, "format", None)
    if output_format is None:
        output_format = "text" if getattr(sys.stdout, "isatty", lambda: False)() else "json"
    try:
        payload = args.handler(args)
        exit_code = SUCCESS if payload.get("status") != "error" else INTERNAL_ERROR
    except CowellCliError as error:
        payload = error_payload(error)
        exit_code = error.exit_code
    except Exception:
        print(redact_text(traceback.format_exc()), file=sys.stderr)
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
        print(json.dumps(redact(payload), ensure_ascii=True, indent=2))
    else:
        print(render_text(redact(payload)))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
