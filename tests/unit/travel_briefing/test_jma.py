from pathlib import Path

import pytest

from travel_briefing.adapters.jma import parse_vpfd51, parse_vpfw50
from travel_briefing.errors import ParseContractChangedError


FIXTURES = (
    Path(__file__).parents[2] / "fixtures" / "travel_briefing" / "jma"
)


def test_vpfd51_parser_preserves_daily_area_values_and_provenance():
    report = parse_vpfd51(
        (FIXTURES / "vpfd51_osaka.xml").read_bytes(),
        source_url="https://www.data.jma.go.jp/synthetic-vpfd51.xml",
        retrieved_at="2026-09-01T17:05:00+09:00",
    )

    assert report.product_code == "VPFD51"
    assert report.issued_at == "2026-09-01T17:00:00+09:00"
    assert report.retrieved_at == "2026-09-01T17:05:00+09:00"
    assert report.source_url.endswith("synthetic-vpfd51.xml")
    assert report.areas == (
        (
            "270000",
            "大阪府",
            "2026-09-01",
            "晴れ",
            None,
            None,
            30,
        ),
        (
            "270000",
            "大阪府",
            "2026-09-02",
            "くもり",
            None,
            None,
            40,
        ),
        (
            "62078",
            "大阪",
            "2026-09-01",
            "",
            33,
            25,
            None,
        ),
        (
            "62078",
            "大阪",
            "2026-09-02",
            "",
            32,
            24,
            None,
        ),
    )


def test_vpfw50_parser_preserves_weekly_values_and_product_identity():
    report = parse_vpfw50(
        (FIXTURES / "vpfw50_osaka.xml").read_bytes(),
        source_url="https://www.data.jma.go.jp/synthetic-vpfw50.xml",
        retrieved_at="2026-09-01T11:05:00+09:00",
    )

    assert report.product_code == "VPFW50"
    assert report.issued_at == "2026-09-01T11:00:00+09:00"
    assert report.areas[0] == (
        "270000",
        "大阪府",
        "2026-09-03",
        "くもり時々晴れ",
        None,
        None,
        30,
    )
    assert report.areas[-1] == (
        "62078",
        "大阪",
        "2026-09-04",
        "",
        29,
        22,
        None,
    )


def test_parser_converts_forecast_times_to_japan_calendar_dates():
    xml_bytes = (FIXTURES / "vpfd51_osaka.xml").read_bytes().replace(
        b"2026-09-01T00:00:00+09:00",
        b"2026-08-31T15:00:00Z",
    )

    report = parse_vpfd51(
        xml_bytes,
        source_url="https://www.data.jma.go.jp/synthetic-vpfd51.xml",
        retrieved_at="2026-09-01T17:05:00+09:00",
    )

    assert report.areas[0].date == "2026-09-01"


def test_parser_rejects_a_value_with_an_unknown_time_reference():
    xml_bytes = (FIXTURES / "vpfd51_osaka.xml").read_bytes().replace(
        b'<jmx_eb:Weather refID="1"',
        b'<jmx_eb:Weather refID="99"',
        1,
    )

    with pytest.raises(ParseContractChangedError, match="approved parser"):
        parse_vpfd51(
            xml_bytes,
            source_url="https://www.data.jma.go.jp/synthetic-vpfd51.xml",
            retrieved_at="2026-09-01T17:05:00+09:00",
        )


def test_parser_uses_the_canonical_weather_value_not_other_text_variants():
    canonical = '<jmx_eb:Weather refID="1" type="天気">晴れ</jmx_eb:Weather>'
    other_variant = (
        '<jmx_eb:Weather refID="1" type="天気予報文">'
        "晴れ、夕方からくもり</jmx_eb:Weather>"
    )
    xml_bytes = (
        (FIXTURES / "vpfd51_osaka.xml")
        .read_text(encoding="utf-8")
        .replace(canonical, canonical + other_variant, 1)
        .encode("utf-8")
    )

    report = parse_vpfd51(
        xml_bytes,
        source_url="https://www.data.jma.go.jp/synthetic-vpfd51.xml",
        retrieved_at="2026-09-01T17:05:00+09:00",
    )

    assert report.areas[0].condition == "晴れ"


def test_parser_rejects_xml_for_the_other_product():
    with pytest.raises(ParseContractChangedError, match="approved parser"):
        parse_vpfd51(
            (FIXTURES / "vpfw50_osaka.xml").read_bytes(),
            source_url="https://www.data.jma.go.jp/synthetic-vpfw50.xml",
            retrieved_at="2026-09-01T11:05:00+09:00",
        )


def test_parser_rejects_non_jma_source_provenance():
    with pytest.raises(ParseContractChangedError, match="approved parser"):
        parse_vpfd51(
            (FIXTURES / "vpfd51_osaka.xml").read_bytes(),
            source_url="https://example.com/not-jma.xml",
            retrieved_at="2026-09-01T17:05:00+09:00",
        )
