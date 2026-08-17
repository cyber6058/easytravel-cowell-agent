import json
from dataclasses import replace

import pytest

from travel_briefing.models import (
    BriefingDraft,
    Conflict,
    DraftStatus,
    Flight,
    ItineraryDay,
    Notice,
    OpField,
    Product,
    SourceEvidence,
    WeatherForecast,
)
from travel_briefing.script_policy import (
    CORE_REQUIRED_FACT_CATEGORIES,
    SECTION_ORDER,
    build_narration_input,
    dumps_narration_input,
)
from travel_briefing.script_validation import (
    check_script,
    dumps_audio_duration_validation,
    dumps_script_validation,
    validate_audio_duration,
)


def sample_script_draft() -> BriefingDraft:
    source_id = "url-1"
    return BriefingDraft.create(
        status=DraftStatus.DRAFT_READY,
        generated_at="2026-08-09T10:00:00+08:00",
        product=Product(
            code="SYN-OSA-5D",
            name="合成大阪五日",
            region="大阪",
            day_count=5,
            departure_date="2026-09-01",
            return_date="2026-09-05",
            source_ids=(source_id,),
        ),
        sources=(
            SourceEvidence(
                source_id=source_id,
                kind="url",
                location="https://example.invalid/tour",
                sha256="a" * 64,
                retrieved_at="2026-08-09T09:55:00+08:00",
                parser_version="synthetic/1",
            ),
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
                source_ids=(source_id,),
            ),
        ),
        days=(
            ItineraryDay(
                number=1,
                date="2026-09-01",
                city="大阪",
                attractions=("大阪城",),
                meals=(),
                hotel="",
                source_ids=(source_id,),
            ),
        ),
        notices=(
            Notice(
                category="tip",
                text="導遊、領隊與司機小費每人每天新台幣300元。",
                source_ids=(source_id,),
            ),
            Notice(
                category="group_size",
                text="本團共30人。",
                source_ids=(source_id,),
            ),
            Notice(
                category="no_leaving_group",
                text="旅途中不可擅自脫隊。",
                source_ids=(source_id,),
            ),
            Notice(
                category="bus_hours",
                text="每日巴士行車時間約4小時。",
                source_ids=(source_id,),
            ),
            Notice(
                category="insurance",
                text="旅行業責任保險每人250萬元。",
                source_ids=(source_id,),
            ),
            Notice(
                category="passport_validity",
                text="護照效期須有6個月以上。",
                source_ids=(source_id,),
            ),
            Notice(
                category="room_type",
                text="房型以兩人一室為主。",
                source_ids=(source_id,),
            ),
            Notice(
                category="vegetarian",
                text="素食旅客請於出發前告知。",
                source_ids=(source_id,),
            ),
            Notice(
                category="voltage",
                text="日本電壓為100V。",
                source_ids=(source_id,),
            ),
        ),
        weather=(
            WeatherForecast(
                date="2026-09-01",
                display_city="大阪",
                forecast_area="大阪府",
                condition="晴時多雲",
                high_c=30,
                low_c=24,
                precipitation_percent=20,
                issued_at="2026-08-31T17:00:00+09:00",
                retrieved_at="2026-08-31T18:00:00+09:00",
                source_url="https://www.jma.go.jp/example",
                available=True,
            ),
        ),
    )


def test_narration_input_builds_source_bound_required_facts():
    narration_input = build_narration_input(sample_script_draft())

    assert tuple(section.section_id for section in narration_input.sections) == (
        SECTION_ORDER
    )
    facts_by_category = {
        fact.category: fact for fact in narration_input.required_facts
    }
    assert set(CORE_REQUIRED_FACT_CATEGORIES) <= set(facts_by_category)
    assert facts_by_category["tip"].protected_text == (
        "導遊、領隊與司機小費每人每天新台幣300元。"
    )
    assert facts_by_category["tip"].source_ids == ("url-1",)
    assert facts_by_category["tip"].critical_values == ("300元",)
    assert facts_by_category["group_size"].critical_values == ("30人",)
    assert facts_by_category["bus_hours"].critical_values == ("4小時",)
    assert facts_by_category["insurance"].critical_values == ("250萬元",)
    assert facts_by_category["passport_validity"].critical_values == ("6個月",)
    assert facts_by_category["voltage"].critical_values == ("100V",)
    assert facts_by_category["weather_reminder"].origin == "policy"
    assert narration_input.review_items == ()
    assert narration_input.source_rule == (
        "Only rewrite the supplied narration input; do not fetch, infer, or add facts."
    )

    pronunciations = {
        (entry.written, entry.kind): entry.spoken
        for entry in narration_input.pronunciation_entries
    }
    assert pronunciations[("JX820", "flight_number")] == "J X 八二零"
    assert pronunciations[("2026年9月1日", "date")] == "二零二六年九月一日"
    assert pronunciations[("300元", "money")] == "三百元"
    assert pronunciations[("100V", "voltage")] == "一百伏特"
    assert pronunciations[("大阪", "japanese_place")] == "大阪"
    assert pronunciations[("大阪城", "japanese_place")] == "大阪城"


