from __future__ import annotations

import os
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from .config import BriefingConfig


ProcessRunner = Callable[..., subprocess.CompletedProcess[str]]
_SPEECH_RUNTIME_TYPE = (
    "Windows.Media.SpeechSynthesis.SpeechSynthesizer,"
    " Windows.Media.SpeechSynthesis, ContentType=WindowsRuntime"
)

_YATING_PROBE_SCRIPT = r'''
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[SPEECH_RUNTIME_TYPE] | Out-Null
$matchingVoices = @(
    [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices |
        Where-Object {
            $_.DisplayName -ceq "Microsoft Yating" -and
            $_.Language -ceq "zh-TW"
        }
)
if ($matchingVoices.Count -eq 1) {
    [Console]::Out.Write("YATING_AVAILABLE")
    exit 0
}
exit 21
'''.replace("SPEECH_RUNTIME_TYPE", _SPEECH_RUNTIME_TYPE).strip()


def configured_executable(value: Path | str | None) -> Path | None:
    if value is None:
        return None
    path = Path(value).expanduser().resolve()
    return path if path.is_file() else None


def tool_check(
    name: str,
    configured_path: str | None = None,
    *,
    require_configured: bool = False,
) -> dict[str, Any]:
    candidate = configured_executable(configured_path)
    configured = candidate is not None
    discovery = "configured" if candidate else "none"
    if candidate is None:
        path_candidate = shutil.which(name)
        if path_candidate:
            candidate = Path(path_candidate)
            discovery = "path"
    if candidate is None:
        candidate = _winget_tool_path(name)
        if candidate:
            discovery = "winget"
    usable = candidate is not None and (configured or not require_configured)
    return {
        "status": "ok" if usable else "warning",
        "available": candidate is not None,
        "usable": usable,
        "configured_path": bool(configured_path),
        "discovery": discovery,
    }


def list_calibration_check(
    config: BriefingConfig | None,
    *,
    configured: bool = True,
    failure_status: str = "missing",
) -> dict[str, Any]:
    if not configured or config is None:
        status = (
            failure_status
            if failure_status in {"missing", "changed", "unsupported"}
            else "missing"
        )
        return {
            "status": status,
            "schema_version": 2,
            "generator_version": "list-calibration/2",
            "master_sha256_matches": False,
            "normalized_structure_fingerprint": False,
        }
    manifest = config.calibration_manifest
    try:
        actual_master_hash = _sha256_file(config.master_path)
        actual_manifest_hash = _sha256_file(
            config.calibration_manifest_path
        )
    except OSError:
        status = "missing"
    else:
        if (
            manifest.schema_version != 2
            or manifest.generator_version != "list-calibration/2"
        ):
            status = "unsupported"
        elif (
            actual_master_hash != config.master_sha256
            or actual_master_hash != manifest.master_sha256
            or actual_manifest_hash
            != config.calibration_manifest_sha256
        ):
            status = "changed"
        else:
            status = "ok"
    return {
        "status": status,
        "schema_version": 2,
        "generator_version": "list-calibration/2",
        "master_sha256_matches": status == "ok",
        "normalized_structure_fingerprint": (
            status == "ok"
            and bool(config.master_structure_fingerprint)
        ),
    }


def hanhan_registered() -> bool:
    token_paths = (
        r"SOFTWARE\Microsoft\Speech\Voices\Tokens",
        r"SOFTWARE\WOW6432Node\Microsoft\Speech\Voices\Tokens",
    )
    return any(_registry_children_contain(path, "hanhan") for path in token_paths)


def yating_registered(
    *,
    runner: ProcessRunner = subprocess.run,
    powershell_executable: str = "powershell.exe",
    timeout_seconds: int = 10,
) -> bool:
    if sys.platform != "win32":
        return False
    command = [
        powershell_executable,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        _YATING_PROBE_SCRIPT,
    ]
    options: dict[str, Any] = {
        "check": False,
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": timeout_seconds,
    }
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        options["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        result = runner(command, **options)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and result.stdout.strip() == "YATING_AVAILABLE"


def word_com_registered() -> bool:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CLSID"):
            return True
    except (ImportError, OSError):
        return False


def _winget_tool_path(name: str) -> Path | None:
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
            return match
    return None


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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
