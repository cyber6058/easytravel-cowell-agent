from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import traceback
from typing import Any, Sequence

from . import __version__
from .capabilities import (
    environment_check,
    hanhan_registered,
    tool_check,
    word_com_registered,
)
from .errors import BriefingCliError
from .exit_codes import INTERNAL_ERROR, SUCCESS


SCHEMA_VERSION = 1
_HANHAN_VOICE = "Microsoft Hanhan Desktop"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="briefing",
        description="EasyTravel briefing document and audio drafts",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check local briefing capabilities")
    doctor.add_argument("--format", choices=("text", "json"), default="text")
    doctor.set_defaults(handler=run_doctor)
    return parser


def run_doctor(_: argparse.Namespace) -> dict[str, Any]:
    hanhan_available = hanhan_registered()
    word_registered = word_com_registered()
    checks = {
        "python": {
            "status": "ok" if sys.version_info >= (3, 12) else "error",
            "version": platform.python_version(),
        },
        "platform": {
            "status": "ok" if sys.platform == "win32" else "warning",
            "windows": sys.platform == "win32",
        },
        "hanhan": {
            "status": "ok" if hanhan_available else "warning",
            "available": hanhan_available,
            "voice": _HANHAN_VOICE,
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
        "pdftoppm": tool_check("pdftoppm"),
        "environment": environment_check(),
    }
    statuses = {check["status"] for check in checks.values()}
    status = (
        "error"
        if "error" in statuses
        else "warning"
        if "warning" in statuses
        else "ok"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "command": "doctor",
        "checks": checks,
    }


def render_text(payload: dict[str, Any]) -> str:
    if payload.get("status") == "error" and "error" in payload:
        error = payload["error"]
        return f"error [{error.get('code')}]: {error.get('message')}"
    lines = [f"EasyTravel briefing doctor: {payload['status']}"]
    for name, result in payload["checks"].items():
        lines.append(f"- {name}: {result['status']}")
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
    args = build_parser().parse_args(argv)
    try:
        payload = args.handler(args)
        exit_code = SUCCESS if payload.get("status") != "error" else INTERNAL_ERROR
    except BriefingCliError as error:
        payload = error_payload(error)
        exit_code = error.exit_code
    except Exception:
        print(traceback.format_exc(), file=sys.stderr)
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
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=True, indent=2))
    else:
        print(render_text(payload))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
