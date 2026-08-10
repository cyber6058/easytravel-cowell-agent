from dataclasses import replace

import pytest

from travel_briefing.errors import BriefingInputError, StaleDraftDecisionError
from travel_briefing.models import (
    BriefingDraft,
    Conflict,
    DraftStatus,
    Flight,
    ItineraryDay,
    Product,
)
from travel_briefing.op_values import (
    apply_conflict_decisions,
    apply_op_values,
    build_missing_op_fields,
)


def draft_with_missing_op_values() -> BriefingDraft:
    return BriefingDraft.create(
        status=DraftStatus.DRAFT_READY,
        generated_at="2026-08-09T12:00:00+08:00",
        product=Product(
            code="OSA-SYN-260901",
            name="合成大阪五日",
            region="大阪",
            day_count=5,
            departure_date="2026-09-01",
            return_date="2026-09-05",
            source_ids=("pdf-p001",),
        ),
        op_fields=build_missing_op_fields(),
    )


def draft_with_missing_product_region() -> BriefingDraft:
    draft = draft_with_missing_op_values()
    return replace(
        draft,
        product=replace(draft.product, region=""),
        op_fields=build_missing_op_fields(include_product_region=True),
    ).with_recomputed_id()


def test_op_can_confirm_a_requested_product_region():
    draft = draft_with_missing_product_region()

    updated = apply_op_values(
        draft,
        {
            "draft_id": draft.draft_id,
            "values": {"product_region": "北海道"},
        },
    )

    assert updated.product.region == "北海道"
    region_field = next(
        field for field in updated.op_fields if field.name == "product_region"
    )
    assert region_field.value == "北海道"
    assert region_field.source == "OP"
    assert region_field.confirmed is True
    assert region_field.highlight == ""
    assert updated.draft_id != draft.draft_id
    assert updated.draft_id == updated.with_recomputed_id().draft_id


@pytest.mark.parametrize("value", ["關西", "日本", "unknown"])
def test_op_rejects_an_unsupported_product_region(value):
    draft = draft_with_missing_product_region()

    with pytest.raises(BriefingInputError) as captured:
        apply_op_values(
            draft,
            {
                "draft_id": draft.draft_id,
                "values": {"product_region": value},
            },
        )

    assert captured.value.details == {"field": "product_region"}


def test_op_cannot_override_a_product_region_that_was_not_requested():
    draft = draft_with_missing_op_values()

    with pytest.raises(BriefingInputError) as captured:
        apply_op_values(
            draft,
            {
                "draft_id": draft.draft_id,
                "values": {"product_region": "北海道"},
            },
        )

    assert captured.value.details == {"fields": ["product_region"]}


def test_current_op_values_confirm_only_submitted_fields():
    draft = draft_with_missing_op_values()

    updated = apply_op_values(
        draft,
        {
            "draft_id": draft.draft_id,
            "values": {
                "meeting_time": "06:30",
                "meeting_place": "桃園機場第一航廈合成集合點",
            },
        },
    )

    fields = {field.name: field for field in updated.op_fields}
    assert fields["meeting_time"].value == "06:30"
    assert fields["meeting_time"].source == "OP"
    assert fields["meeting_time"].confirmed is True
    assert fields["meeting_time"].highlight == ""
    assert fields["meeting_place"].confirmed is True
    assert fields["tour_leader_name"].value == "待 OP 確認"
    assert fields["tour_leader_name"].confirmed is False
    assert fields["tour_leader_name"].highlight == "yellow"
    assert updated.draft_id != draft.draft_id
    assert updated.draft_id == updated.with_recomputed_id().draft_id


def test_changing_op_values_cannot_inherit_a_confirmed_status():
    confirmed = replace(
        draft_with_missing_op_values(),
        status=DraftStatus.CONFIRMED,
    )

    updated = apply_op_values(
        confirmed,
        {
            "draft_id": confirmed.draft_id,
            "values": {"meeting_time": "06:30"},
        },
    )

    assert updated.status is DraftStatus.DRAFT_READY


