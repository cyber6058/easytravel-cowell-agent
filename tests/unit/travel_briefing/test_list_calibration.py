from __future__ import annotations

import json
import hashlib
import copy
from pathlib import Path
from dataclasses import replace

import pytest

from travel_briefing.list_calibration import (
    CalibrationContractError,
    ListCalibrationManifest,
    ListCalibrationSample,
    ListComponentDiagnosisResult,
    ListLayoutProfile,
    ListTemplateInspectionV2,
    build_calibration_manifest,
    build_calibration_conflict_matrix,
    build_blank_component_normalization_choices,
    build_component_normalization_choice_worksheet,
    build_component_normalization_decision_table,
    component_normalization_decision_table_sha256,
    calibrate_list_templates,
    compare_calibration_samples,
    diagnose_calibration_conflicts,
    diagnose_gate_c_5992,
    diagnose_gate_c_v3,
    diagnose_list_components,
    diagnose_list_header_contract,
    load_component_diagnosis_artifact,
    load_component_normalization_decision_table,
    manifest_sha256,
    normalized_structure_fingerprint,
    select_base_sample,
    validate_component_normalization_choices,
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


def test_conflict_matrix_is_deterministic_private_safe_and_decision_bound():
    original = inspection(5, dynamic_seed="private-group-a")
    changed = replace(
        inspection(8, dynamic_seed="private-group-b"),
        border_digest=digest("changed-border"),
        shape_geometry_points=(
            ("private-shape-name", 501.0, 12.0, 42.0, 42.0),
        ),
        table_column_widths_points=(
            original.table_column_widths_points[0],
            original.table_column_widths_points[1],
            (55.0, 71.0, 108.0, 90.0, 72.0, 72.0, 72.0),
            original.table_column_widths_points[3],
        ),
    )
    samples = (
        sample("3" * 64, changed),
        sample("1" * 64, original),
        sample("2" * 64, original),
    )

    matrix = build_calibration_conflict_matrix(
        samples,
        (
            "table_column_widths_points",
            "shape_geometry_points",
            "border_digest",
        ),
    )

    assert matrix["schema_version"] == 1
    assert matrix["stage"] == "compare-samples"
    assert matrix["classification"] == "TEMPLATE_CONTRACT_CONFLICT"
    assert [item["field_path"] for item in matrix["fields"]] == [
        "border_digest",
        "shape_geometry_points",
        "table_column_widths_points",
    ]
    assert all(
        item["normalization_status"] == "REQUIRES_OP_DECISION"
        for item in matrix["fields"]
    )
    assert all(
        [sample_value["source_sha256"] for sample_value in item["samples"]]
        == ["1" * 64, "2" * 64, "3" * 64]
        for item in matrix["fields"]
    )
    serialized = json.dumps(matrix)
    assert "private-group" not in serialized
    assert "private-shape-name" not in serialized
    assert "dynamic_content_digest" not in serialized
    assert "adaptive_profiles" not in serialized
    by_field = {
        item["field_path"]: item
        for item in matrix["fields"]
    }
    assert all(
        set(value) == {"source_sha256", "normalized_digest"}
        for value in by_field["border_digest"]["samples"]
    )
    assert all(
        set(value) == {"source_sha256", "normalized_value"}
        for value in by_field["table_column_widths_points"]["samples"]
    )
    assert all(
        set(value) == {
            "source_sha256",
            "normalized_value_sha256",
        }
        for value in by_field["shape_geometry_points"]["samples"]
    )
    with pytest.raises(ValueError, match="not conflicting"):
        build_calibration_conflict_matrix(samples, ("margins_points",))
    with pytest.raises(ValueError, match="normalized layout field"):
        build_calibration_conflict_matrix(samples, ("private_content",))


def test_comparison_attaches_safe_conflict_matrix_to_contract_error():
    samples = (
        sample("1" * 64, inspection(5, dynamic_seed="private-a")),
        sample("2" * 64, inspection(6, dynamic_seed="private-b")),
        sample(
            "3" * 64,
            replace(
                inspection(7, dynamic_seed="private-c"),
                style_digest=digest("changed-style"),
            ),
        ),
    )

    with pytest.raises(CalibrationContractError) as captured:
        compare_calibration_samples(samples)

    matrix = captured.value.conflict_matrix
    assert matrix is not None
    assert [item["field_path"] for item in matrix["fields"]] == [
        "style_digest"
    ]
    assert "private-" not in json.dumps(matrix)


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


def test_conflict_diagnosis_only_inspects_and_returns_safe_matrix(tmp_path):
    samples = source_files(tmp_path)
    adapter = SyntheticCalibrationAdapter(
        (
            inspection(5, dynamic_seed="private-a"),
            inspection(6, dynamic_seed="private-b"),
            replace(
                inspection(7, dynamic_seed="private-c"),
                style_digest=digest("changed-style"),
            ),
        )
    )

    result = diagnose_calibration_conflicts(samples, adapter=adapter)

    assert adapter.actions == ["inspect-v2"]
    assert result.classification == "TEMPLATE_CONTRACT_CONFLICT"
    assert result.field_paths == ("style_digest",)
    assert result.conflict_matrix is not None
    assert "private-" not in json.dumps(result.conflict_matrix)


def test_conflict_diagnosis_stops_after_compatible_inspection(tmp_path):
    samples = source_files(tmp_path)
    adapter = SyntheticCalibrationAdapter(
        (
            inspection(5, dynamic_seed="a"),
            inspection(6, dynamic_seed="b"),
            inspection(7, dynamic_seed="c"),
        )
    )

    result = diagnose_calibration_conflicts(samples, adapter=adapter)

    assert adapter.actions == ["inspect-v2"]
    assert result.classification == "NORMALIZED_LAYOUT_COMPATIBLE"
    assert result.field_paths == ()
    assert result.conflict_matrix is None


class SyntheticComponentDiagnosticAdapter:
    def __init__(
        self,
        *,
        mutate_source: bool = False,
        add_private_field: bool = False,
    ) -> None:
        self.mutate_source = mutate_source
        self.add_private_field = add_private_field
        self.actions: list[str] = []

    def run(self, job_path: Path, *, timeout_seconds: int) -> None:
        job = json.loads(job_path.read_text(encoding="utf-8"))
        self.actions.append(job["action"])
        assert job["action"] == "diagnose-components-v2"
        assert timeout_seconds == 120
        if self.mutate_source:
            Path(job["sample_paths"][0]).write_bytes(b"changed")
        samples = []
        for index in range(1, 4):
            evidence = {
                "styles": [{
                    "cell_id": "table-003-row-002-column-001",
                    "name_sha256": digest(f"style-{index}"),
                    "vertical_alignment": 0,
                    "shading_color": -16777216,
                }],
                "fonts": [{
                    "cell_id": "table-003-row-002-column-001",
                    "name_sha256": digest(f"font-{index}"),
                    "name_far_east_sha256": digest(f"east-{index}"),
                    "size_points": 10.0,
                    "bold": 0,
                    "italic": 0,
                    "underline": 0,
                    "color": 0,
                }],
                "paragraphs": [{
                    "cell_id": "table-003-row-002-column-001",
                    "alignment": 0,
                    "space_before_points": 0.0,
                    "space_after_points": 0.0,
                    "line_spacing_points": 12.0,
                    "line_spacing_rule": 0,
                    "left_indent_points": 0.0,
                    "right_indent_points": 0.0,
                    "first_line_indent_points": 0.0,
                }],
                "borders": [{
                    "border_id": "table-003-row-002-column-001-top",
                    "line_style": 1,
                    "line_width": 4,
                    "color": 0,
                }],
                "daily_header": [{
                    "cell_id": "table-003-row-001-column-001",
                    "style_sha256": digest(f"header-style-{index}"),
                    "font_sha256": digest(f"header-font-{index}"),
                    "paragraph_sha256": digest(f"header-paragraph-{index}"),
                    "component_sha256": digest(f"header-{index}"),
                }],
                "daily_body": [{
                    "cell_id": "table-003-row-002-column-001",
                    "style_sha256": digest(f"body-style-{index}"),
                    "font_sha256": digest(f"body-font-{index}"),
                    "paragraph_sha256": digest(f"body-paragraph-{index}"),
                    "component_sha256": digest(f"body-{index}"),
                }],
                "shapes": [{
                    "shape_id": "inline-001",
                    "kind": "inline",
                    "left_points": 0.0,
                    "top_points": 0.0,
                    "width_points": 24.0,
                    "height_points": 24.0,
                }],
            }
            if self.add_private_field:
                evidence["private_text"] = "must-not-pass"
            samples.append({
                "sample_id": f"sample-{index:03d}",
                "evidence": evidence,
            })
        report = {
            "schema_version": 2,
            "action": "diagnose-components-v2",
            "word_version": "16.0-synthetic",
            "samples": samples,
        }
        Path(job["report_path"]).write_text(
            json.dumps(report), encoding="utf-8"
        )


def test_component_diagnosis_is_read_only_and_private_safe(tmp_path):
    samples = source_files(tmp_path)
    adapter = SyntheticComponentDiagnosticAdapter()

    result = diagnose_list_components(samples, adapter=adapter)

    assert adapter.actions == ["diagnose-components-v2"]
    assert result.word_version == "16.0-synthetic"
    assert result.source_sha256 == tuple(
        hashlib.sha256(path.read_bytes()).hexdigest() for path in samples
    )
    serialized = json.dumps(result.samples)
    assert "must-not-pass" not in serialized
    assert all(path.name not in serialized for path in samples)


def test_component_diagnosis_detects_source_mutation(tmp_path):
    samples = source_files(tmp_path)

    with pytest.raises(ValueError, match="CALIBRATION_SOURCE_CHANGED"):
        diagnose_list_components(
            samples,
            adapter=SyntheticComponentDiagnosticAdapter(mutate_source=True),
        )


def test_component_diagnosis_rejects_extra_report_fields(tmp_path):
    samples = source_files(tmp_path)

    with pytest.raises(ValueError, match="component diagnostic report"):
        diagnose_list_components(
            samples,
            adapter=SyntheticComponentDiagnosticAdapter(
                add_private_field=True
            ),
        )


def component_result(
    *evidence: dict[str, object],
) -> ListComponentDiagnosisResult:
    return ListComponentDiagnosisResult(
        word_version="16.0-synthetic",
        source_sha256=("a" * 64, "b" * 64, "c" * 64),
        samples=tuple(evidence),
    )


def complete_component_evidence() -> dict[str, object]:
    cell_ids = tuple(
        f"table-{table:03d}-row-{row:03d}-column-{column:03d}"
        for table, row, count in ((1, 2, 3), (2, 2, 6), (3, 2, 7), (4, 1, 3))
        for column in range(1, count + 1)
    )
    styles = [{
        "cell_id": cell_id,
        "name_sha256": digest("style"),
        "vertical_alignment": 0,
        "shading_color": 0,
    } for cell_id in cell_ids]
    fonts = [{
        "cell_id": cell_id,
        "name_sha256": digest("font"),
        "name_far_east_sha256": digest("east"),
        "size_points": 10.0,
        "bold": 0,
        "italic": 0,
        "underline": 0,
        "color": 0,
    } for cell_id in cell_ids]
    paragraphs = [{
        "cell_id": cell_id,
        "alignment": 0,
        "space_before_points": 0.0,
        "space_after_points": 0.0,
        "line_spacing_points": 12.0,
        "line_spacing_rule": 0,
        "left_indent_points": 0.0,
        "right_indent_points": 0.0,
        "first_line_indent_points": 0.0,
    } for cell_id in cell_ids]
    sides = ("top", "left", "bottom", "right", "diagonal-down", "diagonal-up")
    borders = [{
        "border_id": f"{cell_id}-{side}",
        "line_style": 1,
        "line_width": 4,
        "color": 0,
    } for cell_id in cell_ids for side in sides]
    daily_header = [{
        "cell_id": f"table-003-row-001-column-{column:03d}",
        "style_sha256": digest("header-style"),
        "font_sha256": digest("header-font"),
        "paragraph_sha256": digest("header-paragraph"),
        "component_sha256": digest("header-component"),
    } for column in range(1, 8)]
    daily_body = [{
        "cell_id": f"table-003-row-002-column-{column:03d}",
        "style_sha256": digest("body-style"),
        "font_sha256": digest("body-font"),
        "paragraph_sha256": digest("body-paragraph"),
        "component_sha256": digest("body-component"),
    } for column in range(1, 8)]
    return {
        "styles": styles,
        "fonts": fonts,
        "paragraphs": paragraphs,
        "borders": borders,
        "daily_header": daily_header,
        "daily_body": daily_body,
        "shapes": [{
            "shape_id": "floating-001",
            "kind": "floating",
            "left_points": 1.0,
            "top_points": 2.0,
            "width_points": 10.0,
            "height_points": 10.0,
        }],
    }


def component_samples() -> list[dict[str, object]]:
    base = complete_component_evidence()
    return [copy.deepcopy(base) for _ in range(3)]


def test_normalization_table_never_uses_majority_as_a_decision():
    samples = component_samples()
    values = (10.0, 10.0, 12.0)
    for sample, size in zip(samples, values, strict=True):
        sample["fonts"][9]["size_points"] = size

    table = build_component_normalization_decision_table(
        component_result(*samples)
    )

    assert table["classification"] == "REQUIRES_OP_DECISION"
    assert table["policy"]["automatic_majority_selection"] is False
    assert len(table["decisions"]) == 1
    decision = table["decisions"][0]
    assert decision["component_family"] == "fonts"
    assert decision["changed_properties"] == ["size_points"]
    assert decision["status"] == "REQUIRES_OP_BASE"
    assert decision["eligible_source_sha256"] == [
        "a" * 64, "b" * 64, "c" * 64
    ]
    assert [item["source_sha256"] for item in decision["samples"]] == [
        "a" * 64, "b" * 64, "c" * 64
    ]
    assert all(item["eligible_as_base"] for item in decision["samples"])


def test_normalization_table_preserves_complete_unanimous_contract():
    table = build_component_normalization_decision_table(
        component_result(*component_samples())
    )

    assert table["classification"] == "NORMALIZATION_READY"
    assert table["decisions"] == []
    assert table["blockers"] == []
    assert table["preserved_unanimous_counts"] == {
        "styles": 19,
        "fonts": 19,
        "paragraphs": 19,
        "borders": 114,
        "daily_header": 7,
        "daily_body": 7,
        "shapes": 1,
    }


def test_normalization_table_blocks_mixed_value_source_as_base():
    samples = component_samples()
    values = ((15.0, 4), (9999999.0, 9999999), (12.0, 0))
    for sample, (spacing, rule) in zip(samples, values, strict=True):
        sample["paragraphs"][2]["line_spacing_points"] = spacing
        sample["paragraphs"][2]["line_spacing_rule"] = rule

    table = build_component_normalization_decision_table(
        component_result(*samples)
    )

    assert table["classification"] == "BLOCKED_MIXED_VALUE"
    decision = table["decisions"][0]
    assert decision["status"] == "BLOCKED_MIXED_VALUE"
    assert decision["eligible_source_sha256"] == ["a" * 64, "c" * 64]
    assert decision["ineligible_source_sha256"] == ["b" * 64]


def test_normalization_table_groups_floating_shape_geometry():
    samples = component_samples()
    for index, sample in enumerate(samples, start=1):
        sample["shapes"][0].update({
            "left_points": float(index),
            "top_points": float(index + 1),
            "width_points": float(index + 10),
            "height_points": float(index + 10),
        })

    table = build_component_normalization_decision_table(
        component_result(*samples)
    )

    assert len(table["decisions"]) == 1
    assert table["decisions"][0]["component_family"] == "shapes"
    assert table["decisions"][0]["changed_properties"] == [
        "height_points", "left_points", "top_points", "width_points"
    ]
    assert table["decisions"][0]["selection_unit"] == "geometry_bundle"


def test_normalization_table_fails_closed_on_component_presence_change():
    samples = component_samples()
    samples[0]["shapes"].append({
        "shape_id": "floating-002",
        "kind": "floating",
        "left_points": 1.0,
        "top_points": 2.0,
        "width_points": 10.0,
        "height_points": 10.0,
    })

    table = build_component_normalization_decision_table(
        component_result(*samples)
    )

    assert table["classification"] == "COMPONENT_CONTRACT_CONFLICT"
    assert table["blockers"] == [{
        "component_family": "shapes",
        "reason": "COMPONENT_ID_SET_CHANGED",
    }]
    assert table["decisions"] == []


def test_normalization_table_fails_closed_on_shape_kind_change():
    samples = component_samples()
    samples[2]["shapes"][0]["kind"] = "inline"

    with pytest.raises(ValueError, match="component normalization evidence"):
        build_component_normalization_decision_table(
            component_result(*samples)
        )


def test_normalization_table_marks_daily_body_as_derived_audit():
    samples = component_samples()
    for index, sample in enumerate(samples, start=1):
        sample["daily_body"][0].update({
            "font_sha256": digest(f"font-{index}"),
            "paragraph_sha256": digest(f"paragraph-{index}"),
            "component_sha256": digest(f"component-{index}"),
        })

    table = build_component_normalization_decision_table(
        component_result(*samples)
    )

    assert table["decisions"] == []
    assert table["derived_audits"] == [{
        "component_family": "daily_body",
        "component_id": "table-003-row-002-column-001",
        "status": "VERIFY_AFTER_COMPONENT_NORMALIZATION",
    }]


def component_artifact(samples: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": "ok",
        "command": "diagnose-list-components",
        "stage": "component-evidence",
        "word_version": "16.0-synthetic",
        "source_sha256": ["a" * 64, "b" * 64, "c" * 64],
        "samples": samples,
    }


def test_component_artifact_reader_requires_exact_private_safe_schema(tmp_path):
    path = tmp_path / "component-report.json"
    payload = component_artifact(component_samples())
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = load_component_diagnosis_artifact(path)

    assert result.source_sha256 == ("a" * 64, "b" * 64, "c" * 64)
    assert result.word_version == "16.0-synthetic"
    payload["private_text"] = "must-not-pass"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="component diagnosis artifact"):
        load_component_diagnosis_artifact(path)


