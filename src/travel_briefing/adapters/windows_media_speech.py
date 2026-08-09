from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ..errors import (
    AudioSynthesisError,
    LocalTtsUnavailableError,
    UnknownAudioResultError,
)


ProcessRunner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(slots=True)
class WindowsMediaSpeechAdapter:
    script_path: Path
    powershell_executable: str = "powershell.exe"
    runner: ProcessRunner = field(default=subprocess.run, repr=False)

    def synthesize(self, job_path: Path, *, timeout_seconds: int) -> None:
        script = self.script_path.expanduser().resolve()
        job = job_path.expanduser().resolve()
        if not script.is_file():
            raise AudioSynthesisError("Yating PowerShell adapter script is missing")
        if not job.is_file():
            raise AudioSynthesisError("Yating speech job file is missing")
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
            raise UnknownAudioResultError() from error
        except OSError as error:
            raise LocalTtsUnavailableError(
                "Windows PowerShell is unavailable for Yating TTS"
            ) from error
        if result.returncode == 21:
            raise LocalTtsUnavailableError("Local Yating TTS is unavailable")
        if result.returncode != 0:
            raise AudioSynthesisError(
                "Local Yating synthesis failed",
                {"return_code": result.returncode},
            )
