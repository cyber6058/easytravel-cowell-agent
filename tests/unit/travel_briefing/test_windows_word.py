import hashlib
import json
import subprocess
from pathlib import Path

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


PATCH_SCRIPT = (
    Path(__file__).parents[3]
    / "scripts"
    / "briefing"
    / "patch_list_template.ps1"
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


def schema_two_job(tmp_path, *, action="inspect-v2", extra=None):
    payload = {
        "schema_version": 2,
        "action": action,
        "ownership_nonce": "a" * 32,
        "word_pid_path": str((tmp_path / "word-owner.json").resolve()),
        "report_path": str((tmp_path / "report.json").resolve()),
    }
    if action in {
        "inspect-v2",
        "diagnose-header-v2",
        "diagnose-components-v2",
        "diagnose-5992-v2",
        "diagnose-gate-c-v3",
    }:
        payload["sample_paths"] = [
            str((tmp_path / f"sample-{index}.doc").resolve())
            for index in range(1, 4)
        ]
        for item in payload["sample_paths"]:
            Path(item).write_bytes(b"synthetic")
        if action in {"diagnose-5992-v2", "diagnose-gate-c-v3"}:
            payload["sample_sha256"] = [str(index) * 64 for index in range(1, 4)]
            payload["working_copy_paths"] = [
                str((tmp_path / f"working-{index}.doc").resolve())
                for index in range(1, 4)
            ]
    elif action == "diagnose-normalized-copy-v2":
        source = tmp_path / "sample.doc"
        source.write_bytes(b"synthetic")
        payload |= {
            "source_path": str(source.resolve()),
            "source_sha256": hashlib.sha256(
                source.read_bytes()
            ).hexdigest(),
            "working_copy_path": str(
                (tmp_path / "working.doc").resolve()
            ),
        }
    else:
        source = tmp_path / "sample.doc"
        source.write_bytes(b"synthetic")
        payload |= {
            "source_path": str(source.resolve()),
            "working_copy_path": str(
                (tmp_path / "working.doc").resolve()
            ),
            "output_docx": str((tmp_path / "master.docx").resolve()),
        }
    payload.update(extra or {})
    path = tmp_path / "word-job-v2.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
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


def test_word_adapter_exposes_only_allowlisted_failure_diagnostics(tmp_path):
    runner = WordRunner(
        return_code=30,
        stderr=(
            "private content must be ignored\n"
            "WORD_ADAPTER_ERROR stage=bind-owner hresult=-2147352573 "
            "code=NONE\n"
        ),
    )
    word = adapter(tmp_path, runner)

    with pytest.raises(WordGenerationError) as captured:
        word.run(job(tmp_path), timeout_seconds=90)

    assert captured.value.details == {
        "return_code": 30,
        "stage": "bind-owner",
        "hresult": -2147352573,
        "adapter_code": "NONE",
    }


def test_word_adapter_ignores_malformed_failure_diagnostics(tmp_path):
    word = adapter(
        tmp_path,
        WordRunner(
            return_code=30,
            stderr="WORD_ADAPTER_ERROR stage=bind-owner secret=private",
        ),
    )

    with pytest.raises(WordGenerationError) as captured:
        word.run(job(tmp_path), timeout_seconds=90)

    assert captured.value.details == {"return_code": 30}


def test_word_scripts_bind_owned_pid_through_a_temporary_word_window():
    project_root = Path(__file__).parents[3]
    for relative in (
        Path("scripts/briefing/patch_list_template.ps1"),
        Path("scripts/briefing/render_list_template.ps1"),
    ):
        script = (project_root / relative).read_text(encoding="utf-8")
        assert "$Word.Hwnd" not in script
        assert "$Word.Documents.Add()" in script
        assert "$ownershipDocument.ActiveWindow" in script
        assert "$ownershipWindow.Hwnd" in script
        assert "$ownershipDocument.Close($false)" in script


def test_daily_row_resize_reconciles_formatted_text_row_side_effect():
    script = PATCH_SCRIPT.read_text(encoding="utf-8")
    function = script.split("function Set-DailyRowCount {", 1)[1].split(
        "function Set-ListLayoutProfile {", 1
    )[0]

    assert function.count(
        "while ($Table.Rows.Count -gt $targetRows)"
    ) == 2
    assert 'throw "LIST_DAILY_ROW_RESIZE_FAILED"' in function


def test_header_patch_preserves_paragraph_and_cell_terminators():
    script = PATCH_SCRIPT.read_text(encoding="utf-8")
    function = script.split("function Set-HeaderParagraph {", 1)[1].split(
        "function Set-ListCell {", 1
    )[0]

    assert '$paragraph.Range.Text = ([string]$Patch.text) + "`r"' not in function
    assert "$visibleRange.End = $visibleEnd" in function
    assert "$visibleRange.Text = [string]$Patch.text" in function


def test_header_patch_preserves_the_qr_anchored_title_paragraph():
    script = PATCH_SCRIPT.read_text(encoding="utf-8")
    function = script.split("function Set-HeaderParagraph {", 1)[1].split(
        "function Set-ListCell {", 1
    )[0]

    assert "if ($number -eq 1)" in function
    assert 'throw "LIST_HEADER_TITLE_CHANGED"' in function
    assert "return" in function.split("if ($number -eq 1)", 1)[1].split(
        "$visibleRange = $null", 1
    )[0]


def test_continuation_header_uses_first_page_header_policy_not_if_fields():
    script = PATCH_SCRIPT.read_text(encoding="utf-8")
    function = script.split("function Add-ContinuationGroupHeader {", 1)[
        1
    ].split("function Get-DayPageMap {", 1)[0]

    assert "$section.PageSetup.DifferentFirstPageHeaderFooter = $true" in function
    assert "$WdHeaderFooterPrimary" in function
    assert "$WdHeaderFooterFirstPage" in function
    assert ".Fields.Add(" not in function


def test_patch_report_measures_pagination_after_save_as():
    script = PATCH_SCRIPT.read_text(encoding="utf-8")
    function = script.split("function Invoke-Patch {", 1)[1].split(
        "function Invoke-Action {", 1
    )[0]
    save = function.index("$document.SaveAs2($outputDocx")
    day_map = function.index("$dayPageMap = Get-DayPageMap")
    reopen = function.index(
        "$document = $Word.Documents.Open($outputDocx, $false, $true)",
        save,
        day_map,
    )
    final_repaginate = function.rindex(
        "$document.Repaginate()", reopen, day_map
    )
    final_page_count = function.rindex(
        "$pageCount = [int]$document.ComputeStatistics", reopen, day_map
    )

    assert save < reopen < final_repaginate < final_page_count < day_map


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


@pytest.mark.parametrize(
    "action",
    [
        "inspect-v2",
        "diagnose-header-v2",
        "diagnose-components-v2",
        "diagnose-5992-v2",
        "diagnose-gate-c-v3",
        "diagnose-normalized-copy-v2",
        "calibrate",
    ],
)
def test_schema_two_word_jobs_accept_only_the_exact_bounded_shape(
    tmp_path, action
):
    runner = WordRunner()
    word = adapter(tmp_path, runner)

    word.run(schema_two_job(tmp_path, action=action), timeout_seconds=90)

    assert len(runner.calls) == 1
    with pytest.raises(WordGenerationError, match="schema version 2"):
        word.run(
            schema_two_job(
                tmp_path,
                action=action,
                extra={"private_document_text": "must not be accepted"},
            ),
            timeout_seconds=90,
        )
    assert len(runner.calls) == 1


@pytest.mark.parametrize(
    "sample_paths",
    [
        ["one.doc", "two.doc"],
        ["one.doc", "two.doc", "three.pdf"],
        ["one.doc", "one.doc", "three.doc"],
    ],
)
def test_inspect_v2_requires_exactly_three_unique_resolved_word_paths(
    tmp_path, sample_paths
):
    path = schema_two_job(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["sample_paths"] = sample_paths
    path.write_text(json.dumps(payload), encoding="utf-8")
    word = adapter(tmp_path, WordRunner())

    with pytest.raises(WordGenerationError, match="schema version 2"):
        word.run(path, timeout_seconds=90)


def test_calibration_preserves_fixed_header_labels_when_values_are_cleared():
    script = PATCH_SCRIPT.read_text(encoding="utf-8")
    calibrate = script.split("function Invoke-Calibrate", 1)[1].split(
        "function Invoke-Patch", 1
    )[0]

    assert "for ($paragraphNumber = 2; $paragraphNumber -le 3;" in calibrate
    assert "LIST_HEADER_LABEL_MISSING" in calibrate
    assert "$originalText.Substring(0, $labelBreak + 1)" in calibrate
    assert "Set-NormalizedHeaderDynamicTail -HeaderCell $headerCell" in calibrate


def test_calibration_normalizes_only_the_approved_header_tail():
    script = PATCH_SCRIPT.read_text(encoding="utf-8")
    inspection = script.split("function Get-ListInspectionV2", 1)[1].split(
        "function Assert-BasicListContract", 1
    )[0]
    contract = script.split(
        "function Assert-NormalizableHeaderParagraphContract", 1
    )[1].split("function Set-NormalizedHeaderDynamicTail", 1)[0]
    normalization = script.split(
        "function Set-NormalizedHeaderDynamicTail", 1
    )[1].split("function Set-TokenHighlight", 1)[0]

    assert "-AllowVariableHeaderTail" in inspection
    assert "list_header_paragraph_count = 4" in inspection
    assert "Paragraphs.Item(2)" in contract
    assert "Paragraphs.Item(3)" in contract
    assert "LIST_HEADER_DYNAMIC_TAIL_UNSAFE" in contract
    assert "$number = 4" in contract
    assert "Paragraphs.Item(4).Range.Start" in normalization
    assert "$HeaderCell.Range.End - 1" in normalization
    assert '$tailRange.Text = ""' in normalization
    assert "$observedParagraphCount" in normalization
    assert '-Operation "header-tail-postcondition"' in normalization
    assert "-ParagraphNumber $observedParagraphCount" in normalization
    assert "LIST_HEADER_NORMALIZATION_FAILED" in normalization


def test_schema_two_width_fingerprint_uses_fixed_prototype_cells():
    script = PATCH_SCRIPT.read_text(encoding="utf-8")
    helper = script.split("function Get-PrototypeColumnWidths", 1)[1].split(
        "function Get-ListInspectionV2", 1
    )[0]
    inspection = script.split("function Get-ListInspectionV2", 1)[1].split(
        "function Assert-BasicListContract", 1
    )[0]

    assert "$prototypeRows = @(2, 2, 2, 1)" in helper
    assert "$prototypeColumnCounts = @(3, 6, 7, 3)" in helper
    assert '-Operation "table-width-prototype-cell"' in helper
    assert "Get-Cell" in helper
    assert "$cell.Width" in helper
    assert ".Columns.Item(" not in helper
    assert ".Columns.Item(" not in inspection
    assert "Get-PrototypeColumnWidths" in inspection


def test_schema_two_format_fingerprint_uses_fixed_prototype_cells():
    script = PATCH_SCRIPT.read_text(encoding="utf-8")
    helper = script.split("function Get-PrototypeCellFormatEvidence", 1)[1].split(
        "function Get-ListInspectionV2", 1
    )[0]
    inspection = script.split("function Get-ListInspectionV2", 1)[1].split(
        "function Assert-BasicListContract", 1
    )[0]

    assert "Get-Cell" in helper
    assert "$cell.Range" in helper
    assert ".Rows.Item(" not in helper
    assert "$prototypeRows = @(2, 2, 2, 1)" in inspection
    assert "$prototypeColumnCounts = @(3, 6, 7, 3)" in inspection
    assert '-Operation "table-format-prototype-cell"' in inspection
    assert '-Operation "daily-header-prototype-cell"' in inspection
    assert '-Operation "daily-body-prototype-cell"' in inspection
    assert "Get-PrototypeCellFormatEvidence" in inspection
    assert ".Rows.Item(" not in inspection


def test_schema_two_border_fingerprint_uses_fixed_prototype_cells_and_types():
    script = PATCH_SCRIPT.read_text(encoding="utf-8")
    helper = script.split("function Get-PrototypeCellBorderEvidence", 1)[1].split(
        "function Get-ListInspectionV2", 1
    )[0]
    inspection = script.split("function Get-ListInspectionV2", 1)[1].split(
        "function Assert-BasicListContract", 1
    )[0]

    assert "@(-1, -2, -3, -4, -7, -8)" in helper
    assert '"cell-border-top"' in helper
    assert '"cell-border-left"' in helper
    assert '"cell-border-bottom"' in helper
    assert '"cell-border-right"' in helper
    assert '"cell-border-diagonal-down"' in helper
    assert '"cell-border-diagonal-up"' in helper
    assert "Get-Cell" in helper
    assert "$cell.Borders.Item($borderType)" in helper
    assert "$table.Borders" not in inspection
    assert "foreach ($border in" not in inspection
    assert "Get-PrototypeCellBorderEvidence" in inspection


def test_5992_diagnosis_is_one_reported_job_without_master_output():
    script = PATCH_SCRIPT.read_text(encoding="utf-8")
    diagnosis = script.split("function Invoke-DiagnoseGateC", 1)[1].split(
        "function Invoke-Calibrate", 1
    )[0]
    calibration = script.split("function Invoke-Calibrate", 1)[1].split(
        "function Invoke-Patch", 1
    )[0]

    assert "action = [string]$Job.action" in diagnosis
    assert '"diagnose-5992-v2"' in script.split('$stage = "run-action"', 1)[1]
    assert "Invoke-Calibrate" in diagnosis
    assert "-DiagnosticOnly" in diagnosis
    assert "Write-JsonExclusive" in diagnosis
    assert "source_path" not in diagnosis.split("Write-JsonExclusive", 1)[1]
    assert "if ($DiagnosticOnly)" in calibration
    assert "$document.SaveAs2" in calibration.split("if ($DiagnosticOnly)", 1)[1]


def test_gate_c_v3_diagnosis_reuses_safe_checkpoint_report_boundary():
    script = PATCH_SCRIPT.read_text(encoding="utf-8")
    diagnosis = script.split("function Invoke-DiagnoseGateC", 1)[1].split(
        "function Invoke-Calibrate", 1
    )[0]
    dispatch = script.split('$stage = "run-action"', 1)[1]

    assert '"diagnose-gate-c-v3"' in dispatch
    assert "Invoke-DiagnoseGateC" in dispatch
    assert "checkpoint = $checkpointSnapshot" in diagnosis
    assert "source_path" not in diagnosis.split("Write-JsonExclusive", 1)[1]


def test_component_diagnosis_is_read_only_and_emits_no_word_text():
    script = PATCH_SCRIPT.read_text(encoding="utf-8")
    diagnosis = script.split("function Invoke-DiagnoseComponentsV2", 1)[1].split(
        "function Invoke-DiagnoseGateC", 1
    )[0]
    evidence = script.split("function Get-CellComponentEvidence", 1)[1].split(
        "function Get-ListInspectionV2", 1
    )[0]

    assert '"diagnose-components-v2"' in script
    assert "$false, $true" in diagnosis
    assert "Documents.Open" in diagnosis
    assert "Save" not in diagnosis
    assert ".Text" not in evidence
    assert "source_path" not in diagnosis
    assert "name_sha256" in evidence
    assert "shape_id" in evidence
