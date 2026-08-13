from __future__ import annotations

import json
import hashlib
from pathlib import Path
from dataclasses import replace

import pytest

from travel_briefing.list_calibration import (
    CalibrationContractError,
    ListCalibrationManifest,
    ListCalibrationSample,
    ListLayoutProfile,
    ListTemplateInspectionV2,
    build_calibration_manifest,
    calibrate_list_templates,
    compare_calibration_samples,
    diagnose_gate_c_5992,
    diagnose_list_header_contract,
    manifest_sha256,
    normalized_structure_fingerprint,
    select_base_sample,
    validate_calibrated_master,
)
from travel_briefing.template_contract import (
    A4_HEIGHT_POINTS,
    A4_WIDTH_POINTS,
    LIST_ANCHOR_LABELS,
    LIST_HEADER_ACCESSIBLE_CELLS,
    TableShape,
)


def digest(seed: str) -> str:
    return (seed.encode("utf-8").hex() + "0" * 64)[:64]


def profile(
    name: str = "normal",
    *,
    font: float = 10.0,
    spacing: float = 12.0,
) -> ListLayoutProfile:
    return ListLayoutProfile(
        name=name,
        body_font_points=font,
        line_spacing_points=spacing,
        paragraph_space_after_points=1.0,
        cell_top_margin_points=1.4,
        cell_bottom_margin_points=1.4,
    )


def inspection(
    day_count: int = 6,
    *,
    dynamic_seed: str = "group-a",
    profiles: tuple[ListLayoutProfile, ...] | None = None,
) -> ListTemplateInspectionV2:
    return ListTemplateInspectionV2(
        day_count=day_count,
        table_shapes=(
            TableShape(4, 3),
            TableShape(3, 6),
            TableShape(day_count + 1, 7),
            TableShape(1, 3),
        ),
        anchor_labels=LIST_ANCHOR_LABELS,
        list_header_accessible_cells=LIST_HEADER_ACCESSIBLE_CELLS,
        list_header_paragraph_count=4,
        section_count=1,
        page_width_points=A4_WIDTH_POINTS,
        page_height_points=A4_HEIGHT_POINTS,
        orientation="portrait",
        margins_points=(36.0, 31.5, 36.0, 31.5),
        header_distance_points=18.0,
        footer_distance_points=18.0,
        table_column_widths_points=(
            (180.0, 180.0, 180.0),
            (90.0, 90.0, 90.0, 90.0, 90.0, 90.0),
            (54.0, 72.0, 108.0, 90.0, 72.0, 72.0, 72.0),
            (180.0, 180.0, 180.0),
        ),
        merged_cell_map=("table-1:r1c1-r1c3", "table-1:r4c2-r4c3"),
        qr_shape_count=1,
        shape_geometry_points=(("qr", 500.0, 12.0, 42.0, 42.0),),
        style_digest=digest("style"),
        font_digest=digest("font"),
        paragraph_digest=digest("paragraph"),
        border_digest=digest("border"),
        shading_digest=digest("shading"),
        daily_header_digest=digest("daily-header"),
        daily_body_prototype_digest=digest("daily-body"),
        dynamic_content_digest=digest(dynamic_seed),
        adaptive_profiles=profiles
        or (profile(), profile("compact", font=9.0, spacing=10.5)),
    )


def sample(source_hash: str, observed: ListTemplateInspectionV2) -> ListCalibrationSample:
    return ListCalibrationSample.from_inspection(source_hash, observed)


def test_schema_two_inspection_round_trips_all_layout_evidence():
    observed = inspection()

    payload = observed.to_dict()
    restored = ListTemplateInspectionV2.from_dict(payload)

    assert payload["schema_version"] == 2
    assert restored == observed
    assert restored.margins_points == (36.0, 31.5, 36.0, 31.5)
    assert restored.table_shapes[2] == TableShape(7, 7)
    assert restored.shape_geometry_points[0][0] == "qr"
    for required in (
        "style_digest",
        "font_digest",
        "paragraph_digest",
        "border_digest",
        "shading_digest",
    ):
        assert payload[required]

    missing = dict(payload)
    missing.pop("merged_cell_map")
    with pytest.raises(ValueError, match="schema version 2"):
        ListTemplateInspectionV2.from_dict(missing)


