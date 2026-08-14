from __future__ import annotations

import hashlib
import json
import math
import re
import secrets
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from .template_contract import (
    A4_HEIGHT_POINTS,
    A4_WIDTH_POINTS,
    LIST_ANCHOR_LABELS,
    LIST_HEADER_ACCESSIBLE_CELLS,
    TableShape,
    normalize_word_points,
)


CALIBRATION_SCHEMA_VERSION = 2
CALIBRATION_GENERATOR_VERSION = "list-calibration/2"
CALIBRATION_STAGES = (
    "inspect-samples",
    "compare-samples",
    "calibrate-master",
    "validate-master",
    "publish",
)
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_PROFILE_NAME_PATTERN = re.compile(r"[a-z][a-z0-9-]*")
_A4_TOLERANCE_POINTS = 2.0
_GATE_C_5992_PHASES = {"inspect-source", "calibrate-copy", "complete"}
_GATE_C_5992_OPERATIONS = {
    "open-document",
    "table-shape-rows-count",
    "table-shape-columns-count",
    "header-cell-access",
    "anchor-cell-access",
    "page-geometry",
    "header-contract",
    "table-width-columns-count",
    "table-width-column-item",
    "table-width-prototype-cell",
    "table-format-row",
    "table-format-prototype-cell",
    "table-borders",
    "cell-border-top",
    "cell-border-left",
    "cell-border-bottom",
    "cell-border-right",
    "cell-border-diagonal-down",
    "cell-border-diagonal-up",
    "daily-table-access",
    "daily-header-row",
    "daily-body-row",
    "daily-format",
    "daily-header-prototype-cell",
    "daily-body-prototype-cell",
    "inline-shapes",
    "floating-shapes",
    "header-fixed-paragraph",
    "header-tail-normalize",
    "header-tail-postcondition",
    "header-cell-clear",
    "flight-cell-clear",
    "daily-row-normalize",
    "daily-cell-clear",
    "footer-cell-clear",
    "final-inspection",
    "complete",
}
_GATE_C_5992_FIELDS = {
    "document",
    "table_shapes",
    "list_header_accessible_cells",
    "anchor_labels",
    "page_geometry",
    "list_header_paragraph_count",
    "table_column_widths_points",
    "style_digest",
    "border_digest",
    "daily_table",
    "shape_geometry_points",
    "prototype_header",
    "prototype_header_cells",
    "prototype_flight_rows",
    "prototype_daily_rows",
    "prototype_footer",
    "master_inspection",
    "diagnostic",
}


class CalibrationContractError(ValueError):
    def __init__(
        self,
        field_paths: tuple[str, ...],
        *,
        conflict_matrix: dict[str, Any] | None = None,
    ) -> None:
        self.code = "CALIBRATION_CONTRACT_CONFLICT"
        self.field_paths = tuple(sorted(set(field_paths)))
        self.conflict_matrix = conflict_matrix
        fields = ", ".join(self.field_paths)
        super().__init__(f"{self.code}: structural fields differ: {fields}")


class CalibrationSourceChangedError(ValueError):
    code = "CALIBRATION_SOURCE_CHANGED"

    def __init__(self) -> None:
        super().__init__(
            "CALIBRATION_SOURCE_CHANGED: a calibration source changed"
        )


class WordCalibrationAdapter(Protocol):
    def run(self, job_path: Path, *, timeout_seconds: int) -> None: ...


@dataclass(frozen=True, slots=True)
class ListLayoutProfile:
    name: str
    body_font_points: float
    line_spacing_points: float
    paragraph_space_after_points: float
    cell_top_margin_points: float
    cell_bottom_margin_points: float

    def __post_init__(self) -> None:
        if (
            not isinstance(self.name, str)
            or _PROFILE_NAME_PATTERN.fullmatch(self.name) is None
        ):
            raise ValueError("layout profile name is invalid")
        for field_name in (
            "body_font_points",
            "line_spacing_points",
            "paragraph_space_after_points",
            "cell_top_margin_points",
            "cell_bottom_margin_points",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{field_name} must be numeric")
            normalized = normalize_word_points(value)
            if field_name != "paragraph_space_after_points" and normalized <= 0:
                raise ValueError(f"{field_name} must be positive")
            if field_name == "paragraph_space_after_points" and normalized < 0:
                raise ValueError(f"{field_name} must be nonnegative")
            object.__setattr__(self, field_name, normalized)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "body_font_points": self.body_font_points,
            "line_spacing_points": self.line_spacing_points,
            "paragraph_space_after_points": self.paragraph_space_after_points,
            "cell_top_margin_points": self.cell_top_margin_points,
            "cell_bottom_margin_points": self.cell_bottom_margin_points,
        }

    @classmethod
    def from_dict(cls, value: object) -> ListLayoutProfile:
        expected = {
            "name",
            "body_font_points",
            "line_spacing_points",
            "paragraph_space_after_points",
            "cell_top_margin_points",
            "cell_bottom_margin_points",
        }
        _require_exact_object(value, expected, "layout profile")
        assert isinstance(value, dict)
        return cls(**value)


@dataclass(frozen=True, slots=True)
class ListTemplateInspectionV2:
    day_count: int
    table_shapes: tuple[TableShape, ...]
    anchor_labels: tuple[str, ...]
    list_header_accessible_cells: tuple[tuple[int, int], ...]
    list_header_paragraph_count: int
    section_count: int
    page_width_points: float
    page_height_points: float
    orientation: str
    margins_points: tuple[float, float, float, float]
    header_distance_points: float
    footer_distance_points: float
    table_column_widths_points: tuple[tuple[float, ...], ...]
    merged_cell_map: tuple[str, ...]
    qr_shape_count: int
    shape_geometry_points: tuple[
        tuple[str, float, float, float, float], ...
    ]
    style_digest: str
    font_digest: str
    paragraph_digest: str
    border_digest: str
    shading_digest: str
    daily_header_digest: str
    daily_body_prototype_digest: str
    dynamic_content_digest: str
    adaptive_profiles: tuple[ListLayoutProfile, ...]

    def __post_init__(self) -> None:
        _positive_int(self.day_count, "day_count")
        expected_shapes = (
            TableShape(4, 3),
            TableShape(3, 6),
            TableShape(self.day_count + 1, 7),
            TableShape(1, 3),
        )
        if self.table_shapes != expected_shapes:
            raise ValueError("inspection must contain the four LIST table shapes")
        if self.anchor_labels != LIST_ANCHOR_LABELS:
            raise ValueError("inspection anchor labels do not match LIST")
        if self.list_header_accessible_cells != LIST_HEADER_ACCESSIBLE_CELLS:
            raise ValueError("inspection merged header cells do not match LIST")
        if self.list_header_paragraph_count != 4 or self.section_count != 1:
            raise ValueError("inspection header or section count is invalid")
        if self.orientation != "portrait":
            raise ValueError("inspection must use portrait orientation")
        width = _positive_points(self.page_width_points, "page_width_points")
        height = _positive_points(self.page_height_points, "page_height_points")
        if (
            abs(width - A4_WIDTH_POINTS) > _A4_TOLERANCE_POINTS
            or abs(height - A4_HEIGHT_POINTS) > _A4_TOLERANCE_POINTS
        ):
            raise ValueError("inspection must use A4 page geometry")
        object.__setattr__(self, "page_width_points", width)
        object.__setattr__(self, "page_height_points", height)
        if len(self.margins_points) != 4:
            raise ValueError("margins_points must contain four values")
        object.__setattr__(
            self,
            "margins_points",
            tuple(
                _positive_points(item, "margin") for item in self.margins_points
            ),
        )
        object.__setattr__(
            self,
            "header_distance_points",
            _positive_points(self.header_distance_points, "header distance"),
        )
        object.__setattr__(
            self,
            "footer_distance_points",
            _positive_points(self.footer_distance_points, "footer distance"),
        )
        if len(self.table_column_widths_points) != 4:
            raise ValueError("table_column_widths_points must contain four tables")
        normalized_widths = tuple(
            tuple(_positive_points(item, "column width") for item in widths)
            for widths in self.table_column_widths_points
        )
        if tuple(map(len, normalized_widths)) != tuple(
            shape.columns for shape in self.table_shapes
        ):
            raise ValueError("column width counts do not match table shapes")
        object.__setattr__(
            self, "table_column_widths_points", normalized_widths
        )
        if not self.merged_cell_map or not all(
            isinstance(item, str) and item for item in self.merged_cell_map
        ):
            raise ValueError("merged_cell_map must contain stable cell ranges")
        _positive_int(self.qr_shape_count, "qr_shape_count")
        if len(self.shape_geometry_points) < self.qr_shape_count:
            raise ValueError("shape geometry does not contain every QR candidate")
        normalized_geometry = []
        for shape in self.shape_geometry_points:
            if not isinstance(shape, tuple) or len(shape) != 5:
                raise ValueError("shape geometry entry is invalid")
            name, left, top, shape_width, shape_height = shape
            if not isinstance(name, str) or not name:
                raise ValueError("shape geometry name is invalid")
            normalized_geometry.append(
                (
                    name,
                    normalize_word_points(left),
                    normalize_word_points(top),
                    _positive_points(shape_width, "shape width"),
                    _positive_points(shape_height, "shape height"),
                )
            )
        object.__setattr__(
            self, "shape_geometry_points", tuple(normalized_geometry)
        )
        for field_name in (
            "style_digest",
            "font_digest",
            "paragraph_digest",
            "border_digest",
            "shading_digest",
            "daily_header_digest",
            "daily_body_prototype_digest",
            "dynamic_content_digest",
        ):
            _validate_sha256(getattr(self, field_name), field_name)
        if not self.adaptive_profiles:
            raise ValueError("inspection must contain adaptive profiles")
        names = [item.name for item in self.adaptive_profiles]
        if len(names) != len(set(names)):
            raise ValueError("adaptive profile names must be unique")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CALIBRATION_SCHEMA_VERSION,
            "day_count": self.day_count,
            "table_shapes": [shape.to_dict() for shape in self.table_shapes],
            "anchor_labels": list(self.anchor_labels),
            "list_header_accessible_cells": [
                [row, column]
                for row, column in self.list_header_accessible_cells
            ],
            "list_header_paragraph_count": self.list_header_paragraph_count,
            "section_count": self.section_count,
            "page_width_points": self.page_width_points,
            "page_height_points": self.page_height_points,
            "orientation": self.orientation,
            "margins_points": list(self.margins_points),
            "header_distance_points": self.header_distance_points,
            "footer_distance_points": self.footer_distance_points,
            "table_column_widths_points": [
                list(widths) for widths in self.table_column_widths_points
            ],
            "merged_cell_map": list(self.merged_cell_map),
            "qr_shape_count": self.qr_shape_count,
            "shape_geometry_points": [
                list(shape) for shape in self.shape_geometry_points
            ],
            "style_digest": self.style_digest,
            "font_digest": self.font_digest,
            "paragraph_digest": self.paragraph_digest,
            "border_digest": self.border_digest,
            "shading_digest": self.shading_digest,
            "daily_header_digest": self.daily_header_digest,
            "daily_body_prototype_digest": self.daily_body_prototype_digest,
            "dynamic_content_digest": self.dynamic_content_digest,
            "adaptive_profiles": [
                item.to_dict() for item in self.adaptive_profiles
            ],
        }

    @classmethod
    def from_dict(cls, value: object) -> ListTemplateInspectionV2:
        expected = {
            "schema_version",
            "day_count",
            "table_shapes",
            "anchor_labels",
            "list_header_accessible_cells",
            "list_header_paragraph_count",
            "section_count",
            "page_width_points",
            "page_height_points",
            "orientation",
            "margins_points",
            "header_distance_points",
            "footer_distance_points",
            "table_column_widths_points",
            "merged_cell_map",
            "qr_shape_count",
            "shape_geometry_points",
            "style_digest",
            "font_digest",
            "paragraph_digest",
            "border_digest",
            "shading_digest",
            "daily_header_digest",
            "daily_body_prototype_digest",
            "dynamic_content_digest",
            "adaptive_profiles",
        }
        _require_exact_object(
            value, expected, "inspection schema version 2"
        )
        assert isinstance(value, dict)
        if value["schema_version"] != CALIBRATION_SCHEMA_VERSION:
            raise ValueError("inspection does not match schema version 2")
        arrays = (
            "table_shapes",
            "anchor_labels",
            "list_header_accessible_cells",
            "margins_points",
            "table_column_widths_points",
            "merged_cell_map",
            "shape_geometry_points",
            "adaptive_profiles",
        )
        if any(not isinstance(value[key], list) for key in arrays):
            raise ValueError("inspection does not match schema version 2")
        return cls(
            day_count=value["day_count"],
            table_shapes=tuple(
                TableShape.from_dict(item) for item in value["table_shapes"]
            ),
            anchor_labels=tuple(value["anchor_labels"]),
            list_header_accessible_cells=tuple(
                _coordinate(item)
                for item in value["list_header_accessible_cells"]
            ),
            list_header_paragraph_count=value[
                "list_header_paragraph_count"
            ],
            section_count=value["section_count"],
            page_width_points=value["page_width_points"],
            page_height_points=value["page_height_points"],
            orientation=value["orientation"],
            margins_points=tuple(value["margins_points"]),
            header_distance_points=value["header_distance_points"],
            footer_distance_points=value["footer_distance_points"],
            table_column_widths_points=tuple(
                tuple(item)
                for item in value["table_column_widths_points"]
            ),
            merged_cell_map=tuple(value["merged_cell_map"]),
            qr_shape_count=value["qr_shape_count"],
            shape_geometry_points=tuple(
                tuple(item) for item in value["shape_geometry_points"]
            ),
            style_digest=value["style_digest"],
            font_digest=value["font_digest"],
            paragraph_digest=value["paragraph_digest"],
            border_digest=value["border_digest"],
            shading_digest=value["shading_digest"],
            daily_header_digest=value["daily_header_digest"],
            daily_body_prototype_digest=value[
                "daily_body_prototype_digest"
            ],
            dynamic_content_digest=value["dynamic_content_digest"],
            adaptive_profiles=tuple(
                ListLayoutProfile.from_dict(item)
                for item in value["adaptive_profiles"]
            ),
        )