def decision_table_with_one_font_choice() -> dict[str, object]:
    samples = component_samples()
    samples[2]["fonts"][9]["size_points"] = 12.0
    return build_component_normalization_decision_table(
        component_result(*samples)
    )


def valid_choice_artifact(table: dict[str, object]) -> dict[str, object]:
    decision = table["decisions"][0]
    selected = decision["samples"][0]
    return {
        "schema_version": 1,
        "decision_table_sha256": (
            component_normalization_decision_table_sha256(table)
        ),
        "source_sha256": list(table["source_sha256"]),
        "choices": [{
            "decision_id": decision["decision_id"],
            "selected_source_sha256": selected["source_sha256"],
            "selected_component_value_sha256": selected[
                "component_value_sha256"
            ],
        }],
    }


def test_op_choice_validator_binds_table_source_and_component_hashes():
    table = decision_table_with_one_font_choice()
    artifact = valid_choice_artifact(table)

    validated = validate_component_normalization_choices(table, artifact)

    assert validated == artifact
    assert validated is not artifact


@pytest.mark.parametrize("mutation", ["missing", "extra", "duplicate"])
def test_op_choice_validator_rejects_non_exact_decision_set(mutation):
    table = decision_table_with_one_font_choice()
    artifact = valid_choice_artifact(table)
    if mutation == "missing":
        artifact["choices"] = []
    elif mutation == "extra":
        artifact["choices"].append({
            **artifact["choices"][0],
            "decision_id": "fonts:table-001-row-002-column-001",
        })
    else:
        artifact["choices"].append(dict(artifact["choices"][0]))

    with pytest.raises(ValueError, match="OP normalization choices"):
        validate_component_normalization_choices(table, artifact)


