from __future__ import annotations

import hashlib
import json
import re
import secrets
import shutil
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Protocol

from .errors import UnknownWordResultError, WordGenerationError
from .list_calibration import (
    ListInspectionBatchResult,
    WordCalibrationAdapter,
    inspect_list_templates_v2 as _inspect_list_templates_v2,
)
from .models import BriefingDraft, DraftStatus, OpField
from .op_values import REQUIRED_OP_FIELD_NAMES
from .template_contract import (
    LIST_ANCHOR_LABELS,
    ListTemplateInspection,
    TableShape,
    expected_list_table_shapes,
    layout_fingerprint,
    validate_list_template,
)


WAITING_FOR_OP = "待 OP 確認"
LIST_WORD_GENERATOR_VERSION = "list-word/2"
DEFAULT_ROUTE_CHARACTER_LIMIT = 256
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_MEAL_NOT_INCLUDED = re.compile(
    r"(?:^\s*[x×無]\s*$|敬請自理|自理|方便逛街)", re.IGNORECASE
)


def format_list_day_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        return value
    if parsed.isoformat() != value:
        return value
    return f"{parsed.month}/{parsed.day}"


@dataclass(frozen=True, slots=True)
class HeaderParagraphPatch:
    paragraph: int
    text: str
    highlight_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "paragraph": self.paragraph,
            "text": self.text,
            "highlight_text": self.highlight_text,
        }


@dataclass(frozen=True, slots=True)
class CellPatch:
    table: int
    row: int
    column: int
    text: str
    highlight_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "table": self.table,
            "row": self.row,
            "column": self.column,
            "text": self.text,
            "highlight_text": self.highlight_text,
        }


@dataclass(frozen=True, slots=True)
class AnchorCheck:
    label: str
    table: int
    row: int
    column: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "table": self.table,
            "row": self.row,
            "column": self.column,
        }


@dataclass(frozen=True, slots=True)
class ListPatchPlan:
    schema_version: int
    generator_version: str
    draft_id: str
    document_status: str
    target_day_count: int
    master_sha256: str
    calibration_manifest_sha256: str
    normalized_structure_fingerprint: str
    layout_profiles: tuple[dict[str, Any], ...]
    expected_master_table_shapes: tuple[TableShape, ...]
    expected_table_shapes: tuple[TableShape, ...]
    anchor_checks: tuple[AnchorCheck, ...]
    header_paragraphs: tuple[HeaderParagraphPatch, ...]
    cells: tuple[CellPatch, ...]

    def header_paragraph(self, paragraph: int) -> HeaderParagraphPatch:
        matches = [item for item in self.header_paragraphs if item.paragraph == paragraph]
        if len(matches) != 1:
            raise KeyError(paragraph)
        return matches[0]

    def cell(self, table: int, row: int, column: int) -> CellPatch:
        matches = [
            item
            for item in self.cells
            if (item.table, item.row, item.column) == (table, row, column)
        ]
        if len(matches) != 1:
            raise KeyError((table, row, column))
        return matches[0]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generator_version": self.generator_version,
            "draft_id": self.draft_id,
            "document_status": self.document_status,
            "target_day_count": self.target_day_count,
            "master_sha256": self.master_sha256,
            "calibration_manifest_sha256": (
                self.calibration_manifest_sha256
            ),
            "normalized_structure_fingerprint": (
                self.normalized_structure_fingerprint
            ),
            "layout_profiles": list(self.layout_profiles),
            "expected_master_table_shapes": [
                shape.to_dict() for shape in self.expected_master_table_shapes
            ],
            "expected_table_shapes": [
                shape.to_dict() for shape in self.expected_table_shapes
            ],
            "anchor_checks": [item.to_dict() for item in self.anchor_checks],
            "header_paragraphs": [item.to_dict() for item in self.header_paragraphs],
            "cells": [item.to_dict() for item in self.cells],
        }


class WordAdapter(Protocol):
    def run(self, job_path: Path, *, timeout_seconds: int) -> None: ...


@dataclass(frozen=True, slots=True)
class ListWordBuildResult:
    docx_path: Path
    sha256: str
    byte_count: int
    source_layout_fingerprint: str
    output_layout_fingerprint: str
    computed_page_count: int
    generator_version: str
    selected_layout_profile: str
    day_page_map: tuple[DayPagePlacement, ...]
    continuation_group_header: bool
    repeated_daily_header: bool


