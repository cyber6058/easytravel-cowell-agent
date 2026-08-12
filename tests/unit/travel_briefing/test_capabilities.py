import subprocess

from travel_briefing import capabilities
from travel_briefing.capabilities import (
    list_calibration_check,
    configured_executable,
    tool_check,
    yating_registered,
)
from tests.unit.travel_briefing.test_briefing_config import valid_config
from travel_briefing.config import parse_config


class YatingProbeRunner:
    def __init__(self, *, return_code=0, stdout="YATING_AVAILABLE\n") -> None:
        self.return_code = return_code
        self.stdout = stdout
        self.command = None
        self.options = None

    def __call__(self, command, **options):
        self.command = command
        self.options = options
        return subprocess.CompletedProcess(
            command,
            returncode=self.return_code,
            stdout=self.stdout,
            stderr="",
        )


def test_cloud_or_mp3_tools_require_an_explicit_existing_executable(tmp_path):
    executable = tmp_path / "ffmpeg.exe"

    assert configured_executable(None) is None
    assert configured_executable(executable) is None

    executable.write_bytes(b"synthetic executable")

    assert configured_executable(executable) == executable.resolve()


def test_ffmpeg_found_on_path_is_reported_but_not_usable_without_configuration(
    monkeypatch, tmp_path
):
    executable = tmp_path / "ffmpeg.exe"
    executable.write_bytes(b"synthetic executable")
    monkeypatch.setattr(capabilities.shutil, "which", lambda _: str(executable))

    check = tool_check("ffmpeg", require_configured=True)

    assert check == {
        "status": "warning",
        "available": True,
        "usable": False,
        "configured_path": False,
        "discovery": "path",
    }


def test_yating_probe_only_enumerates_the_exact_windows_media_voice(monkeypatch):
    runner = YatingProbeRunner()
    monkeypatch.setattr(capabilities.sys, "platform", "win32")

    available = yating_registered(runner=runner, timeout_seconds=7)

    assert available is True
    assert runner.command[:4] == [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
    ]
    probe = runner.command[-1]
    assert "SpeechSynthesizer]::AllVoices" in probe
    assert 'DisplayName -ceq "Microsoft Yating"' in probe
    assert 'Language -ceq "zh-TW"' in probe
    assert "SynthesizeSsmlToStreamAsync" not in probe
    assert "SynthesizeTextToStreamAsync" not in probe
    assert "Hanhan" not in probe
    assert runner.options["timeout"] == 7


def test_yating_probe_fails_closed_on_ambiguous_output(monkeypatch):
    runner = YatingProbeRunner(stdout="Microsoft Yating\nMicrosoft Yating\n")
    monkeypatch.setattr(capabilities.sys, "platform", "win32")

    assert yating_registered(runner=runner) is False


def test_list_calibration_capability_is_hash_only_and_offline(tmp_path):
    config = parse_config(valid_config(tmp_path))

    assert list_calibration_check(config) == {
        "status": "ok",
        "schema_version": 2,
        "generator_version": "list-calibration/2",
        "master_sha256_matches": True,
        "normalized_structure_fingerprint": True,
    }

    config.master_path.write_bytes(b"changed")
    check = list_calibration_check(config)
    assert check["status"] == "changed"
    assert str(config.master_path) not in str(check)