def test_narration_input_accepts_current_standard_notice_categories():
    draft = sample_script_draft()
    extra = tuple(
        Notice(category=category, text=text, source_ids=("url-1",))
        for category, text in (
            ("group_notes", "合成團務提醒。"),
            ("general_notice", "合成一般提醒。"),
            ("time_difference", "合成時差提醒。"),
            ("communications", "合成通訊提醒。"),
            ("visa", "合成簽證提醒。"),
            ("currency", "合成幣值提醒。"),
            ("weather_notice", "合成一般天氣提醒。"),
        )
    )
    with_standard_notices = replace(
        draft,
        notices=draft.notices + extra,
    ).with_recomputed_id()

    narration_input = build_narration_input(with_standard_notices)

    assert not any(
        item.code == "UNKNOWN_NOTICE_CATEGORY"
        for item in narration_input.review_items
    )
    facts = {fact.category: fact for fact in narration_input.required_facts}
    assert "group_notes" not in facts
    assert facts["currency"].section_id == "tips_and_group_rules"
    assert facts["visa"].section_id == "passport_and_accessibility"
    assert facts["weather_notice"].section_id == "voltage_and_weather"


def test_narration_input_does_not_invent_a_missing_required_fact():
    draft = sample_script_draft()
    without_voltage = replace(
        draft,
        notices=tuple(
            notice for notice in draft.notices if notice.category != "voltage"
        ),
    ).with_recomputed_id()

    narration_input = build_narration_input(without_voltage)

    assert narration_input.ready is True
    assert not any(
        fact.category == "voltage" for fact in narration_input.required_facts
    )
    assert any(
        item.code == "MISSING_REQUIRED_FACT" and item.field == "voltage"
        for item in narration_input.review_items
    )
    assert "100V" not in dumps_narration_input(narration_input)


def test_narration_input_prohibits_unresolved_and_unconfirmed_values():
    draft = sample_script_draft()
    blocked = replace(
        draft,
        status=DraftStatus.BLOCKED,
        conflicts=(
            Conflict(
                field="hotel",
                source_a="pdf-1",
                value_a="大阪甲飯店",
                source_b="url-1",
                value_b="大阪乙飯店",
                severity="blocking",
                decision="",
                decided_by="",
            ),
        ),
        op_fields=(
            OpField(
                name="meeting_time",
                value="07:00",
                source="OP",
                confirmed=False,
            ),
        ),
    ).with_recomputed_id()

    narration_input = build_narration_input(blocked)
    payload = json.loads(dumps_narration_input(narration_input))

    assert narration_input.ready is False
    assert narration_input.prohibited_values == (
        "大阪甲飯店",
        "大阪乙飯店",
        "07:00",
    )
    assert payload["schema_version"] == 1
    assert payload["type"] == "briefing_narration_input"
    assert payload["draft_id"] == blocked.draft_id
    assert [item["character_count"] for item in payload["prohibited_values"]] == [
        5,
        5,
        4,
    ]
    serialized = dumps_narration_input(narration_input)
    assert "大阪甲飯店" not in serialized
    assert "大阪乙飯店" not in serialized
    assert "07:00" not in serialized
    assert "BLOCKED_DRAFT" in {item["code"] for item in payload["review_items"]}


def test_narration_input_requires_source_evidence_for_variable_facts():
    draft = sample_script_draft()
    untraceable = replace(
        draft,
        notices=(replace(draft.notices[0], source_ids=("missing-source",)),)
        + draft.notices[1:],
    ).with_recomputed_id()

    narration_input = build_narration_input(untraceable)

    assert narration_input.ready is False
    assert any(
        item.code == "FACT_SOURCE_UNKNOWN" and item.field == "tip-001"
        for item in narration_input.review_items
    )


