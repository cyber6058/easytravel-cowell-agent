from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from importlib import resources
from pathlib import Path
from typing import Any

from .adapters.jma import JmaAreaForecast, JmaForecastReport
from .errors import BriefingSourceError, ParseContractChangedError
from .models import DraftWarning, ItineraryDay, WeatherForecast


UNAVAILABLE_TEXT = "尚無短期預報，請於出發前更新"
JMA_ATTRIBUTION = "資料來源：日本氣象廳（JMA）"


@dataclass(frozen=True, slots=True)
class WeatherBuildResult:
    forecasts: tuple[WeatherForecast, ...]
    warnings: tuple[DraftWarning, ...]
    attribution: str = JMA_ATTRIBUTION


@dataclass(frozen=True, slots=True)
class _AreaAlias:
    forecast_area_code: str
    temperature_station_code: str


def build_weather_forecasts(
    days: tuple[ItineraryDay, ...],
    reports: tuple[JmaForecastReport, ...],
    *,
    aliases_path: str | Path | None = None,
) -> WeatherBuildResult:
    aliases = _load_aliases(aliases_path)
    forecasts: list[WeatherForecast] = []
    warning_codes: dict[str, DraftWarning] = {}
    for day in days:
        alias = aliases.get(_alias_key(day.city)) if day.city.strip() else None
        if alias is None:
            code = (
                "WEATHER_CITY_MISSING"
                if not day.city.strip()
                else "WEATHER_AREA_UNMAPPED"
            )
            warning_codes.setdefault(
                code,
                DraftWarning(
                    code=code,
                    message=(
                        "每日住宿城市缺漏，未查詢 JMA。"
                        if code == "WEATHER_CITY_MISSING"
                        else "住宿城市沒有唯一 JMA 預報區映射。"
                    ),
                ),
            )
            forecasts.append(_unavailable(day))
            continue
        selected = _select_report(day.date, alias.forecast_area_code, reports)
        if selected is None:
            warning_codes.setdefault(
                "JMA_FORECAST_UNAVAILABLE",
                DraftWarning(
                    code="JMA_FORECAST_UNAVAILABLE",
                    message="JMA 暫無可用短期預報，請於出發前更新。",
                ),
            )
            forecasts.append(_unavailable(day))
            continue
        report, area = selected
        station = _find_area(
            report,
            alias.temperature_station_code,
            day.date,
        )
        forecasts.append(
            WeatherForecast(
                date=day.date,
                display_city=day.city,
                forecast_area=area.area_name,
                condition=area.condition,
                high_c=None if station is None else station.high_c,
                low_c=None if station is None else station.low_c,
                precipitation_percent=area.precipitation_percent,
                issued_at=report.issued_at,
                retrieved_at=report.retrieved_at,
                source_url=report.source_url,
                available=True,
            )
        )
    return WeatherBuildResult(
        forecasts=tuple(forecasts),
        warnings=tuple(warning_codes.values()),
    )


def _select_report(
    forecast_date: str,
    area_code: str,
    reports: tuple[JmaForecastReport, ...],
) -> tuple[JmaForecastReport, JmaAreaForecast] | None:
    for product_code in ("VPFD51", "VPFW50"):
        candidates = [
            (report, area)
            for report in reports
            if report.product_code == product_code
            if (area := _find_area(report, area_code, forecast_date)) is not None
            and area.condition
        ]
        if not candidates:
            continue
        latest_time = max(
            datetime.fromisoformat(report.issued_at)
            for report, _ in candidates
        )
        latest = [
            candidate
            for candidate in candidates
            if datetime.fromisoformat(candidate[0].issued_at) == latest_time
        ]
        fingerprints = {
            (
                area.condition,
                area.precipitation_percent,
                _station_values(report, forecast_date),
            )
            for report, area in latest
        }
        if len(fingerprints) != 1:
            raise ParseContractChangedError("JMA conflicting reports")
        return sorted(latest, key=lambda item: item[0].source_url)[0]
    return None


def _station_values(
    report: JmaForecastReport,
    forecast_date: str,
) -> tuple[tuple[str, int | None, int | None], ...]:
    return tuple(
        (area.area_code, area.high_c, area.low_c)
        for area in report.areas
        if area.date == forecast_date
        and (area.high_c is not None or area.low_c is not None)
    )


def _find_area(
    report: JmaForecastReport,
    area_code: str,
    forecast_date: str,
) -> JmaAreaForecast | None:
    matches = tuple(
        area
        for area in report.areas
        if area.area_code == area_code and area.date == forecast_date
    )
    if len(matches) > 1:
        raise ParseContractChangedError("JMA duplicate forecast area")
    return matches[0] if matches else None


def _unavailable(day: ItineraryDay) -> WeatherForecast:
    return WeatherForecast(
        date=day.date,
        display_city=day.city,
        forecast_area="",
        condition=UNAVAILABLE_TEXT,
        high_c=None,
        low_c=None,
        precipitation_percent=None,
        issued_at="",
        retrieved_at="",
        source_url="",
        available=False,
    )


def _load_aliases(
    aliases_path: str | Path | None,
) -> dict[str, _AreaAlias]:
    try:
        if aliases_path is None:
            text = (
                resources.files("travel_briefing")
                .joinpath("data/jma_area_aliases.json")
                .read_text(encoding="utf-8")
            )
        else:
            text = Path(aliases_path).read_text(encoding="utf-8")
        payload = json.loads(text)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise BriefingSourceError("JMA area alias configuration is invalid") from error
    if not isinstance(payload, list):
        raise BriefingSourceError("JMA area alias configuration is invalid")

    result: dict[str, _AreaAlias] = {}
    for raw_record in payload:
        record = _validated_alias_record(raw_record)
        for alias in raw_record["aliases"]:
            key = _alias_key(alias)
            if not key or key in result:
                raise BriefingSourceError(
                    "JMA area aliases must map each city exactly once"
                )
            result[key] = record
    return result


def _validated_alias_record(raw_record: Any) -> _AreaAlias:
    if not isinstance(raw_record, dict):
        raise BriefingSourceError("JMA area alias configuration is invalid")
    aliases = raw_record.get("aliases")
    area_code = raw_record.get("forecast_area_code")
    station_code = raw_record.get("temperature_station_code")
    if (
        not isinstance(aliases, list)
        or not aliases
        or not all(isinstance(alias, str) for alias in aliases)
        or not isinstance(area_code, str)
        or not area_code.isdigit()
        or not isinstance(station_code, str)
        or not station_code.isdigit()
    ):
        raise BriefingSourceError("JMA area alias configuration is invalid")
    return _AreaAlias(area_code, station_code)


def _alias_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return "".join(normalized.split())
