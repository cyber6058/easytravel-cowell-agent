import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from travel_briefing import cli
from travel_briefing import capabilities
from travel_briefing.list_calibration import CalibrationContractError
from travel_briefing.models import DraftStatus
from tests.unit.travel_briefing.test_list_calibration import (
    component_artifact,
    component_result,
    component_samples,
)


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
            "--decision-table",
            "decision-table.json",
            "--normalization-choices",
            "choices.json",
            "--width-base-sample",
            "sample-001",
        ]
    )

    diagnosed = parser.parse_args(
        [
            "diagnose-list-conflicts",
            "--sample",
            "one.doc",
            "--sample",
            "two.doc",
            "--sample",
            "three.docx",
            "--private-dir",
            "private",
        ]
    )
    component_diagnosed = parser.parse_args(
        [
            "diagnose-list-components",
            "--sample", "one.doc",
            "--sample", "two.doc",
            "--sample", "three.docx",
            "--private-dir", "private-components",
        ]
    )
    planned = parser.parse_args(
        [
            "plan-list-normalization",
            "--component-report", "component-report.json",
            "--private-dir", "normalization-plan",
        ]
    )
    choice_prepared = parser.parse_args(
        [
            "prepare-list-normalization-choices",
            "--component-report", "component-report.json",
            "--decision-table", "decision-table.json",
            "--private-dir", "normalization-choices",
        ]
    )
    gate_c_diagnosed = parser.parse_args(
        [
            "diagnose-normalized-gate-c-failure",
            "--sample", "one.doc",
            "--sample", "two.doc",
            "--sample", "three.docx",
            "--decision-table", "decision-table.json",
            "--normalization-choices", "choices.json",
            "--width-base-sample", "sample-001",
            "--private-dir", "gate-c-diagnosis",
        ]
    )
    working_copy_diagnosed = parser.parse_args(
        [
            "diagnose-sample-001-working-copy",
            "--sample", "one.doc",
            "--decision-table", "decision-table.json",
            "--normalization-choices", "choices.json",
            "--private-dir", "working-copy-diagnosis",
        ]
    )

    assert prepared.command == "prepare"
    assert checked.command == "check-script"
    assert rendered.tts == "yating"
    assert calibrated.command == "calibrate-list"
    assert calibrated.width_base_sample == "sample-001"
    assert diagnosed.command == "diagnose-list-conflicts"
    assert component_diagnosed.command == "diagnose-list-components"
    assert planned.command == "plan-list-normalization"
    assert choice_prepared.command == "prepare-list-normalization-choices"
    assert gate_c_diagnosed.command == (
        "diagnose-normalized-gate-c-failure"
    )
    assert not hasattr(gate_c_diagnosed, "pdftoppm")
    assert working_copy_diagnosed.command == (
        "diagnose-sample-001-working-copy"
    )
    assert not hasattr(working_copy_diagnosed, "pdftoppm")
    assert not hasattr(planned, "sample")
    assert not hasattr(choice_prepared, "sample")
    assert not hasattr(diagnosed, "pdftoppm")
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


