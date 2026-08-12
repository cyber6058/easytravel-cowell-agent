from __future__ import annotations

import json
from dataclasses import replace

import pytest

from travel_briefing.list_calibration import (
    CalibrationContractError,
    ListCalibrationManifest,
    ListCalibrationSample,
    ListLayoutProfile,
    ListTemplateInspectionV2,
    build_calibration_manifest,
    compare_calibration_samples,
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
