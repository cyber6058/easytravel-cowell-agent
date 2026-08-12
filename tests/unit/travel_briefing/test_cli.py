import argparse
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from travel_briefing import cli
from travel_briefing import capabilities
from travel_briefing.models import DraftStatus


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


def test_cli_exposes_prepare_check_script_and_yating_only_render():
    parser = cli.build_parser()

    prepared = parser.parse_args(
        [
            "prepare",
            "--pdf",
            "synthetic.pdf",
            "--output-dir",
            "briefings",
        ]
    )
    checked = parser.parse_args(
        ["check-script", "--manifest", "manifest.json", "--script", "script.txt"]
    )
    rendered = parser.parse_args(
        ["render", "--manifest", "manifest.json", "--script", "script.txt"]
    )

    assert prepared.command == "prepare"
    assert checked.command == "check-script"
    assert rendered.tts == "yating"
    with pytest.raises(cli.BriefingInputError):
        parser.parse_args(
            [
                "render",
                "--manifest",
                "manifest.json",
                "--script",
                "script.txt",
                "--tts",
                "hanhan",
            ]
        )


def test_invalid_cli_arguments_return_the_stable_input_error_code(capsys):
    exit_code = cli.main(
        [
            "render",
            "--manifest",
            "manifest.json",
            "--script",
            "script.txt",
            "--tts",
            "hanhan",
            "--format",
            "json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 40
    assert payload["error"]["code"] == "INPUT_ERROR"


def test_prepare_cli_returns_needs_review_without_exposing_source_content(
    monkeypatch,
    capsys,
    tmp_path,
):
    captured = {}

    def prepare(**kwargs):
        captured.update(kwargs)
        run = tmp_path / "briefings" / "SYN-OSA-260901" / "run"
        return SimpleNamespace(
            run_directory=run,
            draft=SimpleNamespace(
                draft_id="a" * 64,
                status=DraftStatus.DRAFT_READY,
            ),
            manifest_path=run / "manifest.json",
            review_path=run / "review.md",
            narration_input_path=run / "narration-input.json",
        )

    monkeypatch.setattr(cli, "prepare_briefing", prepare)

    exit_code = cli.main(
        [
            "prepare",
            "--url",
            "https://www.newamazing.com.tw/GroupDetail.asp?GroupNo=SYN",
            "--output-dir",
            str(tmp_path / "briefings"),
            "--generated-at",
            "2026-08-12T16:00:00+08:00",
            "--format",
            "json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 20
    assert payload["status"] == "needs_review"
    assert payload["command"] == "prepare"
    assert payload["draft_id"] == "a" * 64
    assert "source_html" not in payload
    assert captured["source_url"].startswith("https://www.newamazing.com.tw/")
    assert captured["output_root"] == Path(tmp_path / "briefings")


def test_cli_unexpected_error_never_prints_traceback_or_private_exception_text(
    monkeypatch,
    capsys,
):
    def fail(_):
        raise RuntimeError("private passenger detail sensitive-marker")

    monkeypatch.setattr(cli, "run_doctor", fail)
    parser = cli.build_parser()
    monkeypatch.setattr(cli, "build_parser", lambda: parser)
    parser.set_defaults(handler=fail)

    exit_code = cli.main(["doctor", "--format", "json"])

    captured = capsys.readouterr()
    assert exit_code == 50
    assert "private passenger" not in captured.out
    assert "private passenger" not in captured.err
    assert "Traceback" not in captured.err


def test_confirm_render_does_not_require_local_template_configuration(
    monkeypatch,
    tmp_path,
):
    manifest = (
        tmp_path
        / "briefings"
        / "SYN-OSA-260901"
        / "20260812T160000+0800"
        / "manifest.json"
    )
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}", encoding="utf-8")
    script = tmp_path / "script.txt"
    script.write_text("synthetic", encoding="utf-8")
    captured = {}

    def render(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            run_directory=manifest.parent,
            draft=SimpleNamespace(
                draft_id="a" * 64,
                status=DraftStatus.CONFIRMED,
            ),
            manifest_path=manifest,
            delivery_paths=(),
        )

    monkeypatch.setattr(cli, "load_config", lambda _: pytest.fail("config loaded"))
    monkeypatch.setattr(cli, "render_briefing", render)
    args = cli.build_parser().parse_args(
        [
            "render",
            "--manifest",
            str(manifest),
            "--script",
            str(script),
            "--confirm-draft-id",
            "a" * 64,
            "--generated-at",
            "2026-08-12T16:00:00+08:00",
        ]
    )

    payload = cli.run_render(args)

    assert payload["status"] == "ok"
    assert captured["output_root"] == manifest.parents[2]
    with pytest.raises(AssertionError, match="must not rerun Word"):
        captured["backend"].render_word(SimpleNamespace())


def test_check_script_derives_output_root_only_from_canonical_run_shape(
    monkeypatch,
    tmp_path,
):
    manifest = (
        tmp_path
        / "briefings"
        / "SYN-OSA-260901"
        / "20260812T160000+0800"
        / "manifest.json"
    )
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}", encoding="utf-8")
    script = tmp_path / "script.txt"
    script.write_text("synthetic", encoding="utf-8")
    captured = {}

    def check(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            ready=False,
            report_path=manifest.parent / "script-check.json",
            validation=SimpleNamespace(
                issues=(),
                estimated_duration_seconds=12.0,
                script_sha256="b" * 64,
            ),
        )

    monkeypatch.setattr(cli, "check_briefing_script", check)
    args = cli.build_parser().parse_args(
        [
            "check-script",
            "--manifest",
            str(manifest),
            "--script",
            str(script),
        ]
    )

    payload = cli.run_check_script(args)

    assert payload["status"] == "needs_review"
    assert captured["output_root"] == manifest.parents[2]

    shallow = tmp_path / "manifest.json"
    shallow.write_text("{}", encoding="utf-8")
    shallow_args = cli.build_parser().parse_args(
        [
            "check-script",
            "--manifest",
            str(shallow),
            "--script",
            str(script),
        ]
    )
    with pytest.raises(cli.BriefingInputError, match="run"):
        cli.run_check_script(shallow_args)
