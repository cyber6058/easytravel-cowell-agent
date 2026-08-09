from pathlib import Path

import pytest

from travel_briefing.adapters.newamazing import parse_newamazing_html
from travel_briefing.errors import ParseContractChangedError


FIXTURE = (
    Path(__file__).parents[2]
    / "fixtures"
    / "travel_briefing"
    / "synthetic_newamazing_groupdetail.html"
)
SOURCE_URL = (
    "https://www.newamazing.com.tw/GroupDetail.asp?GroupNo=OSA-SYN-260901"
)


def fixture_html() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_newamazing_parser_returns_source_bound_structured_fields():
    parsed = parse_newamazing_html(
        fixture_html(),
        source_url=SOURCE_URL,
        retrieved_at="2026-08-09T10:30:00+08:00",
    )

    assert parsed.source.kind == "newamazing_html"
    assert parsed.source.location == SOURCE_URL
    assert parsed.source.parser_version == "newamazing-html/1"
    assert len(parsed.source.sha256) == 64
    assert parsed.product.code == "OSA-SYN-260901"
    assert parsed.product.name == "合成大阪五日"
    assert parsed.product.region == "大阪"
    assert parsed.product.day_count == 5
    assert parsed.product.departure_date == "2026-09-01"
    assert parsed.product.return_date == "2026-09-05"
    assert parsed.product.source_ids == (parsed.source.source_id,)

    assert [
        (flight.number, flight.origin, flight.destination)
        for flight in parsed.flights
    ] == [
        ("JX820", "TPE", "KIX"),
        ("JX821", "KIX", "TPE"),
    ]
    assert parsed.flights[0].departure_time == "08:30"
    assert parsed.flights[1].arrival_time == "15:25"
    assert [day.number for day in parsed.days] == [1, 2, 3, 4, 5]
    assert parsed.days[1].attractions == ("清水寺", "嵐山")
    assert parsed.days[3].hotel == "合成神戶飯店"
    assert {notice.category for notice in parsed.notices} == {
        "tip",
        "group_size",
        "no_leaving_group",
        "bus_hours",
        "insurance",
        "passport_validity",
        "room_type",
        "vegetarian",
        "voltage",
    }
    assert all(
        item.source_ids == (parsed.source.source_id,)
        for item in (*parsed.flights, *parsed.days, *parsed.notices)
    )


def test_newamazing_parser_fails_closed_when_a_required_anchor_disappears():
    changed = fixture_html().replace("<h2>其他說明</h2>", "<h2>旅遊須知新版</h2>")

    with pytest.raises(ParseContractChangedError) as captured:
        parse_newamazing_html(
            changed,
            source_url=SOURCE_URL,
            retrieved_at="2026-08-09T10:30:00+08:00",
        )

    assert captured.value.code == "PARSE_CONTRACT_CHANGED"
    assert captured.value.details == {"anchor": "其他說明"}


def test_newamazing_parser_uses_headers_instead_of_fixed_flight_columns():
    reordered = fixture_html().replace(
        "<th>航空公司</th><th>日期</th><th>起飛時間</th><th>出發地</th>\n"
        "              <th>班號</th><th>目的地</th><th>抵達時間</th>",
        "<th>班號</th><th>目的地</th><th>抵達時間</th><th>航空公司</th>\n"
        "              <th>日期</th><th>起飛時間</th><th>出發地</th>",
    ).replace(
        "<td>星宇航空</td><td>2026/09/01</td><td>08:30</td><td>TPE</td>\n"
        "              <td>JX820</td><td>KIX</td><td>12:10</td>",
        "<td>JX820</td><td>KIX</td><td>12:10</td><td>星宇航空</td>\n"
        "              <td>2026/09/01</td><td>08:30</td><td>TPE</td>",
    ).replace(
        "<td>星宇航空</td><td>2026/09/05</td><td>13:20</td><td>KIX</td>\n"
        "              <td>JX821</td><td>TPE</td><td>15:25</td>",
        "<td>JX821</td><td>TPE</td><td>15:25</td><td>星宇航空</td>\n"
        "              <td>2026/09/05</td><td>13:20</td><td>KIX</td>",
    )

    parsed = parse_newamazing_html(
        reordered,
        source_url=SOURCE_URL,
        retrieved_at="2026-08-09T10:30:00+08:00",
    )

    assert parsed.flights[0].number == "JX820"
    assert parsed.flights[0].airline == "星宇航空"
    assert parsed.flights[0].origin == "TPE"


def test_newamazing_parser_rejects_a_day_count_mismatch():
    changed = fixture_html().replace(
        "<dt>行程天數</dt><dd>5 天</dd>",
        "<dt>行程天數</dt><dd>6 天</dd>",
    )

    with pytest.raises(ParseContractChangedError) as captured:
        parse_newamazing_html(
            changed,
            source_url=SOURCE_URL,
            retrieved_at="2026-08-09T10:30:00+08:00",
        )

    assert captured.value.details == {"anchor": "行程天數"}