def test_op_choice_validator_rejects_ineligible_mixed_value_source():
    samples = component_samples()
    samples[0]["paragraphs"][2]["line_spacing_points"] = 15.0
    samples[1]["paragraphs"][2]["line_spacing_points"] = 9999999.0
    samples[1]["paragraphs"][2]["line_spacing_rule"] = 9999999
    table = build_component_normalization_decision_table(
        component_result(*samples)
    )
    artifact = valid_choice_artifact(table)
    decision = table["decisions"][0]
    blocked = decision["samples"][1]
    artifact["choices"][0].update({
        "selected_source_sha256": blocked["source_sha256"],
        "selected_component_value_sha256": blocked[
            "component_value_sha256"
        ],
    })

    with pytest.raises(ValueError, match="OP normalization choices"):
        validate_component_normalization_choices(table, artifact)


def test_op_choice_validator_rejects_wrong_table_or_component_hash():
    table = decision_table_with_one_font_choice()
    artifact = valid_choice_artifact(table)
    artifact["decision_table_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="OP normalization choices"):
        validate_component_normalization_choices(table, artifact)

    artifact = valid_choice_artifact(table)
    artifact["choices"][0]["selected_component_value_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="OP normalization choices"):
        validate_component_normalization_choices(table, artifact)


def test_decision_table_hash_rejects_unapproved_fields():
    table = decision_table_with_one_font_choice()
    table["private_text"] = "must-not-pass"

    with pytest.raises(ValueError, match="component normalization decision table"):
        component_normalization_decision_table_sha256(table)


def test_decision_table_reader_requires_exact_private_safe_schema(tmp_path):
    table = decision_table_with_one_font_choice()
    path = tmp_path / "normalization-decision-table.json"
    path.write_text(json.dumps(table), encoding="utf-8")

    loaded = load_component_normalization_decision_table(path)

    assert loaded == table
    assert loaded is not table
    table["source_path"] = "must-not-pass"
    path.write_text(json.dumps(table), encoding="utf-8")
    with pytest.raises(
        ValueError, match="component normalization decision table"
    ):
        load_component_normalization_decision_table(path)


def test_choice_worksheet_exposes_only_fixed_labels_and_safe_changed_values():
    samples = component_samples()
    for sample, size in zip(samples, (10.0, 10.0, 12.0), strict=True):
        sample["fonts"][9]["size_points"] = size
    diagnosis = component_result(*samples)
    table = build_component_normalization_decision_table(diagnosis)

    worksheet = build_component_normalization_choice_worksheet(
        diagnosis, table
    )

    assert worksheet["sample_labels"] == [
        {"sample_id": "sample-001", "source_sha256": "a" * 64},
        {"sample_id": "sample-002", "source_sha256": "b" * 64},
        {"sample_id": "sample-003", "source_sha256": "c" * 64},
    ]
    decision = worksheet["decisions"][0]
    assert decision["changed_properties"] == ["size_points"]
    assert [option["safe_values"] for option in decision["options"]] == [
        {"size_points": 10.0},
        {"size_points": 10.0},
        {"size_points": 12.0},
    ]
    serialized = json.dumps(worksheet)
    assert "recommend" not in serialized.casefold()
    assert "source_path" not in serialized
    assert ".doc" not in serialized


def test_choice_worksheet_marks_mixed_value_option_ineligible():
    samples = component_samples()
    samples[0]["paragraphs"][2]["line_spacing_points"] = 15.0
    samples[1]["paragraphs"][2]["line_spacing_points"] = 9999999.0
    samples[1]["paragraphs"][2]["line_spacing_rule"] = 9999999
    diagnosis = component_result(*samples)
    table = build_component_normalization_decision_table(diagnosis)

    worksheet = build_component_normalization_choice_worksheet(
        diagnosis, table
    )

    options = worksheet["decisions"][0]["options"]
    assert [option["eligible_as_base"] for option in options] == [
        True, False, True
    ]
    assert options[1]["safe_values"] == {
        "line_spacing_points": 9999999.0,
        "line_spacing_rule": 9999999,
    }


def test_choice_worksheet_rejects_mismatched_diagnosis_and_table():
    diagnosis = component_result(*component_samples())
    table = decision_table_with_one_font_choice()

    with pytest.raises(ValueError, match="do not match"):
        build_component_normalization_choice_worksheet(diagnosis, table)


def test_blank_choices_are_incomplete_until_op_fills_exact_hash_binding():
    table = decision_table_with_one_font_choice()

    artifact = build_blank_component_normalization_choices(table)

    assert artifact["choices"] == [{
        "decision_id": table["decisions"][0]["decision_id"],
        "selected_source_sha256": "",
        "selected_component_value_sha256": "",
    }]
    with pytest.raises(ValueError, match="OP normalization choices"):
        validate_component_normalization_choices(table, artifact)
    artifact["choices"][0].update(
        valid_choice_artifact(table)["choices"][0]
    )
    assert validate_component_normalization_choices(table, artifact) == artifact


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
        action: str = "diagnose-5992-v2",
        hresult: int = -2146822296,
    ) -> None:
        self.mutate_source = mutate_source
        self.add_private_field = add_private_field
        self.action = action
        self.hresult = hresult
        self.actions: list[str] = []
        self.working_copy_paths: list[Path] = []

    def run(self, job_path: Path, *, timeout_seconds: int) -> None:
        job = json.loads(job_path.read_text(encoding="utf-8"))
        self.actions.append(job["action"])
        assert job["action"] == self.action
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
        operation = (
            "table-width-prototype-cell"
            if self.action == "diagnose-5992-v2"
            else "table-format-prototype-cell"
        )
        field_id = (
            "table_column_widths_points"
            if self.action == "diagnose-5992-v2"
            else "style_digest"
        )
        report = {
            "schema_version": 2,
            "action": self.action,
            "word_version": "16.0-synthetic",
            "classification": "ERROR_OBSERVED",
            "completed_source_inspections": 3,
            "selected_base_sample_id": "sample-002",
            "checkpoint": {
                "phase": "calibrate-copy",
                "sample_id": "sample-002",
                "operation": operation,
                "field_id": field_id,
                "table_number": 3,
                "row_number": 2,
                "column_number": 1,
                "paragraph_number": 0,
            },
            "error": {
                "hresult": self.hresult,
                "hresult_hex": f"0x{self.hresult & 0xFFFFFFFF:08X}",
                "low_word_error_number": self.hresult & 0xFFFF,
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


def test_gate_c_v3_diagnosis_is_generic_hash_bound_and_private_safe(tmp_path):
    samples = source_files(tmp_path)
    adapter = Synthetic5992DiagnosticAdapter(
        action="diagnose-gate-c-v3",
        hresult=-2146233087,
    )

    result = diagnose_gate_c_v3(samples, adapter=adapter)

    assert adapter.actions == ["diagnose-gate-c-v3"]
    assert result.hresult_hex == "0x80131501"
    assert result.low_word_error_number == 5377
    payload = result.to_dict()
    assert payload["source_hashes_unchanged"] is True
    assert payload["checkpoint"]["operation"] == (
        "table-format-prototype-cell"
    )
    serialized = json.dumps(payload)
    assert "LIST-" not in serialized
    assert "source_path" not in serialized
    assert all(not path.exists() for path in adapter.working_copy_paths)


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
    stages = []

    result = calibrate_list_templates(
        samples,
        master_path=master,
        manifest_path=manifest_path,
        adapter=adapter,
        created_at="2026-08-13T09:00:00+08:00",
        on_stage=stages.append,
    )

    assert adapter.actions == ["inspect-v2", "calibrate"]
    assert stages == [
        "inspect-samples",
        "compare-samples",
        "calibrate-master",
        "validate-master",
        "publish",
    ]
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
    stages = []

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
            on_stage=stages.append,
        )
    assert adapter.actions == ["inspect-v2"]
    assert stages == ["inspect-samples", "compare-samples"]

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
