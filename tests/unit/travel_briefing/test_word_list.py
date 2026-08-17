import json
from dataclasses import replace
from pathlib import Path

import pytest

from travel_briefing.models import (
    BriefingDraft,
    Conflict,
    DraftStatus,
    Flight,
    ItineraryDay,
    OpField,
    Product,
)
from travel_briefing.word_list import (
    WAITING_FOR_OP,
    build_list_patch_plan,
    build_list_word,
    compact_route_text,
    inspect_list_template,
    inspect_list_templates_v2,
    probe_word_capability,
)
from travel_briefing.list_calibration import (
    ListLayoutProfile,
    ListTemplateInspectionV2,
)
from travel_briefing.template_contract import (
    LIST_ANCHOR_LABELS,
    LIST_HEADER_ACCESSIBLE_CELLS,
    ListTemplateInspection,
    expected_list_table_shapes,
    layout_fingerprint,
)


def draft(day_count: int = 5) -> BriefingDraft:
    days = tuple(
        ItineraryDay(
            number=number,
            date=f"2026-09-{number:02d}",
            city="大阪",
            attractions=(f"合成景點 {number}A", f"合成景點 {number}B"),
            meals=("早餐", "午餐", "晚餐"),
            hotel=f"合成飯店 {number}",
            source_ids=("pdf-1",),
        )
        for number in range(1, day_count + 1)
    )
    return BriefingDraft.create(
        status=DraftStatus.DRAFT_READY,
        generated_at="2026-08-12T14:00:00+08:00",
        product=Product(
            code="OSA-SYN-260901",
            name=f"合成大阪{day_count}日",
            region="大阪",
            day_count=day_count,
            departure_date="2026-09-01",
            return_date=f"2026-09-{day_count:02d}",
            source_ids=("pdf-1",),
        ),
        flights=(
            Flight(
                date="2026-09-01",
                airline="星宇航空",
                number="JX820",
                origin="TPE",
                destination="KIX",
                departure_time="08:30",
                arrival_time="12:00",
                source_ids=("pdf-1",),
            ),
            Flight(
                date=f"2026-09-{day_count:02d}",
                airline="星宇航空",
                number="JX821",
                origin="KIX",
                destination="TPE",
                departure_time="13:00",
                arrival_time="15:25",
                source_ids=("pdf-1",),
            ),
        ),
        days=days,
        op_fields=(
            missing_op_field("meeting_time"),
            confirmed_op_field("meeting_place", "第二航廈集合處"),
            confirmed_op_field("tour_leader_name", "合成領隊"),
            missing_op_field("tour_leader_phone"),
            missing_op_field("identification_or_luggage_tag"),
            missing_op_field("airport_representative"),
            missing_op_field("emergency_contact_name"),
            missing_op_field("emergency_contact_phone"),
            missing_op_field("alternate_hotel"),
        ),
    )


def missing_op_field(name: str) -> OpField:
    return OpField(
        name=name,
        value=WAITING_FOR_OP,
        source="",
        confirmed=False,
        highlight="yellow",
    )


def confirmed_op_field(name: str, value: str) -> OpField:
    return OpField(
        name=name,
        value=value,
        source="OP",
        confirmed=True,
    )


@pytest.mark.parametrize("day_count", [1, 4, 5, 6, 7, 8, 12])
def test_patch_plan_maps_any_positive_trip_to_dynamic_daily_rows(day_count):
    plan = build_list_patch_plan(
        draft(day_count),
        master_sha256="a" * 64,
        calibration_manifest_sha256="b" * 64,
        normalized_structure_fingerprint="c" * 64,
        layout_profiles=(
            {
                "name": "normal",
                "body_font_points": 10.0,
                "line_spacing_points": 12.0,
                "paragraph_space_after_points": 1.0,
                "cell_top_margin_points": 1.4,
                "cell_bottom_margin_points": 1.4,
            },
        ),
    )

    assert plan.schema_version == 2
    assert plan.generator_version == "list-word/2"
    assert plan.master_sha256 == "a" * 64
    assert plan.calibration_manifest_sha256 == "b" * 64
    assert plan.normalized_structure_fingerprint == "c" * 64
    assert plan.target_day_count == day_count
    assert plan.expected_master_table_shapes[2].rows == 2
    assert plan.expected_table_shapes[2].rows == day_count + 1
    assert plan.header_paragraph(2).text == "團體編號：OSA-SYN-260901"
    assert plan.header_paragraph(3).text == f"團體名稱：合成大阪{day_count}日"
    assert plan.cell(1, 2, 2).text == f"集合時間：{WAITING_FOR_OP}"
    assert plan.cell(1, 2, 2).highlight_text == WAITING_FOR_OP
    assert plan.cell(1, 3, 1).text == "集合地點：第二航廈集合處"
    assert plan.cell(2, 2, 2).text == "JX820"
    assert plan.cell(3, 2, 1).text == "9/1"
    assert plan.cell(3, day_count + 1, 2).text == (
        f"合成景點 {day_count}A／合成景點 {day_count}B"
    )
    assert plan.cell(4, 1, 2).text == WAITING_FOR_OP
    assert plan.cell(4, 1, 2).highlight_text == WAITING_FOR_OP


