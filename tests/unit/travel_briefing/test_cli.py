import argparse
import json
import subprocess
import sys

from travel_briefing import cli
from travel_briefing import capabilities


def test_doctor_reports_offline_capabilities_without_exposing_secrets(
    monkeypatch, capsys
):
    monkeypatch.setenv("AZURE_SPEECH_KEY", "super-secret-test-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "eastasia")
    monkeypatch.setattr(cli, "yating_registered", lambda: True)
    monkeypatch.setattr(cli, "hanhan_registered", lambda: False)

    exit_code = cli.main(["doctor", "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["command"] == "doctor"
    assert set(payload["checks"]) == {
        "python",
        "platform",
        "yating",
        "hanhan",
        "ffmpeg",
        "word_com",
        "pdftoppm",
    }
    assert payload["checks"]["yating"] == {
        "status": "ok",
        "available": True,
        "voice": "Microsoft Yating",
        "language": "zh-TW",
        "engine": "windows-media-speech",
        "role": "official_tts",
        "probe": "voice_enumeration_only",
    }
    assert payload["checks"]["hanhan"]["status"] == "ok"
    assert payload["checks"]["hanhan"]["available"] is False
    assert payload["checks"]["hanhan"]["role"] == "legacy_comparison_only"
    assert "azure" not in captured.out.casefold()
    assert "super-secret-test-key" not in captured.out
    assert "eastasia" not in captured.out


def test_documented_module_entrypoint_executes_briefing_cli():
    result = subprocess.run(
        [sys.executable, "-m", "travel_briefing", "doctor", "--format", "json"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "doctor"
    assert payload["schema_version"] == 1


def test_doctor_finds_pdftoppm_in_a_winget_package_when_path_is_restricted(
    monkeypatch, tmp_path
):
    executable = (
        tmp_path
        / "Microsoft"
        / "WinGet"
        / "Packages"
        / "Example.Poppler_Winget.Source"
        / "poppler"
        / "Library"
        / "bin"
        / "pdftoppm.exe"
    )
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(capabilities.shutil, "which", lambda _: None)
    monkeypatch.setattr(capabilities.sys, "platform", "win32")

    payload = cli.run_doctor(argparse.Namespace())

    assert payload["checks"]["pdftoppm"]["available"] is True
    assert payload["checks"]["pdftoppm"]["discovery"] == "winget"