@dataclass(frozen=True, slots=True)
class DayPagePlacement:
    day_number: int
    start_page: int
    end_page: int

    @classmethod
    def from_dict(cls, value: object) -> DayPagePlacement:
        expected = {"day_number", "start_page", "end_page"}
        if not isinstance(value, dict) or set(value) != expected:
            raise ValueError("LIST day page map entry is invalid")
        result = cls(**value)
        if any(
            isinstance(item, bool) or not isinstance(item, int) or item <= 0
            for item in (
                result.day_number,
                result.start_page,
                result.end_page,
            )
        ):
            raise ValueError("LIST day page map entry is invalid")
        if result.start_page != result.end_page:
            raise ValueError(
                f"LIST_DAY_ROW_TOO_TALL: day {result.day_number}"
            )
        return result


@dataclass(frozen=True, slots=True)
class WordCapabilityProbeResult:
    available: bool
    word_version: str


@dataclass(frozen=True, slots=True)
class ListTemplateProbeResult:
    template_path: Path
    day_count: int
    layout_fingerprint: str
    inspection: ListTemplateInspection
    word_version: str


def inspect_list_templates_v2(
    sample_paths: tuple[Path, ...],
    *,
    adapter: WordCalibrationAdapter,
    timeout_seconds: int = 120,
) -> ListInspectionBatchResult:
    return _inspect_list_templates_v2(
        sample_paths,
        adapter=adapter,
        timeout_seconds=timeout_seconds,
    )


def probe_word_capability(
    adapter: WordAdapter,
    *,
    timeout_seconds: int = 20,
) -> WordCapabilityProbeResult:
    if timeout_seconds <= 0 or timeout_seconds > 20:
        raise ValueError("Word capability probe must use 1 to 20 seconds")
    with tempfile.TemporaryDirectory(prefix="easytravel-word-probe-") as temp:
        work_dir = Path(temp)
        job_path = work_dir / "word-job.json"
        report_path = work_dir / "probe-report.json"
        job = {
            "schema_version": 1,
            "action": "probe",
            "ownership_nonce": secrets.token_hex(16),
            "word_pid_path": str(work_dir / "word-owner.json"),
            "report_path": str(report_path),
        }
        _write_job(job_path, job)
        adapter.run(job_path, timeout_seconds=timeout_seconds)
        report = _read_simple_word_report(report_path, action="probe")
    return WordCapabilityProbeResult(
        available=True,
        word_version=report["word_version"],
    )


def inspect_list_template(
    template_path: Path,
    *,
    adapter: WordAdapter,
    expected_layout_fingerprint: str | None = None,
    timeout_seconds: int = 60,
) -> ListTemplateProbeResult:
    template = template_path.expanduser().resolve()
    if not template.is_file() or template.suffix.lower() not in {".doc", ".docx"}:
        raise ValueError("LIST template must be an existing .doc or .docx file")
    if timeout_seconds <= 0:
        raise ValueError("LIST template inspection timeout must be positive")
    with tempfile.TemporaryDirectory(prefix="easytravel-list-inspect-") as temp:
        work_dir = Path(temp)
        job_path = work_dir / "word-job.json"
        report_path = work_dir / "inspection-report.json"
        job = {
            "schema_version": 1,
            "action": "inspect",
            "ownership_nonce": secrets.token_hex(16),
            "word_pid_path": str(work_dir / "word-owner.json"),
            "report_path": str(report_path),
            "template_path": str(template),
            "anchor_checks": [item.to_dict() for item in _list_anchor_checks()],
        }
        _write_job(job_path, job)
        adapter.run(job_path, timeout_seconds=timeout_seconds)
        report = _read_inspection_report(report_path)
    inspection = report["inspection"]
    day_count = _inspection_day_count(inspection)
    actual_fingerprint = layout_fingerprint(inspection)
    validate_list_template(
        inspection,
        day_count=day_count,
        expected_layout_fingerprint=(
            expected_layout_fingerprint or actual_fingerprint
        ),
    )
    return ListTemplateProbeResult(
        template_path=template,
        day_count=day_count,
        layout_fingerprint=actual_fingerprint,
        inspection=inspection,
        word_version=report["word_version"],
    )