def test_patch_plan_requires_complete_sequential_days_and_at_most_two_flights():
    source = draft()
    with pytest.raises(ValueError, match="day records"):
        build_list_patch_plan(
            replace(source, days=source.days[:-1]),
            expected_layout_fingerprint="a" * 64,
        )

    duplicated = replace(
        source,
        days=(source.days[0], source.days[0], *source.days[2:]),
    )
    with pytest.raises(ValueError, match="sequential"):
        build_list_patch_plan(
            duplicated,
            expected_layout_fingerprint="a" * 64,
        )
    with pytest.raises(ValueError, match="flight rows"):
        build_list_patch_plan(
            replace(source, flights=(*source.flights, source.flights[0])),
            expected_layout_fingerprint="a" * 64,
        )


def test_confirmed_document_refuses_unconfirmed_or_yellow_op_fields():
    source = replace(draft(), status=DraftStatus.CONFIRMED)

    with pytest.raises(ValueError, match="CONFIRMED"):
        build_list_patch_plan(
            source,
            expected_layout_fingerprint="a" * 64,
        )

    with pytest.raises(ValueError, match="CONFIRMED"):
        build_list_patch_plan(
            replace(source, op_fields=()),
            expected_layout_fingerprint="a" * 64,
        )


def test_patch_plan_never_renders_an_unresolved_blocking_conflict():
    source = replace(
        draft(),
        status=DraftStatus.BLOCKED,
        conflicts=(
            Conflict(
                field="product.departure_date",
                source_a="pdf-1",
                value_a="2026-09-01",
                source_b="web-1",
                value_b="2026-09-02",
                severity="blocking",
                decision="",
                decided_by="",
            ),
        ),
    ).with_recomputed_id()

    with pytest.raises(ValueError, match="blocking conflicts"):
        build_list_patch_plan(
            source,
            expected_layout_fingerprint="a" * 64,
        )


def test_compaction_removes_only_parenthetical_detail_and_never_truncates():
    attractions = (
        "大阪城（外觀拍照與自由散步）",
        "清水寺（含參拜時間）",
    )

    assert compact_route_text(attractions, max_characters=80) == (
        "大阪城（外觀拍照與自由散步）／清水寺（含參拜時間）"
    )
    assert compact_route_text(attractions, max_characters=8) == "大阪城、清水寺"
    with pytest.raises(ValueError, match="too long"):
        compact_route_text(("無法安全縮短的超級長景點名稱",), max_characters=4)


def test_patch_plan_requires_a_sha256_layout_fingerprint():
    with pytest.raises(ValueError, match="fingerprint"):
        build_list_patch_plan(draft(), expected_layout_fingerprint="unknown")


