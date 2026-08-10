from dataclasses import replace

import pytest

from travel_briefing.adapters.newamazing import ParsedNewAmazingPage
from travel_briefing.adapters.pdf_itinerary import ParsedPdfItinerary
from travel_briefing.merge import merge_briefing_sources
from travel_briefing.models import (
    DraftStatus,
    Flight,
    ItineraryDay,
    Notice,
    Product,
    SourceEvidence,
    WeatherForecast,
)
from travel_briefing.op_values import (
    REQUIRED_OP_FIELD_NAMES,
    apply_conflict_decisions,
)


PDF_SOURCE = SourceEvidence(
    source_id="pdf-p001",
    kind="pdf_page",
    location="synthetic.pdf#page=1",
    sha256="a" * 64,
    retrieved_at="2026-08-09T11:00:00+08:00",
    parser_version="pdf-itinerary/1",
)
WEB_SOURCE = SourceEvidence(
    source_id="web-1",
    kind="newamazing_html",
    location=(
        "https://www.newamazing.com.tw/EW/GO/GroupDetail.asp?"
        "prodCd=OSA-SYN-260901"
    ),
    sha256="b" * 64,
    retrieved_at="2026-08-09T11:05:00+08:00",
    parser_version="newamazing-html/1",
)


def product(source_id: str) -> Product:
    return Product(
        code="OSA-SYN-260901",
        name="合成大阪五日",
        region="大阪",
        day_count=5,
        departure_date="2026-09-01",
        return_date="2026-09-05",
        source_ids=(source_id,),
    )


def flights(source_id: str) -> tuple[Flight, ...]:
    return (
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
        Flight(
            date="2026-09-05",
            airline="星宇航空",
            number="JX821",
            origin="KIX",
            destination="TPE",
            departure_time="13:20",
            arrival_time="15:25",
            source_ids=(source_id,),
        ),
    )


def days(source_id: str) -> tuple[ItineraryDay, ...]:
    return tuple(
        ItineraryDay(
            number=number,
            date=f"2026-09-0{number}",
            city="大阪",
            attractions=(f"合成景點 {number}A", f"合成景點 {number}B"),
            meals=("早餐", "晚餐"),
            hotel="合成大阪飯店" if number < 5 else "無",
            source_ids=(source_id,),
        )
        for number in range(1, 6)
    )


def pdf_source() -> ParsedPdfItinerary:
    return ParsedPdfItinerary(
        sources=(PDF_SOURCE,),
        product=product(PDF_SOURCE.source_id),
        flights=flights(PDF_SOURCE.source_id),
        days=days(PDF_SOURCE.source_id),
    )


def web_source() -> ParsedNewAmazingPage:
    return ParsedNewAmazingPage(
        source=WEB_SOURCE,
        product=product(WEB_SOURCE.source_id),
        flights=flights(WEB_SOURCE.source_id),
        days=days(WEB_SOURCE.source_id),
        notices=(
            Notice(
                category="tip",
                text="每人每天新台幣 300 元。",
                source_ids=(WEB_SOURCE.source_id,),
            ),
        ),
    )


def test_merge_prefers_pdf_itinerary_and_current_web_notices():
    pdf = pdf_source()
    web = web_source()

    draft = merge_briefing_sources(
        generated_at="2026-08-09T11:10:00+08:00",
        pdf=pdf,
        web=web,
    )

    assert draft.status is DraftStatus.DRAFT_READY
    assert draft.product == pdf.product
    assert draft.flights == pdf.flights
    assert draft.days == pdf.days
    assert draft.notices == web.notices
    assert draft.sources == (PDF_SOURCE, WEB_SOURCE)
    assert draft.conflicts == ()
    assert draft.draft_id == draft.with_recomputed_id().draft_id


def test_merge_marks_every_missing_op_field_as_a_yellow_placeholder():
    draft = merge_briefing_sources(
        generated_at="2026-08-09T11:10:00+08:00",
        web=web_source(),
    )

    assert tuple(field.name for field in draft.op_fields) == (
        REQUIRED_OP_FIELD_NAMES
    )
    assert all(field.value == "待 OP 確認" for field in draft.op_fields)
    assert all(field.source == "" for field in draft.op_fields)
    assert all(field.confirmed is False for field in draft.op_fields)
    assert all(field.highlight == "yellow" for field in draft.op_fields)