def test_normalized_fingerprint_ignores_rows_content_and_adaptive_profiles():
    original = inspection(5, dynamic_seed="private-group-a")
    allowed_variant = inspection(
        12,
        dynamic_seed="private-group-b",
        profiles=(profile(font=10.25), profile("compact", font=8.75)),
    )

    assert normalized_structure_fingerprint(original) == (
        normalized_structure_fingerprint(allowed_variant)
    )

    structural_variants = (
        replace(original, margins_points=(37.0, 31.5, 36.0, 31.5)),
        replace(
            original,
            table_column_widths_points=(
                original.table_column_widths_points[0],
                original.table_column_widths_points[1],
                (55.0, 71.0, 108.0, 90.0, 72.0, 72.0, 72.0),
                original.table_column_widths_points[3],
            ),
        ),
        replace(original, merged_cell_map=("table-1:r1c1-r1c2",)),
        replace(
            original,
            qr_shape_count=2,
            shape_geometry_points=original.shape_geometry_points
            + (("qr-2", 450.0, 12.0, 42.0, 42.0),),
        ),
        replace(original, style_digest=digest("changed-style")),
    )
    assert all(
        normalized_structure_fingerprint(changed)
        != normalized_structure_fingerprint(original)
        for changed in structural_variants
    )


def test_comparison_allows_only_declared_adaptive_differences():
    samples = (
        sample("1" * 64, inspection(5, dynamic_seed="a")),
        sample(
            "2" * 64,
            inspection(
                6,
                dynamic_seed="b",
                profiles=(profile(font=10.5), profile("compact", font=9.25)),
            ),
        ),
        sample("3" * 64, inspection(8, dynamic_seed="c")),
    )

    compared = compare_calibration_samples(samples)

    assert compared.base_sample_sha256 == "2" * 64
    assert compared.normalized_structure_fingerprint == (
        samples[0].normalized_structure_fingerprint
    )

    changed = replace(
        samples[2].inspection,
        table_column_widths_points=(
            samples[2].inspection.table_column_widths_points[0],
            samples[2].inspection.table_column_widths_points[1],
            (55.0, 71.0, 108.0, 90.0, 72.0, 72.0, 72.0),
            samples[2].inspection.table_column_widths_points[3],
        ),
    )
    conflicting = samples[:2] + (sample("3" * 64, changed),)

    with pytest.raises(CalibrationContractError) as captured:
        compare_calibration_samples(conflicting)

    assert captured.value.code == "CALIBRATION_CONTRACT_CONFLICT"
    assert "table_column_widths_points" in captured.value.field_paths
    assert "private-group" not in str(captured.value)


def test_base_selection_uses_median_day_then_lowest_hash():
    samples = (
        sample("f" * 64, inspection(5)),
        sample("b" * 64, inspection(6)),
        sample("a" * 64, inspection(6)),
    )

    assert select_base_sample(samples).source_sha256 == "a" * 64


def test_profiles_are_ordered_by_readability_and_respect_common_lower_bound():
    samples = (
        sample(
            "1" * 64,
            inspection(
                5,
                profiles=(profile(font=10.0), profile("compact", font=8.5)),
            ),
        ),
        sample(
            "2" * 64,
            inspection(
                6,
                profiles=(profile(font=10.5), profile("compact", font=9.0)),
            ),
        ),
        sample(
            "3" * 64,
            inspection(
                7,
                profiles=(profile(font=10.25), profile("compact", font=8.75)),
            ),
        ),
    )

    compared = compare_calibration_samples(samples)

    assert [item.name for item in compared.layout_profiles] == [
        "normal",
        "compact",
    ]
    assert [item.body_font_points for item in compared.layout_profiles] == [
        10.5,
        9.0,
    ]
    assert compared.minimum_font_points == 9.0
    assert all(
        item.body_font_points >= compared.minimum_font_points
        for item in compared.layout_profiles
    )