class SyntheticWordAdapter:
    def __init__(
        self,
        source_inspection,
        output_inspection,
        *,
        page_count=1,
        selected_profile="normal",
        day_page_map=None,
        continuation_group_header=True,
        repeated_daily_header=True,
    ) -> None:
        self.source_inspection = source_inspection
        self.output_inspection = output_inspection
        self.page_count = page_count
        self.selected_profile = selected_profile
        self.day_page_map = day_page_map
        self.continuation_group_header = continuation_group_header
        self.repeated_daily_header = repeated_daily_header
        self.jobs = []

    def run(self, job_path: Path, *, timeout_seconds: int) -> None:
        self.jobs.append((job_path, timeout_seconds))
        job = json.loads(job_path.read_text(encoding="utf-8"))
        output = Path(job["output_docx"])
        output.write_bytes(b"synthetic docx package")
        target_days = job["plan"]["target_day_count"]
        day_page_map = self.day_page_map or [
            {
                "day_number": number,
                "start_page": min(number, self.page_count),
                "end_page": min(number, self.page_count),
            }
            for number in range(1, target_days + 1)
        ]
        Path(job["report_path"]).write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "action": "patch",
                    "word_version": "synthetic",
                    "source_inspection": self.source_inspection.to_dict(),
                    "output_inspection": self.output_inspection.to_dict(),
                    "selected_layout_profile": self.selected_profile,
                    "computed_page_count": self.page_count,
                    "day_page_map": day_page_map,
                    "continuation_group_header": (
                        self.continuation_group_header
                    ),
                    "repeated_daily_header": self.repeated_daily_header,
                    "qr_policy": "first_page_only",
                    "output_bytes": output.stat().st_size,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )


def template_inspection(day_count: int) -> ListTemplateInspection:
    return ListTemplateInspection(
        table_shapes=expected_list_table_shapes(day_count),
        anchor_labels=LIST_ANCHOR_LABELS,
        list_header_accessible_cells=LIST_HEADER_ACCESSIBLE_CELLS,
        list_header_paragraph_count=4,
        header_qr_candidate_count=1,
        section_count=1,
        page_width_points=595.28,
        page_height_points=841.89,
        orientation="portrait",
    )


def template_inspection_v2(day_count: int) -> ListTemplateInspectionV2:
    hashes = {
        name: (name.encode("utf-8").hex() + "0" * 64)[:64]
        for name in (
            "style",
            "font",
            "paragraph",
            "border",
            "shading",
            "daily-header",
            "daily-body",
            "dynamic",
        )
    }
    return ListTemplateInspectionV2(
        day_count=day_count,
        table_shapes=expected_list_table_shapes(day_count),
        anchor_labels=LIST_ANCHOR_LABELS,
        list_header_accessible_cells=LIST_HEADER_ACCESSIBLE_CELLS,
        list_header_paragraph_count=4,
        section_count=1,
        page_width_points=595.28,
        page_height_points=841.89,
        orientation="portrait",
        margins_points=(36.0, 36.0, 31.5, 31.5),
        header_distance_points=18.0,
        footer_distance_points=18.0,
        table_column_widths_points=(
            (180.0, 180.0, 180.0),
            (90.0, 90.0, 90.0, 90.0, 90.0, 90.0),
            (54.0, 72.0, 108.0, 90.0, 72.0, 72.0, 72.0),
            (180.0, 180.0, 180.0),
        ),
        merged_cell_map=("table-1:r1c1-r1c3",),
        qr_shape_count=1,
        shape_geometry_points=(("qr", 500.0, 12.0, 42.0, 42.0),),
        style_digest=hashes["style"],
        font_digest=hashes["font"],
        paragraph_digest=hashes["paragraph"],
        border_digest=hashes["border"],
        shading_digest=hashes["shading"],
        daily_header_digest=hashes["daily-header"],
        daily_body_prototype_digest=hashes["daily-body"],
        dynamic_content_digest=hashes["dynamic"],
        adaptive_profiles=(
            ListLayoutProfile(
                name="normal",
                body_font_points=10.0,
                line_spacing_points=12.0,
                paragraph_space_after_points=1.0,
                cell_top_margin_points=1.4,
                cell_bottom_margin_points=1.4,
            ),
        ),
    )


class SyntheticInspectionV2Adapter:
    def __init__(self, observed: ListTemplateInspectionV2) -> None:
        self.observed = observed

    def run(self, job_path: Path, *, timeout_seconds: int) -> None:
        job = json.loads(job_path.read_text(encoding="utf-8"))
        report = {
            "schema_version": 2,
            "action": "inspect-v2",
            "word_version": "16.0-synthetic",
            "samples": [
                {
                    "sample_id": f"sample-{index:03d}",
                    "inspection": self.observed.to_dict(),
                }
                for index in range(1, 4)
            ],
        }
        Path(job["report_path"]).write_text(
            json.dumps(report, ensure_ascii=False),
            encoding="utf-8",
        )