def test_diagnose_list_conflicts_is_read_only_and_writes_safe_report(
    monkeypatch, capsys, tmp_path
):
    samples = tuple(
        tmp_path / f"private-source-{number}.doc"
        for number in range(3)
    )
    for number, sample in enumerate(samples):
        sample.write_bytes(f"synthetic-{number}".encode())
    private = tmp_path / "new-private"
    matrix = {
        "schema_version": 1,
        "stage": "compare-samples",
        "classification": "TEMPLATE_CONTRACT_CONFLICT",
        "fields": [],
    }

    def diagnose(paths, **kwargs):
        assert paths == samples
        assert kwargs["timeout_seconds"] == 180
        assert kwargs["adapter"].script_path.name == (
            "patch_list_template.ps1"
        )
        return SimpleNamespace(
            word_version="16.0-synthetic",
            source_sha256=("a" * 64, "b" * 64, "c" * 64),
            classification="TEMPLATE_CONTRACT_CONFLICT",
            field_paths=("style_digest",),
            conflict_matrix=matrix,
        )

    monkeypatch.setattr(cli, "diagnose_calibration_conflicts", diagnose)
    monkeypatch.setattr(
        cli,
        "calibrate_list_templates",
        lambda *args, **kwargs: pytest.fail("calibration must not run"),
    )
    exit_code = cli.main(
        [
            "diagnose-list-conflicts",
            *sum((["--sample", str(path)] for path in samples), []),
            "--private-dir",
            str(private),
            "--format",
            "json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    report_path = private / "conflict-diagnosis.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert exit_code == 20
    assert payload == {
        "schema_version": 1,
        "status": "needs_review",
        "command": "diagnose-list-conflicts",
        "classification": "TEMPLATE_CONTRACT_CONFLICT",
        "field_paths": ["style_digest"],
        "report": str(report_path),
    }
    assert report == {
        "schema_version": 1,
        "status": "needs_review",
        "command": "diagnose-list-conflicts",
        "stage": "compare-samples",
        "classification": "TEMPLATE_CONTRACT_CONFLICT",
        "word_version": "16.0-synthetic",
        "source_sha256": ["a" * 64, "b" * 64, "c" * 64],
        "field_paths": ["style_digest"],
        "conflict_matrix": matrix,
    }
    serialized = json.dumps(report)
    assert all(sample.name not in serialized for sample in samples)
    assert not (private / "LIST-master.docx").exists()
    assert not (private / "calibration-manifest.json").exists()


def test_diagnose_list_conflicts_rejects_existing_private_dir_before_word(
    monkeypatch, tmp_path
):
    samples = tuple(tmp_path / f"sample-{number}.doc" for number in range(3))
    for sample in samples:
        sample.write_bytes(b"synthetic")
    private = tmp_path / "private"
    private.mkdir()
    monkeypatch.setattr(
        cli,
        "diagnose_calibration_conflicts",
        lambda *args, **kwargs: pytest.fail("Word inspection must not run"),
    )

    with pytest.raises(cli.BriefingInputError, match="must not exist"):
        cli.run_diagnose_list_conflicts(
            SimpleNamespace(sample=samples, private_dir=private)
        )


def test_diagnose_list_components_writes_only_safe_private_report(
    monkeypatch, capsys, tmp_path
):
    samples = tuple(tmp_path / f"private-{index}.doc" for index in range(3))
    for sample in samples:
        sample.write_bytes(b"synthetic")
    private = tmp_path / "components"
    evidence = {
        "styles": [], "fonts": [], "paragraphs": [], "borders": [],
        "daily_header": [], "daily_body": [], "shapes": [],
    }

    def diagnose(paths, **kwargs):
        assert paths == samples
        assert kwargs["timeout_seconds"] == 120
        return SimpleNamespace(
            word_version="16.0-synthetic",
            source_sha256=("a" * 64, "b" * 64, "c" * 64),
            samples=(evidence, evidence, evidence),
        )

    monkeypatch.setattr(cli, "diagnose_list_components", diagnose)
    monkeypatch.setattr(
        cli,
        "calibrate_list_templates",
        lambda *args, **kwargs: pytest.fail("calibration must not run"),
    )

    exit_code = cli.main([
        "diagnose-list-components",
        *sum((["--sample", str(path)] for path in samples), []),
        "--private-dir", str(private),
        "--format", "json",
    ])

    report_path = private / "component-diagnosis.json"
    payload = json.loads(capsys.readouterr().out)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["report"] == str(report_path)
    assert report["samples"] == [evidence, evidence, evidence]
    serialized = json.dumps(report)
    assert all(sample.name not in serialized for sample in samples)
    assert not (private / "LIST-master.docx").exists()


def test_plan_list_normalization_is_offline_and_exclusive(
    monkeypatch, capsys, tmp_path
):
    component_report = tmp_path / "component-report.json"
    component_report.write_text("{}", encoding="utf-8")
    private = tmp_path / "normalization-plan"
    diagnosis = SimpleNamespace(source_sha256=("a" * 64,) * 3)
    table = {
        "schema_version": 1,
        "stage": "component-normalization-decision",
        "classification": "REQUIRES_OP_DECISION",
        "source_sha256": ["a" * 64, "b" * 64, "c" * 64],
        "policy": {},
        "preserved_unanimous_counts": {},
        "decisions": [],
        "derived_audits": [],
        "blockers": [],
    }

    def load(path):
        assert path == component_report.resolve()
        return diagnosis

    monkeypatch.setattr(cli, "load_component_diagnosis_artifact", load)
    monkeypatch.setattr(
        cli,
        "build_component_normalization_decision_table",
        lambda value: table if value is diagnosis else pytest.fail(),
    )
    monkeypatch.setattr(
        cli,
        "component_normalization_decision_table_sha256",
        lambda value: "d" * 64 if value is table else pytest.fail(),
    )
    monkeypatch.setattr(
        cli,
        "diagnose_list_components",
        lambda *args, **kwargs: pytest.fail("Word must not run"),
    )
    monkeypatch.setattr(
        cli,
        "calibrate_list_templates",
        lambda *args, **kwargs: pytest.fail("calibration must not run"),
    )

    exit_code = cli.main([
        "plan-list-normalization",
        "--component-report", str(component_report),
        "--private-dir", str(private),
        "--format", "json",
    ])

    report_path = private / "normalization-decision-table.json"
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 20
    assert json.loads(report_path.read_text(encoding="utf-8")) == table
    assert payload == {
        "schema_version": 1,
        "status": "needs_review",
        "command": "plan-list-normalization",
        "classification": "REQUIRES_OP_DECISION",
        "decision_table_sha256": "d" * 64,
        "report": str(report_path),
    }
    assert not (private / "LIST-master.docx").exists()


def test_plan_list_normalization_rejects_existing_private_dir_before_read(
    monkeypatch, tmp_path
):
    component_report = tmp_path / "component-report.json"
    component_report.write_text("{}", encoding="utf-8")
    private = tmp_path / "existing"
    private.mkdir()
    monkeypatch.setattr(
        cli,
        "load_component_diagnosis_artifact",
        lambda *args: pytest.fail("report must not be read"),
    )

    with pytest.raises(cli.BriefingInputError, match="must not exist"):
        cli.run_plan_list_normalization(SimpleNamespace(
            component_report=component_report,
            private_dir=private,
        ))


def test_plan_list_normalization_accepts_strict_synthetic_report(
    monkeypatch, capsys, tmp_path
):
    component_report = tmp_path / "component-report.json"
    component_report.write_text(
        json.dumps(component_artifact(component_samples())),
        encoding="utf-8",
    )
    private = tmp_path / "normalization-plan"
    monkeypatch.setattr(
        cli,
        "diagnose_list_components",
        lambda *args, **kwargs: pytest.fail("Word must not run"),
    )
    monkeypatch.setattr(
        cli,
        "calibrate_list_templates",
        lambda *args, **kwargs: pytest.fail("calibration must not run"),
    )

    exit_code = cli.main([
        "plan-list-normalization",
        "--component-report", str(component_report),
        "--private-dir", str(private),
        "--format", "json",
    ])

    payload = json.loads(capsys.readouterr().out)
    table = json.loads(
        (private / "normalization-decision-table.json").read_text(
            encoding="utf-8"
        )
    )
    assert exit_code == 0
    assert payload["classification"] == "NORMALIZATION_READY"
    assert table["classification"] == "NORMALIZATION_READY"
    assert table["decisions"] == []


def test_prepare_normalization_choices_writes_only_offline_review_artifacts(
    monkeypatch, capsys, tmp_path
):
    samples = component_samples()
    samples[2]["fonts"][9]["size_points"] = 12.0
    diagnosis = component_result(*samples)
    table = cli.build_component_normalization_decision_table(diagnosis)
    component_report = tmp_path / "component-report.json"
    component_report.write_text(
        json.dumps(component_artifact(samples)), encoding="utf-8"
    )
    decision_table = tmp_path / "decision-table.json"
    decision_table.write_text(json.dumps(table), encoding="utf-8")
    private = tmp_path / "normalization-choices"
    monkeypatch.setattr(
        cli,
        "diagnose_list_components",
        lambda *args, **kwargs: pytest.fail("Word must not run"),
    )
    monkeypatch.setattr(
        cli,
        "calibrate_list_templates",
        lambda *args, **kwargs: pytest.fail("calibration must not run"),
    )

    exit_code = cli.main([
        "prepare-list-normalization-choices",
        "--component-report", str(component_report),
        "--decision-table", str(decision_table),
        "--private-dir", str(private),
        "--format", "json",
    ])

    payload = json.loads(capsys.readouterr().out)
    worksheet = json.loads(
        (private / "normalization-choice-worksheet.json").read_text(
            encoding="utf-8"
        )
    )
    blank = json.loads(
        (private / "normalization-choices.blank.json").read_text(
            encoding="utf-8"
        )
    )
    assert exit_code == 20
    assert payload["status"] == "needs_review"
    assert payload["decision_count"] == 1
    assert worksheet["decisions"][0]["options"][2]["safe_values"] == {
        "size_points": 12.0
    }
    assert blank["choices"][0]["selected_source_sha256"] == ""
    assert not (private / "LIST-master.docx").exists()


def test_prepare_normalization_choices_rejects_existing_dir_before_read(
    monkeypatch, tmp_path
):
    component_report = tmp_path / "component-report.json"
    decision_table = tmp_path / "decision-table.json"
    component_report.write_text("{}", encoding="utf-8")
    decision_table.write_text("{}", encoding="utf-8")
    private = tmp_path / "existing"
    private.mkdir()
    monkeypatch.setattr(
        cli,
        "load_component_diagnosis_artifact",
        lambda *args: pytest.fail("component report must not be read"),
    )
    monkeypatch.setattr(
        cli,
        "load_component_normalization_decision_table",
        lambda *args: pytest.fail("decision table must not be read"),
    )

    with pytest.raises(cli.BriefingInputError, match="must not exist"):
        cli.run_prepare_list_normalization_choices(SimpleNamespace(
            component_report=component_report,
            decision_table=decision_table,
            private_dir=private,
        ))


def test_normalized_gate_c_failure_diagnosis_is_read_only_and_safe(
    monkeypatch, capsys, tmp_path
):
    samples = []
    for index in range(3):
        path = tmp_path / f"sample-{index}.doc"
        path.write_bytes(f"source-{index}".encode())
        samples.append(path)
    hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in samples]
    decision_table = tmp_path / "decision-table.json"
    choices_path = tmp_path / "choices.json"
    decision_table.write_text("{}", encoding="utf-8")
    choices_path.write_text("{}", encoding="utf-8")
    private = tmp_path / "diagnosis"
    table = {"source_sha256": hashes}
    validated_choices = {"choices": []}
    monkeypatch.setattr(
        cli, "load_component_normalization_decision_table", lambda path: table
    )
    monkeypatch.setattr(
        cli,
        "validate_component_normalization_choices",
        lambda observed_table, artifact: validated_choices,
    )
    monkeypatch.setattr(
        cli,
        "inspect_list_templates_v2",
        lambda *args, **kwargs: SimpleNamespace(
            samples=("safe-inspection",),
            word_version="16.0-synthetic",
        ),
    )
    monkeypatch.setattr(
        cli,
        "compare_calibration_samples_with_normalization",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            ValueError("calibration samples have no common normal profile")
        ),
    )
    monkeypatch.setattr(
        cli,
        "calibrate_list_templates",
        lambda *args, **kwargs: pytest.fail("calibration must not run"),
    )

    exit_code = cli.main([
        "diagnose-normalized-gate-c-failure",
        *sum((["--sample", str(path)] for path in samples), []),
        "--decision-table", str(decision_table),
        "--normalization-choices", str(choices_path),
        "--width-base-sample", "sample-001",
        "--private-dir", str(private),
        "--format", "json",
    ])

    payload = json.loads(capsys.readouterr().out)
    report = json.loads(
        (private / "normalized-gate-c-failure-diagnosis.json").read_text(
            encoding="utf-8"
        )
    )
    assert exit_code == 20
    assert payload["classification"] == "ERROR_OBSERVED"
    assert report["stage"] == "compare-normalized-layout"
    assert report["error"] == {
        "exception_type": "ValueError",
        "error_code": "NO_COMMON_NORMAL_PROFILE",
        "field_paths": [],
    }
    assert "source_path" not in json.dumps(report)
    assert not (private / "LIST-master.docx").exists()


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