@dataclass(frozen=True, slots=True)
class ListCalibrationSample:
    source_sha256: str
    day_count: int
    normalized_structure_fingerprint: str
    inspection: ListTemplateInspectionV2

    def __post_init__(self) -> None:
        _validate_nonzero_sha256(
            self.source_sha256, "sample source SHA-256"
        )
        _positive_int(self.day_count, "sample day_count")
        _validate_nonzero_sha256(
            self.normalized_structure_fingerprint,
            "sample normalized structure fingerprint",
        )
        if self.day_count != self.inspection.day_count:
            raise ValueError("sample day count does not match inspection")
        if (
            self.normalized_structure_fingerprint
            != normalized_structure_fingerprint(self.inspection)
        ):
            raise ValueError("sample fingerprint does not match inspection")

    @classmethod
    def from_inspection(
        cls,
        source_sha256: str,
        inspection: ListTemplateInspectionV2,
    ) -> ListCalibrationSample:
        return cls(
            source_sha256=source_sha256,
            day_count=inspection.day_count,
            normalized_structure_fingerprint=(
                normalized_structure_fingerprint(inspection)
            ),
            inspection=inspection,
        )


@dataclass(frozen=True, slots=True)
class CalibrationSampleEvidence:
    source_sha256: str
    day_count: int
    normalized_structure_fingerprint: str

    def __post_init__(self) -> None:
        _validate_nonzero_sha256(
            self.source_sha256, "sample source SHA-256"
        )
        _positive_int(self.day_count, "sample day count")
        _validate_nonzero_sha256(
            self.normalized_structure_fingerprint,
            "sample normalized structure fingerprint",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_sha256": self.source_sha256,
            "day_count": self.day_count,
            "normalized_structure_fingerprint": (
                self.normalized_structure_fingerprint
            ),
        }

    @classmethod
    def from_dict(cls, value: object) -> CalibrationSampleEvidence:
        expected = {
            "source_sha256",
            "day_count",
            "normalized_structure_fingerprint",
        }
        _require_exact_object(value, expected, "calibration sample evidence")
        assert isinstance(value, dict)
        return cls(**value)


@dataclass(frozen=True, slots=True)
class CalibrationComparison:
    samples: tuple[ListCalibrationSample, ...]
    base_sample_sha256: str
    normalized_structure_fingerprint: str
    normalized_layout: tuple[tuple[str, Any], ...]
    layout_profiles: tuple[ListLayoutProfile, ...]
    minimum_font_points: float


@dataclass(frozen=True, slots=True)
class HeaderParagraphObservation:
    paragraph_number: int
    visible_character_count: int
    fixed_label_ids: tuple[str, ...]
    fullwidth_colon_count: int
    inline_shape_count: int
    ends_with_cell_marker: bool

    def __post_init__(self) -> None:
        _positive_int(self.paragraph_number, "paragraph number")
        for field_name in (
            "visible_character_count",
            "fullwidth_colon_count",
            "inline_shape_count",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        allowed = {"group_code", "group_name"}
        if (
            not isinstance(self.fixed_label_ids, tuple)
            or len(self.fixed_label_ids) != len(set(self.fixed_label_ids))
            or any(item not in allowed for item in self.fixed_label_ids)
        ):
            raise ValueError("fixed_label_ids contains an unsupported label")
        if not isinstance(self.ends_with_cell_marker, bool):
            raise ValueError("ends_with_cell_marker must be boolean")

    def to_dict(self) -> dict[str, Any]:
        return {
            "paragraph_number": self.paragraph_number,
            "visible_character_count": self.visible_character_count,
            "fixed_label_ids": list(self.fixed_label_ids),
            "fullwidth_colon_count": self.fullwidth_colon_count,
            "inline_shape_count": self.inline_shape_count,
            "ends_with_cell_marker": self.ends_with_cell_marker,
        }


@dataclass(frozen=True, slots=True)
class ListHeaderDiagnosticEvidence:
    source_sha256: str
    list_header_paragraph_count: int
    paragraphs: tuple[HeaderParagraphObservation, ...]

    def __post_init__(self) -> None:
        _validate_nonzero_sha256(self.source_sha256, "sample source SHA-256")
        _positive_int(
            self.list_header_paragraph_count,
            "list header paragraph count",
        )
        if (
            len(self.paragraphs) != self.list_header_paragraph_count
            or tuple(item.paragraph_number for item in self.paragraphs)
            != tuple(range(1, self.list_header_paragraph_count + 1))
        ):
            raise ValueError("header paragraph observations are not contiguous")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_sha256": self.source_sha256,
            "field_path": "list_header_paragraph_count",
            "observed_value": self.list_header_paragraph_count,
            "paragraphs": [item.to_dict() for item in self.paragraphs],
        }


@dataclass(frozen=True, slots=True)
class ListHeaderDiagnosticResult:
    word_version: str
    samples: tuple[ListHeaderDiagnosticEvidence, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.word_version, str) or not self.word_version:
            raise ValueError("Word version is required")
        if len(self.samples) != 3 or len(
            {item.source_sha256 for item in self.samples}
        ) != 3:
            raise ValueError("header diagnosis requires three unique samples")

    @property
    def classification(self) -> str:
        observed = {
            item.list_header_paragraph_count for item in self.samples
        }
        if observed == {4}:
            return "EXPECTED_CONTRACT_MATCH"
        if len(observed) == 1:
            return "COMMON_EXPECTED_CONTRACT_MISMATCH"
        return "SAMPLE_CONTRACT_CONFLICT"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "status": "DIAGNOSED",
            "classification": self.classification,
            "word_version": self.word_version,
            "expected_contract": {
                "field_path": "list_header_paragraph_count",
                "expected_value": 4,
            },
            "source_hashes_unchanged": True,
            "samples": [item.to_dict() for item in self.samples],
        }


@dataclass(frozen=True, slots=True)
class GateC5992Checkpoint:
    phase: str
    sample_id: str
    operation: str
    field_id: str
    table_number: int
    row_number: int
    column_number: int
    paragraph_number: int

    def __post_init__(self) -> None:
        if self.phase not in _GATE_C_5992_PHASES:
            raise ValueError("Gate C 5992 checkpoint phase is invalid")
        if self.sample_id not in {
            "sample-000",
            "sample-001",
            "sample-002",
            "sample-003",
        }:
            raise ValueError("Gate C 5992 checkpoint sample ID is invalid")
        if self.operation not in _GATE_C_5992_OPERATIONS:
            raise ValueError("Gate C 5992 checkpoint operation is invalid")
        if self.field_id not in _GATE_C_5992_FIELDS:
            raise ValueError("Gate C 5992 checkpoint field ID is invalid")
        for name in (
            "table_number",
            "row_number",
            "column_number",
            "paragraph_number",
        ):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= 32
            ):
                raise ValueError(f"Gate C 5992 checkpoint {name} is invalid")
        if self.phase == "inspect-source" and self.sample_id == "sample-000":
            raise ValueError("source inspection checkpoint requires a sample ID")
        if self.phase == "complete" and (
            self.sample_id != "sample-000" or self.operation != "complete"
        ):
            raise ValueError("completed Gate C 5992 checkpoint is invalid")

    @property
    def field_path(self) -> str:
        if self.phase == "inspect-source":
            sample_index = int(self.sample_id[-3:]) - 1
            return f"samples[{sample_index}].inspection.{self.field_id}"
        if self.phase == "calibrate-copy":
            return f"master_working_copy.{self.field_id}"
        return "diagnostic"

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "sample_id": self.sample_id,
            "operation": self.operation,
            "field_path": self.field_path,
            "table_number": self.table_number,
            "row_number": self.row_number,
            "column_number": self.column_number,
            "paragraph_number": self.paragraph_number,
        }