def build_list_patch_plan(
    draft: BriefingDraft,
    *,
    expected_layout_fingerprint: str | None = None,
    master_sha256: str | None = None,
    calibration_manifest_sha256: str | None = None,
    normalized_structure_fingerprint: str | None = None,
    layout_profiles: tuple[dict[str, Any], ...] | None = None,
    route_character_limit: int = DEFAULT_ROUTE_CHARACTER_LIMIT,
) -> ListPatchPlan:
    legacy_fingerprint = expected_layout_fingerprint
    master_hash = _validate_fingerprint(
        master_sha256 or legacy_fingerprint or ""
    )
    calibration_hash = _validate_fingerprint(
        calibration_manifest_sha256 or legacy_fingerprint or ""
    )
    normalized_fingerprint = _validate_fingerprint(
        normalized_structure_fingerprint or legacy_fingerprint or ""
    )
    profiles = layout_profiles or (
        {
            "name": "normal",
            "body_font_points": 10.0,
            "line_spacing_points": 12.0,
            "paragraph_space_after_points": 1.0,
            "cell_top_margin_points": 1.0,
            "cell_bottom_margin_points": 1.0,
        },
    )
    _validate_layout_profiles(profiles)
    shapes = expected_list_table_shapes(draft.product.day_count)
    _validate_draft_shape(draft)
    _validate_document_state(draft)
    op_fields = {field.name: field for field in draft.op_fields}
    title_lines = _split_title(draft.product.name)
    title_text = "\v".join(title_lines)
    header_paragraphs = (
        HeaderParagraphPatch(paragraph=1, text="日本精緻假期"),
        HeaderParagraphPatch(
            paragraph=2,
            text=f"團體編號：{draft.product.code or WAITING_FOR_OP}",
            highlight_text="" if draft.product.code else WAITING_FOR_OP,
        ),
        HeaderParagraphPatch(
            paragraph=3,
            text=f"團體名稱：{title_text}",
            highlight_text=(WAITING_FOR_OP if title_lines[0] == WAITING_FOR_OP else ""),
        ),
        HeaderParagraphPatch(
            paragraph=4,
            text="",
        ),
    )
    cells: list[CellPatch] = []
    cells.extend(_build_header_cells(draft, op_fields))
    cells.extend(_build_flight_cells(draft))
    cells.extend(
        _build_day_cells(draft, route_character_limit=route_character_limit)
    )
    cells.extend(_build_guide_cells(op_fields))
    return ListPatchPlan(
        schema_version=2,
        generator_version=LIST_WORD_GENERATOR_VERSION,
        draft_id=draft.draft_id,
        document_status=draft.status.value,
        target_day_count=draft.product.day_count,
        master_sha256=master_hash,
        calibration_manifest_sha256=calibration_hash,
        normalized_structure_fingerprint=normalized_fingerprint,
        layout_profiles=profiles,
        expected_master_table_shapes=expected_list_table_shapes(1),
        expected_table_shapes=shapes,
        anchor_checks=_list_anchor_checks(),
        header_paragraphs=header_paragraphs,
        cells=tuple(cells),
    )