def manifest() -> ListCalibrationManifest:
    compared = compare_calibration_samples(
        (
            sample("1" * 64, inspection(5, dynamic_seed="a")),
            sample("2" * 64, inspection(6, dynamic_seed="b")),
            sample("3" * 64, inspection(7, dynamic_seed="c")),
        )
    )
    return build_calibration_manifest(
        compared,
        master_sha256="a" * 64,
        master_structure_fingerprint=compared.normalized_structure_fingerprint,
        created_at="2026-08-13T08:00:00+08:00",
        word_version="16.0.19029",
        calibration_report_sha256="b" * 64,
    )


def test_manifest_round_trip_is_canonical_hash_stable_and_private_safe():
    original = manifest()
    payload = original.to_dict()
    restored = ListCalibrationManifest.from_dict(
        json.loads(original.to_canonical_json())
    )

    assert restored == original
    assert manifest_sha256(restored) == manifest_sha256(original)
    assert len(payload["sample_evidence"]) == 3
    serialized = original.to_canonical_json()
    assert "source_path" not in serialized
    assert "private-group" not in serialized

    unknown = dict(payload)
    unknown["source_path"] = r"C:\Downloads\LIST-private.doc"
    with pytest.raises(ValueError, match="schema version 2"):
        ListCalibrationManifest.from_dict(unknown)

    for evidence in (
        payload["sample_evidence"][:2],
        [payload["sample_evidence"][0]] * 3,
    ):
        invalid = dict(payload)
        invalid["sample_evidence"] = evidence
        with pytest.raises(ValueError, match="three unique"):
            ListCalibrationManifest.from_dict(invalid)

    zero_hash = dict(payload)
    zero_hash["master_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="non-zero"):
        ListCalibrationManifest.from_dict(zero_hash)


@pytest.mark.parametrize(
    "changes",
    [
        {"master_sha256": "c" * 64},
        {"master_structure_fingerprint": "c" * 64},
        {"generator_version": "list-calibration/1"},
        {"schema_version": 1},
    ],
)
def test_master_validation_fails_closed_on_any_identity_drift(changes):
    calibrated = manifest()
    supplied = calibrated.to_dict() | changes
    if (
        "schema_version" in changes
        or "generator_version" in changes
        or "master_structure_fingerprint" in changes
    ):
        with pytest.raises(ValueError):
            ListCalibrationManifest.from_dict(supplied)
        return

    changed = ListCalibrationManifest.from_dict(supplied)
    with pytest.raises(ValueError, match="master"):
        validate_calibrated_master(
            changed,
            master_sha256="a" * 64,
            master_structure_fingerprint=(
                calibrated.master_structure_fingerprint
            ),
        )


def test_master_validation_accepts_exact_manifest_identity():
    calibrated = manifest()

    validate_calibrated_master(
        calibrated,
        master_sha256=calibrated.master_sha256,
        master_structure_fingerprint=(
            calibrated.master_structure_fingerprint
        ),
    )


class SyntheticCalibrationAdapter:
    def __init__(
        self,
        inspections: tuple[ListTemplateInspectionV2, ...],
        *,
        mutate_source: bool = False,
    ) -> None:
        self.inspections = inspections
        self.mutate_source = mutate_source
        self.actions: list[str] = []

    def run(self, job_path: Path, *, timeout_seconds: int) -> None:
        job = json.loads(job_path.read_text(encoding="utf-8"))
        self.actions.append(job["action"])
        if job["action"] == "inspect-v2":
            assert len(job["sample_paths"]) == 3
            if self.mutate_source:
                Path(job["sample_paths"][1]).write_bytes(b"changed")
            report = {
                "schema_version": 2,
                "action": "inspect-v2",
                "word_version": "16.0-synthetic",
                "samples": [
                    {
                        "sample_id": f"sample-{index:03d}",
                        "inspection": observed.to_dict(),
                    }
                    for index, observed in enumerate(
                        self.inspections, start=1
                    )
                ],
            }
        else:
            source = Path(job["source_path"])
            working_copy = Path(job["working_copy_path"])
            output = Path(job["output_docx"])
            assert source.is_file()
            assert not working_copy.exists()
            assert not output.exists()
            output.write_bytes(b"synthetic calibrated docx")
            master_inspection = replace(
                self.inspections[1],
                day_count=1,
                table_shapes=(
                    TableShape(4, 3),
                    TableShape(3, 6),
                    TableShape(2, 7),
                    TableShape(1, 3),
                ),
                dynamic_content_digest=digest("empty-master"),
            )
            report = {
                "schema_version": 2,
                "action": "calibrate",
                "word_version": "16.0-synthetic",
                "master_inspection": master_inspection.to_dict(),
                "forbidden_dynamic_token_types": [],
                "output_bytes": output.stat().st_size,
            }
        Path(job["report_path"]).write_text(
            json.dumps(report, ensure_ascii=False),
            encoding="utf-8",
        )


def source_files(tmp_path) -> tuple[Path, ...]:
    paths = tuple(tmp_path / f"LIST-{index}.doc" for index in range(1, 4))
    for index, path in enumerate(paths, start=1):
        path.write_bytes(f"synthetic-{index}".encode())
    return paths


class SyntheticHeaderDiagnosticAdapter:
    def __init__(
        self,
        paragraph_counts: tuple[int, int, int],
        *,
        mutate_source: bool = False,
        add_private_field: bool = False,
    ) -> None:
        self.paragraph_counts = paragraph_counts
        self.mutate_source = mutate_source
        self.add_private_field = add_private_field
        self.actions: list[str] = []

    def run(self, job_path: Path, *, timeout_seconds: int) -> None:
        job = json.loads(job_path.read_text(encoding="utf-8"))
        self.actions.append(job["action"])
        assert job["action"] == "diagnose-header-v2"
        assert timeout_seconds == 120
        if self.mutate_source:
            Path(job["sample_paths"][1]).write_bytes(b"changed")
        samples = []
        for index, count in enumerate(self.paragraph_counts, start=1):
            evidence = {
                "list_header_paragraph_count": count,
                "paragraphs": [
                    {
                        "paragraph_number": number,
                        "visible_character_count": 0 if number == count else 12,
                        "fixed_label_ids": (
                            ["group_code"]
                            if number == 2
                            else ["group_name"]
                            if number == 3
                            else []
                        ),
                        "fullwidth_colon_count": (
                            1 if number in {2, 3} else 0
                        ),
                        "inline_shape_count": 0,
                        "ends_with_cell_marker": number == count,
                    }
                    for number in range(1, count + 1)
                ],
            }
            if self.add_private_field:
                evidence["private_text"] = "must not be accepted"
            samples.append(
                {
                    "sample_id": f"sample-{index:03d}",
                    "evidence": evidence,
                }
            )
        Path(job["report_path"]).write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "action": "diagnose-header-v2",
                    "word_version": "16.0-synthetic",
                    "samples": samples,
                }
            ),
            encoding="utf-8",
        )