def test_build_list_word_uses_a_temp_job_and_publishes_exclusively(tmp_path):
    template = tmp_path / "private-template.doc"
    template.write_bytes(b"synthetic private template")
    output = tmp_path / "new-output.docx"
    source_inspection = template_inspection(1)
    adapter = SyntheticWordAdapter(source_inspection, template_inspection(7))

    result = build_list_word(
        draft(7),
        template_path=template,
        output_docx=output,
        expected_layout_fingerprint=layout_fingerprint(source_inspection),
        adapter=adapter,
        timeout_seconds=90,
    )

    assert output.read_bytes() == b"synthetic docx package"
    assert template.read_bytes() == b"synthetic private template"
    assert result.docx_path == output.resolve()
    assert result.byte_count == len(b"synthetic docx package")
    assert result.selected_layout_profile == "normal"
    assert result.day_page_map[-1].day_number == 7
    assert result.continuation_group_header is True
    assert result.repeated_daily_header is True
    assert result.source_layout_fingerprint == layout_fingerprint(source_inspection)
    assert result.output_layout_fingerprint == layout_fingerprint(
        template_inspection(7)
    )
    assert (
        result.source_layout_fingerprint
        == result.output_layout_fingerprint
    )
    received_job, timeout = adapter.jobs[0]
    assert timeout == 90
    assert received_job.name == "word-job.json"
    assert not received_job.exists()


def test_build_list_word_refuses_existing_output_before_calling_word(tmp_path):
    template = tmp_path / "private-template.doc"
    template.write_bytes(b"synthetic private template")
    output = tmp_path / "existing.docx"
    output.write_bytes(b"user owned")
    observed = template_inspection(5)
    adapter = SyntheticWordAdapter(observed, observed)

    with pytest.raises(ValueError, match="must not already exist"):
        build_list_word(
            draft(),
            template_path=template,
            output_docx=output,
            expected_layout_fingerprint=layout_fingerprint(observed),
            adapter=adapter,
        )

    assert output.read_bytes() == b"user owned"
    assert adapter.jobs == []


def test_build_list_word_rejects_report_or_qr_drift_without_publishing(tmp_path):
    template = tmp_path / "private-template.docx"
    template.write_bytes(b"synthetic private template")
    output = tmp_path / "new-output.docx"
    source_inspection = template_inspection(1)
    changed_output = replace(
        template_inspection(5),
        header_qr_candidate_count=0,
    )
    adapter = SyntheticWordAdapter(source_inspection, changed_output)

    with pytest.raises(ValueError, match="QR candidate"):
        build_list_word(
            draft(),
            template_path=template,
            output_docx=output,
            expected_layout_fingerprint=layout_fingerprint(source_inspection),
            adapter=adapter,
        )

    assert not output.exists()


@pytest.mark.parametrize(
    ("day_count", "page_count", "selected_profile"),
    [(8, 1, "compact"), (7, 2, "normal"), (8, 3, "normal")],
)
def test_word_pagination_outcome_depends_on_report_not_day_count(
    tmp_path,
    day_count,
    page_count,
    selected_profile,
):
    template = tmp_path / "list-master.docx"
    template.write_bytes(b"synthetic master")
    output = tmp_path / "output.docx"
    source = template_inspection(1)
    profiles = (
        {
            "name": "normal",
            "body_font_points": 10.0,
            "line_spacing_points": 12.0,
            "paragraph_space_after_points": 1.0,
            "cell_top_margin_points": 1.4,
            "cell_bottom_margin_points": 1.4,
        },
        {
            "name": "compact",
            "body_font_points": 9.0,
            "line_spacing_points": 10.5,
            "paragraph_space_after_points": 0.0,
            "cell_top_margin_points": 1.4,
            "cell_bottom_margin_points": 1.4,
        },
    )
    adapter = SyntheticWordAdapter(
        source,
        template_inspection(day_count),
        page_count=page_count,
        selected_profile=selected_profile,
    )

    result = build_list_word(
        draft(day_count),
        template_path=template,
        output_docx=output,
        expected_layout_fingerprint=layout_fingerprint(source),
        layout_profiles=profiles,
        adapter=adapter,
    )

    assert result.computed_page_count == page_count
    assert result.selected_layout_profile == selected_profile
    received = json.loads(
        adapter.jobs[0][0].read_text(encoding="utf-8")
    ) if adapter.jobs[0][0].exists() else None
    assert received is None


