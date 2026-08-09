from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
import traceback
from pathlib import Path
from typing import Any, Sequence

from . import __version__
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
    hanhan_available = _hanhan_registered()
    word_com_registered = _word_com_registered()
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
        "ffmpeg": _tool_check("ffmpeg", os.environ.get("BRIEFING_FFMPEG")),
        "word_com": {
            "status": "ok" if word_com_registered else "warning",
            "registered": word_com_registered,
            "probe": "registry_only",
        },
        "pdftoppm": _tool_check("pdftoppm"),
        "environment": _environment_check(),
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


def _tool_check(name: str, configured_path: str | None = None) -> dict[str, Any]:
    candidate = None
    discovery = "none"
    if configured_path:
        path = Path(configured_path).expanduser()
        if path.is_file():
            candidate = str(path)
            discovery = "configured"
    if candidate is None:
        candidate = shutil.which(name)
        if candidate:
            discovery = "path"
    if candidate is None:
        candidate = _winget_tool_path(name)
        if candidate:
            discovery = "winget"
    return {
        "status": "ok" if candidate else "warning",
        "available": candidate is not None,
        "configured_path": bool(configured_path),
        "discovery": discovery,
    }


def _winget_tool_path(name: str) -> str | None:
    if sys.platform != "win32":
        return None
    package_hint = {"ffmpeg": "ffmpeg", "pdftoppm": "poppler"}.get(name)
    local_app_data = os.environ.get("LOCALAPPDATA")
    if package_hint is None or not local_app_data:
        return None
    packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
    try:
        package_dirs = sorted(
            path
            for path in packages.iterdir()
            if path.is_dir() and package_hint in path.name.casefold()
        )
    except OSError:
        return None
    for package_dir in package_dirs:
        try:
            match = next(package_dir.rglob(f"{name}.exe"), None)
        except OSError:
            continue
        if match is not None and match.is_file():
            return str(match)
    return None


def _environment_check() -> dict[str, Any]:
    key_configured = bool(os.environ.get("AZURE_SPEECH_KEY"))
    region_configured = bool(os.environ.get("AZURE_SPEECH_REGION"))
    return {
        "status": "ok" if key_configured and region_configured else "warning",
        "azure_speech_key_configured": key_configured,
        "azure_speech_region_configured": region_configured,
    }


def _hanhan_registered() -> bool:
    token_paths = (
        r"SOFTWARE\Microsoft\Speech\Voices\Tokens",
        r"SOFTWARE\WOW6432Node\Microsoft\Speech\Voices\Tokens",
    )
    return any(_registry_children_contain(path, "hanhan") for path in token_paths)


def _word_com_registered() -> bool:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CLSID"):
            return True
    except (ImportError, OSError):
        return False


def _registry_children_contain(path: str, needle: str) -> bool:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
            index = 0
            while True:
                try:
                    name = winreg.EnumKey(key, index)
                except OSError:
                    return False
                if needle.casefold() in name.casefold():
                    return True
                index += 1
    except (ImportError, OSError):
        return False


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
