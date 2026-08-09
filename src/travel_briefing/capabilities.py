from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any


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


def environment_check() -> dict[str, Any]:
    key_configured = bool(os.environ.get("AZURE_SPEECH_KEY"))
    region_configured = bool(os.environ.get("AZURE_SPEECH_REGION"))
    return {
        "status": "ok" if key_configured and region_configured else "warning",
        "azure_speech_key_configured": key_configured,
        "azure_speech_region_configured": region_configured,
    }


def hanhan_registered() -> bool:
    token_paths = (
        r"SOFTWARE\Microsoft\Speech\Voices\Tokens",
        r"SOFTWARE\WOW6432Node\Microsoft\Speech\Voices\Tokens",
    )
    return any(_registry_children_contain(path, "hanhan") for path in token_paths)


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