def test_calibrate_list_contract_conflict_writes_safe_exclusive_review(
    monkeypatch, capsys, tmp_path
):
    samples = tuple(
        tmp_path / f"private-source-{number}.doc"
        for number in range(3)
    )
    for number, sample in enumerate(samples):
        sample.write_bytes(f"synthetic-{number}".encode())
    pdftoppm = tmp_path / "pdftoppm.exe"
    pdftoppm.write_bytes(b"synthetic")
    private = tmp_path / "new-private"
    conflict_matrix = {
        "schema_version": 1,
        "stage": "compare-samples",
        "classification": "TEMPLATE_CONTRACT_CONFLICT",
        "fields": [
            {
                "field_path": "style_digest",
                "normalization_status": "REQUIRES_OP_DECISION",
                "samples": [
                    {
                        "source_sha256": "a" * 64,
                        "normalized_digest": "b" * 64,
                    }
                ],
            }
        ],
    }

    def conflict(paths, **kwargs):
        kwargs["on_stage"]("inspect-samples")
        kwargs["on_stage"]("compare-samples")
        raise CalibrationContractError(
            ("margins_points", "style_digest"),
            conflict_matrix=conflict_matrix,
        )

    monkeypatch.setattr(cli, "calibrate_list_templates", conflict)
    exit_code = cli.main(
        [
            "calibrate-list",
            *sum((["--sample", str(path)] for path in samples), []),
            "--private-dir",
            str(private),
            "--pdftoppm",
            str(pdftoppm),
            "--generated-at",
            "2026-08-14T12:00:00+08:00",
            "--format",
            "json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    review_path = private / "calibration-review.json"
    review = json.loads(review_path.read_text(encoding="utf-8"))
    assert exit_code == 20
    assert payload["error"]["code"] == "CALIBRATION_CONTRACT_CONFLICT"
    assert payload["error"]["details"] == {
        "stage": "compare-samples",
        "field_paths": ["margins_points", "style_digest"],
        "review": str(review_path),
    }
    assert review == {
        "schema_version": 1,
        "status": "needs_review",
        "error_code": "CALIBRATION_CONTRACT_CONFLICT",
        "stage": "compare-samples",
        "source_sha256": [
            hashlib.sha256(sample.read_bytes()).hexdigest()
            for sample in samples
        ],
        "field_paths": ["margins_points", "style_digest"],
        "conflict_matrix": conflict_matrix,
    }
    serialized = json.dumps(review)
    assert all(sample.name not in serialized for sample in samples)
    assert not (private / "LIST-master.docx").exists()
    assert not (private / "calibration-manifest.json").exists()


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


def test_working_copy_diagnosis_writes_only_private_safe_report(
    monkeypatch,
    capsys,
    tmp_path,
):
    sample = tmp_path / "private-sample-name.doc"
    sample.write_bytes(b"synthetic sample")
    source_hash = hashlib.sha256(sample.read_bytes()).hexdigest()
    decision_table = tmp_path / "decision-table.json"
    decision_table.write_text("{}", encoding="utf-8")
    choices_path = tmp_path / "choices.json"
    choices_path.write_text("{}", encoding="utf-8")
    private = tmp_path / "private-report"

    monkeypatch.setattr(
        cli,
        "load_component_normalization_decision_table",
        lambda _: {
            "source_sha256": [source_hash, "b" * 64, "c" * 64],
        },
    )
    monkeypatch.setattr(
        cli,
        "validate_component_normalization_choices",
        lambda _table, _choices: {
            "choices": [
                {"selected_source_sha256": source_hash},
                {"selected_source_sha256": source_hash},
            ],
        },
    )
    monkeypatch.setattr(
        cli,
        "diagnose_normalized_working_copy",
        lambda *_args, **_kwargs: {
            "word_version": "16.0",
            "source_sha256": source_hash,
            "classification": "NOT_REPRODUCED",
            "checkpoint": {
                "phase": "calibrate-copy",
                "operation": "complete",
            },
            "error": None,
            "source_hash_unchanged": True,
            "working_copy_cleaned": True,
        },
    )
    monkeypatch.setattr(
        cli,
        "calibrate_list_templates",
        lambda *_args, **_kwargs: pytest.fail("must not calibrate or publish"),
    )

    exit_code = cli.main(
        [
            "diagnose-sample-001-working-copy",
            "--sample",
            str(sample),
            "--decision-table",
            str(decision_table),
            "--normalization-choices",
            str(choices_path),
            "--private-dir",
            str(private),
            "--format",
            "json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    report_path = private / "sample-001-working-copy-diagnosis.json"
    report_text = report_path.read_text(encoding="utf-8")
    assert exit_code == 20
    assert payload["classification"] == "NOT_REPRODUCED"
    assert list(private.iterdir()) == [report_path]
    assert not tuple(private.rglob("*.doc*"))
    assert "manifest" not in report_text.casefold()
    assert sample.name not in report_text
    assert str(sample) not in report_text


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