def test_op_values_reject_a_stale_draft_binding():
    draft = draft_with_missing_op_values()

    with pytest.raises(StaleDraftDecisionError) as captured:
        apply_op_values(
            draft,
            {
                "draft_id": "0" * 64,
                "values": {"meeting_time": "06:30"},
            },
        )

    assert captured.value.code == "STALE_DRAFT_DECISION"
    assert captured.value.details == {"kind": "op_values"}


@pytest.mark.parametrize("value", ["", "   ", "待 OP 確認", "待OP確認"])
def test_op_values_cannot_confirm_an_empty_or_placeholder_value(value):
    draft = draft_with_missing_op_values()

    with pytest.raises(BriefingInputError):
        apply_op_values(
            draft,
            {
                "draft_id": draft.draft_id,
                "values": {"meeting_time": value},
            },
        )


def draft_with_blocking_conflicts() -> BriefingDraft:
    return BriefingDraft.create(
        status=DraftStatus.BLOCKED,
        generated_at="2026-08-09T12:00:00+08:00",
        product=Product(
            code="OSA-SYN-260901",
            name="合成大阪五日",
            region="大阪",
            day_count=5,
            departure_date="2026-09-01",
            return_date="2026-09-05",
            source_ids=("pdf-p001",),
        ),
        flights=(
            Flight(
                date="2026-09-01",
                airline="星宇航空",
                number="JX820",
                origin="TPE",
                destination="KIX",
                departure_time="08:30",
                arrival_time="12:10",
                source_ids=("pdf-p001",),
            ),
        ),
        days=(
            ItineraryDay(
                number=1,
                date="2026-09-01",
                city="大阪",
                attractions=("大阪城", "清水寺"),
                meals=("早餐",),
                hotel="合成大阪飯店",
                source_ids=("pdf-p001",),
            ),
        ),
        conflicts=(
            Conflict(
                field="product.departure_date",
                source_a="pdf-p001",
                value_a="2026-09-01",
                source_b="web-1",
                value_b="2026-09-02",
                severity="blocking",
                decision="",
                decided_by="",
            ),
            Conflict(
                field="flights[1].number",
                source_a="pdf-p001",
                value_a="JX820",
                source_b="web-1",
                value_b="VZ566",
                severity="blocking",
                decision="",
                decided_by="",
            ),
            Conflict(
                field="days[1].attractions",
                source_a="pdf-p001",
                value_a='["大阪城","清水寺"]',
                source_b="web-1",
                value_b='["清水寺","大阪城"]',
                severity="blocking",
                decision="",
                decided_by="",
            ),
        ),
    )


def test_conflict_decisions_write_selected_values_back_to_the_draft():
    draft = draft_with_blocking_conflicts()

    updated = apply_conflict_decisions(
        draft,
        {
            "draft_id": draft.draft_id,
            "decisions": {
                "product.departure_date": "use_b",
                "flights[1].number": "use_b",
                "days[1].attractions": "use_b",
            },
        },
    )

    assert updated.product.departure_date == "2026-09-02"
    assert updated.flights[0].number == "VZ566"
    assert updated.days[0].attractions == ("清水寺", "大阪城")
    assert all(conflict.decision == "use_b" for conflict in updated.conflicts)
    assert all(conflict.decided_by == "OP" for conflict in updated.conflicts)
    assert updated.status is DraftStatus.DRAFT_READY
    assert updated.draft_id != draft.draft_id


def test_conflict_decisions_reject_a_stale_draft_binding():
    draft = draft_with_blocking_conflicts()

    with pytest.raises(StaleDraftDecisionError) as captured:
        apply_conflict_decisions(
            draft,
            {
                "draft_id": "0" * 64,
                "decisions": {"product.departure_date": "use_a"},
            },
        )

    assert captured.value.code == "STALE_DRAFT_DECISION"
    assert captured.value.details == {"kind": "conflict_decisions"}