def test_header_diagnosis_is_read_only_hash_bound_and_private_safe(tmp_path):
    samples = source_files(tmp_path)
    adapter = SyntheticHeaderDiagnosticAdapter((5, 5, 5))

    result = diagnose_list_header_contract(samples, adapter=adapter)

    assert adapter.actions == ["diagnose-header-v2"]
    assert result.classification == "COMMON_EXPECTED_CONTRACT_MISMATCH"
    assert [item.list_header_paragraph_count for item in result.samples] == [
        5,
        5,
        5,
    ]
    payload = result.to_dict()
    serialized = json.dumps(payload)
    assert payload["source_hashes_unchanged"] is True
    assert all(
        item["field_path"] == "list_header_paragraph_count"
        for item in payload["samples"]
    )
    assert "LIST-" not in serialized
    assert "private_text" not in serialized


def test_header_diagnosis_detects_source_mutation(tmp_path):
    samples = source_files(tmp_path)
    adapter = SyntheticHeaderDiagnosticAdapter(
        (4, 5, 4),
        mutate_source=True,
    )

    with pytest.raises(ValueError) as captured:
        diagnose_list_header_contract(samples, adapter=adapter)

    assert getattr(captured.value, "code", "") == "CALIBRATION_SOURCE_CHANGED"
    assert adapter.actions == ["diagnose-header-v2"]


