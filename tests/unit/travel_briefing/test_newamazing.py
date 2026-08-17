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
LIVE_CARDS_FIXTURE = (
    Path(__file__).parents[2]
    / "fixtures"
    / "travel_briefing"
    / "synthetic_newamazing_live_cards.html"
)
SOURCE_URL = (
    "https://www.newamazing.com.tw/GroupDetail.asp?GroupNo=OSA-SYN-260901"
)


def fixture_html() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def live_cards_html() -> str:
    return LIVE_CARDS_FIXTURE.read_text(encoding="utf-8")


def test_newamazing_parser_supports_the_live_card_contract_without_guessing_city():
    source_url = (
        "https://www.newamazing.com.tw/EW/GO/GroupDetail.asp?"
        "prodCd=OSA-SYN-260901"
    )

    parsed = parse_newamazing_html(
        live_cards_html(),
        source_url=source_url,
        retrieved_at="2026-08-10T12:00:00+08:00",
    )

    assert parsed.product.code == "OSA-SYN-260901"
    assert parsed.product.name == "合成大阪五日"
    assert parsed.product.day_count == 5
    assert parsed.product.departure_date == "2026-09-01"
    assert parsed.product.return_date == "2026-09-05"
    assert [flight.number for flight in parsed.flights] == ["JX820", "JX821"]
    assert parsed.flights[0].origin == "桃園機場"
    assert parsed.flights[1].arrival_time == "15:25"
    assert [day.number for day in parsed.days] == [1, 2, 3, 4, 5]
    assert [day.date for day in parsed.days] == [
        "2026-09-01",
        "2026-09-02",
        "2026-09-03",
        "2026-09-04",
        "2026-09-05",
    ]
    assert all(day.city == "" for day in parsed.days)
    assert parsed.days[1].attractions == (
        "飯店→琵琶湖遊覽船~密西根號巡遊(航程約60分鐘)→"
        "琵琶湖Valley露台纜車(來回)~ 眺望日本最大之湖『琵琶湖』→飯店",
    )
    assert parsed.days[1].meals == ("飯店早餐", "合成午餐", "合成晚餐")
    assert parsed.days[1].hotel == "合成京都飯店"
    assert parsed.days[3].hotel == "合成神戶飯店"
    assert {notice.category for notice in parsed.notices} == {
        "tip",
        "group_size",
        "voltage",
    }


def test_live_card_parser_uses_first_flight_when_departure_node_is_absent():
    changed = live_cards_html().replace(
        '<li class="departure_date">2026/09/01</li>',
        "",
        1,
    )

    parsed = parse_newamazing_html(
        changed,
        source_url=(
            "https://www.newamazing.com.tw/EW/GO/GroupDetail.asp?"
            "prodCd=OSA-SYN-260901"
        ),
        retrieved_at="2026-08-17T12:00:00+08:00",
    )

    assert parsed.product.day_count == 5
    assert parsed.product.departure_date == "2026-09-01"
    assert parsed.product.return_date == "2026-09-05"
    assert parsed.flights[0].date == parsed.product.departure_date
    assert parsed.flights[-1].date == parsed.product.return_date


def test_live_card_parser_preserves_unknown_dates_for_time_only_flights():
    changed = (
        live_cards_html()
        .replace(
            '<li class="departure_date">2026/09/01</li>',
            "",
            1,
        )
        .replace("2026/09/01 08:30", "08:30", 1)
        .replace("2026/09/01 12:10", "12:10", 1)
        .replace("2026/09/05 13:20", "13:20", 1)
        .replace("2026/09/05 15:25", "15:25", 1)
    )

    parsed = parse_newamazing_html(
        changed,
        source_url=(
            "https://www.newamazing.com.tw/EW/GO/GroupDetail.asp?"
            "prodCd=OSA-SYN-260901"
        ),
        retrieved_at="2026-08-17T12:00:00+08:00",
    )

    assert parsed.source.parser_version == "newamazing-html/7"
    assert parsed.product.departure_date == ""
    assert parsed.product.return_date == ""
    assert [flight.date for flight in parsed.flights] == ["", ""]
    assert [flight.departure_time for flight in parsed.flights] == [
        "08:30",
        "13:20",
    ]
    assert [day.date for day in parsed.days] == ["", "", "", "", ""]


