from __future__ import annotations

import hashlib
import json
import re
import secrets
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

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
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_PROFILE_NAME_PATTERN = re.compile(r"[a-z][a-z0-9-]*")
_A4_TOLERANCE_POINTS = 2.0


class CalibrationContractError(ValueError):
    def __init__(self, field_paths: tuple[str, ...]) -> None:
        self.code = "CALIBRATION_CONTRACT_CONFLICT"
        self.field_paths = tuple(sorted(set(field_paths)))
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


def calibrate_list_templates(
    sample_paths: tuple[Path, ...],
    *,
    master_path: Path,
    manifest_path: Path,
    adapter: WordCalibrationAdapter,
    created_at: str,
    timeout_seconds: int = 180,
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
    inspected = inspect_list_templates_v2(
        samples,
        adapter=adapter,
        timeout_seconds=timeout_seconds,
    )
    comparison = compare_calibration_samples(inspected.samples)
    base_index = next(
        index
        for index, item in enumerate(inspected.samples)
        if item.source_sha256 == comparison.base_sample_sha256
    )
    before_calibration = tuple(_sha256_file(path) for path in samples)
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


def compare_calibration_samples(
    samples: tuple[ListCalibrationSample, ...],
) -> CalibrationComparison:
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
    if conflicts:
        raise CalibrationContractError(tuple(conflicts))
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