@pytest.mark.parametrize(
    ("adapter_changes", "message"),
    [
        (
            {
                "day_page_map": [
                    {"day_number": 1, "start_page": 1, "end_page": 2},
                    *[
                        {
                            "day_number": number,
                            "start_page": 2,
                            "end_page": 2,
                        }
                        for number in range(2, 8)
                    ],
                ],
                "page_count": 2,
            },
            "LIST_DAY_ROW_TOO_TALL",
        ),
        (
            {
                "day_page_map": [
                    {
                        "day_number": number,
                        "start_page": 1,
                        "end_page": 1,
                    }
                    for number in range(1, 7)
                ],
            },
            "day page map",
        ),
        ({"page_count": 0}, "page count"),
        ({"selected_profile": "unapproved"}, "layout profile"),
        ({"continuation_group_header": False}, "continuation"),
        ({"repeated_daily_header": False}, "repeated"),
    ],
)
def test_word_pagination_report_fails_closed(
    tmp_path,
    adapter_changes,
    message,
):
    template = tmp_path / "list-master.docx"
    template.write_bytes(b"synthetic master")
    source = template_inspection(1)
    adapter = SyntheticWordAdapter(
        source,
        template_inspection(7),
        **adapter_changes,
    )

    with pytest.raises((ValueError, Exception), match=message):
        build_list_word(
            draft(7),
            template_path=template,
            output_docx=tmp_path / "output.docx",
            expected_layout_fingerprint=layout_fingerprint(source),
            adapter=adapter,
        )

    assert not (tmp_path / "output.docx").exists()


class SyntheticProbeInspectAdapter:
    def __init__(self, observed) -> None:
        self.observed = observed
        self.actions = []

    def run(self, job_path: Path, *, timeout_seconds: int) -> None:
        job = json.loads(job_path.read_text(encoding="utf-8"))
        self.actions.append((job["action"], timeout_seconds))
        report = {
            "schema_version": 1,
            "action": job["action"],
            "word_version": "16.0-synthetic",
        }
        if job["action"] == "inspect":
            report["inspection"] = self.observed.to_dict()
            assert [item["label"] for item in job["anchor_checks"]] == list(
                LIST_ANCHOR_LABELS
            )
        Path(job["report_path"]).write_text(
            json.dumps(report, ensure_ascii=False),
            encoding="utf-8",
        )


def test_word_probe_is_version_only_and_bounded_to_twenty_seconds():
    adapter = SyntheticProbeInspectAdapter(template_inspection(5))

    result = probe_word_capability(adapter)

    assert result.available is True
    assert result.word_version == "16.0-synthetic"
    assert adapter.actions == [("probe", 20)]


def test_template_inspection_returns_but_does_not_auto_approve_a_fingerprint(
    tmp_path,
):
    template = tmp_path / "private-template.doc"
    template.write_bytes(b"synthetic private template")
    observed = template_inspection(6)
    adapter = SyntheticProbeInspectAdapter(observed)

    result = inspect_list_template(template, adapter=adapter)

    assert result.day_count == 6
    assert result.layout_fingerprint == layout_fingerprint(observed)
    assert result.word_version == "16.0-synthetic"
    with pytest.raises(ValueError, match="fingerprint"):
        inspect_list_template(
            template,
            adapter=adapter,
            expected_layout_fingerprint="0" * 64,
        )


def test_schema_two_inspection_wrapper_returns_sanitized_sample_evidence(
    tmp_path,
):
    paths = tuple(tmp_path / f"sample-{index}.doc" for index in range(1, 4))
    for path in paths:
        path.write_bytes(b"synthetic")
    observed = template_inspection_v2(5)
    adapter = SyntheticInspectionV2Adapter(observed)

    result = inspect_list_templates_v2(paths, adapter=adapter)

    assert len(result.samples) == 3
    assert result.word_version == "16.0-synthetic"
    assert all(
        item.source_sha256 == result.samples[0].source_sha256
        for item in result.samples
    )