def test_merge_warns_when_url_only_source_has_no_explicit_lodging_city():
    web = web_source()
    web = replace(
        web,
        days=tuple(replace(day, city="") for day in web.days),
    )

    draft = merge_briefing_sources(
        generated_at="2026-08-09T11:10:00+08:00",
        web=web,
    )

    assert draft.status is DraftStatus.DRAFT_READY
    assert [warning.code for warning in draft.warnings] == [
        "SOURCE_CITY_MISSING"
    ]
    assert draft.warnings[0].source_ids == (WEB_SOURCE.source_id,)


def test_merge_uses_pdf_city_when_live_web_contract_does_not_publish_one():
    web = web_source()
    web = replace(
        web,
        days=tuple(replace(day, city="") for day in web.days),
    )

    draft = merge_briefing_sources(
        generated_at="2026-08-09T11:10:00+08:00",
        pdf=pdf_source(),
        web=web,
    )

    assert draft.status is DraftStatus.DRAFT_READY
    assert not any(conflict.field.endswith(".city") for conflict in draft.conflicts)
    assert "SOURCE_CITY_MISSING" in {
        warning.code for warning in draft.warnings
    }


def test_merge_attaches_weather_without_overriding_higher_priority_sources():
    forecast = WeatherForecast(
        date="2026-09-01",
        display_city="大阪",
        forecast_area="大阪府",
        condition="晴",
        high_c=30,
        low_c=24,
        precipitation_percent=20,
        issued_at="2026-08-31T17:00:00+09:00",
        retrieved_at="2026-08-31T18:00:00+09:00",
        source_url="https://www.jma.go.jp/synthetic",
        available=True,
    )
    pdf = pdf_source()

    draft = merge_briefing_sources(
        generated_at="2026-08-09T11:10:00+08:00",
        pdf=pdf,
        web=web_source(),
        weather=(forecast,),
    )

    assert draft.product == pdf.product
    assert draft.days == pdf.days
    assert draft.weather == (forecast,)


@pytest.mark.parametrize(
    ("source_kind", "expected_source_id", "expected_warning_codes"),
    [
        ("pdf", PDF_SOURCE.source_id, ["WEB_NOTICES_MISSING"]),
        ("web", WEB_SOURCE.source_id, []),
    ],
)
def test_merge_supports_each_single_source_without_claiming_missing_notices(
    source_kind,
    expected_source_id,
    expected_warning_codes,
):
    inputs = (
        {"pdf": pdf_source()} if source_kind == "pdf" else {"web": web_source()}
    )

    draft = merge_briefing_sources(
        generated_at="2026-08-09T11:10:00+08:00",
        **inputs,
    )

    assert draft.status is DraftStatus.DRAFT_READY
    assert draft.product.source_ids == (expected_source_id,)
    assert [warning.code for warning in draft.warnings] == (
        expected_warning_codes
    )
    if source_kind == "pdf":
        assert draft.notices == ()
    else:
        assert draft.notices == web_source().notices


@pytest.mark.parametrize(
    ("case", "expected_field"),
    [
        ("departure_date", "product.departure_date"),
        ("return_date", "product.return_date"),
        ("day_count", "product.day_count"),
        ("flight_number", "flights[1].number"),
        ("hotel", "days[2].hotel"),
        ("city", "days[2].city"),
        ("attraction_order", "days[2].attractions"),
    ],
)
def test_merge_blocks_each_safety_critical_source_conflict(
    case,
    expected_field,
):
    web = web_source()
    if case == "departure_date":
        web = replace(
            web,
            product=replace(web.product, departure_date="2026-09-02"),
        )
    elif case == "return_date":
        web = replace(
            web,
            product=replace(web.product, return_date="2026-09-06"),
        )
    elif case == "day_count":
        web = replace(web, product=replace(web.product, day_count=6))
    elif case == "flight_number":
        web = replace(
            web,
            flights=(replace(web.flights[0], number="VZ566"), *web.flights[1:]),
        )
    elif case in {"hotel", "city", "attraction_order"}:
        day = web.days[1]
        if case == "hotel":
            day = replace(day, hotel="另一合成飯店")
        elif case == "city":
            day = replace(day, city="京都")
        else:
            day = replace(day, attractions=tuple(reversed(day.attractions)))
        web = replace(web, days=(web.days[0], day, *web.days[2:]))

    draft = merge_briefing_sources(
        generated_at="2026-08-09T11:10:00+08:00",
        pdf=pdf_source(),
        web=web,
    )

    assert draft.status is DraftStatus.BLOCKED
    assert len(draft.conflicts) == 1
    conflict = draft.conflicts[0]
    assert conflict.field == expected_field
    assert conflict.source_a == PDF_SOURCE.source_id
    assert conflict.source_b == WEB_SOURCE.source_id
    assert conflict.severity == "blocking"
    assert conflict.decision == ""
    assert conflict.decided_by == ""