def test_header_diagnosis_rejects_any_unapproved_report_field(tmp_path):
    samples = source_files(tmp_path)
    adapter = SyntheticHeaderDiagnosticAdapter(
        (4, 4, 4),
        add_private_field=True,
    )

    with pytest.raises(ValueError, match="schema version 2"):
        diagnose_list_header_contract(samples, adapter=adapter)


class Synthetic5992DiagnosticAdapter:
    def __init__(
        self,
        *,
        mutate_source: bool = False,
        add_private_field: bool = False,
    ) -> None:
        self.mutate_source = mutate_source
        self.add_private_field = add_private_field
        self.actions: list[str] = []
        self.working_copy_paths: list[Path] = []

    def run(self, job_path: Path, *, timeout_seconds: int) -> None:
        job = json.loads(job_path.read_text(encoding="utf-8"))
        self.actions.append(job["action"])
        assert job["action"] == "diagnose-5992-v2"
        assert timeout_seconds == 180
        assert job["sample_sha256"] == [
            hashlib.sha256(Path(path).read_bytes()).hexdigest()
            for path in job["sample_paths"]
        ]
        self.working_copy_paths = [
            Path(path) for path in job["working_copy_paths"]
        ]
        assert all(path.parent == job_path.parent for path in self.working_copy_paths)
        assert all(not path.exists() for path in self.working_copy_paths)
        if self.mutate_source:
            Path(job["sample_paths"][0]).write_bytes(b"changed")
        report = {
            "schema_version": 2,
            "action": "diagnose-5992-v2",
            "word_version": "16.0-synthetic",
            "classification": "ERROR_OBSERVED",
            "completed_source_inspections": 3,
            "selected_base_sample_id": "sample-002",
            "checkpoint": {
                "phase": "calibrate-copy",
                "sample_id": "sample-002",
                "operation": "table-width-prototype-cell",
                "field_id": "table_column_widths_points",
                "table_number": 3,
                "row_number": 2,
                "column_number": 1,
                "paragraph_number": 0,
            },
            "error": {
                "hresult": -2146822296,
                "hresult_hex": "0x800A1768",
                "low_word_error_number": 5992,
                "adapter_code": "NONE",
            },
        }
        if self.add_private_field:
            report["private_text"] = "must not be accepted"
        Path(job["report_path"]).write_text(
            json.dumps(report),
            encoding="utf-8",
        )


def test_5992_diagnosis_is_single_run_hash_bound_and_private_safe(tmp_path):
    samples = source_files(tmp_path)
    adapter = Synthetic5992DiagnosticAdapter()

    result = diagnose_gate_c_5992(samples, adapter=adapter)

    assert adapter.actions == ["diagnose-5992-v2"]
    assert result.classification == "ERROR_OBSERVED"
    assert result.low_word_error_number == 5992
    payload = result.to_dict()
    assert payload["source_hashes_unchanged"] is True
    assert payload["checkpoint"]["field_path"] == (
        "master_working_copy.table_column_widths_points"
    )
    serialized = json.dumps(payload)
    assert "LIST-" not in serialized
    assert "private_text" not in serialized
    assert all(not path.exists() for path in adapter.working_copy_paths)


def test_5992_diagnosis_detects_source_mutation(tmp_path):
    samples = source_files(tmp_path)
    adapter = Synthetic5992DiagnosticAdapter(mutate_source=True)

    with pytest.raises(ValueError) as captured:
        diagnose_gate_c_5992(samples, adapter=adapter)

    assert getattr(captured.value, "code", "") == "CALIBRATION_SOURCE_CHANGED"
    assert adapter.actions == ["diagnose-5992-v2"]