def build_list_word(
    draft: BriefingDraft,
    *,
    template_path: Path,
    output_docx: Path,
    expected_layout_fingerprint: str | None = None,
    master_sha256: str | None = None,
    calibration_manifest_sha256: str | None = None,
    normalized_structure_fingerprint: str | None = None,
    layout_profiles: tuple[dict[str, Any], ...] | None = None,
    adapter: WordAdapter,
    timeout_seconds: int = 120,
    route_character_limit: int = DEFAULT_ROUTE_CHARACTER_LIMIT,
) -> ListWordBuildResult:
    template = template_path.expanduser().resolve()
    output = output_docx.expanduser().resolve()
    if not template.is_file():
        raise ValueError("LIST template must be an existing file")
    if template.suffix.lower() not in {".doc", ".docx"}:
        raise ValueError("LIST template must be .doc or .docx")
    if output.suffix.lower() != ".docx":
        raise ValueError("LIST output must be .docx")
    if output == template:
        raise ValueError("LIST output must differ from the source template")
    if output.exists():
        raise ValueError("LIST output must not already exist")
    if timeout_seconds <= 0:
        raise ValueError("Word generation timeout must be positive")
    actual_master_sha256 = _sha256_file(template)
    configured_master_sha256 = _validate_fingerprint(
        master_sha256 or expected_layout_fingerprint or ""
    )
    if (
        master_sha256 is not None
        and actual_master_sha256 != configured_master_sha256
    ):
        raise ValueError("LIST master SHA-256 changed before Word generation")
    plan = build_list_patch_plan(
        draft,
        expected_layout_fingerprint=expected_layout_fingerprint,
        master_sha256=configured_master_sha256,
        calibration_manifest_sha256=calibration_manifest_sha256,
        normalized_structure_fingerprint=normalized_structure_fingerprint,
        layout_profiles=layout_profiles,
        route_character_limit=route_character_limit,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="easytravel-list-word-") as temp:
        work_dir = Path(temp)
        job_path = work_dir / "word-job.json"
        temporary_docx = work_dir / "patched.docx"
        report_path = work_dir / "patch-report.json"
        pid_path = work_dir / "word-owner.json"
        working_copy = work_dir / f"working{template.suffix.lower()}"
        job = {
            "schema_version": 1,
            "action": "patch",
            "ownership_nonce": secrets.token_hex(16),
            "word_pid_path": str(pid_path),
            "template_path": str(template),
            "working_copy_path": str(working_copy),
            "output_docx": str(temporary_docx),
            "report_path": str(report_path),
            "plan": plan.to_dict(),
        }
        _write_job(job_path, job)
        try:
            adapter.run(job_path, timeout_seconds=timeout_seconds)
        except UnknownWordResultError as error:
            error.details.update(
                temporary_docx_exists=temporary_docx.is_file(),
                temporary_docx_bytes=(
                    temporary_docx.stat().st_size if temporary_docx.is_file() else 0
                ),
                report_exists=report_path.is_file(),
            )
            raise
        report = _read_patch_report(
            report_path,
            target_day_count=draft.product.day_count,
            approved_profiles=tuple(
                item["name"] for item in plan.layout_profiles
            ),
        )
        if not temporary_docx.is_file() or temporary_docx.stat().st_size == 0:
            raise WordGenerationError(
                "Word adapter returned success without a DOCX output"
            )
        if report["output_bytes"] != temporary_docx.stat().st_size:
            raise WordGenerationError("Word output size does not match its report")
        source_inspection = report["source_inspection"]
        source_day_count = _inspection_day_count(source_inspection)
        source_fingerprint = validate_list_template(
            source_inspection,
            day_count=source_day_count,
            expected_layout_fingerprint=layout_fingerprint(
                source_inspection
            ),
        )
        output_inspection = report["output_inspection"]
        output_fingerprint = layout_fingerprint(output_inspection)
        validate_list_template(
            output_inspection,
            day_count=draft.product.day_count,
            expected_layout_fingerprint=output_fingerprint,
        )
        if (
            output_inspection.header_qr_candidate_count
            != source_inspection.header_qr_candidate_count
        ):
            raise ValueError("LIST output did not preserve the template QR candidate")
        if (
            master_sha256 is not None
            and _sha256_file(template) != configured_master_sha256
        ):
            raise ValueError("LIST master changed during Word generation")
        _copy_exclusive(temporary_docx, output)
    return ListWordBuildResult(
        docx_path=output,
        sha256=_sha256_file(output),
        byte_count=output.stat().st_size,
        source_layout_fingerprint=source_fingerprint,
        output_layout_fingerprint=output_fingerprint,
        computed_page_count=report["computed_page_count"],
        generator_version=LIST_WORD_GENERATOR_VERSION,
        selected_layout_profile=report["selected_layout_profile"],
        day_page_map=report["day_page_map"],
        continuation_group_header=report[
            "continuation_group_header"
        ],
        repeated_daily_header=report["repeated_daily_header"],
    )


