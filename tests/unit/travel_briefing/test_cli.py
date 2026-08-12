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
        "list_calibration",
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
    calibrated = parser.parse_args(
        [
            "calibrate-list",
            "--sample",
            "one.doc",
            "--sample",
            "two.doc",
            "--sample",
            "three.docx",
            "--private-dir",
            "private",
            "--pdftoppm",
            "pdftoppm.exe",
        ]
    )

    assert prepared.command == "prepare"
    assert checked.command == "check-script"
    assert rendered.tts == "yating"
    assert calibrated.command == "calibrate-list"
    assert not hasattr(rendered, "template")
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
    with pytest.raises(cli.BriefingInputError):
        parser.parse_args(
            [
                "render",
                "--manifest",
                "manifest.json",
                "--script",
                "script.txt",
                "--template",
                "LIST.doc",
            ]
        )


def test_calibrate_list_cli_uses_exact_three_samples_and_safe_json(
    monkeypatch, capsys, tmp_path
):
    samples = []
    for number in range(1, 4):
        path = tmp_path / f"private-source-{number}.doc"
        path.write_bytes(f"source-{number}".encode())
        samples.append(path)
    pdftoppm = tmp_path / "pdftoppm.exe"
    pdftoppm.write_bytes(b"synthetic")
    private = tmp_path / "new-private"
    captured = {}

    def calibrate(paths, **kwargs):
        captured.update(paths=paths, **kwargs)
        master = private / "LIST-master.docx"
        manifest_path = private / "calibration-manifest.json"
        master.write_bytes(b"master")
        manifest_path.write_text("{}", encoding="utf-8")
        return SimpleNamespace(
            master_path=master,
            manifest_path=manifest_path,
            master_sha256="a" * 64,
            manifest_sha256="b" * 64,
            sample_evidence=tuple(
                SimpleNamespace(
                    source_sha256=character * 64,
                    day_count=day_count,
                )
                for character, day_count in zip("cde", (5, 6, 7))
            ),
            word_version="16.0-synthetic",
        )

    monkeypatch.setattr(cli, "calibrate_list_templates", calibrate)
    exit_code = cli.main(
        [
            "calibrate-list",
            *sum((["--sample", str(path)] for path in samples), []),
            "--private-dir",
            str(private),
            "--pdftoppm",
            str(pdftoppm),
            "--generated-at",
            "2026-08-13T09:00:00+08:00",
            "--format",
            "json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == {
        "schema_version": 1,
        "status": "ok",
        "command": "calibrate-list",
        "master_path": str(private / "LIST-master.docx"),
        "calibration_manifest": str(
            private / "calibration-manifest.json"
        ),
        "master_sha256": "a" * 64,
        "calibration_manifest_sha256": "b" * 64,
        "samples": [
            {"sha256": "c" * 64, "day_count": 5},
            {"sha256": "d" * 64, "day_count": 6},
            {"sha256": "e" * 64, "day_count": 7},
        ],
        "word_version": "16.0-synthetic",
    }
    output = json.dumps(payload)
    assert all(path.name not in output for path in samples)
    assert captured["adapter"].script_path.name == (
        "patch_list_template.ps1"
    )


def test_calibrate_list_rejects_existing_private_dir_before_word(tmp_path):
    private = tmp_path / "private"
    private.mkdir()
    samples = tuple(tmp_path / f"sample-{number}.doc" for number in range(3))
    for sample in samples:
        sample.write_bytes(b"synthetic")
    pdftoppm = tmp_path / "pdftoppm.exe"
    pdftoppm.write_bytes(b"synthetic")
    args = SimpleNamespace(
        sample=samples,
        private_dir=private,
        pdftoppm=pdftoppm,
        generated_at="2026-08-13T09:00:00+08:00",
    )

    with pytest.raises(cli.BriefingInputError, match="must not exist"):
        cli.run_calibrate_list(args)


def test_doctor_preserves_changed_calibration_status_without_private_paths(
    monkeypatch,
):
    private_path = r"C:\private\LIST-master.docx"
    error = cli.BriefingInputError(
        "LIST_RECALIBRATION_REQUIRED",
        {"status": "changed", "path": private_path},
    )
    monkeypatch.setattr(
        cli,
        "load_config",
        lambda _: (_ for _ in ()).throw(error),
    )
    monkeypatch.setattr(cli, "yating_registered", lambda: False)
    monkeypatch.setattr(cli, "hanhan_registered", lambda: False)
    monkeypatch.setattr(cli, "word_com_registered", lambda: False)

    payload = cli.run_doctor(SimpleNamespace(config=None))

    assert payload["checks"]["list_calibration"]["status"] == "changed"
    assert private_path not in json.dumps(payload)


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