@dataclass(frozen=True, slots=True)
class GateC5992DiagnosticResult:
    word_version: str
    source_sha256: tuple[str, str, str]
    classification: str
    completed_source_inspections: int
    selected_base_sample_id: str
    checkpoint: GateC5992Checkpoint
    hresult: int
    hresult_hex: str
    low_word_error_number: int
    adapter_code: str

    def __post_init__(self) -> None:
        if not isinstance(self.word_version, str) or not self.word_version:
            raise ValueError("Word version is required")
        if len(self.source_sha256) != 3 or len(set(self.source_sha256)) != 3:
            raise ValueError("Gate C 5992 diagnosis requires three unique samples")
        for item in self.source_sha256:
            _validate_nonzero_sha256(item, "sample source SHA-256")
        if self.classification not in {"ERROR_OBSERVED", "NOT_REPRODUCED"}:
            raise ValueError("Gate C 5992 classification is invalid")
        if (
            isinstance(self.completed_source_inspections, bool)
            or not isinstance(self.completed_source_inspections, int)
            or not 0 <= self.completed_source_inspections <= 3
        ):
            raise ValueError("completed source inspection count is invalid")
        if self.selected_base_sample_id not in {
            "sample-000",
            "sample-001",
            "sample-002",
            "sample-003",
        }:
            raise ValueError("selected base sample ID is invalid")
        if (
            isinstance(self.hresult, bool)
            or not isinstance(self.hresult, int)
            or not -(2**31) <= self.hresult < 2**31
        ):
            raise ValueError("Gate C 5992 HRESULT is invalid")
        if self.hresult_hex != f"0x{self.hresult & 0xFFFFFFFF:08X}":
            raise ValueError("Gate C 5992 hexadecimal HRESULT is invalid")
        if self.low_word_error_number != (self.hresult & 0xFFFF):
            raise ValueError("Gate C 5992 low-word error number is invalid")
        if (
            not isinstance(self.adapter_code, str)
            or re.fullmatch(r"NONE|[A-Z][A-Z0-9_]{1,79}", self.adapter_code)
            is None
        ):
            raise ValueError("Gate C 5992 adapter code is invalid")
        if self.classification == "NOT_REPRODUCED" and (
            self.completed_source_inspections != 3
            or self.selected_base_sample_id == "sample-000"
            or self.hresult != 0
            or self.adapter_code != "NONE"
            or self.checkpoint.phase != "complete"
        ):
            raise ValueError("non-reproduced Gate C 5992 result is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "status": "DIAGNOSED",
            "classification": self.classification,
            "word_version": self.word_version,
            "source_hashes_unchanged": True,
            "source_sha256": list(self.source_sha256),
            "completed_source_inspections": self.completed_source_inspections,
            "selected_base_sample_id": self.selected_base_sample_id,
            "checkpoint": self.checkpoint.to_dict(),
            "error": {
                "hresult": self.hresult,
                "hresult_hex": self.hresult_hex,
                "low_word_error_number": self.low_word_error_number,
                "adapter_code": self.adapter_code,
            },
        }


@dataclass(frozen=True, slots=True)
class ListCalibrationManifest:
    schema_version: int
    generator_version: str
    sample_evidence: tuple[CalibrationSampleEvidence, ...]
    base_sample_sha256: str
    master_sha256: str
    master_structure_fingerprint: str
    normalized_layout: tuple[tuple[str, Any], ...]
    layout_profiles: tuple[ListLayoutProfile, ...]
    minimum_font_points: float
    continuation_group_header: bool
    repeat_daily_header: bool
    allow_day_row_split: bool
    qr_policy: str
    created_at: str
    word_version: str
    calibration_report_sha256: str

    def __post_init__(self) -> None:
        if self.schema_version != CALIBRATION_SCHEMA_VERSION:
            raise ValueError("calibration manifest schema version must be 2")
        if self.generator_version != CALIBRATION_GENERATOR_VERSION:
            raise ValueError(
                "calibration manifest generator version is invalid"
            )
        if len(self.sample_evidence) != 3 or len(
            {item.source_sha256 for item in self.sample_evidence}
        ) != 3:
            raise ValueError(
                "calibration manifest requires three unique samples"
            )
        fingerprints = {
            item.normalized_structure_fingerprint
            for item in self.sample_evidence
        }
        if fingerprints != {self.master_structure_fingerprint}:
            raise ValueError(
                "sample and master structure fingerprints differ"
            )
        for field_name in (
            "base_sample_sha256",
            "master_sha256",
            "master_structure_fingerprint",
            "calibration_report_sha256",
        ):
            _validate_nonzero_sha256(getattr(self, field_name), field_name)
        if self.base_sample_sha256 not in {
            item.source_sha256 for item in self.sample_evidence
        }:
            raise ValueError("base sample is not present in evidence")
        if not self.normalized_layout:
            raise ValueError("normalized layout is required")
        if (
            not self.layout_profiles
            or self.layout_profiles[0].name != "normal"
        ):
            raise ValueError(
                "ordered layout profiles must start with normal"
            )
        minimum = _positive_points(
            self.minimum_font_points, "minimum font"
        )
        object.__setattr__(self, "minimum_font_points", minimum)
        if any(
            item.body_font_points < minimum
            for item in self.layout_profiles
        ):
            raise ValueError(
                "layout profile is below the common minimum font"
            )
        if (
            self.continuation_group_header is not True
            or self.repeat_daily_header is not True
            or self.allow_day_row_split is not False
            or self.qr_policy != "first_page_only"
        ):
            raise ValueError("calibration pagination policy is invalid")
        for field_name in ("created_at", "word_version"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{field_name} must be non-empty text")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generator_version": self.generator_version,
            "sample_evidence": [
                item.to_dict() for item in self.sample_evidence
            ],
            "base_sample_sha256": self.base_sample_sha256,
            "master_sha256": self.master_sha256,
            "master_structure_fingerprint": (
                self.master_structure_fingerprint
            ),
            "normalized_layout": _thaw_object(self.normalized_layout),
            "layout_profiles": [
                item.to_dict() for item in self.layout_profiles
            ],
            "minimum_font_points": self.minimum_font_points,
            "continuation_group_header": self.continuation_group_header,
            "repeat_daily_header": self.repeat_daily_header,
            "allow_day_row_split": self.allow_day_row_split,
            "qr_policy": self.qr_policy,
            "created_at": self.created_at,
            "word_version": self.word_version,
            "calibration_report_sha256": (
                self.calibration_report_sha256
            ),
        }

    def to_canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def from_dict(cls, value: object) -> ListCalibrationManifest:
        expected = {
            "schema_version",
            "generator_version",
            "sample_evidence",
            "base_sample_sha256",
            "master_sha256",
            "master_structure_fingerprint",
            "normalized_layout",
            "layout_profiles",
            "minimum_font_points",
            "continuation_group_header",
            "repeat_daily_header",
            "allow_day_row_split",
            "qr_policy",
            "created_at",
            "word_version",
            "calibration_report_sha256",
        }
        _require_exact_object(
            value, expected, "calibration manifest schema version 2"
        )
        assert isinstance(value, dict)
        if not isinstance(value["sample_evidence"], list) or not isinstance(
            value["layout_profiles"], list
        ):
            raise ValueError("calibration manifest arrays are invalid")
        if not isinstance(value["normalized_layout"], dict):
            raise ValueError(
                "calibration manifest normalized layout is invalid"
            )
        return cls(
            schema_version=value["schema_version"],
            generator_version=value["generator_version"],
            sample_evidence=tuple(
                CalibrationSampleEvidence.from_dict(item)
                for item in value["sample_evidence"]
            ),
            base_sample_sha256=value["base_sample_sha256"],
            master_sha256=value["master_sha256"],
            master_structure_fingerprint=value[
                "master_structure_fingerprint"
            ],
            normalized_layout=_freeze_object(value["normalized_layout"]),
            layout_profiles=tuple(
                ListLayoutProfile.from_dict(item)
                for item in value["layout_profiles"]
            ),
            minimum_font_points=value["minimum_font_points"],
            continuation_group_header=value[
                "continuation_group_header"
            ],
            repeat_daily_header=value["repeat_daily_header"],
            allow_day_row_split=value["allow_day_row_split"],
            qr_policy=value["qr_policy"],
            created_at=value["created_at"],
            word_version=value["word_version"],
            calibration_report_sha256=value[
                "calibration_report_sha256"
            ],
        )


@dataclass(frozen=True, slots=True)
class ListInspectionBatchResult:
    samples: tuple[ListCalibrationSample, ...]
    word_version: str


@dataclass(frozen=True, slots=True)
class CalibrationConflictDiagnosisResult:
    word_version: str
    source_sha256: tuple[str, str, str]
    classification: str
    field_paths: tuple[str, ...]
    conflict_matrix: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class ListComponentDiagnosisResult:
    word_version: str
    source_sha256: tuple[str, str, str]
    samples: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class ListCalibrationBuildResult:
    master_path: Path
    manifest_path: Path
    master_sha256: str
    manifest_sha256: str
    word_version: str
    sample_evidence: tuple[CalibrationSampleEvidence, ...]


def diagnose_list_header_contract(
    sample_paths: tuple[Path, ...],
    *,
    adapter: WordCalibrationAdapter,
    timeout_seconds: int = 120,
) -> ListHeaderDiagnosticResult:
    samples = _resolve_sample_paths(sample_paths)
    if timeout_seconds <= 0:
        raise ValueError("LIST header diagnosis timeout must be positive")
    before = tuple(_sha256_file(path) for path in samples)
    with tempfile.TemporaryDirectory(
        prefix="easytravel-list-header-diagnose-"
    ) as temp:
        work_dir = Path(temp)
        job_path = work_dir / "word-job.json"
        report_path = work_dir / "header-diagnostic-report.json"
        job = {
            "schema_version": 2,
            "action": "diagnose-header-v2",
            "ownership_nonce": secrets.token_hex(16),
            "word_pid_path": str(work_dir / "word-owner.json"),
            "report_path": str(report_path),
            "sample_paths": [str(path) for path in samples],
        }
        _write_json_exclusive(job_path, job)
        adapter.run(job_path, timeout_seconds=timeout_seconds)
        report = _read_header_diagnostic_report(report_path)
    after = tuple(_sha256_file(path) for path in samples)
    if after != before:
        raise CalibrationSourceChangedError()
    return ListHeaderDiagnosticResult(
        word_version=report["word_version"],
        samples=tuple(
            ListHeaderDiagnosticEvidence(
                source_sha256=source_hash,
                list_header_paragraph_count=item[
                    "list_header_paragraph_count"
                ],
                paragraphs=tuple(
                    HeaderParagraphObservation(**paragraph)
                    for paragraph in item["paragraphs"]
                ),
            )
            for source_hash, item in zip(
                before, report["samples"], strict=True
            )
        ),
    )


def diagnose_list_components(
    sample_paths: tuple[Path, ...],
    *,
    adapter: WordCalibrationAdapter,
    timeout_seconds: int = 120,
) -> ListComponentDiagnosisResult:
    """Read only allowlisted formatting components from three LIST samples."""
    samples = _resolve_sample_paths(sample_paths)
    if timeout_seconds <= 0:
        raise ValueError("LIST component diagnosis timeout must be positive")
    before = tuple(_sha256_file(path) for path in samples)
    with tempfile.TemporaryDirectory(
        prefix="easytravel-list-component-diagnose-"
    ) as temp:
        work_dir = Path(temp)
        job_path = work_dir / "word-job.json"
        report_path = work_dir / "component-diagnostic-report.json"
        job = {
            "schema_version": 2,
            "action": "diagnose-components-v2",
            "ownership_nonce": secrets.token_hex(16),
            "word_pid_path": str(work_dir / "word-owner.json"),
            "report_path": str(report_path),
            "sample_paths": [str(path) for path in samples],
        }
        _write_json_exclusive(job_path, job)
        adapter.run(job_path, timeout_seconds=timeout_seconds)
        report = _read_component_diagnostic_report(report_path)
    after = tuple(_sha256_file(path) for path in samples)
    if after != before:
        raise CalibrationSourceChangedError()
    return ListComponentDiagnosisResult(
        word_version=report["word_version"],
        source_sha256=before,
        samples=tuple(item["evidence"] for item in report["samples"]),
    )