def compact_route_text(
    attractions: tuple[str, ...],
    *,
    max_characters: int = DEFAULT_ROUTE_CHARACTER_LIMIT,
) -> str:
    if max_characters <= 0:
        raise ValueError("route character limit must be positive")
    normalized = tuple(item.strip() for item in attractions if item.strip())
    if not normalized:
        return WAITING_FOR_OP
    full = "／".join(normalized)
    if len(full) <= max_characters:
        return full
    raise ValueError(
        "LIST route text is too long to preserve in full"
    )


def _meal_marker(value: str) -> str:
    normalized = value.strip()
    if not normalized or _MEAL_NOT_INCLUDED.search(normalized):
        return "X"
    return "O"


def _validate_draft_shape(draft: BriefingDraft) -> None:
    day_count = draft.product.day_count
    if len(draft.days) != day_count or tuple(
        day.number for day in draft.days
    ) != tuple(range(1, day_count + 1)):
        raise ValueError("LIST output requires complete sequential day records")
    if len(draft.flights) > 2:
        raise ValueError("LIST output has only two flight rows")


def _validate_document_state(draft: BriefingDraft) -> None:
    unresolved = [
        conflict.field
        for conflict in draft.conflicts
        if conflict.severity == "blocking" and not conflict.decision.strip()
    ]
    if unresolved:
        raise ValueError("LIST output cannot contain unresolved blocking conflicts")
    if draft.status is not DraftStatus.CONFIRMED:
        return
    fields_by_name = {field.name: field for field in draft.op_fields}
    missing_required = set(REQUIRED_OP_FIELD_NAMES) - set(fields_by_name)
    unconfirmed = [
        field.name
        for field in draft.op_fields
        if not field.confirmed or field.highlight == "yellow"
    ]
    if missing_required or unconfirmed or not draft.product.region:
        raise ValueError(
            "CONFIRMED LIST output cannot contain unresolved or yellow fields"
        )


def _build_header_cells(
    draft: BriefingDraft, op_fields: dict[str, OpField]
) -> tuple[CellPatch, ...]:
    meeting_time = _op_display(op_fields, "meeting_time")
    meeting_place = _op_display(op_fields, "meeting_place")
    leader_name = _op_display(op_fields, "tour_leader_name")
    leader_phone = _op_display(op_fields, "tour_leader_phone")
    tag = _op_display(op_fields, "identification_or_luggage_tag")
    airport = _op_display(op_fields, "airport_representative")
    leader_text = f"領隊姓名：{leader_name[0]}\r*台灣手機：{leader_phone[0]}"
    return (
        CellPatch(
            table=1,
            row=2,
            column=1,
            text=f"出發日期：{draft.product.departure_date or WAITING_FOR_OP}",
            highlight_text=("" if draft.product.departure_date else WAITING_FOR_OP),
        ),
        CellPatch(
            table=1,
            row=2,
            column=2,
            text=f"集合時間：{meeting_time[0]}",
            highlight_text=meeting_time[1],
        ),
        CellPatch(
            table=1,
            row=2,
            column=3,
            text=leader_text,
            highlight_text=_combined_highlight(leader_name, leader_phone),
        ),
        CellPatch(
            table=1,
            row=3,
            column=1,
            text=f"集合地點：{meeting_place[0]}",
            highlight_text=meeting_place[1],
        ),
        CellPatch(
            table=1,
            row=4,
            column=1,
            text=f"識別牌：{tag[0]}",
            highlight_text=tag[1],
        ),
        CellPatch(
            table=1,
            row=4,
            column=2,
            text=f"機場專員：{airport[0]}",
            highlight_text=airport[1],
        ),
    )


def _build_flight_cells(draft: BriefingDraft) -> tuple[CellPatch, ...]:
    patches: list[CellPatch] = []
    for offset in range(2):
        flight = draft.flights[offset] if offset < len(draft.flights) else None
        values = (
            flight.date,
            flight.number,
            flight.origin,
            flight.destination,
            flight.departure_time,
            flight.arrival_time,
        ) if flight is not None else ("", "", "", "", "", "")
        for column, raw in enumerate(values, start=1):
            text = raw or WAITING_FOR_OP
            patches.append(
                CellPatch(
                    table=2,
                    row=offset + 2,
                    column=column,
                    text=text,
                    highlight_text="" if raw else WAITING_FOR_OP,
                )
            )
    return tuple(patches)