@pytest.mark.parametrize(
    ("region", "city", "attraction"),
    [
        ("大阪", "京都", "清水寺"),
        ("東北", "仙台", "松島"),
        ("北海道", "札幌", "小樽"),
    ],
)
def test_pronunciation_policy_covers_common_places_in_all_three_regions(
    region,
    city,
    attraction,
):
    draft = sample_script_draft()
    regional = replace(
        draft,
        product=replace(draft.product, region=region),
        days=(replace(draft.days[0], city=city, attractions=(attraction,)),),
    ).with_recomputed_id()

    narration_input = build_narration_input(regional)

    entries = {
        entry.written
        for entry in narration_input.pronunciation_entries
        if entry.kind == "japanese_place"
    }
    assert {city, attraction} <= entries
    assert not any(
        item.code == "UNKNOWN_PRONUNCIATION_TERM"
        for item in narration_input.review_items
    )


def test_unknown_place_is_left_unchanged_for_review():
    draft = sample_script_draft()
    unknown_place = "合成祕境村"
    regional = replace(
        draft,
        days=(replace(draft.days[0], attractions=(unknown_place,)),),
    ).with_recomputed_id()

    narration_input = build_narration_input(regional)

    assert narration_input.ready is True
    assert unknown_place not in {
        entry.written for entry in narration_input.pronunciation_entries
    }
    assert any(
        item.code == "UNKNOWN_PRONUNCIATION_TERM"
        and item.field == unknown_place
        for item in narration_input.review_items
    )
    assert all(
        "不舒服" not in entry.written
        for entry in narration_input.pronunciation_entries
    )


def test_url_only_review_gaps_allow_a_source_bound_draft_script():
    draft = sample_script_draft()
    reviewable = replace(
        draft,
        notices=tuple(
            notice
            for notice in draft.notices
            if notice.category not in {"insurance", "no_leaving_group"}
        ),
        op_fields=(
            OpField(
                name="meeting_time",
                value="待 OP 確認",
                source="OP",
                confirmed=False,
            ),
        ),
        weather=(),
        days=(
            replace(draft.days[0], attractions=("合成未確認景點",)),
        ),
    ).with_recomputed_id()

    narration_input = build_narration_input(reviewable)
    issue_codes = {item.code for item in narration_input.review_items}

    assert narration_input.ready is True
    assert {
        "MISSING_REQUIRED_FACT",
        "UNCONFIRMED_OP_FIELD",
        "WEATHER_DATA_UNAVAILABLE",
        "UNKNOWN_PRONUNCIATION_TERM",
    } <= issue_codes
    validation = check_script(
        narration_input,
        script_from_input(narration_input),
    )
    assert validation.ready is True
    assert "NARRATION_INPUT_NOT_READY" not in {
        issue.code for issue in validation.issues
    }


def script_from_input(narration_input) -> str:
    lines: list[str] = []
    for section in narration_input.sections:
        lines.append(section.marker)
        lines.extend(
            fact.protected_text
            for fact in narration_input.required_facts
            if fact.section_id == section.section_id
        )
    return "\n".join(lines) + "\n"


def test_check_script_accepts_ordered_source_bound_content():
    narration_input = build_narration_input(sample_script_draft())
    script = script_from_input(narration_input)

    result = check_script(narration_input, script)
    payload = json.loads(dumps_script_validation(result))

    assert result.ready is True
    assert result.status == "ready_with_warnings"
    assert result.section_order == SECTION_ORDER
    assert result.character_count > 0
    assert result.estimated_duration_seconds == round(
        result.character_count / result.estimated_chars_per_second,
        1,
    )
    assert {issue.code for issue in result.issues} == {
        "ESTIMATED_AUDIO_TOO_SHORT"
    }
    assert payload["type"] == "briefing_script_validation"
    assert payload["draft_id"] == narration_input.draft_id
    assert "導遊" not in dumps_script_validation(result)


def test_check_script_rejects_reordered_sections():
    narration_input = build_narration_input(sample_script_draft())
    script = script_from_input(narration_input)
    first, second = narration_input.sections[:2]
    script = script.replace(first.marker, "<!-- swap:first -->", 1)
    script = script.replace(second.marker, first.marker, 1)
    script = script.replace("<!-- swap:first -->", second.marker, 1)

    result = check_script(narration_input, script)

    assert result.ready is False
    assert result.status == "blocked"
    assert "SECTION_ORDER_INVALID" in {issue.code for issue in result.issues}