def load_component_diagnosis_artifact(
    path: Path,
) -> ListComponentDiagnosisResult:
    payload = _read_json_object(path.expanduser().resolve(), "component diagnosis")
    label = "component diagnosis artifact"
    _require_exact_schema_one_object(
        payload,
        {
            "schema_version",
            "status",
            "command",
            "stage",
            "word_version",
            "source_sha256",
            "samples",
        },
        label,
    )
    if (
        payload["schema_version"] != 1
        or payload["status"] != "ok"
        or payload["command"] != "diagnose-list-components"
        or payload["stage"] != "component-evidence"
        or not isinstance(payload["word_version"], str)
        or not payload["word_version"]
        or not isinstance(payload["source_sha256"], list)
        or len(payload["source_sha256"]) != 3
        or not isinstance(payload["samples"], list)
        or len(payload["samples"]) != 3
    ):
        raise ValueError(f"{label} does not match schema version 1")
    source_hashes = tuple(
        _validate_nonzero_sha256(value, "component source SHA-256")
        for value in payload["source_sha256"]
    )
    if len(set(source_hashes)) != 3:
        raise ValueError(f"{label} does not match schema version 1")
    for evidence in payload["samples"]:
        _validate_component_evidence(evidence, label)
    return ListComponentDiagnosisResult(
        word_version=payload["word_version"],
        source_sha256=source_hashes,
        samples=tuple(payload["samples"]),
    )


def load_component_normalization_decision_table(
    path: Path,
) -> dict[str, Any]:
    payload = _read_json_object(
        path.expanduser().resolve(),
        "component normalization decision table",
    )
    _validate_component_normalization_decision_table(payload)
    return json.loads(json.dumps(payload))


def build_component_normalization_decision_table(
    diagnosis: ListComponentDiagnosisResult,
) -> dict[str, Any]:
    """Build a fail-closed OP decision table without selecting a majority."""
    if not isinstance(diagnosis, ListComponentDiagnosisResult):
        raise TypeError("component diagnosis result is required")
    if len(diagnosis.samples) != 3 or len(diagnosis.source_sha256) != 3:
        raise ValueError("component decision table requires three samples")
    source_hashes = tuple(
        _validate_nonzero_sha256(value, "component source SHA-256")
        for value in diagnosis.source_sha256
    )
    if len(set(source_hashes)) != 3:
        raise ValueError("component decision table sources must be unique")
    for evidence in diagnosis.samples:
        _validate_component_evidence(
            evidence, "component normalization evidence"
        )

    family_policy = (
        ("styles", "cell_id", "style_bundle"),
        ("fonts", "cell_id", "font_bundle"),
        ("paragraphs", "cell_id", "paragraph_bundle"),
        ("borders", "border_id", "border_bundle"),
        ("daily_header", "cell_id", "daily_header_bundle"),
        ("daily_body", "cell_id", "derived_audit"),
        ("shapes", "shape_id", "geometry_bundle"),
    )
    prototype_ids = {
        f"table-{table:03d}-row-{row:03d}-column-{column:03d}"
        for table, row, count in ((1, 2, 3), (2, 2, 6), (3, 2, 7), (4, 1, 3))
        for column in range(1, count + 1)
    }
    border_sides = {
        "top", "left", "bottom", "right", "diagonal-down", "diagonal-up"
    }
    expected_identity_sets = {
        "styles": prototype_ids,
        "fonts": prototype_ids,
        "paragraphs": prototype_ids,
        "borders": {
            f"{component_id}-{side}"
            for component_id in prototype_ids
            for side in border_sides
        },
        "daily_header": {
            f"table-003-row-001-column-{column:03d}"
            for column in range(1, 8)
        },
        "daily_body": {
            f"table-003-row-002-column-{column:03d}"
            for column in range(1, 8)
        },
    }
    maps_by_family: dict[str, tuple[dict[str, dict[str, Any]], ...]] = {}
    blockers: list[dict[str, str]] = []
    for family, identity_key, _selection_unit in family_policy:
        family_maps = []
        duplicate_found = False
        for evidence in diagnosis.samples:
            items = evidence[family]
            assert isinstance(items, list)
            component_map = {
                str(item[identity_key]): item for item in items
            }
            if len(component_map) != len(items):
                duplicate_found = True
            family_maps.append(component_map)
        maps = tuple(family_maps)
        maps_by_family[family] = maps
        if duplicate_found:
            blockers.append(
                {
                    "component_family": family,
                    "reason": "DUPLICATE_COMPONENT_ID",
                }
            )
            continue
        identity_sets = tuple(set(item) for item in maps)
        if identity_sets[0] != identity_sets[1] or identity_sets[1] != identity_sets[2]:
            blockers.append(
                {
                    "component_family": family,
                    "reason": "COMPONENT_ID_SET_CHANGED",
                }
            )
            continue
        if (
            family in expected_identity_sets
            and identity_sets[0] != expected_identity_sets[family]
        ) or (family == "shapes" and not identity_sets[0]):
            blockers.append(
                {
                    "component_family": family,
                    "reason": "REQUIRED_COMPONENT_SET_INVALID",
                }
            )
            continue
        if family == "shapes" and any(
            len({str(item[component_id]["kind"]) for item in maps}) != 1
            for component_id in identity_sets[0]
        ):
            blockers.append(
                {
                    "component_family": family,
                    "reason": "SHAPE_KIND_CHANGED",
                }
            )

    policy = _component_normalization_policy()
    if blockers:
        return {
            "schema_version": 1,
            "stage": "component-normalization-decision",
            "classification": "COMPONENT_CONTRACT_CONFLICT",
            "source_sha256": list(source_hashes),
            "policy": policy,
            "preserved_unanimous_counts": {},
            "decisions": [],
            "derived_audits": [],
            "blockers": blockers,
        }

    decisions = []
    derived_audits = []
    preserved_counts: dict[str, int] = {}
    mixed_value_found = False
    for family, identity_key, selection_unit in family_policy:
        maps = maps_by_family[family]
        preserved = 0
        for component_id in sorted(maps[0]):
            components = tuple(item[component_id] for item in maps)
            canonical = tuple(
                _canonical_layout_value(item) for item in components
            )
            if canonical[0] == canonical[1] == canonical[2]:
                preserved += 1
                continue
            if family == "daily_body":
                derived_audits.append(
                    {
                        "component_family": family,
                        "component_id": component_id,
                        "status": "VERIFY_AFTER_COMPONENT_NORMALIZATION",
                    }
                )
                continue
            changed_properties = sorted(
                key
                for key in components[0]
                if key != identity_key
                and len(
                    {
                        _canonical_layout_value(item[key])
                        for item in components
                    }
                )
                > 1
            )
            sentinel_flags = tuple(
                _contains_word_mixed_value(item) for item in components
            )
            status = (
                "BLOCKED_MIXED_VALUE"
                if any(sentinel_flags)
                else "REQUIRES_OP_BASE"
            )
            if any(sentinel_flags):
                mixed_value_found = True
            decisions.append(
                {
                    "decision_id": f"{family}:{component_id}",
                    "component_family": family,
                    "component_id": component_id,
                    "selection_unit": selection_unit,
                    "changed_properties": changed_properties,
                    "status": status,
                    "eligible_source_sha256": [
                        source_hash
                        for source_hash, blocked in zip(
                            source_hashes, sentinel_flags, strict=True
                        )
                        if not blocked
                    ],
                    "ineligible_source_sha256": [
                        source_hash
                        for source_hash, blocked in zip(
                            source_hashes, sentinel_flags, strict=True
                        )
                        if blocked
                    ],
                    "samples": [
                        {
                            "source_sha256": source_hash,
                            "component_value_sha256": hashlib.sha256(
                                value.encode("utf-8")
                            ).hexdigest(),
                            "eligible_as_base": not blocked,
                        }
                        for source_hash, value, blocked in zip(
                            source_hashes,
                            canonical,
                            sentinel_flags,
                            strict=True,
                        )
                    ],
                }
            )
        preserved_counts[family] = preserved
    classification = (
        "BLOCKED_MIXED_VALUE"
        if mixed_value_found
        else "REQUIRES_OP_DECISION"
        if decisions
        else "DERIVED_AUDIT_PENDING"
        if derived_audits
        else "NORMALIZATION_READY"
    )
    return {
        "schema_version": 1,
        "stage": "component-normalization-decision",
        "classification": classification,
        "source_sha256": list(source_hashes),
        "policy": policy,
        "preserved_unanimous_counts": preserved_counts,
        "decisions": decisions,
        "derived_audits": derived_audits,
        "blockers": [],
    }