@pytest.mark.parametrize(
    ("case", "expected_field"),
    [
        ("product_code", "product.code"),
        ("flight_count", "flights"),
        ("day_numbers", "days"),
    ],
)
def test_merge_fails_closed_on_identity_or_sequence_shape_mismatch(
    case,
    expected_field,
):
    web = web_source()
    if case == "product_code":
        web = replace(web, product=replace(web.product, code="OSA-OTHER-260901"))
    elif case == "flight_count":
        web = replace(web, flights=web.flights[:1])
    else:
        web = replace(web, days=web.days[:-1])

    draft = merge_briefing_sources(
        generated_at="2026-08-09T11:10:00+08:00",
        pdf=pdf_source(),
        web=web,
    )

    assert draft.status is DraftStatus.BLOCKED
    assert [conflict.field for conflict in draft.conflicts] == [expected_field]


@pytest.mark.parametrize("sequence", ["flights", "days"])
def test_sequence_conflict_decision_restores_the_selected_typed_values(sequence):
    web = web_source()
    if sequence == "flights":
        web = replace(web, flights=web.flights[:1])
    else:
        web = replace(
            web,
            product=replace(
                web.product,
                day_count=4,
                return_date="2026-09-04",
            ),
            days=web.days[:-1],
        )
    draft = merge_briefing_sources(
        generated_at="2026-08-09T11:10:00+08:00",
        pdf=pdf_source(),
        web=web,
    )

    decisions = {sequence: "use_b"}
    if sequence == "days":
        decisions.update(
            {
                "product.day_count": "use_b",
                "product.return_date": "use_b",
            }
        )
    updated = apply_conflict_decisions(
        draft,
        {
            "draft_id": draft.draft_id,
            "decisions": decisions,
        },
    )

    assert getattr(updated, sequence) == getattr(web, sequence)
    assert updated.product.day_count == web.product.day_count
    assert updated.product.return_date == web.product.return_date
    assert updated.status is DraftStatus.DRAFT_READY


@pytest.mark.parametrize(
    ("case", "warning_code"),
    [
        ("punctuation", "SOURCE_EQUIVALENT_TEXT"),
        ("city_abbreviation", "SOURCE_EQUIVALENT_TEXT"),
        ("meals", "MEAL_TEXT_DIFFERENCE"),
    ],
)
def test_merge_warns_for_non_semantic_text_differences_and_keeps_pdf(
    case,
    warning_code,
):
    pdf = pdf_source()
    web = web_source()
    pdf_day = pdf.days[1]
    web_day = web.days[1]
    if case == "punctuation":
        pdf_day = replace(pdf_day, hotel="合成・大阪飯店")
        web_day = replace(web_day, hotel="合成／大阪飯店")
    elif case == "city_abbreviation":
        pdf_day = replace(pdf_day, city="大阪市")
        web_day = replace(web_day, city="大阪")
    else:
        pdf_day = replace(pdf_day, meals=("早餐", "飯店晚餐"))
        web_day = replace(web_day, meals=("早餐", "自理"))
    pdf = replace(pdf, days=(pdf.days[0], pdf_day, *pdf.days[2:]))
    web = replace(web, days=(web.days[0], web_day, *web.days[2:]))

    draft = merge_briefing_sources(
        generated_at="2026-08-09T11:10:00+08:00",
        pdf=pdf,
        web=web,
    )

    assert draft.status is DraftStatus.DRAFT_READY
    assert draft.conflicts == ()
    assert draft.days[1] == pdf_day
    assert [warning.code for warning in draft.warnings] == [warning_code]
    assert draft.warnings[0].source_ids == (
        PDF_SOURCE.source_id,
        WEB_SOURCE.source_id,
    )
