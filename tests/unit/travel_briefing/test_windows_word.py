import json
import subprocess

import pytest

from travel_briefing.adapters.windows_word import (
    OwnedWordProcess,
    WindowsWordAdapter,
)
from travel_briefing.errors import (
    UnknownWordResultError,
    WordAutomationUnavailableError,
    WordGenerationError,
)


class WordRunner:
    def __init__(self, *, return_code=0, stderr="") -> None:
        self.return_code = return_code
        self.stderr = stderr
        self.calls = []

    def __call__(self, command, **options):
        self.calls.append((command, options))
        return subprocess.CompletedProcess(
            command,
            returncode=self.return_code,
            stdout="",
            stderr=self.stderr,
        )


def adapter(tmp_path, runner, terminator=lambda _: False):
    script = tmp_path / "patch_list_template.ps1"
    script.write_text("# synthetic adapter", encoding="utf-8")
    return WindowsWordAdapter(
        script_path=script,
        runner=runner,
        process_terminator=terminator,
    )


def job(tmp_path, action="patch"):
    path = tmp_path / "word-job.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "action": action,
                "ownership_nonce": "a" * 32,
                "word_pid_path": str(tmp_path / "word-owner.json"),
            }
        ),
        encoding="utf-8",
    )
    return path


def test_word_adapter_passes_only_the_job_path_to_hidden_powershell(tmp_path):
    runner = WordRunner()
    word = adapter(tmp_path, runner)
    job_path = job(tmp_path)

    word.run(job_path, timeout_seconds=90)

    command, options = runner.calls[0]
    assert command == [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(word.script_path.resolve()),
        "-JobPath",
        str(job_path.resolve()),
    ]
    assert options["timeout"] == 90
    assert options["encoding"] == "utf-8"


def test_word_probe_has_a_hard_twenty_second_limit(tmp_path):
    word = adapter(tmp_path, WordRunner())

    with pytest.raises(ValueError, match="20 seconds"):
        word.run(job(tmp_path, action="probe"), timeout_seconds=21)


def test_word_timeout_stops_only_the_nonce_bound_word_pid_and_never_retries(
    tmp_path,
):
    job_path = job(tmp_path)
    owner_path = tmp_path / "word-owner.json"
    owner_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "ownership_nonce": "a" * 32,
                "pid": 4321,
                "process_name": "WINWORD",
                "start_time_utc_ticks": 638906112000000000,
            }
        ),
        encoding="utf-8",
    )
    calls = []

    def timeout_runner(command, **options):
        raise subprocess.TimeoutExpired(command, options["timeout"])

    def terminator(process):
        calls.append(process)
        return True

    word = adapter(tmp_path, timeout_runner, terminator)

    with pytest.raises(UnknownWordResultError) as captured:
        word.run(job_path, timeout_seconds=90)

    assert calls == [
        OwnedWordProcess(
            pid=4321,
            process_name="WINWORD",
            start_time_utc_ticks=638906112000000000,
        )
    ]
    assert captured.value.details == {
        "owned_word_process_found": True,
        "owned_word_process_stopped": True,
    }


@pytest.mark.parametrize(
    ("return_code", "error_type"),
    [(21, WordAutomationUnavailableError), (30, WordGenerationError)],
)
def test_word_adapter_maps_stable_script_failures(tmp_path, return_code, error_type):
    word = adapter(tmp_path, WordRunner(return_code=return_code))

    with pytest.raises(error_type):
        word.run(job(tmp_path), timeout_seconds=90)


def test_word_timeout_does_not_stop_a_stale_or_ambiguous_pid_record(tmp_path):
    job_path = job(tmp_path)
    (tmp_path / "word-owner.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "ownership_nonce": "different",
                "pid": 4321,
                "process_name": "WINWORD",
                "start_time_utc_ticks": 638906112000000000,
            }
        ),
        encoding="utf-8",
    )
    calls = []

    def timeout_runner(command, **options):
        raise subprocess.TimeoutExpired(command, options["timeout"])

    word = adapter(tmp_path, timeout_runner, lambda process: calls.append(process))

    with pytest.raises(UnknownWordResultError) as captured:
        word.run(job_path, timeout_seconds=90)

    assert calls == []
    assert captured.value.details == {
        "owned_word_process_found": False,
        "owned_word_process_stopped": False,
    }