def test_live_card_parser_rejects_mixed_dated_and_time_only_flights():
    changed = live_cards_html().replace("2026/09/01 12:10", "12:10", 1)

    with pytest.raises(ParseContractChangedError) as captured:
        parse_newamazing_html(
            changed,
            source_url=(
                "https://www.newamazing.com.tw/EW/GO/GroupDetail.asp?"
                "prodCd=OSA-SYN-260901"
            ),
            retrieved_at="2026-08-17T12:00:00+08:00",
        )

    assert captured.value.code == "PARSE_CONTRACT_CHANGED"
    assert captured.value.details == {"anchor": "航班日期"}


def test_live_card_parser_keeps_explicit_product_dates_with_time_only_flights():
    changed = (
        live_cards_html()
        .replace("2026/09/01 08:30", "08:30", 1)
        .replace("2026/09/01 12:10", "12:10", 1)
        .replace("2026/09/05 13:20", "13:20", 1)
        .replace("2026/09/05 15:25", "15:25", 1)
    )

    parsed = parse_newamazing_html(
        changed,
        source_url=(
            "https://www.newamazing.com.tw/EW/GO/GroupDetail.asp?"
            "prodCd=OSA-SYN-260901"
        ),
        retrieved_at="2026-08-17T12:00:00+08:00",
    )

    assert parsed.product.departure_date == "2026-09-01"
    assert parsed.product.return_date == "2026-09-05"
    assert [flight.date for flight in parsed.flights] == ["", ""]
    assert [day.date for day in parsed.days] == [
        "2026-09-01",
        "2026-09-02",
        "2026-09-03",
        "2026-09-04",
        "2026-09-05",
    ]


def test_live_card_parser_rejects_a_non_hhmm_time_only_value():
    changed = live_cards_html().replace("2026/09/01 08:30", "8:30", 1)

    with pytest.raises(ParseContractChangedError) as captured:
        parse_newamazing_html(
            changed,
            source_url=(
                "https://www.newamazing.com.tw/EW/GO/GroupDetail.asp?"
                "prodCd=OSA-SYN-260901"
            ),
            retrieved_at="2026-08-17T12:00:00+08:00",
        )

    assert captured.value.code == "PARSE_CONTRACT_CHANGED"
    assert captured.value.details == {"anchor": "日期時間格式"}


def test_live_card_departure_fallback_rejects_a_last_flight_date_mismatch():
    changed = (
        live_cards_html()
        .replace(
            '<li class="departure_date">2026/09/01</li>',
            "",
            1,
        )
        .replace("2026/09/05 13:20", "2026/09/06 13:20", 1)
    )

    with pytest.raises(ParseContractChangedError) as captured:
        parse_newamazing_html(
            changed,
            source_url=(
                "https://www.newamazing.com.tw/EW/GO/GroupDetail.asp?"
                "prodCd=OSA-SYN-260901"
            ),
            retrieved_at="2026-08-17T12:00:00+08:00",
        )

    assert captured.value.code == "PARSE_CONTRACT_CHANGED"
    assert captured.value.details == {"anchor": "航班日期"}


def test_live_card_parser_extracts_explicit_facts_from_compound_notice():
    source_url = (
        "https://www.newamazing.com.tw/EW/GO/GroupDetail.asp?"
        "prodCd=OSA-SYN-260901"
    )
    compound = live_cards_html().replace(
        "<li><h4>出團人數</h4><p>本團共 30 人。</p></li>",
        (
            "<li><h4>出團備註</h4><p>"
            "本團出團人數為 30 人。旅客不得脫隊。"
            "巴士每日行車時間為 4 小時。本行程已投保旅遊保險。"
            "護照有效效期須有 6 個月。房型為兩人一室。"
            "素食旅客須於出發前告知。"
            "</p></li>"
        ),
    )

    parsed = parse_newamazing_html(
        compound,
        source_url=source_url,
        retrieved_at="2026-08-17T12:00:00+08:00",
    )

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
        "group_notes",
    }
    group_size = next(
        notice for notice in parsed.notices if notice.category == "group_size"
    )
    assert group_size.text == "本團出團人數為 30 人。"