def test_5992_diagnosis_rejects_unapproved_report_fields(tmp_path):
    samples = source_files(tmp_path)
    adapter = Synthetic5992DiagnosticAdapter(add_private_field=True)

    with pytest.raises(ValueError, match="schema version 2"):
        diagnose_gate_c_5992(samples, adapter=adapter)


def test_calibration_inspects_before_building_and_publishes_private_safe_files(
    tmp_path,
):
    samples = source_files(tmp_path)
    master = tmp_path / "private" / "list-master.docx"
    manifest_path = tmp_path / "private" / "calibration-manifest.json"
    adapter = SyntheticCalibrationAdapter(
        (
            inspection(5, dynamic_seed="a"),
            inspection(6, dynamic_seed="b"),
            inspection(7, dynamic_seed="c"),
        )
    )

    result = calibrate_list_templates(
        samples,
        master_path=master,
        manifest_path=manifest_path,
        adapter=adapter,
        created_at="2026-08-13T09:00:00+08:00",
    )

    assert adapter.actions == ["inspect-v2", "calibrate"]
    assert result.master_path == master.resolve()
    assert result.manifest_path == manifest_path.resolve()
    assert result.master_sha256 == hashlib.sha256(
        b"synthetic calibrated docx"
    ).hexdigest()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["base_sample_sha256"] == hashlib.sha256(
        b"synthetic-2"
    ).hexdigest()
    assert all(
        set(item)
        == {
            "source_sha256",
            "day_count",
            "normalized_structure_fingerprint",
        }
        for item in payload["sample_evidence"]
    )
    assert "LIST-1.doc" not in manifest_path.read_text(encoding="utf-8")


def test_calibration_detects_source_mutation_and_never_builds_master(
    tmp_path,
):
    samples = source_files(tmp_path)
    adapter = SyntheticCalibrationAdapter(
        (
            inspection(5),
            inspection(6),
            inspection(7),
        ),
        mutate_source=True,
    )

    with pytest.raises(ValueError) as captured:
        calibrate_list_templates(
            samples,
            master_path=tmp_path / "master.docx",
            manifest_path=tmp_path / "manifest.json",
            adapter=adapter,
            created_at="2026-08-13T09:00:00+08:00",
        )

    assert getattr(captured.value, "code", "") == (
        "CALIBRATION_SOURCE_CHANGED"
    )
    assert adapter.actions == ["inspect-v2"]
    assert not (tmp_path / "master.docx").exists()


def test_calibration_conflict_and_existing_destinations_fail_before_mutation(
    tmp_path,
):
    samples = source_files(tmp_path)
    conflicted = replace(
        inspection(7),
        margins_points=(40.0, 31.5, 36.0, 31.5),
    )
    adapter = SyntheticCalibrationAdapter(
        (inspection(5), inspection(6), conflicted)
    )

    with pytest.raises(
        CalibrationContractError,
        match="margins_points",
    ):
        calibrate_list_templates(
            samples,
            master_path=tmp_path / "master.docx",
            manifest_path=tmp_path / "manifest.json",
            adapter=adapter,
            created_at="2026-08-13T09:00:00+08:00",
        )
    assert adapter.actions == ["inspect-v2"]

    master = tmp_path / "owned.docx"
    master.write_bytes(b"user owned")
    clean_adapter = SyntheticCalibrationAdapter(
        (inspection(5), inspection(6), inspection(7))
    )
    with pytest.raises(ValueError, match="must not already exist"):
        calibrate_list_templates(
            samples,
            master_path=master,
            manifest_path=tmp_path / "manifest.json",
            adapter=clean_adapter,
            created_at="2026-08-13T09:00:00+08:00",
        )
    assert master.read_bytes() == b"user owned"
    assert clean_adapter.actions == []
