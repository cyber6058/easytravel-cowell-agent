import argparse
import json
import subprocess
import sys

from travel_briefing import cli


def test_doctor_reports_offline_capabilities_without_exposing_secrets(
    monkeypatch, capsys
):
    monkeypatch.setenv("AZURE_SPEECH_KEY", "super-secret-test-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "eastasia")

    exit_code = cli.main(["doctor", "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["command"] == "doctor"
    assert set(payload["checks"]) == {
        "python",
        "platform",
        "hanhan",
        "ffmpeg",
        "word_com",
        "pdftoppm",
        "environment",
    }
    assert payload["checks"]["environment"] == {
        "status": "ok",
        "azure_speech_key_configured": True,
        "azure_speech_region_configured": True,
    }
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
    monkeypatch.setattr(cli.shutil, "which", lambda _: None)
    monkeypatch.setattr(cli.sys, "platform", "win32")

    payload = cli.run_doctor(argparse.Namespace())

    assert payload["checks"]["pdftoppm"]["available"] is True
    assert payload["checks"]["pdftoppm"]["discovery"] == "winget"