def _build_day_cells(
    draft: BriefingDraft,
    *,
    route_character_limit: int,
) -> tuple[CellPatch, ...]:
    patches: list[CellPatch] = []
    for row, day in enumerate(draft.days, start=2):
        route = compact_route_text(
            day.attractions,
            max_characters=route_character_limit,
        )
        meals = (*day.meals[:3], *("" for _ in range(max(0, 3 - len(day.meals)))))
        meal_markers = tuple(_meal_marker(meal) for meal in meals)
        values = (
            (
                format_list_day_date(day.date) if day.date else WAITING_FOR_OP,
                "" if day.date else WAITING_FOR_OP,
            ),
            (route, WAITING_FOR_OP if route == WAITING_FOR_OP else ""),
            (day.hotel or WAITING_FOR_OP, "" if day.hotel else WAITING_FOR_OP),
            ("", ""),
            *((marker, "") for marker in meal_markers),
        )
        for column, (text, highlight) in enumerate(values, start=1):
            patches.append(
                CellPatch(
                    table=3,
                    row=row,
                    column=column,
                    text=text,
                    highlight_text=highlight,
                )
            )
    return tuple(patches)


def _build_guide_cells(op_fields: dict[str, OpField]) -> tuple[CellPatch, ...]:
    name = _op_display(op_fields, "emergency_contact_name")
    phone = _op_display(op_fields, "emergency_contact_phone")
    return (
        CellPatch(4, 1, 2, name[0], name[1]),
        CellPatch(4, 1, 3, phone[0], phone[1]),
    )


def _op_display(
    fields: dict[str, OpField], name: str
) -> tuple[str, str]:
    field = fields.get(name)
    if field is None or not field.confirmed or not field.value.strip():
        return WAITING_FOR_OP, WAITING_FOR_OP
    return field.value.strip(), ""


def _combined_highlight(*values: tuple[str, str]) -> str:
    return WAITING_FOR_OP if any(highlight for _, highlight in values) else ""


def _split_title(value: str) -> tuple[str, ...]:
    title = value.strip()
    if not title:
        return (WAITING_FOR_OP,)
    if len(title) <= 28:
        return (title,)
    break_at = max(
        title.rfind(separator, 0, 29)
        for separator in ("～", "~", "|", "｜", "・")
    )
    if break_at <= 0:
        break_at = 28
    else:
        break_at += 1
    return title[:break_at], title[break_at:].lstrip()


def _validate_fingerprint(value: str) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise ValueError("expected layout fingerprint must be lowercase SHA-256")
    return value


def _validate_layout_profiles(
    profiles: tuple[dict[str, Any], ...],
) -> None:
    required = {
        "name",
        "body_font_points",
        "line_spacing_points",
        "paragraph_space_after_points",
        "cell_top_margin_points",
        "cell_bottom_margin_points",
    }
    if (
        not isinstance(profiles, tuple)
        or not profiles
        or any(
            not isinstance(item, dict) or set(item) != required
            for item in profiles
        )
        or profiles[0].get("name") != "normal"
    ):
        raise ValueError("LIST layout profiles are invalid")


def _list_anchor_checks() -> tuple[AnchorCheck, ...]:
    coordinates = (
        (1, 1, 1),
        (1, 1, 1),
        (1, 2, 1),
        (1, 2, 2),
        (1, 2, 3),
        (1, 3, 1),
        (1, 4, 1),
        (1, 4, 2),
    )
    return tuple(
        AnchorCheck(label, table, row, column)
        for label, (table, row, column) in zip(
            LIST_ANCHOR_LABELS,
            coordinates,
            strict=True,
        )
    )