def test_live_card_parser_maps_current_standard_notice_headings():
    source_url = (
        "https://www.newamazing.com.tw/EW/GO/GroupDetail.asp?"
        "prodCd=OSA-SYN-260901"
    )
    standard = live_cards_html().replace(
        "<li><h4>電壓</h4><p>日本電壓為 100V。</p></li>",
        (
            "<li><h4>電壓</h4><p>日本電壓為 100V。</p></li>"
            "<li><h4>出團備註</h4><p>合成團務提醒。</p></li>"
            "<li><h4>注意事項</h4><p>合成一般提醒。</p></li>"
            "<li><h4>時差</h4><p>合成時差提醒。</p></li>"
            "<li><h4>電話通訊</h4><p>合成通訊提醒。</p></li>"
            "<li><h4>簽證護照</h4><p>合成簽證提醒。</p></li>"
            "<li><h4>幣值</h4><p>合成幣值提醒。</p></li>"
            "<li><h4>天氣</h4><p>合成一般天氣提醒。</p></li>"
        ),
    )

    parsed = parse_newamazing_html(
        standard,
        source_url=source_url,
        retrieved_at="2026-08-17T12:00:00+08:00",
    )

    categories = {notice.category for notice in parsed.notices}
    assert {
        "group_notes",
        "general_notice",
        "time_difference",
        "communications",
        "visa",
        "currency",
        "weather_notice",
    } <= categories
    assert "other" not in categories


def test_live_card_parser_keeps_region_blank_when_the_source_does_not_publish_it():
    changed = live_cards_html().replace("合成大阪五日", "合成關西五日")

    parsed = parse_newamazing_html(
        changed,
        source_url=(
            "https://www.newamazing.com.tw/EW/GO/GroupDetail.asp?"
            "prodCd=OSA-SYN-260901"
        ),
        retrieved_at="2026-08-10T12:00:00+08:00",
    )

    assert parsed.product.name == "合成關西五日"
    assert parsed.product.region == ""


def test_live_card_parser_rejects_multiple_published_regions():
    changed = live_cards_html().replace("合成大阪五日", "合成大阪北海道五日")

    with pytest.raises(ParseContractChangedError) as captured:
        parse_newamazing_html(
            changed,
            source_url=(
                "https://www.newamazing.com.tw/EW/GO/GroupDetail.asp?"
                "prodCd=OSA-SYN-260901"
            ),
            retrieved_at="2026-08-10T12:00:00+08:00",
        )

    assert captured.value.details == {"anchor": "產品區域"}


def test_live_card_parser_fails_closed_when_product_code_field_disappears():
    changed = live_cards_html().replace(
        'name="contGCode"',
        'name="changedCode"',
        1,
    )

    with pytest.raises(ParseContractChangedError) as captured:
        parse_newamazing_html(
            changed,
            source_url=(
                "https://www.newamazing.com.tw/EW/GO/GroupDetail.asp?"
                "prodCd=OSA-SYN-260901"
            ),
            retrieved_at="2026-08-10T12:00:00+08:00",
        )

    assert captured.value.code == "PARSE_CONTRACT_CHANGED"
    assert captured.value.details == {"anchor": "產品代碼"}


def test_live_card_parser_rejects_flights_outside_the_product_dates():
    changed = live_cards_html().replace(
        "2026/09/01 08:30",
        "2026/09/02 08:30",
        1,
    )

    with pytest.raises(ParseContractChangedError) as captured:
        parse_newamazing_html(
            changed,
            source_url=(
                "https://www.newamazing.com.tw/EW/GO/GroupDetail.asp?"
                "prodCd=OSA-SYN-260901"
            ),
            retrieved_at="2026-08-10T12:00:00+08:00",
        )

    assert captured.value.code == "PARSE_CONTRACT_CHANGED"
    assert captured.value.details == {"anchor": "航班日期"}


def test_newamazing_parser_returns_source_bound_structured_fields():
    parsed = parse_newamazing_html(
        fixture_html(),
        source_url=SOURCE_URL,
        retrieved_at="2026-08-09T10:30:00+08:00",
    )

    assert parsed.source.kind == "newamazing_html"
    assert parsed.source.location == SOURCE_URL
    assert parsed.source.parser_version == "newamazing-html/7"
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
