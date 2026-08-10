from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import NamedTuple, NoReturn
from urllib.parse import urlsplit
from xml.etree import ElementTree

from ..errors import ParseContractChangedError


class JmaAreaForecast(NamedTuple):
    area_code: str
    area_name: str
    date: str
    condition: str
    high_c: int | None
    low_c: int | None
    precipitation_percent: int | None


@dataclass(frozen=True, slots=True)
class JmaForecastReport:
    product_code: str
    issued_at: str
    retrieved_at: str
    source_url: str
    areas: tuple[JmaAreaForecast, ...]


def parse_vpfd51(
    xml_bytes: bytes,
    *,
    source_url: str,
    retrieved_at: str,
) -> JmaForecastReport:
    return _parse_report(
        xml_bytes,
        product_code="VPFD51",
        expected_title="府県天気予報",
        source_url=source_url,
        retrieved_at=retrieved_at,
    )


def parse_vpfw50(
    xml_bytes: bytes,
    *,
    source_url: str,
    retrieved_at: str,
) -> JmaForecastReport:
    return _parse_report(
        xml_bytes,
        product_code="VPFW50",
        expected_title="府県週間天気予報",
        source_url=source_url,
        retrieved_at=retrieved_at,
    )


def _parse_report(
    xml_bytes: bytes,
    *,
    product_code: str,
    expected_title: str,
    source_url: str,
    retrieved_at: str,
) -> JmaForecastReport:
    parsed_url = urlsplit(source_url)
    if parsed_url.scheme != "https" or parsed_url.hostname not in {
        "www.data.jma.go.jp",
        "xml.kishou.go.jp",
    }:
        _contract_changed("JMA source URL")
    try:
        root = ElementTree.fromstring(xml_bytes)
    except (ElementTree.ParseError, ValueError) as error:
        raise ParseContractChangedError("JMA XML") from error

    if _required_text(root, "Control", "Title") != expected_title:
        _contract_changed("JMA product title")
    if _required_text(root, "Control", "Status") != "通常":
        _contract_changed("JMA report status")
    issued_at = _aware_datetime(
        _required_text(root, "Head", "ReportDateTime"),
        "JMA report time",
    )
    retrieved_at = _aware_datetime(retrieved_at, "JMA retrieval time")

    values: dict[tuple[str, str], dict[str, object]] = {}
    for series in _descendants(root, "TimeSeriesInfo"):
        time_by_id = _time_definitions(series)
        for item in _children(series, "Item"):
            location = _first_child(item, ("Area", "Station"))
            if location is None:
                _contract_changed("JMA forecast location")
            area_name = _required_child_text(location, "Name")
            area_code = _required_child_text(location, "Code")
            for prop in _descendants(item, "Property"):
                property_type = _required_child_text(prop, "Type")
                metric = _metric_for_type(property_type)
                if metric is None:
                    continue
                for element in prop.iter():
                    if not _is_metric_element(element, metric):
                        continue
                    ref_id = element.attrib.get("refID", "")
                    if not ref_id:
                        continue
                    text = (element.text or "").strip()
                    if not text:
                        continue
                    if ref_id not in time_by_id:
                        _contract_changed("JMA value time reference")
                    key = (area_code, time_by_id[ref_id])
                    record = values.setdefault(
                        key,
                        {
                            "area_name": area_name,
                            "condition": "",
                            "high_c": None,
                            "low_c": None,
                            "precipitation_percent": None,
                        },
                    )
                    if record["area_name"] != area_name:
                        _contract_changed("JMA area identity")
                    _store_metric(record, metric, text)

    if not values:
        _contract_changed("JMA forecast values")
    areas = tuple(
        JmaAreaForecast(
            area_code=area_code,
            area_name=str(record["area_name"]),
            date=forecast_date,
            condition=str(record["condition"]),
            high_c=_optional_int(record["high_c"]),
            low_c=_optional_int(record["low_c"]),
            precipitation_percent=_optional_int(
                record["precipitation_percent"]
            ),
        )
        for (area_code, forecast_date), record in values.items()
    )
    return JmaForecastReport(
        product_code=product_code,
        issued_at=issued_at,
        retrieved_at=retrieved_at,
        source_url=source_url,
        areas=areas,
    )


def _time_definitions(series: ElementTree.Element) -> dict[str, str]:
    result: dict[str, str] = {}
    for definition in _descendants(series, "TimeDefine"):
        time_id = definition.attrib.get("timeId", "").strip()
        if not time_id or time_id in result:
            _contract_changed("JMA time definitions")
        date_time = _aware_datetime(
            _required_child_text(definition, "DateTime"),
            "JMA forecast time",
        )
        japan_time = datetime.fromisoformat(date_time).astimezone(
            timezone(timedelta(hours=9))
        )
        result[time_id] = japan_time.date().isoformat()
    if not result:
        _contract_changed("JMA time definitions")
    return result


def _metric_for_type(property_type: str) -> str | None:
    if property_type == "天気":
        return "condition"
    if property_type in {"最高気温", "日中の最高気温"}:
        return "high_c"
    if property_type in {"最低気温", "朝の最低気温"}:
        return "low_c"
    if "降水確率" in property_type:
        return "precipitation_percent"
    return None


def _is_metric_element(
    element: ElementTree.Element,
    metric: str,
) -> bool:
    name = _local_name(element.tag)
    if metric == "condition":
        return name == "Weather" and element.attrib.get("type") == "天気"
    if metric == "precipitation_percent":
        return name == "ProbabilityOfPrecipitation"
    return name == "Temperature"


def _store_metric(record: dict[str, object], metric: str, text: str) -> None:
    if metric == "condition":
        current = str(record[metric])
        if current and current != text:
            _contract_changed("JMA conflicting weather")
        record[metric] = text
        return
    try:
        number = int(text)
    except ValueError:
        _contract_changed(f"JMA {metric}")
    if metric == "precipitation_percent":
        if number < 0 or number > 100:
            _contract_changed("JMA precipitation probability")
        current = record[metric]
        record[metric] = number if current is None else max(int(current), number)
        return
    if number < -100 or number > 100:
        _contract_changed("JMA temperature")
    current = record[metric]
    if current is not None and int(current) != number:
        _contract_changed("JMA conflicting temperature")
    record[metric] = number


def _aware_datetime(value: str, anchor: str) -> str:
    candidate = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        _contract_changed(anchor)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _contract_changed(anchor)
    return parsed.isoformat()


def _required_text(
    root: ElementTree.Element,
    parent_name: str,
    child_name: str,
) -> str:
    parent = next(_descendants(root, parent_name), None)
    if parent is None:
        _contract_changed(f"JMA {parent_name}")
    return _required_child_text(parent, child_name)


def _required_child_text(parent: ElementTree.Element, name: str) -> str:
    child = next(_children(parent, name), None)
    value = "" if child is None else (child.text or "").strip()
    if not value:
        _contract_changed(f"JMA {name}")
    return value


def _first_child(
    parent: ElementTree.Element,
    names: tuple[str, ...],
) -> ElementTree.Element | None:
    return next(
        (child for child in parent if _local_name(child.tag) in names),
        None,
    )


def _children(
    parent: ElementTree.Element,
    name: str,
):
    return (child for child in parent if _local_name(child.tag) == name)


def _descendants(
    parent: ElementTree.Element,
    name: str,
):
    return (
        element for element in parent.iter() if _local_name(element.tag) == name
    )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _optional_int(value: object) -> int | None:
    return None if value is None else int(value)


def _contract_changed(anchor: str) -> NoReturn:
    raise ParseContractChangedError(anchor)