def _read_patch_report(
    path: Path,
    *,
    target_day_count: int,
    approved_profiles: tuple[str, ...],
) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise WordGenerationError("Word patch report is not valid UTF-8 JSON") from error
    expected_keys = {
        "schema_version",
        "action",
        "word_version",
        "source_inspection",
        "output_inspection",
        "selected_layout_profile",
        "computed_page_count",
        "day_page_map",
        "continuation_group_header",
        "repeated_daily_header",
        "qr_policy",
        "output_bytes",
    }
    if (
        not isinstance(payload, dict)
        or set(payload) != expected_keys
        or payload.get("schema_version") != 2
        or payload.get("action") != "patch"
        or not isinstance(payload.get("word_version"), str)
        or not payload["word_version"]
        or isinstance(payload.get("computed_page_count"), bool)
        or not isinstance(payload.get("computed_page_count"), int)
        or payload["computed_page_count"] <= 0
        or payload.get("selected_layout_profile")
        not in approved_profiles
        or payload.get("continuation_group_header") is not True
        or payload.get("repeated_daily_header") is not True
        or payload.get("qr_policy") != "first_page_only"
        or not isinstance(payload.get("day_page_map"), list)
        or isinstance(payload.get("output_bytes"), bool)
        or not isinstance(payload.get("output_bytes"), int)
        or payload["output_bytes"] <= 0
    ):
        if (
            isinstance(payload, dict)
            and payload.get("schema_version") == 2
        ):
            if payload.get("computed_page_count") in {0, None}:
                raise ValueError("LIST page count must be positive")
            if (
                payload.get("selected_layout_profile")
                not in approved_profiles
            ):
                raise ValueError("LIST layout profile is not approved")
            if payload.get("continuation_group_header") is not True:
                raise ValueError("LIST continuation header is missing")
            if payload.get("repeated_daily_header") is not True:
                raise ValueError("LIST repeated daily header is missing")
        raise WordGenerationError(
            "Word patch report does not match schema version 2"
        )
    try:
        source = ListTemplateInspection.from_dict(payload["source_inspection"])
        output = ListTemplateInspection.from_dict(payload["output_inspection"])
    except ValueError as error:
        raise WordGenerationError("Word template inspection report is invalid") from error
    try:
        day_page_map = tuple(
            DayPagePlacement.from_dict(item)
            for item in payload["day_page_map"]
        )
    except ValueError as error:
        if "LIST_DAY_ROW_TOO_TALL" in str(error):
            raise
        raise ValueError("LIST day page map is invalid") from error
    if (
        tuple(item.day_number for item in day_page_map)
        != tuple(range(1, target_day_count + 1))
        or any(
            item.start_page > payload["computed_page_count"]
            for item in day_page_map
        )
    ):
        raise ValueError("LIST day page map is incomplete or non-sequential")
    return {
        **payload,
        "source_inspection": source,
        "output_inspection": output,
        "selected_layout_profile": payload[
            "selected_layout_profile"
        ],
        "day_page_map": day_page_map,
    }


def _read_simple_word_report(path: Path, *, action: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise WordGenerationError("Word report is not valid UTF-8 JSON") from error
    if (
        not isinstance(payload, dict)
        or set(payload) != {"schema_version", "action", "word_version"}
        or payload.get("schema_version") != 1
        or payload.get("action") != action
        or not isinstance(payload.get("word_version"), str)
        or not payload["word_version"]
    ):
        raise WordGenerationError("Word report does not match schema version 1")
    return payload


def _read_inspection_report(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise WordGenerationError(
            "Word inspection report is not valid UTF-8 JSON"
        ) from error
    if (
        not isinstance(payload, dict)
        or set(payload)
        != {"schema_version", "action", "word_version", "inspection"}
        or payload.get("schema_version") != 1
        or payload.get("action") != "inspect"
        or not isinstance(payload.get("word_version"), str)
        or not payload["word_version"]
    ):
        raise WordGenerationError(
            "Word inspection report does not match schema version 1"
        )
    try:
        inspection = ListTemplateInspection.from_dict(payload["inspection"])
    except ValueError as error:
        raise WordGenerationError("Word template inspection report is invalid") from error
    return {**payload, "inspection": inspection}


def _inspection_day_count(inspection: ListTemplateInspection) -> int:
    if len(inspection.table_shapes) != 4:
        raise ValueError("LIST source inspection has an invalid table count")
    day_count = inspection.table_shapes[2].rows - 1
    expected_list_table_shapes(day_count)
    return day_count


def _write_job(path: Path, payload: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(payload, ensure_ascii=False, indent=2))
        output.write("\n")


def _copy_exclusive(source: Path, destination: Path) -> None:
    created = False
    try:
        with source.open("rb") as input_stream, destination.open("xb") as output_stream:
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
