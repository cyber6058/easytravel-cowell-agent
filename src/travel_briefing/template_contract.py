from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


A4_WIDTH_POINTS = 595.28
A4_HEIGHT_POINTS = 841.89
_PAGE_SIZE_TOLERANCE_POINTS = 2.0
_SUPPORTED_DAY_COUNTS = frozenset({5, 6, 7})
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")

# Word exposes only the first coordinate of a horizontally merged cell.  This
# is the accessible-cell pattern established by the confirmed short LIST
# header: row 1 spans three columns, row 3 spans three columns, and row 4's
# second cell spans the final two columns.
LIST_HEADER_ACCESSIBLE_CELLS = (
    (1, 1),
    (2, 1),
    (2, 2),
    (2, 3),
    (3, 1),
    (4, 1),
    (4, 2),
)
LIST_ANCHOR_LABELS = (
    "團體編號",
    "團體名稱",
    "出發日期",
    "集合時間",
    "領隊姓名",
    "集合地點",
    "識別牌",
    "機場專員",
)


def normalize_word_points(value: int | float) -> float:
    """Return a stable hundredth-point value for Word COM measurements."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Word points must be numeric")
    return float(
        Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


@dataclass(frozen=True, slots=True)
class TableShape:
    rows: int
    columns: int

    def to_dict(self) -> dict[str, int]:
        return {"rows": self.rows, "columns": self.columns}

    @classmethod
    def from_dict(cls, value: object) -> TableShape:
        if not isinstance(value, dict) or set(value) != {"rows", "columns"}:
            raise ValueError("table shape must contain rows and columns")
        rows = value["rows"]
        columns = value["columns"]
        if (
            isinstance(rows, bool)
            or not isinstance(rows, int)
            or isinstance(columns, bool)
            or not isinstance(columns, int)
            or rows <= 0
            or columns <= 0
        ):
            raise ValueError("table shape values must be positive integers")
        return cls(rows=rows, columns=columns)


@dataclass(frozen=True, slots=True)
class ListTemplateInspection:
    table_shapes: tuple[TableShape, ...]
    anchor_labels: tuple[str, ...]
    list_header_accessible_cells: tuple[tuple[int, int], ...]
    list_header_paragraph_count: int
    header_qr_candidate_count: int
    section_count: int
    page_width_points: float
    page_height_points: float
    orientation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_shapes": [shape.to_dict() for shape in self.table_shapes],
            "anchor_labels": list(self.anchor_labels),
            "list_header_accessible_cells": [
                [row, column]
                for row, column in self.list_header_accessible_cells
            ],
            "list_header_paragraph_count": self.list_header_paragraph_count,
            "header_qr_candidate_count": self.header_qr_candidate_count,
            "section_count": self.section_count,
            "page_width_points": round(float(self.page_width_points), 2),
            "page_height_points": round(float(self.page_height_points), 2),
            "orientation": self.orientation,
        }

    @classmethod
    def from_dict(cls, value: object) -> ListTemplateInspection:
        expected_keys = {
            "table_shapes",
            "anchor_labels",
            "list_header_accessible_cells",
            "list_header_paragraph_count",
            "header_qr_candidate_count",
            "section_count",
            "page_width_points",
            "page_height_points",
            "orientation",
        }
        if not isinstance(value, dict) or set(value) != expected_keys:
            raise ValueError("template inspection does not match schema version 1")
        shapes = value["table_shapes"]
        anchors = value["anchor_labels"]
        cells = value["list_header_accessible_cells"]
        if (
            not isinstance(shapes, list)
            or not isinstance(anchors, list)
            or not isinstance(cells, list)
        ):
            raise ValueError("template inspection arrays are invalid")
        return cls(
            table_shapes=tuple(TableShape.from_dict(shape) for shape in shapes),
            anchor_labels=tuple(_text(anchor, "anchor label") for anchor in anchors),
            list_header_accessible_cells=tuple(
                _decode_cell_coordinate(cell) for cell in cells
            ),
            list_header_paragraph_count=_positive_int(
                value["list_header_paragraph_count"], "header paragraph count"
            ),
            header_qr_candidate_count=_nonnegative_int(
                value["header_qr_candidate_count"], "QR candidate count"
            ),
            section_count=_positive_int(value["section_count"], "section count"),
            page_width_points=_positive_number(
                value["page_width_points"], "page width"
            ),
            page_height_points=_positive_number(
                value["page_height_points"], "page height"
            ),
            orientation=_text(value["orientation"], "orientation"),
        )


def expected_list_table_shapes(day_count: int) -> tuple[TableShape, ...]:
    if day_count not in _SUPPORTED_DAY_COUNTS:
        raise ValueError("LIST template day count must be 5, 6, or 7")
    return (
        TableShape(rows=4, columns=3),
        TableShape(rows=3, columns=6),
        TableShape(rows=day_count + 1, columns=7),
        TableShape(rows=1, columns=3),
    )


def layout_fingerprint(inspection: ListTemplateInspection) -> str:
    value = inspection.to_dict()
    canonical_lines = (
        "list-template-layout/1",
        "table_shapes="
        + ",".join(
            f"{shape['rows']}x{shape['columns']}" for shape in value["table_shapes"]
        ),
        "anchor_labels=" + ",".join(value["anchor_labels"]),
        "list_header_accessible_cells="
        + ",".join(
            f"{row}:{column}"
            for row, column in value["list_header_accessible_cells"]
        ),
        f"list_header_paragraph_count={value['list_header_paragraph_count']}",
        f"header_qr_candidate_count={value['header_qr_candidate_count']}",
        f"section_count={value['section_count']}",
        f"page_width_points={value['page_width_points']:.2f}",
        f"page_height_points={value['page_height_points']:.2f}",
        f"orientation={value['orientation']}",
    )
    canonical = "\n".join(canonical_lines).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def validate_list_template(
    inspection: ListTemplateInspection,
    *,
    day_count: int,
    expected_layout_fingerprint: str,
) -> str:
    expected_shapes = expected_list_table_shapes(day_count)
    if inspection.table_shapes != expected_shapes:
        raise ValueError("LIST template table shapes do not match the contract")
    if inspection.anchor_labels != LIST_ANCHOR_LABELS:
        raise ValueError("LIST template anchor labels do not match the contract")
    if inspection.list_header_accessible_cells != LIST_HEADER_ACCESSIBLE_CELLS:
        raise ValueError("LIST template merged-cell structure has changed")
    if inspection.list_header_paragraph_count != 4:
        raise ValueError("LIST template must expose exactly four header paragraphs")
    if inspection.header_qr_candidate_count < 1:
        raise ValueError("LIST template header has no QR candidate")
    if inspection.section_count != 1:
        raise ValueError("LIST template must contain one section")
    if (
        inspection.orientation != "portrait"
        or abs(inspection.page_width_points - A4_WIDTH_POINTS)
        > _PAGE_SIZE_TOLERANCE_POINTS
        or abs(inspection.page_height_points - A4_HEIGHT_POINTS)
        > _PAGE_SIZE_TOLERANCE_POINTS
    ):
        raise ValueError("LIST template must use A4 portrait page geometry")
    expected = _validate_sha256(expected_layout_fingerprint)
    actual = layout_fingerprint(inspection)
    if actual != expected:
        raise ValueError("LIST template layout fingerprint does not match configuration")
    return actual


def _validate_sha256(value: str) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise ValueError("expected layout fingerprint must be lowercase SHA-256")
    return value


def _decode_cell_coordinate(value: object) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("cell coordinate must be a two-item array")
    row = _positive_int(value[0], "cell row")
    column = _positive_int(value[1], "cell column")
    return row, column


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _nonnegative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer")
    return value


def _positive_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{label} must be a positive number")
    return float(value)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be non-empty text")
    return value