def _contains_word_mixed_value(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value == 9999999
    if isinstance(value, dict):
        return any(_contains_word_mixed_value(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_word_mixed_value(item) for item in value)
    return False


def component_normalization_decision_table_sha256(
    table: dict[str, Any],
) -> str:
    _validate_component_normalization_decision_table(table)
    return hashlib.sha256(
        _canonical_layout_value(table).encode("utf-8")
    ).hexdigest()


def build_component_normalization_choice_worksheet(
    diagnosis: ListComponentDiagnosisResult,
    table: dict[str, Any],
) -> dict[str, Any]:
    """Expose only allowlisted values needed for an explicit OP base choice."""
    expected = build_component_normalization_decision_table(diagnosis)
    _validate_component_normalization_decision_table(table)
    if table != expected:
        raise ValueError("component diagnosis and decision table do not match")

    source_hashes = tuple(table["source_sha256"])
    sample_labels = [
        {
            "sample_id": f"sample-{index:03d}",
            "source_sha256": source_hash,
        }
        for index, source_hash in enumerate(source_hashes, start=1)
    ]
    identity_keys = {
        "styles": "cell_id",
        "fonts": "cell_id",
        "paragraphs": "cell_id",
        "borders": "border_id",
        "daily_header": "cell_id",
        "shapes": "shape_id",
    }
    component_maps = {
        family: tuple(
            {
                str(item[identity_key]): item
                for item in evidence[family]
            }
            for evidence in diagnosis.samples
        )
        for family, identity_key in identity_keys.items()
    }
    decisions = []
    for decision in table["decisions"]:
        family = decision["component_family"]
        component_id = decision["component_id"]
        options = []
        for label, sample, component_map in zip(
            sample_labels,
            decision["samples"],
            component_maps[family],
            strict=True,
        ):
            component = component_map.get(component_id)
            if component is None:
                raise ValueError(
                    "component diagnosis and decision table do not match"
                )
            component_hash = hashlib.sha256(
                _canonical_layout_value(component).encode("utf-8")
            ).hexdigest()
            if (
                sample["source_sha256"] != label["source_sha256"]
                or sample["component_value_sha256"] != component_hash
            ):
                raise ValueError(
                    "component diagnosis and decision table do not match"
                )
            options.append(
                {
                    "sample_id": label["sample_id"],
                    "source_sha256": label["source_sha256"],
                    "component_value_sha256": component_hash,
                    "eligible_as_base": sample["eligible_as_base"],
                    "safe_values": {
                        key: component[key]
                        for key in decision["changed_properties"]
                    },
                }
            )
        decisions.append(
            {
                "decision_id": decision["decision_id"],
                "component_family": family,
                "component_id": component_id,
                "selection_unit": decision["selection_unit"],
                "changed_properties": list(
                    decision["changed_properties"]
                ),
                "status": decision["status"],
                "options": options,
            }
        )
    return {
        "schema_version": 1,
        "stage": "component-normalization-choice-review",
        "classification": table["classification"],
        "decision_table_sha256": (
            component_normalization_decision_table_sha256(table)
        ),
        "sample_labels": sample_labels,
        "policy": {
            "automatic_majority_selection": False,
            "selection_instruction": (
                "SELECT_ONE_ELIGIBLE_BASE_PER_DECISION"
            ),
            "sentinel_option_action": "INELIGIBLE",
        },
        "decisions": decisions,
        "derived_audits": json.loads(json.dumps(table["derived_audits"])),
        "blockers": json.loads(json.dumps(table["blockers"])),
    }


def build_blank_component_normalization_choices(
    table: dict[str, Any],
) -> dict[str, Any]:
    """Build an intentionally incomplete artifact for explicit OP entry."""
    _validate_component_normalization_decision_table(table)
    return {
        "schema_version": 1,
        "decision_table_sha256": (
            component_normalization_decision_table_sha256(table)
        ),
        "source_sha256": list(table["source_sha256"]),
        "choices": [
            {
                "decision_id": decision["decision_id"],
                "selected_source_sha256": "",
                "selected_component_value_sha256": "",
            }
            for decision in table["decisions"]
        ],
    }


def validate_component_normalization_choices(
    table: dict[str, Any],
    artifact: object,
) -> dict[str, Any]:
    label = "OP normalization choices"
    _validate_component_normalization_decision_table(table)
    _require_exact_schema_one_object(
        artifact,
        {
            "schema_version",
            "decision_table_sha256",
            "source_sha256",
            "choices",
        },
        label,
    )
    assert isinstance(artifact, dict)
    if (
        artifact["schema_version"] != 1
        or artifact["decision_table_sha256"]
        != component_normalization_decision_table_sha256(table)
        or artifact["source_sha256"] != table["source_sha256"]
        or not isinstance(artifact["choices"], list)
        or table["classification"] == "COMPONENT_CONTRACT_CONFLICT"
    ):
        raise ValueError(f"{label} does not match decision table")
    decisions = {item["decision_id"]: item for item in table["decisions"]}
    choices: dict[str, dict[str, Any]] = {}
    for choice in artifact["choices"]:
        _require_exact_schema_one_object(
            choice,
            {
                "decision_id",
                "selected_source_sha256",
                "selected_component_value_sha256",
            },
            label,
        )
        assert isinstance(choice, dict)
        decision_id = choice["decision_id"]
        if not isinstance(decision_id, str) or decision_id in choices:
            raise ValueError(f"{label} does not match decision table")
        source_hash = _validate_sha256(
            choice["selected_source_sha256"], label
        )
        value_hash = _validate_sha256(
            choice["selected_component_value_sha256"], label
        )
        decision = decisions.get(decision_id)
        if decision is None or source_hash not in decision[
            "eligible_source_sha256"
        ]:
            raise ValueError(f"{label} does not match decision table")
        matching = [
            item
            for item in decision["samples"]
            if item["source_sha256"] == source_hash
            and item["component_value_sha256"] == value_hash
            and item["eligible_as_base"] is True
        ]
        if len(matching) != 1:
            raise ValueError(f"{label} does not match decision table")
        choices[decision_id] = choice
    if set(choices) != set(decisions):
        raise ValueError(f"{label} does not match decision table")
    return json.loads(json.dumps(artifact))


def _component_normalization_policy() -> dict[str, Any]:
    return {
        "contract_fixed": ["component_identity_set", "shape_kind"],
        "unanimous_components": "PRESERVE_UNANIMOUS",
        "conflicting_components": "REQUIRES_OP_BASE",
        "mixed_value_sentinel": 9999999,
        "mixed_value_action": "BLOCK_SOURCE_AS_BASE",
        "floating_shape_selection": "GEOMETRY_BUNDLE",
        "automatic_majority_selection": False,
        "op_choice_binding": "SOURCE_AND_COMPONENT_SHA256",
    }


def _validate_component_normalization_decision_table(
    table: object,
) -> None:
    label = "component normalization decision table"
    top_keys = {
        "schema_version",
        "stage",
        "classification",
        "source_sha256",
        "policy",
        "preserved_unanimous_counts",
        "decisions",
        "derived_audits",
        "blockers",
    }
    _require_exact_schema_one_object(table, top_keys, label)
    assert isinstance(table, dict)
    classifications = {
        "COMPONENT_CONTRACT_CONFLICT",
        "BLOCKED_MIXED_VALUE",
        "REQUIRES_OP_DECISION",
        "DERIVED_AUDIT_PENDING",
        "NORMALIZATION_READY",
    }
    if (
        table["schema_version"] != 1
        or table["stage"] != "component-normalization-decision"
        or table["classification"] not in classifications
        or table["policy"] != _component_normalization_policy()
        or not isinstance(table["source_sha256"], list)
        or len(table["source_sha256"]) != 3
        or not isinstance(table["preserved_unanimous_counts"], dict)
        or not isinstance(table["decisions"], list)
        or not isinstance(table["derived_audits"], list)
        or not isinstance(table["blockers"], list)
    ):
        raise ValueError(f"{label} does not match schema version 1")
    sources = tuple(
        _validate_nonzero_sha256(value, label)
        for value in table["source_sha256"]
    )
    if len(set(sources)) != 3:
        raise ValueError(f"{label} does not match schema version 1")
    _validate_normalization_blockers(table["blockers"], label)
    _validate_normalization_audits(table["derived_audits"], label)
    _validate_normalization_decisions(table["decisions"], sources, label)
    family_names = {
        "styles", "fonts", "paragraphs", "borders",
        "daily_header", "daily_body", "shapes",
    }
    counts = table["preserved_unanimous_counts"]
    if counts and (
        set(counts) != family_names
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in counts.values()
        )
    ):
        raise ValueError(f"{label} does not match schema version 1")
    if counts:
        decision_counts = {
            family: sum(
                item["component_family"] == family
                for item in table["decisions"]
            )
            for family in family_names
        }
        audit_counts = {
            family: sum(
                item["component_family"] == family
                for item in table["derived_audits"]
            )
            for family in family_names
        }
        expected_counts = {
            "styles": 19,
            "fonts": 19,
            "paragraphs": 19,
            "borders": 114,
            "daily_header": 7,
            "daily_body": 7,
        }
        if any(
            counts[family]
            + decision_counts[family]
            + audit_counts[family]
            != expected
            for family, expected in expected_counts.items()
        ) or counts["shapes"] + decision_counts["shapes"] < 1:
            raise ValueError(f"{label} does not match schema version 1")
    has_mixed = any(
        item["status"] == "BLOCKED_MIXED_VALUE"
        for item in table["decisions"]
    )
    expected_classification = (
        "COMPONENT_CONTRACT_CONFLICT"
        if table["blockers"]
        else "BLOCKED_MIXED_VALUE"
        if has_mixed
        else "REQUIRES_OP_DECISION"
        if table["decisions"]
        else "DERIVED_AUDIT_PENDING"
        if table["derived_audits"]
        else "NORMALIZATION_READY"
    )
    if (
        table["classification"] != expected_classification
        or (table["blockers"] and table["decisions"])
        or (table["blockers"] and counts)
    ):
        raise ValueError(f"{label} does not match schema version 1")


def _validate_normalization_blockers(value: list[Any], label: str) -> None:
    allowed = {
        "DUPLICATE_COMPONENT_ID",
        "COMPONENT_ID_SET_CHANGED",
        "REQUIRED_COMPONENT_SET_INVALID",
        "SHAPE_KIND_CHANGED",
    }
    families = {
        "styles", "fonts", "paragraphs", "borders",
        "daily_header", "daily_body", "shapes",
    }
    seen = set()
    for item in value:
        _require_exact_schema_one_object(
            item, {"component_family", "reason"}, label
        )
        identity = (item["component_family"], item["reason"])
        if (
            item["component_family"] not in families
            or item["reason"] not in allowed
            or identity in seen
        ):
            raise ValueError(f"{label} does not match schema version 1")
        seen.add(identity)


def _validate_normalization_audits(value: list[Any], label: str) -> None:
    seen = set()
    for item in value:
        _require_exact_schema_one_object(
            item, {"component_family", "component_id", "status"}, label
        )
        identity = (item["component_family"], item["component_id"])
        if (
            item["component_family"] != "daily_body"
            or item["status"] != "VERIFY_AFTER_COMPONENT_NORMALIZATION"
            or identity in seen
        ):
            raise ValueError(f"{label} does not match schema version 1")
        seen.add(identity)


def _validate_normalization_decisions(
    value: list[Any], sources: tuple[str, ...], label: str
) -> None:
    selection_units = {
        "styles": "style_bundle",
        "fonts": "font_bundle",
        "paragraphs": "paragraph_bundle",
        "borders": "border_bundle",
        "daily_header": "daily_header_bundle",
        "shapes": "geometry_bundle",
    }
    seen = set()
    keys = {
        "decision_id",
        "component_family",
        "component_id",
        "selection_unit",
        "changed_properties",
        "status",
        "eligible_source_sha256",
        "ineligible_source_sha256",
        "samples",
    }
    for item in value:
        _require_exact_schema_one_object(item, keys, label)
        family = item["component_family"]
        decision_id = item["decision_id"]
        if (
            family not in selection_units
            or item["selection_unit"] != selection_units[family]
            or decision_id != f"{family}:{item['component_id']}"
            or decision_id in seen
            or item["status"]
            not in {"REQUIRES_OP_BASE", "BLOCKED_MIXED_VALUE"}
            or not isinstance(item["changed_properties"], list)
            or not item["changed_properties"]
            or item["changed_properties"]
            != sorted(set(item["changed_properties"]))
        ):
            raise ValueError(f"{label} does not match schema version 1")
        seen.add(decision_id)
        eligible = item["eligible_source_sha256"]
        ineligible = item["ineligible_source_sha256"]
        if (
            not isinstance(eligible, list)
            or not isinstance(ineligible, list)
            or set(eligible) | set(ineligible) != set(sources)
            or set(eligible) & set(ineligible)
            or len(set(eligible)) != len(eligible)
            or len(set(ineligible)) != len(ineligible)
            or eligible != [source for source in sources if source in eligible]
            or ineligible
            != [source for source in sources if source in ineligible]
            or not eligible
            or (item["status"] == "BLOCKED_MIXED_VALUE") != bool(ineligible)
            or not isinstance(item["samples"], list)
            or len(item["samples"]) != 3
        ):
            raise ValueError(f"{label} does not match schema version 1")
        for source, sample in zip(sources, item["samples"], strict=True):
            _require_exact_schema_one_object(
                sample,
                {
                    "source_sha256",
                    "component_value_sha256",
                    "eligible_as_base",
                },
                label,
            )
            if (
                sample["source_sha256"] != source
                or _validate_sha256(
                    sample["component_value_sha256"], label
                ) != sample["component_value_sha256"]
                or not isinstance(sample["eligible_as_base"], bool)
                or sample["eligible_as_base"] != (source in eligible)
            ):
                raise ValueError(f"{label} does not match schema version 1")


def diagnose_gate_c_5992(
    sample_paths: tuple[Path, ...],
    *,
    adapter: WordCalibrationAdapter,
    timeout_seconds: int = 180,
) -> GateC5992DiagnosticResult:
    return _diagnose_gate_c(
        sample_paths,
        adapter=adapter,
        timeout_seconds=timeout_seconds,
        action="diagnose-5992-v2",
        temp_prefix="easytravel-list-diagnose-5992-",
    )


def diagnose_gate_c_v3(
    sample_paths: tuple[Path, ...],
    *,
    adapter: WordCalibrationAdapter,
    timeout_seconds: int = 180,
) -> GateC5992DiagnosticResult:
    return _diagnose_gate_c(
        sample_paths,
        adapter=adapter,
        timeout_seconds=timeout_seconds,
        action="diagnose-gate-c-v3",
        temp_prefix="easytravel-list-diagnose-gate-c-v3-",
    )


def _diagnose_gate_c(
    sample_paths: tuple[Path, ...],
    *,
    adapter: WordCalibrationAdapter,
    timeout_seconds: int,
    action: str,
    temp_prefix: str,
) -> GateC5992DiagnosticResult:
    samples = _resolve_sample_paths(sample_paths)
    if timeout_seconds <= 0:
        raise ValueError("Gate C diagnosis timeout must be positive")
    before = tuple(_sha256_file(path) for path in samples)
    with tempfile.TemporaryDirectory(prefix=temp_prefix) as temp:
        work_dir = Path(temp)
        job_path = work_dir / "word-job.json"
        report_path = work_dir / "diagnostic-report.json"
        working_copies = tuple(
            work_dir / f"working-{index:03d}{sample.suffix.lower()}"
            for index, sample in enumerate(samples, start=1)
        )
        job = {
            "schema_version": 2,
            "action": action,
            "ownership_nonce": secrets.token_hex(16),
            "word_pid_path": str(work_dir / "word-owner.json"),
            "report_path": str(report_path),
            "sample_paths": [str(path) for path in samples],
            "sample_sha256": list(before),
            "working_copy_paths": [str(path) for path in working_copies],
        }
        _write_json_exclusive(job_path, job)
        adapter.run(job_path, timeout_seconds=timeout_seconds)
        report = _read_gate_c_diagnostic_report(
            report_path,
            expected_action=action,
        )
    after = tuple(_sha256_file(path) for path in samples)
    if after != before:
        raise CalibrationSourceChangedError()
    return GateC5992DiagnosticResult(
        word_version=report["word_version"],
        source_sha256=before,
        classification=report["classification"],
        completed_source_inspections=report[
            "completed_source_inspections"
        ],
        selected_base_sample_id=report["selected_base_sample_id"],
        checkpoint=GateC5992Checkpoint(**report["checkpoint"]),
        hresult=report["error"]["hresult"],
        hresult_hex=report["error"]["hresult_hex"],
        low_word_error_number=report["error"]["low_word_error_number"],
        adapter_code=report["error"]["adapter_code"],
    )


def inspect_list_templates_v2(
    sample_paths: tuple[Path, ...],
    *,
    adapter: WordCalibrationAdapter,
    timeout_seconds: int = 120,
) -> ListInspectionBatchResult:
    samples = _resolve_sample_paths(sample_paths)
    if timeout_seconds <= 0:
        raise ValueError("LIST inspection timeout must be positive")
    before = tuple(_sha256_file(path) for path in samples)
    with tempfile.TemporaryDirectory(
        prefix="easytravel-list-inspect-v2-"
    ) as temp:
        work_dir = Path(temp)
        job_path = work_dir / "word-job.json"
        report_path = work_dir / "inspection-report.json"
        job = {
            "schema_version": 2,
            "action": "inspect-v2",
            "ownership_nonce": secrets.token_hex(16),
            "word_pid_path": str(work_dir / "word-owner.json"),
            "report_path": str(report_path),
            "sample_paths": [str(path) for path in samples],
        }
        _write_json_exclusive(job_path, job)
        adapter.run(job_path, timeout_seconds=timeout_seconds)
        report = _read_inspection_batch_report(report_path)
    after = tuple(_sha256_file(path) for path in samples)
    if after != before:
        raise CalibrationSourceChangedError()
    return ListInspectionBatchResult(
        samples=tuple(
            ListCalibrationSample.from_inspection(source_hash, observed)
            for source_hash, observed in zip(
                before, report["inspections"], strict=True
            )
        ),
        word_version=report["word_version"],
    )


def diagnose_calibration_conflicts(
    sample_paths: tuple[Path, ...],
    *,
    adapter: WordCalibrationAdapter,
    timeout_seconds: int = 180,
) -> CalibrationConflictDiagnosisResult:
    inspected = inspect_list_templates_v2(
        sample_paths,
        adapter=adapter,
        timeout_seconds=timeout_seconds,
    )
    field_paths = _calibration_conflict_field_paths(inspected.samples)
    conflict_matrix = (
        build_calibration_conflict_matrix(
            inspected.samples,
            field_paths,
        )
        if field_paths
        else None
    )
    return CalibrationConflictDiagnosisResult(
        word_version=inspected.word_version,
        source_sha256=tuple(
            item.source_sha256 for item in inspected.samples
        ),
        classification=(
            "TEMPLATE_CONTRACT_CONFLICT"
            if field_paths
            else "NORMALIZED_LAYOUT_COMPATIBLE"
        ),
        field_paths=field_paths,
        conflict_matrix=conflict_matrix,
    )


def calibrate_list_templates(
    sample_paths: tuple[Path, ...],
    *,
    master_path: Path,
    manifest_path: Path,
    adapter: WordCalibrationAdapter,
    created_at: str,
    timeout_seconds: int = 180,
    on_stage: Callable[[str], None] | None = None,
) -> ListCalibrationBuildResult:
    samples = _resolve_sample_paths(sample_paths)
    master = master_path.expanduser().resolve()
    manifest_destination = manifest_path.expanduser().resolve()
    if master.suffix.lower() != ".docx":
        raise ValueError("calibrated LIST master must be .docx")
    if manifest_destination.suffix.lower() != ".json":
        raise ValueError("calibration manifest must be .json")
    if master == manifest_destination:
        raise ValueError("master and manifest destinations must differ")
    if master.exists() or manifest_destination.exists():
        raise ValueError(
            "calibration destinations must not already exist"
        )
    if timeout_seconds <= 0:
        raise ValueError("LIST calibration timeout must be positive")
    _report_calibration_stage(on_stage, "inspect-samples")
    inspected = inspect_list_templates_v2(
        samples,
        adapter=adapter,
        timeout_seconds=timeout_seconds,
    )
    _report_calibration_stage(on_stage, "compare-samples")
    comparison = compare_calibration_samples(inspected.samples)
    base_index = next(
        index
        for index, item in enumerate(inspected.samples)
        if item.source_sha256 == comparison.base_sample_sha256
    )
    before_calibration = tuple(_sha256_file(path) for path in samples)
    _report_calibration_stage(on_stage, "calibrate-master")
    with tempfile.TemporaryDirectory(
        prefix="easytravel-list-calibrate-"
    ) as temp:
        work_dir = Path(temp)
        job_path = work_dir / "word-job.json"
        report_path = work_dir / "calibration-report.json"
        temporary_master = work_dir / "list-master.docx"
        job = {
            "schema_version": 2,
            "action": "calibrate",
            "ownership_nonce": secrets.token_hex(16),
            "word_pid_path": str(work_dir / "word-owner.json"),
            "report_path": str(report_path),
            "source_path": str(samples[base_index]),
            "working_copy_path": str(
                work_dir / f"working{samples[base_index].suffix.lower()}"
            ),
            "output_docx": str(temporary_master),
        }
        _write_json_exclusive(job_path, job)
        adapter.run(job_path, timeout_seconds=timeout_seconds)
        _report_calibration_stage(on_stage, "validate-master")
        report = _read_calibration_report(report_path)
        after_calibration = tuple(_sha256_file(path) for path in samples)
        if after_calibration != before_calibration:
            raise CalibrationSourceChangedError()
        if (
            not temporary_master.is_file()
            or temporary_master.stat().st_size == 0
        ):
            raise ValueError(
                "calibration completed without a master document"
            )
        if report["output_bytes"] != temporary_master.stat().st_size:
            raise ValueError(
                "calibrated master size does not match report"
            )
        if report["forbidden_dynamic_token_types"]:
            raise ValueError(
                "calibrated master retains forbidden dynamic tokens"
            )
        master_hash = _sha256_file(temporary_master)
        master_fingerprint = normalized_structure_fingerprint(
            report["master_inspection"]
        )
        if (
            master_fingerprint
            != comparison.normalized_structure_fingerprint
        ):
            raise CalibrationContractError(
                ("master_structure_fingerprint",)
            )
        calibration_manifest = build_calibration_manifest(
            comparison,
            master_sha256=master_hash,
            master_structure_fingerprint=master_fingerprint,
            created_at=created_at,
            word_version=report["word_version"],
            calibration_report_sha256=_sha256_file(report_path),
        )
        _report_calibration_stage(on_stage, "publish")
        master.parent.mkdir(parents=True, exist_ok=True)
        manifest_destination.parent.mkdir(parents=True, exist_ok=True)
        master_created = False
        try:
            _copy_exclusive(temporary_master, master)
            master_created = True
            _write_text_exclusive(
                manifest_destination,
                calibration_manifest.to_canonical_json() + "\n",
            )
        except BaseException:
            if master_created:
                master.unlink(missing_ok=True)
            raise
    return ListCalibrationBuildResult(
        master_path=master,
        manifest_path=manifest_destination,
        master_sha256=master_hash,
        manifest_sha256=_sha256_file(manifest_destination),
        word_version=report["word_version"],
        sample_evidence=calibration_manifest.sample_evidence,
    )


def normalized_structure_fingerprint(
    inspection: ListTemplateInspectionV2,
) -> str:
    canonical = json.dumps(
        _normalized_layout_dict(inspection),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def select_base_sample(
    samples: tuple[ListCalibrationSample, ...],
) -> ListCalibrationSample:
    if not samples:
        raise ValueError("calibration samples are required")
    sorted_days = sorted(item.day_count for item in samples)
    median_day_count = sorted_days[len(sorted_days) // 2]
    return min(
        (item for item in samples if item.day_count == median_day_count),
        key=lambda item: item.source_sha256,
    )


def build_calibration_conflict_matrix(
    samples: tuple[ListCalibrationSample, ...],
    field_paths: tuple[str, ...],
) -> dict[str, Any]:
    if len(samples) != 3 or len(
        {item.source_sha256 for item in samples}
    ) != 3:
        raise ValueError("conflict matrix requires three unique samples")
    ordered_samples = tuple(
        sorted(samples, key=lambda item: item.source_sha256)
    )
    layouts = tuple(
        _normalized_layout_dict(item.inspection)
        for item in ordered_samples
    )
    fields = tuple(sorted(set(field_paths)))
    if not fields:
        raise ValueError("conflict matrix field paths are required")
    available_fields = set(layouts[0])
    if any(
        field not in available_fields
        or any(field not in layout for layout in layouts)
        for field in fields
    ):
        raise ValueError("conflict matrix field is not a normalized layout field")
    matrix_fields = []
    for field in fields:
        values = tuple(layout[field] for layout in layouts)
        canonical_values = {
            _canonical_layout_value(value)
            for value in values
        }
        if len(canonical_values) < 2:
            raise ValueError(
                f"conflict matrix field is not conflicting: {field}"
            )
        matrix_fields.append(
            {
                "field_path": field,
                "normalization_status": "REQUIRES_OP_DECISION",
                "samples": [
                    {
                        "source_sha256": item.source_sha256,
                        **_safe_conflict_matrix_value(field, value),
                    }
                    for item, value in zip(
                        ordered_samples, values, strict=True
                    )
                ],
            }
        )
    return {
        "schema_version": 1,
        "stage": "compare-samples",
        "classification": "TEMPLATE_CONTRACT_CONFLICT",
        "fields": matrix_fields,
    }


def _safe_conflict_matrix_value(
    field: str,
    value: Any,
) -> dict[str, Any]:
    canonical = _canonical_layout_value(value)
    if field.endswith("_digest"):
        return {"normalized_digest": value}
    if _is_numeric_layout_value(value):
        return {"normalized_value": json.loads(canonical)}
    return {
        "normalized_value_sha256": hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()
    }


def _canonical_layout_value(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _is_numeric_layout_value(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, (list, tuple)):
        return all(_is_numeric_layout_value(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_numeric_layout_value(item)
            for key, item in value.items()
        )
    return False


def compare_calibration_samples(
    samples: tuple[ListCalibrationSample, ...],
) -> CalibrationComparison:
    if len(samples) != 3 or len(
        {item.source_sha256 for item in samples}
    ) != 3:
        raise ValueError("calibration requires three unique samples")
    field_paths = _calibration_conflict_field_paths(samples)
    if field_paths:
        raise CalibrationContractError(
            field_paths,
            conflict_matrix=build_calibration_conflict_matrix(
                samples,
                field_paths,
            ),
        )
    reference = _normalized_layout_dict(samples[0].inspection)
    common_names = {
        profile.name
        for profile in samples[0].inspection.adaptive_profiles
    }
    for item in samples[1:]:
        common_names.intersection_update(
            profile.name for profile in item.inspection.adaptive_profiles
        )
    common_minimum = max(
        min(
            profile.body_font_points
            for profile in item.inspection.adaptive_profiles
        )
        for item in samples
    )
    profiles = []
    for name in common_names:
        candidates = [
            profile
            for item in samples
            for profile in item.inspection.adaptive_profiles
            if profile.name == name
        ]
        selected = max(
            candidates,
            key=lambda profile: (
                profile.body_font_points,
                profile.line_spacing_points,
                profile.paragraph_space_after_points,
            ),
        )
        if selected.body_font_points >= common_minimum:
            profiles.append(selected)
    profiles.sort(
        key=lambda item: (
            item.name != "normal",
            -item.body_font_points,
            -item.line_spacing_points,
            item.name,
        )
    )
    if not profiles or profiles[0].name != "normal":
        raise ValueError(
            "calibration samples have no common normal profile"
        )
    base = select_base_sample(samples)
    return CalibrationComparison(
        samples=samples,
        base_sample_sha256=base.source_sha256,
        normalized_structure_fingerprint=(
            normalized_structure_fingerprint(samples[0].inspection)
        ),
        normalized_layout=_freeze_object(reference),
        layout_profiles=tuple(profiles),
        minimum_font_points=common_minimum,
    )


def build_calibration_manifest(
    comparison: CalibrationComparison,
    *,
    master_sha256: str,
    master_structure_fingerprint: str,
    created_at: str,
    word_version: str,
    calibration_report_sha256: str,
) -> ListCalibrationManifest:
    evidence = tuple(
        CalibrationSampleEvidence(
            source_sha256=item.source_sha256,
            day_count=item.day_count,
            normalized_structure_fingerprint=(
                item.normalized_structure_fingerprint
            ),
        )
        for item in sorted(
            comparison.samples,
            key=lambda sample: sample.source_sha256,
        )
    )
    return ListCalibrationManifest(
        schema_version=CALIBRATION_SCHEMA_VERSION,
        generator_version=CALIBRATION_GENERATOR_VERSION,
        sample_evidence=evidence,
        base_sample_sha256=comparison.base_sample_sha256,
        master_sha256=master_sha256,
        master_structure_fingerprint=master_structure_fingerprint,
        normalized_layout=comparison.normalized_layout,
        layout_profiles=comparison.layout_profiles,
        minimum_font_points=comparison.minimum_font_points,
        continuation_group_header=True,
        repeat_daily_header=True,
        allow_day_row_split=False,
        qr_policy="first_page_only",
        created_at=created_at,
        word_version=word_version,
        calibration_report_sha256=calibration_report_sha256,
    )


def manifest_sha256(manifest: ListCalibrationManifest) -> str:
    return hashlib.sha256(
        manifest.to_canonical_json().encode("utf-8")
    ).hexdigest()


def validate_calibrated_master(
    manifest: ListCalibrationManifest,
    *,
    master_sha256: str,
    master_structure_fingerprint: str,
) -> None:
    actual_hash = _validate_nonzero_sha256(
        master_sha256, "master SHA-256"
    )
    actual_fingerprint = _validate_nonzero_sha256(
        master_structure_fingerprint,
        "master structure fingerprint",
    )
    if (
        manifest.schema_version != CALIBRATION_SCHEMA_VERSION
        or manifest.generator_version != CALIBRATION_GENERATOR_VERSION
        or actual_hash != manifest.master_sha256
        or actual_fingerprint != manifest.master_structure_fingerprint
    ):
        raise ValueError(
            "calibrated master identity does not match manifest"
        )


def _normalized_layout_dict(
    inspection: ListTemplateInspectionV2,
) -> dict[str, Any]:
    value = inspection.to_dict()
    normalized_shapes = list(value["table_shapes"])
    normalized_shapes[2] = {"rows": 2, "columns": 7}
    return {
        "contract": "list-template-layout/2",
        "table_shapes": normalized_shapes,
        "anchor_labels": value["anchor_labels"],
        "list_header_accessible_cells": value[
            "list_header_accessible_cells"
        ],
        "list_header_paragraph_count": value[
            "list_header_paragraph_count"
        ],
        "section_count": value["section_count"],
        "page_width_points": value["page_width_points"],
        "page_height_points": value["page_height_points"],
        "orientation": value["orientation"],
        "margins_points": value["margins_points"],
        "header_distance_points": value["header_distance_points"],
        "footer_distance_points": value["footer_distance_points"],
        "table_column_widths_points": value[
            "table_column_widths_points"
        ],
        "merged_cell_map": value["merged_cell_map"],
        "qr_shape_count": value["qr_shape_count"],
        "shape_geometry_points": value["shape_geometry_points"],
        "style_digest": value["style_digest"],
        "font_digest": value["font_digest"],
        "paragraph_digest": value["paragraph_digest"],
        "border_digest": value["border_digest"],
        "shading_digest": value["shading_digest"],
        "daily_header_digest": value["daily_header_digest"],
        "daily_body_prototype_digest": value[
            "daily_body_prototype_digest"
        ],
    }


def _resolve_sample_paths(
    sample_paths: tuple[Path, ...],
) -> tuple[Path, ...]:
    if not isinstance(sample_paths, tuple) or len(sample_paths) != 3:
        raise ValueError(
            "LIST calibration requires exactly three sample files"
        )
    resolved = tuple(path.expanduser().resolve() for path in sample_paths)
    if len(set(resolved)) != 3:
        raise ValueError("LIST calibration samples must be unique")
    if any(
        not path.is_file()
        or path.suffix.lower() not in {".doc", ".docx"}
        for path in resolved
    ):
        raise ValueError(
            "LIST calibration samples must be existing Word files"
        )
    return resolved


def _read_component_diagnostic_report(path: Path) -> dict[str, Any]:
    label = "component diagnostic report"
    payload = _read_json_object(path, "component diagnostic")
    _require_exact_object(
        payload,
        {"schema_version", "action", "word_version", "samples"},
        label,
    )
    if (
        payload["schema_version"] != 2
        or payload["action"] != "diagnose-components-v2"
        or not isinstance(payload["word_version"], str)
        or not payload["word_version"]
        or not isinstance(payload["samples"], list)
        or len(payload["samples"]) != 3
    ):
        raise ValueError(f"{label} does not match schema version 2")
    for index, sample in enumerate(payload["samples"], start=1):
        _require_exact_object(sample, {"sample_id", "evidence"}, label)
        if sample["sample_id"] != f"sample-{index:03d}":
            raise ValueError(f"{label} does not match schema version 2")
        _validate_component_evidence(sample["evidence"], label)
    return payload


def _validate_component_evidence(value: object, label: str) -> None:
    families = {
        "styles",
        "fonts",
        "paragraphs",
        "borders",
        "daily_header",
        "daily_body",
        "shapes",
    }
    _require_exact_object(value, families, label)
    assert isinstance(value, dict)
    validators = {
        "styles": _validate_style_component,
        "fonts": _validate_font_component,
        "paragraphs": _validate_paragraph_component,
        "borders": _validate_border_component,
        "daily_header": _validate_daily_component,
        "daily_body": _validate_daily_component,
        "shapes": _validate_shape_component,
    }
    for family, validator in validators.items():
        items = value[family]
        if not isinstance(items, list):
            raise ValueError(f"{label} does not match schema version 2")
        for item in items:
            validator(item, label)


def _validate_style_component(value: object, label: str) -> None:
    keys = {
        "cell_id", "name_sha256", "vertical_alignment", "shading_color"
    }
    _require_exact_object(value, keys, label)
    assert isinstance(value, dict)
    _validate_cell_id(value["cell_id"], label)
    _validate_sha256(value["name_sha256"], label)
    _validate_int_components(value, keys - {"cell_id", "name_sha256"}, label)


def _validate_font_component(value: object, label: str) -> None:
    keys = {
        "cell_id", "name_sha256", "name_far_east_sha256", "size_points",
        "bold", "italic", "underline", "color",
    }
    _require_exact_object(value, keys, label)
    assert isinstance(value, dict)
    _validate_cell_id(value["cell_id"], label)
    _validate_sha256(value["name_sha256"], label)
    _validate_sha256(value["name_far_east_sha256"], label)
    _validate_number(value["size_points"], label)
    _validate_int_components(
        value,
        {"bold", "italic", "underline", "color"},
        label,
    )


def _validate_paragraph_component(value: object, label: str) -> None:
    integer_keys = {"alignment", "line_spacing_rule"}
    point_keys = {
        "space_before_points", "space_after_points", "line_spacing_points",
        "left_indent_points", "right_indent_points",
        "first_line_indent_points",
    }
    _require_exact_object(
        value, {"cell_id"} | integer_keys | point_keys, label
    )
    assert isinstance(value, dict)
    _validate_cell_id(value["cell_id"], label)
    _validate_int_components(value, integer_keys, label)
    for key in point_keys:
        _validate_number(value[key], label)


def _validate_border_component(value: object, label: str) -> None:
    keys = {"border_id", "line_style", "line_width", "color"}
    _require_exact_object(value, keys, label)
    assert isinstance(value, dict)
    if (
        not isinstance(value["border_id"], str)
        or re.fullmatch(
            r"table-[0-9]{3}-row-[0-9]{3}-column-[0-9]{3}-"
            r"(top|left|bottom|right|diagonal-down|diagonal-up)",
            value["border_id"],
        ) is None
    ):
        raise ValueError(f"{label} does not match schema version 2")
    _validate_int_components(value, keys - {"border_id"}, label)


def _validate_daily_component(value: object, label: str) -> None:
    keys = {
        "cell_id",
        "style_sha256",
        "font_sha256",
        "paragraph_sha256",
        "component_sha256",
    }
    _require_exact_object(value, keys, label)
    assert isinstance(value, dict)
    _validate_cell_id(value["cell_id"], label)
    for key in keys - {"cell_id"}:
        _validate_sha256(value[key], label)


def _validate_shape_component(value: object, label: str) -> None:
    keys = {
        "shape_id", "kind", "left_points", "top_points", "width_points",
        "height_points",
    }
    _require_exact_object(value, keys, label)
    assert isinstance(value, dict)
    if (
        value["kind"] not in {"inline", "floating"}
        or not isinstance(value["shape_id"], str)
        or re.fullmatch(r"(inline|floating)-[0-9]{3}", value["shape_id"])
        is None
        or not value["shape_id"].startswith(value["kind"] + "-")
    ):
        raise ValueError(f"{label} does not match schema version 2")
    for key in keys - {"shape_id", "kind"}:
        _validate_number(value[key], label)


def _validate_cell_id(value: object, label: str) -> None:
    if (
        not isinstance(value, str)
        or re.fullmatch(
            r"table-[0-9]{3}-row-[0-9]{3}-column-[0-9]{3}", value
        ) is None
    ):
        raise ValueError(f"{label} does not match schema version 2")


def _validate_int_components(
    value: dict[str, Any], keys: set[str], label: str
) -> None:
    if any(
        isinstance(value[key], bool) or not isinstance(value[key], int)
        for key in keys
    ):
        raise ValueError(f"{label} does not match schema version 2")


def _validate_number(value: object, label: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError(f"{label} does not match schema version 2")


def _read_header_diagnostic_report(path: Path) -> dict[str, Any]:
    payload = _read_json_object(path, "header diagnostic")
    expected = {
        "schema_version",
        "action",
        "word_version",
        "samples",
    }
    if (
        set(payload) != expected
        or payload.get("schema_version") != 2
        or payload.get("action") != "diagnose-header-v2"
        or not isinstance(payload.get("word_version"), str)
        or not payload["word_version"]
        or not isinstance(payload.get("samples"), list)
        or len(payload["samples"]) != 3
    ):
        raise ValueError(
            "Word header diagnostic report does not match schema version 2"
        )
    parsed = []
    evidence_keys = {
        "list_header_paragraph_count",
        "paragraphs",
    }
    paragraph_keys = {
        "paragraph_number",
        "visible_character_count",
        "fixed_label_ids",
        "fullwidth_colon_count",
        "inline_shape_count",
        "ends_with_cell_marker",
    }
    for index, item in enumerate(payload["samples"], start=1):
        if (
            not isinstance(item, dict)
            or set(item) != {"sample_id", "evidence"}
            or item.get("sample_id") != f"sample-{index:03d}"
            or not isinstance(item.get("evidence"), dict)
            or set(item["evidence"]) != evidence_keys
        ):
            raise ValueError(
                "Word header diagnostic report does not match schema version 2"
            )
        evidence = item["evidence"]
        count = evidence["list_header_paragraph_count"]
        paragraphs = evidence["paragraphs"]
        if (
            isinstance(count, bool)
            or not isinstance(count, int)
            or not 1 <= count <= 32
            or not isinstance(paragraphs, list)
            or len(paragraphs) != count
        ):
            raise ValueError(
                "Word header diagnostic report does not match schema version 2"
            )
        normalized_paragraphs = []
        for number, paragraph in enumerate(paragraphs, start=1):
            if (
                not isinstance(paragraph, dict)
                or set(paragraph) != paragraph_keys
                or paragraph.get("paragraph_number") != number
                or not isinstance(paragraph.get("fixed_label_ids"), list)
            ):
                raise ValueError(
                    "Word header diagnostic report does not match schema version 2"
                )
            normalized_paragraphs.append(
                {
                    **paragraph,
                    "fixed_label_ids": tuple(
                        paragraph["fixed_label_ids"]
                    ),
                }
            )
        parsed.append(
            {
                "list_header_paragraph_count": count,
                "paragraphs": tuple(normalized_paragraphs),
            }
        )
    return {
        "word_version": payload["word_version"],
        "samples": tuple(parsed),
    }


def _read_gate_c_diagnostic_report(
    path: Path,
    *,
    expected_action: str,
) -> dict[str, Any]:
    payload = _read_json_object(path, "Gate C diagnostic")
    expected = {
        "schema_version",
        "action",
        "word_version",
        "classification",
        "completed_source_inspections",
        "selected_base_sample_id",
        "checkpoint",
        "error",
    }
    if (
        set(payload) != expected
        or payload.get("schema_version") != 2
        or payload.get("action") != expected_action
        or not isinstance(payload.get("word_version"), str)
        or not payload["word_version"]
        or payload.get("classification")
        not in {"ERROR_OBSERVED", "NOT_REPRODUCED"}
    ):
        raise ValueError(
            "Word Gate C report does not match schema version 2"
        )
    checkpoint = payload.get("checkpoint")
    error = payload.get("error")
    checkpoint_keys = {
        "phase",
        "sample_id",
        "operation",
        "field_id",
        "table_number",
        "row_number",
        "column_number",
        "paragraph_number",
    }
    error_keys = {
        "hresult",
        "hresult_hex",
        "low_word_error_number",
        "adapter_code",
    }
    if (
        not isinstance(checkpoint, dict)
        or set(checkpoint) != checkpoint_keys
        or not isinstance(error, dict)
        or set(error) != error_keys
    ):
        raise ValueError(
            "Word Gate C report does not match schema version 2"
        )
    count = payload["completed_source_inspections"]
    selected = payload["selected_base_sample_id"]
    hresult = error["hresult"]
    low_word = error["low_word_error_number"]
    if (
        isinstance(count, bool)
        or not isinstance(count, int)
        or not 0 <= count <= 3
        or selected
        not in {"sample-000", "sample-001", "sample-002", "sample-003"}
        or isinstance(hresult, bool)
        or not isinstance(hresult, int)
        or not -(2**31) <= hresult < 2**31
        or not isinstance(low_word, int)
        or isinstance(low_word, bool)
        or not 0 <= low_word <= 65535
        or error["hresult_hex"] != f"0x{hresult & 0xFFFFFFFF:08X}"
        or low_word != (hresult & 0xFFFF)
        or not isinstance(error["adapter_code"], str)
        or re.fullmatch(
            r"NONE|[A-Z][A-Z0-9_]{1,79}", error["adapter_code"]
        )
        is None
    ):
        raise ValueError(
            "Word Gate C report does not match schema version 2"
        )
    normalized_checkpoint = GateC5992Checkpoint(**checkpoint)
    result = {
        "word_version": payload["word_version"],
        "classification": payload["classification"],
        "completed_source_inspections": count,
        "selected_base_sample_id": selected,
        "checkpoint": {
            "phase": normalized_checkpoint.phase,
            "sample_id": normalized_checkpoint.sample_id,
            "operation": normalized_checkpoint.operation,
            "field_id": normalized_checkpoint.field_id,
            "table_number": normalized_checkpoint.table_number,
            "row_number": normalized_checkpoint.row_number,
            "column_number": normalized_checkpoint.column_number,
            "paragraph_number": normalized_checkpoint.paragraph_number,
        },
        "error": dict(error),
    }
    GateC5992DiagnosticResult(
        word_version=result["word_version"],
        source_sha256=("1" * 64, "2" * 64, "3" * 64),
        classification=result["classification"],
        completed_source_inspections=result[
            "completed_source_inspections"
        ],
        selected_base_sample_id=result["selected_base_sample_id"],
        checkpoint=normalized_checkpoint,
        hresult=result["error"]["hresult"],
        hresult_hex=result["error"]["hresult_hex"],
        low_word_error_number=result["error"]["low_word_error_number"],
        adapter_code=result["error"]["adapter_code"],
    )
    return result


def _calibration_conflict_field_paths(
    samples: tuple[ListCalibrationSample, ...],
) -> tuple[str, ...]:
    if len(samples) != 3 or len(
        {item.source_sha256 for item in samples}
    ) != 3:
        raise ValueError("calibration requires three unique samples")
    reference = _normalized_layout_dict(samples[0].inspection)
    conflicts: set[str] = set()
    for item in samples[1:]:
        current = _normalized_layout_dict(item.inspection)
        conflicts.update(
            key for key in reference if reference[key] != current.get(key)
        )
        conflicts.update(key for key in current if key not in reference)
    return tuple(sorted(conflicts))


def _report_calibration_stage(
    callback: Callable[[str], None] | None,
    stage: str,
) -> None:
    if stage not in CALIBRATION_STAGES:
        raise ValueError("unsupported calibration stage")
    if callback is not None:
        callback(stage)


def _read_inspection_batch_report(path: Path) -> dict[str, Any]:
    payload = _read_json_object(path, "inspection")
    expected = {
        "schema_version",
        "action",
        "word_version",
        "samples",
    }
    if (
        set(payload) != expected
        or payload.get("schema_version") != 2
        or payload.get("action") != "inspect-v2"
        or not isinstance(payload.get("word_version"), str)
        or not payload["word_version"]
        or not isinstance(payload.get("samples"), list)
        or len(payload["samples"]) != 3
    ):
        raise ValueError(
            "Word inspection report does not match schema version 2"
        )
    inspections = []
    for index, item in enumerate(payload["samples"], start=1):
        if (
            not isinstance(item, dict)
            or set(item) != {"sample_id", "inspection"}
            or item.get("sample_id") != f"sample-{index:03d}"
        ):
            raise ValueError(
                "Word inspection report does not match schema version 2"
            )
        inspections.append(
            ListTemplateInspectionV2.from_dict(item["inspection"])
        )
    return {
        "word_version": payload["word_version"],
        "inspections": tuple(inspections),
    }


def _read_calibration_report(path: Path) -> dict[str, Any]:
    payload = _read_json_object(path, "calibration")
    expected = {
        "schema_version",
        "action",
        "word_version",
        "master_inspection",
        "forbidden_dynamic_token_types",
        "output_bytes",
    }
    if (
        set(payload) != expected
        or payload.get("schema_version") != 2
        or payload.get("action") != "calibrate"
        or not isinstance(payload.get("word_version"), str)
        or not payload["word_version"]
        or not isinstance(
            payload.get("forbidden_dynamic_token_types"), list
        )
        or any(
            not isinstance(item, str)
            for item in payload["forbidden_dynamic_token_types"]
        )
        or isinstance(payload.get("output_bytes"), bool)
        or not isinstance(payload.get("output_bytes"), int)
        or payload["output_bytes"] <= 0
    ):
        raise ValueError(
            "Word calibration report does not match schema version 2"
        )
    return {
        **payload,
        "master_inspection": ListTemplateInspectionV2.from_dict(
            payload["master_inspection"]
        ),
    }


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(
            f"Word {label} report is not valid UTF-8 JSON"
        ) from error
    if not isinstance(payload, dict):
        raise ValueError(f"Word {label} report must be a JSON object")
    return payload


def _write_json_exclusive(path: Path, payload: dict[str, Any]) -> None:
    _write_text_exclusive(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )


def _write_text_exclusive(path: Path, value: str) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)


def _copy_exclusive(source: Path, destination: Path) -> None:
    created = False
    try:
        with source.open("rb") as input_stream, destination.open(
            "xb"
        ) as output_stream:
            created = True
            shutil.copyfileobj(input_stream, output_stream)
    except BaseException:
        if created:
            destination.unlink(missing_ok=True)
        raise


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _freeze_object(value: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    return tuple(
        (key, _freeze_value(item)) for key, item in sorted(value.items())
    )


def _freeze_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _freeze_object(value)
    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)
    return value


def _thaw_object(
    value: tuple[tuple[str, Any], ...],
) -> dict[str, Any]:
    return {key: _thaw_value(item) for key, item in value}


def _thaw_value(value: Any) -> Any:
    if isinstance(value, tuple):
        if all(
            isinstance(item, tuple)
            and len(item) == 2
            and isinstance(item[0], str)
            for item in value
        ):
            return _thaw_object(value)
        return [_thaw_value(item) for item in value]
    return value


def _require_exact_object(
    value: object,
    expected: set[str],
    label: str,
) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label} does not match schema version 2")


def _require_exact_schema_one_object(
    value: object,
    expected: set[str],
    label: str,
) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label} does not match schema version 1")


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _positive_points(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or value <= 0
    ):
        raise ValueError(f"{label} must be positive")
    return normalize_word_points(value)


def _validate_sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or _SHA256_PATTERN.fullmatch(value) is None
    ):
        raise ValueError(f"{label} must be lowercase SHA-256")
    return value


def _validate_nonzero_sha256(value: object, label: str) -> str:
    validated = _validate_sha256(value, label)
    if validated == "0" * 64:
        raise ValueError(f"{label} must be non-zero")
    return validated


def _coordinate(value: object) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("cell coordinate must contain two items")
    return (
        _positive_int(value[0], "cell row"),
        _positive_int(value[1], "cell column"),
    )