def test_check_script_rejects_keyword_match_with_opposite_meaning():
    narration_input = build_narration_input(sample_script_draft())
    script = script_from_input(narration_input).replace(
        "旅途中不可擅自脫隊。",
        "旅途中可以擅自脫隊。",
    )
    assert "脫隊" in script

    result = check_script(narration_input, script)

    issue_codes = {issue.code for issue in result.issues}
    assert result.ready is False
    assert "REQUIRED_FACT_NOT_PRESERVED" in issue_codes
    assert "CONTRADICTORY_CLAIM" in issue_codes


def test_check_script_rejects_changed_or_unapproved_critical_numbers():
    narration_input = build_narration_input(sample_script_draft())
    script = script_from_input(narration_input).replace("300元", "500元")

    result = check_script(narration_input, script)

    issue_codes = {issue.code for issue in result.issues}
    assert result.ready is False
    assert "CRITICAL_VALUE_MISSING" in issue_codes
    assert "UNAPPROVED_CRITICAL_VALUE" in issue_codes


@pytest.mark.parametrize("unapproved_value", ["JX999", "07:15", "2026年9月9日"])
def test_check_script_rejects_other_unapproved_numeric_claims(unapproved_value):
    narration_input = build_narration_input(sample_script_draft())
    script = script_from_input(narration_input).replace(
        narration_input.sections[-1].marker,
        f"另請留意{unapproved_value}。\n" + narration_input.sections[-1].marker,
    )

    result = check_script(narration_input, script)

    assert result.ready is False
    assert "UNAPPROVED_CRITICAL_VALUE" in {
        issue.code for issue in result.issues
    }


def test_check_script_rejects_a_disputed_value_anywhere_in_the_script():
    draft = sample_script_draft()
    blocked = replace(
        draft,
        status=DraftStatus.BLOCKED,
        conflicts=(
            Conflict(
                field="hotel",
                source_a="pdf-1",
                value_a="大阪甲飯店",
                source_b="url-1",
                value_b="大阪乙飯店",
                severity="blocking",
                decision="",
                decided_by="",
            ),
        ),
    ).with_recomputed_id()
    narration_input = build_narration_input(blocked)
    script = script_from_input(narration_input).replace(
        narration_input.sections[-1].marker,
        "大阪甲飯店。\n" + narration_input.sections[-1].marker,
    )

    result = check_script(narration_input, script)

    assert result.ready is False
    assert "PROHIBITED_VALUE_PRESENT" in {issue.code for issue in result.issues}


@pytest.mark.parametrize("duration_seconds", [360.0, 420.25, 480.0])
def test_actual_audio_duration_accepts_only_the_six_to_eight_minute_window(
    duration_seconds,
):
    result = validate_audio_duration(duration_seconds, revision_count=0)

    assert result.status == "accepted"
    assert result.action == "none"
    assert result.can_revise is False


@pytest.mark.parametrize(
    ("duration_seconds", "action"),
    [(359.999, "supplement_once"), (480.001, "compress_once")],
)
def test_actual_audio_duration_allows_one_fixed_revision(duration_seconds, action):
    result = validate_audio_duration(duration_seconds, revision_count=0)
    payload = json.loads(dumps_audio_duration_validation(result))

    assert result.status == "revise_once"
    assert result.action == action
    assert result.can_revise is True
    assert "protected facts" in result.revision_rule
    assert payload["duration_seconds"] == duration_seconds
    assert payload["target_seconds"] == {"minimum": 360.0, "maximum": 480.0}


@pytest.mark.parametrize("duration_seconds", [300.0, 500.0])
def test_actual_audio_duration_blocks_after_the_single_revision(duration_seconds):
    result = validate_audio_duration(duration_seconds, revision_count=1)

    assert result.status == "blocked"
    assert result.action == "manual_review"
    assert result.can_revise is False


@pytest.mark.parametrize(
    ("duration_seconds", "revision_count"),
    [(0, 0), (-1, 0), (360, -1), (360, 2)],
)
def test_actual_audio_duration_rejects_invalid_measurements(
    duration_seconds,
    revision_count,
):
    with pytest.raises(ValueError):
        validate_audio_duration(duration_seconds, revision_count=revision_count)
