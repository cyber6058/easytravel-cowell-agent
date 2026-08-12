from dataclasses import replace

import pytest

from travel_briefing.template_contract import (
    A4_HEIGHT_POINTS,
    A4_WIDTH_POINTS,
    LIST_ANCHOR_LABELS,
    LIST_HEADER_ACCESSIBLE_CELLS,
    ListTemplateInspection,
    TableShape,
    expected_list_table_shapes,
    layout_fingerprint,
    normalize_word_points,
    validate_list_template,
)


def inspection(day_count: int = 5) -> ListTemplateInspection:
    return ListTemplateInspection(
        table_shapes=expected_list_table_shapes(day_count),
        anchor_labels=LIST_ANCHOR_LABELS,
        list_header_accessible_cells=LIST_HEADER_ACCESSIBLE_CELLS,
        list_header_paragraph_count=4,
        header_qr_candidate_count=1,
        section_count=1,
        page_width_points=A4_WIDTH_POINTS,
        page_height_points=A4_HEIGHT_POINTS,
        orientation="portrait",
    )


@pytest.mark.parametrize(
    ("day_count", "daily_rows"),
    [(5, 6), (6, 7), (7, 8)],
)
def test_list_contract_supports_exactly_five_six_or_seven_days(
    day_count, daily_rows
):
    shapes = expected_list_table_shapes(day_count)

    assert shapes == (
        TableShape(rows=4, columns=3),
        TableShape(rows=3, columns=6),
        TableShape(rows=daily_rows, columns=7),
        TableShape(rows=1, columns=3),
    )


@pytest.mark.parametrize("day_count", [4, 8])
def test_list_contract_rejects_unsupported_day_counts(day_count):
    with pytest.raises(ValueError, match="5, 6, or 7"):
        expected_list_table_shapes(day_count)


def test_template_validation_accepts_only_the_configured_layout_fingerprint():
    observed = inspection()
    expected_fingerprint = layout_fingerprint(observed)

    validated = validate_list_template(
        observed,
        day_count=5,
        expected_layout_fingerprint=expected_fingerprint,
    )

    assert validated == expected_fingerprint
    with pytest.raises(ValueError, match="fingerprint"):
        validate_list_template(
            observed,
            day_count=5,
            expected_layout_fingerprint="0" * 64,
        )


@pytest.mark.parametrize(
    ("changed", "message"),
    [
        (
            {"table_shapes": (TableShape(4, 3), TableShape(3, 6))},
            "table shapes",
        ),
        ({"list_header_accessible_cells": ((1, 1),)}, "merged-cell"),
        ({"anchor_labels": ("團體編號",)}, "anchor labels"),
        ({"list_header_paragraph_count": 3}, "header paragraphs"),
        ({"header_qr_candidate_count": 0}, "QR candidate"),
        ({"section_count": 2}, "one section"),
        ({"page_width_points": 612.0}, "A4 portrait"),
        ({"orientation": "landscape"}, "A4 portrait"),
    ],
)
def test_template_validation_fails_closed_on_contract_drift(changed, message):
    original = inspection()
    observed = replace(original, **changed)

    with pytest.raises(ValueError, match=message):
        validate_list_template(
            observed,
            day_count=5,
            expected_layout_fingerprint=layout_fingerprint(observed),
        )


def test_layout_fingerprint_is_canonical_and_contains_no_document_text():
    first = inspection(6)
    second = ListTemplateInspection.from_dict(first.to_dict())

    assert layout_fingerprint(first) == layout_fingerprint(second)
    assert len(layout_fingerprint(first)) == 64


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [(31.504, 31.5), (31.505, 31.51), (31, 31.0)],
)
def test_word_points_are_normalized_to_hundredths(raw, normalized):
    assert normalize_word_points(raw) == normalized
