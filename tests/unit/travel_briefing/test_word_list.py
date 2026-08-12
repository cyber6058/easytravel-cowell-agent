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
    probe_word_capability,
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


@pytest.mark.parametrize("day_count", [5, 6, 7])
def test_patch_plan_maps_a_draft_to_the_existing_four_table_layout(day_count):
    plan = build_list_patch_plan(
        draft(day_count),
        expected_layout_fingerprint="a" * 64,
    )

    assert plan.schema_version == 1
    assert plan.generator_version == "list-word/1"
    assert plan.target_day_count == day_count
    assert plan.expected_table_shapes[2].rows == day_count + 1
    assert plan.header_paragraph(2).text == "團體編號：OSA-SYN-260901"
    assert plan.header_paragraph(3).text == f"團體名稱：合成大阪{day_count}日"
    assert plan.cell(1, 2, 2).text == f"集合時間：{WAITING_FOR_OP}"
    assert plan.cell(1, 2, 2).highlight_text == WAITING_FOR_OP
    assert plan.cell(1, 3, 1).text == "集合地點：第二航廈集合處"
    assert plan.cell(2, 2, 2).text == "JX820"
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
    def __init__(self, source_inspection, output_inspection) -> None:
        self.source_inspection = source_inspection
        self.output_inspection = output_inspection
        self.jobs = []

    def run(self, job_path: Path, *, timeout_seconds: int) -> None:
        self.jobs.append((job_path, timeout_seconds))
        job = json.loads(job_path.read_text(encoding="utf-8"))
        output = Path(job["output_docx"])
        output.write_bytes(b"synthetic docx package")
        Path(job["report_path"]).write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "action": "patch",
                    "word_version": "synthetic",
                    "source_inspection": self.source_inspection.to_dict(),
                    "output_inspection": self.output_inspection.to_dict(),
                    "computed_page_count": 1,
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


def test_build_list_word_uses_a_temp_job_and_publishes_exclusively(tmp_path):
    template = tmp_path / "private-template.doc"
    template.write_bytes(b"synthetic private template")
    output = tmp_path / "new-output.docx"
    source_inspection = template_inspection(5)
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
    assert result.source_layout_fingerprint == layout_fingerprint(source_inspection)
    assert result.output_layout_fingerprint == layout_fingerprint(
        template_inspection(7)
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
    source_inspection = template_inspection(5)
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
