from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ..errors import (
    UnknownWordResultError,
    WordAutomationUnavailableError,
    WordGenerationError,
)


ProcessRunner = Callable[..., subprocess.CompletedProcess[str]]
ProcessTerminator = Callable[["OwnedWordProcess"], bool]


@dataclass(frozen=True, slots=True)
class OwnedWordProcess:
    pid: int
    process_name: str
    start_time_utc_ticks: int


@dataclass(slots=True)
class WindowsWordAdapter:
    script_path: Path
    powershell_executable: str = "powershell.exe"
    runner: ProcessRunner = field(default=subprocess.run, repr=False)
    process_terminator: ProcessTerminator = field(
        default=lambda process: stop_owned_word_process(process),
        repr=False,
    )

    def run(self, job_path: Path, *, timeout_seconds: int) -> None:
        script = self.script_path.expanduser().resolve()
        job = job_path.expanduser().resolve()
        if not script.is_file():
            raise WordGenerationError("Word PowerShell adapter script is missing")
        if not job.is_file():
            raise WordGenerationError("Word automation job file is missing")
        job_metadata = _read_job_metadata(job)
        if job_metadata["action"] == "probe" and timeout_seconds > 20:
            raise ValueError("Word capability probe cannot exceed 20 seconds")
        if timeout_seconds <= 0:
            raise ValueError("Word automation timeout must be positive")
        command = [
            self.powershell_executable,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-JobPath",
            str(job),
        ]
        options: dict[str, Any] = {
            "check": False,
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "timeout": timeout_seconds,
        }
        if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            options["creationflags"] = subprocess.CREATE_NO_WINDOW
        try:
            result = self.runner(command, **options)
        except subprocess.TimeoutExpired as error:
            owned = _read_owned_word_process(
                job_metadata["word_pid_path"],
                ownership_nonce=job_metadata["ownership_nonce"],
            )
            stopped = False
            if owned is not None:
                try:
                    stopped = bool(self.process_terminator(owned))
                except OSError:
                    stopped = False
            raise UnknownWordResultError(
                details={
                    "owned_word_process_found": owned is not None,
                    "owned_word_process_stopped": stopped,
                }
            ) from error
        except OSError as error:
            raise WordAutomationUnavailableError(
                "Windows PowerShell is unavailable for Word automation"
            ) from error
        if result.returncode == 21:
            raise WordAutomationUnavailableError()
        if result.returncode != 0:
            raise WordGenerationError(
                "Word automation failed",
                {"return_code": result.returncode},
            )


def stop_owned_word_process(
    process: OwnedWordProcess,
    *,
    runner: ProcessRunner = subprocess.run,
    powershell_executable: str = "powershell.exe",
) -> bool:
    if (
        process.pid <= 0
        or process.start_time_utc_ticks <= 0
        or process.process_name != "WINWORD"
    ):
        return False
    script = (
        "$ErrorActionPreference='Stop';"
        f"$p=Get-Process -Id {process.pid} -ErrorAction SilentlyContinue;"
        "if($null -eq $p){exit 3};"
        "if($p.ProcessName -cne 'WINWORD'){exit 4};"
        "$ticks=$p.StartTime.ToUniversalTime().Ticks;"
        f"if($ticks -ne {process.start_time_utc_ticks}){{exit 5}};"
        f"Stop-Process -Id {process.pid} -Force;"
        "[Console]::Out.Write('STOPPED')"
    )
    command = [
        powershell_executable,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        script,
    ]
    options: dict[str, Any] = {
        "check": False,
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": 10,
    }
    if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        options["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        result = runner(command, **options)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and result.stdout == "STOPPED"


def _read_job_metadata(path: Path) -> dict[str, str | Path]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise WordGenerationError("Word automation job is not valid UTF-8 JSON") from error
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise WordGenerationError("Word automation job does not match schema version 1")
    action = payload.get("action")
    nonce = payload.get("ownership_nonce")
    pid_path = payload.get("word_pid_path")
    if action not in {"probe", "inspect", "patch", "render"}:
        raise WordGenerationError("Word automation job action is unsupported")
    if (
        not isinstance(nonce, str)
        or _is_hex_nonce(nonce) is False
        or not isinstance(pid_path, str)
        or not pid_path
    ):
        raise WordGenerationError("Word automation ownership metadata is invalid")
    return {
        "action": action,
        "ownership_nonce": nonce,
        "word_pid_path": Path(pid_path).expanduser().resolve(),
    }


def _read_owned_word_process(
    path: Path,
    *,
    ownership_nonce: str,
) -> OwnedWordProcess | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != 1
        or payload.get("ownership_nonce") != ownership_nonce
        or payload.get("process_name") != "WINWORD"
    ):
        return None
    pid = payload.get("pid")
    ticks = payload.get("start_time_utc_ticks")
    if (
        isinstance(pid, bool)
        or not isinstance(pid, int)
        or pid <= 0
        or isinstance(ticks, bool)
        or not isinstance(ticks, int)
        or ticks <= 0
    ):
        return None
    return OwnedWordProcess(
        pid=pid,
        process_name="WINWORD",
        start_time_utc_ticks=ticks,
    )


def _is_hex_nonce(value: str) -> bool:
    return len(value) == 32 and all(character in "0123456789abcdef" for character in value)
