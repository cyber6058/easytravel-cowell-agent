import json
from dataclasses import replace
from pathlib import Path

import pytest

from travel_briefing.adapters.jma import parse_vpfd51, parse_vpfw50
from travel_briefing.errors import BriefingSourceError, ParseContractChangedError
from travel_briefing.models import ItineraryDay
from travel_briefing.weather import build_weather_forecasts


FIXTURES = (
    Path(__file__).parents[2] / "fixtures" / "travel_briefing" / "jma"
)


def itinerary_day(number: int, date: str, city: str = "大阪") -> ItineraryDay:
    return ItineraryDay(
        number=number,
        date=date,
        city=city,
        attractions=("合成景點",),
        meals=(),
        hotel="合成飯店",
    )


def reports():
    return (
        parse_vpfd51(
            (FIXTURES / "vpfd51_osaka.xml").read_bytes(),
            source_url="https://www.data.jma.go.jp/synthetic-vpfd51.xml",
            retrieved_at="2026-09-01T17:05:00+09:00",
        ),
        parse_vpfw50(
            (FIXTURES / "vpfw50_osaka.xml").read_bytes(),
            source_url="https://www.data.jma.go.jp/synthetic-vpfw50.xml",
            retrieved_at="2026-09-01T11:05:00+09:00",
        ),
    )


def test_weather_builder_prefers_short_term_then_uses_weekly_forecast():
    result = build_weather_forecasts(
        (
            itinerary_day(1, "2026-09-01"),
            itinerary_day(2, "2026-09-02"),
            itinerary_day(3, "2026-09-03"),
            itinerary_day(4, "2026-09-04"),
        ),
        reports(),
    )

    assert [forecast.condition for forecast in result.forecasts] == [
        "晴れ",
        "くもり",
        "くもり時々晴れ",
        "雨",
    ]
    assert [forecast.high_c for forecast in result.forecasts] == [33, 32, 31, 29]
    assert [forecast.low_c for forecast in result.forecasts] == [25, 24, 23, 22]
    assert [forecast.precipitation_percent for forecast in result.forecasts] == [
        30,
        40,
        30,
        70,
    ]
    assert all(forecast.forecast_area == "大阪府" for forecast in result.forecasts)
    assert all(forecast.available for forecast in result.forecasts)
    assert result.forecasts[0].source_url.endswith("synthetic-vpfd51.xml")
    assert result.forecasts[-1].source_url.endswith("synthetic-vpfw50.xml")
    assert result.warnings == ()
    assert result.attribution == "資料來源：日本氣象廳（JMA）"


def test_weather_builder_keeps_safe_rows_when_city_or_forecast_is_unavailable():
    result = build_weather_forecasts(
        (
            itinerary_day(1, "2026-09-01", city=""),
            itinerary_day(2, "2026-09-08"),
            itinerary_day(3, "2026-09-09"),
        ),
        reports(),
    )

    assert [forecast.condition for forecast in result.forecasts] == [
        "尚無短期預報，請於出發前更新",
        "尚無短期預報，請於出發前更新",
        "尚無短期預報，請於出發前更新",
    ]
    assert all(not forecast.available for forecast in result.forecasts)
    assert all(forecast.source_url == "" for forecast in result.forecasts)
    assert [warning.code for warning in result.warnings] == [
        "WEATHER_CITY_MISSING",
        "JMA_FORECAST_UNAVAILABLE",
    ]


def test_weather_builder_uses_the_newer_report_of_the_same_product():
    short_term, weekly = reports()
    newer = replace(
        short_term,
        issued_at="2026-09-01T18:00:00+09:00",
        source_url="https://www.data.jma.go.jp/synthetic-vpfd51-later.xml",
        areas=tuple(
            area._replace(condition="雨")
            if area.area_code == "270000" and area.date == "2026-09-01"
            else area
            for area in short_term.areas
        ),
    )

    result = build_weather_forecasts(
        (itinerary_day(1, "2026-09-01"),),
        (short_term, weekly, newer),
    )

    assert result.forecasts[0].condition == "雨"
    assert result.forecasts[0].issued_at == "2026-09-01T18:00:00+09:00"


def test_weather_builder_rejects_conflicting_reports_at_the_same_issue_time():
    short_term, weekly = reports()
    conflicting = replace(
        short_term,
        source_url="https://www.data.jma.go.jp/synthetic-conflict.xml",
        areas=tuple(
            area._replace(condition="雨")
            if area.area_code == "270000" and area.date == "2026-09-01"
            else area
            for area in short_term.areas
        ),
    )

    with pytest.raises(ParseContractChangedError, match="approved parser"):
        build_weather_forecasts(
            (itinerary_day(1, "2026-09-01"),),
            (short_term, weekly, conflicting),
        )


def test_weather_builder_rejects_an_alias_mapped_more_than_once(tmp_path):
    aliases_path = tmp_path / "aliases.json"
    aliases_path.write_text(
        json.dumps(
            [
                {
                    "aliases": ["大阪"],
                    "forecast_area_code": "270000",
                    "temperature_station_code": "62078",
                },
                {
                    "aliases": ["大阪"],
                    "forecast_area_code": "999999",
                    "temperature_station_code": "99999",
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(BriefingSourceError, match="exactly once"):
        build_weather_forecasts(
            (itinerary_day(1, "2026-09-01"),),
            reports(),
            aliases_path=aliases_path,
        )
