from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, timedelta
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup, Tag

from ..errors import ParseContractChangedError
from ..input_validation import validate_newamazing_url
from ..models import Flight, ItineraryDay, Notice, Product, SourceEvidence


PARSER_VERSION = "newamazing-html/5"

_NOTICE_CATEGORIES = {
    "小費": "tip",
    "出團人數": "group_size",
    "團體人數": "group_size",
    "不可脫隊": "no_leaving_group",
    "參團規範": "no_leaving_group",
    "巴士行車時間": "bus_hours",
    "行程變更": "itinerary_change",
    "車上座位": "seat",
    "保險": "insurance",
    "安全": "safety",
    "個人用藥": "medication",
    "護照效期": "passport_validity",
    "簽證": "visa",
    "行動提醒": "accessibility",
    "房型": "room_type",
    "單人房差": "single_room_supplement",
    "素食": "vegetarian",
    "電壓": "voltage",
    "出團備註": "group_notes",
    "注意事項": "general_notice",
    "時差": "time_difference",
    "電話通訊": "communications",
    "簽證護照": "visa",
    "幣值": "currency",
    "天氣": "weather_notice",
}

_EXPLICIT_NOTICE_FACT_PATTERNS = {
    "group_size": re.compile(
        r"(?:出團|團體|成團)人數|\d+\s*人\s*(?:至|到|[-~～])\s*\d+\s*人"
    ),
    "no_leaving_group": re.compile(
        r"(?:不可|不得|禁止).{0,8}脫隊|脫隊.{0,8}(?:不可|不得|禁止)"
    ),
    "bus_hours": re.compile(
        r"(?:巴士|遊覽車|行車).{0,16}(?:小時|時間)"
    ),
    "insurance": re.compile(r"保險"),
    "passport_validity": re.compile(
        r"護照.{0,16}(?:效期|有效)|(?:效期|有效).{0,16}護照"
    ),
    "room_type": re.compile(r"房型|兩人一室|雙人房"),
    "vegetarian": re.compile(r"素食|素餐"),
}

_NOTICE_SENTENCES = re.compile(r"[^。！？!?；;]+(?:[。！？!?；;]+|$)")

_FLIGHT_HEADERS = {
    "date": ("日期", "航班日期"),
    "airline": ("航空公司", "航空"),
    "number": ("班號", "航班"),
    "origin": ("出發地", "起飛機場"),
    "destination": ("目的地", "抵達機場"),
    "departure_time": ("起飛時間", "出發時間"),
    "arrival_time": ("抵達時間", "到達時間"),
}

_LIVE_FLIGHT_HEADERS = {
    "airline": ("航空公司", "航空"),
    "number": ("航班", "班號"),
    "origin": ("出發地", "起飛機場"),
    "departure_datetime": ("出發時間", "起飛時間"),
    "destination": ("目的地", "抵達機場"),
    "arrival_datetime": ("抵達時間", "到達時間"),
}


@dataclass(frozen=True, slots=True)
class ParsedNewAmazingPage:
    source: SourceEvidence
    product: Product
    flights: tuple[Flight, ...]
    days: tuple[ItineraryDay, ...]
    notices: tuple[Notice, ...]


def parse_newamazing_html(
    html: str,
    *,
    source_url: str,
    retrieved_at: str,
) -> ParsedNewAmazingPage:
    if not isinstance(html, str) or not html.strip():
        _contract_changed("html")
    validated_url = validate_newamazing_url(source_url)
    digest = hashlib.sha256(html.encode("utf-8")).hexdigest()
    source_id = f"newamazing-{digest[:16]}"
    source_ids = (source_id,)
    source = SourceEvidence(
        source_id=source_id,
        kind="newamazing_html",
        location=validated_url.value,
        sha256=digest,
        retrieved_at=retrieved_at,
        parser_version=PARSER_VERSION,
    )

    soup = BeautifulSoup(html, "html.parser")
    root = soup.find("main") or soup.body or soup
    if _has_live_card_signal(root):
        product, flights, days, notices = _parse_live_card_page(
            root,
            source_url=validated_url.value,
            source_ids=source_ids,
        )
        return ParsedNewAmazingPage(
            source=source,
            product=product,
            flights=flights,
            days=days,
            notices=notices,
        )

    product_section = _required_section(root, "產品資訊")
    flight_section = _required_section(root, "航班資訊")
    itinerary_section = _required_section(root, "每日行程")
    notices_section = _required_section(root, "其他說明")

    title_node = root.find("h1")
    product_name = _text(title_node) if isinstance(title_node, Tag) else ""
    if not product_name:
        _contract_changed("產品名稱")
    product_code = _required_value(
        product_section,
        "產品代碼",
        ("產品代碼", "行程代碼", "團號"),
    ).upper()
    departure_date = _parse_date(
        _required_value(product_section, "出發日期", ("出發日期",))
    )
    return_date = _parse_date(
        _required_value(product_section, "回程日期", ("回程日期",))
    )
    day_count = _parse_day_count(
        _required_value(product_section, "行程天數", ("行程天數",))
    )
    region = _parse_region(product_name)

    flights = _parse_flights(flight_section, source_ids)
    days = _parse_days(itinerary_section, source_ids)
    if len(days) != day_count or tuple(day.number for day in days) != tuple(
        range(1, day_count + 1)
    ):
        _contract_changed("行程天數")
    if days[0].date != departure_date or days[-1].date != return_date:
        _contract_changed("行程日期")
    notices = _parse_notices(notices_section, source_ids)

    return ParsedNewAmazingPage(
        source=source,
        product=Product(
            code=product_code,
            name=product_name,
            region=region,
            day_count=day_count,
            departure_date=departure_date,
            return_date=return_date,
            source_ids=source_ids,
        ),
        flights=flights,
        days=days,
        notices=notices,
    )


def _has_live_card_signal(root: Tag) -> bool:
    return root.select_one(
        ".product_basic_info, #ReferenceFlights, #DailyItinerary"
    ) is not None


def _parse_live_card_page(
    root: Tag,
    *,
    source_url: str,
    source_ids: tuple[str, ...],
) -> tuple[
    Product,
    tuple[Flight, ...],
    tuple[ItineraryDay, ...],
    tuple[Notice, ...],
]:
    product_name = _required_live_input(root, "contGName", "產品名稱")
    title = root.find("h3")
    if not isinstance(title, Tag) or _text(title) != product_name:
        _contract_changed("產品名稱")

    product_code = _required_live_input(root, "contGCode", "產品代碼").upper()
    query_codes = parse_qs(urlsplit(source_url).query).get("prodCd", [])
    if len(query_codes) != 1 or query_codes[0].upper() != product_code:
        _contract_changed("產品代碼")

    product_info = root.select_one(".product_basic_info")
    if not isinstance(product_info, Tag):
        _contract_changed("產品資訊")
    departure_node = product_info.select_one(".departure_date")
    duration_node = product_info.select_one(".return_date")
    if not isinstance(departure_node, Tag) or not isinstance(duration_node, Tag):
        _contract_changed("產品資訊")
    departure_date = _parse_date(_text(departure_node))
    day_count = _parse_day_count(_text(duration_node))
    return_date = (
        date.fromisoformat(departure_date) + timedelta(days=day_count - 1)
    ).isoformat()

    flights = _parse_live_flights(root, source_ids)
    if flights[0].date != departure_date or flights[-1].date != return_date:
        _contract_changed("航班日期")
    days = _parse_live_days(
        root,
        departure_date=departure_date,
        day_count=day_count,
        source_ids=source_ids,
    )
    notices = _parse_live_notices(root, source_ids)
    return (
        Product(
            code=product_code,
            name=product_name,
            region=_parse_region(product_name),
            day_count=day_count,
            departure_date=departure_date,
            return_date=return_date,
            source_ids=source_ids,
        ),
        flights,
        days,
        notices,
    )


def _required_live_input(root: Tag, name: str, anchor: str) -> str:
    matches = root.select(f'input[name="{name}"]')
    if len(matches) != 1:
        _contract_changed(anchor)
    value = _text_value(str(matches[0].get("value", "")))
    if not value:
        _contract_changed(anchor)
    return value


def _parse_live_flights(
    root: Tag,
    source_ids: tuple[str, ...],
) -> tuple[Flight, ...]:
    section = root.select_one("#ReferenceFlights")
    if not isinstance(section, Tag):
        _contract_changed("航班參考")
    header = section.select_one(".flight_title")
    if not isinstance(header, Tag):
        _contract_changed("航班欄位")
    header_cells = header.find_all("li", recursive=False)
    indexes = _live_header_indexes(header_cells)

    flights: list[Flight] = []
    for row in section.select(".flight_content"):
        cells = row.find_all("li", recursive=False)
        if len(cells) != len(header_cells):
            _contract_changed("航班資料列")
        values = {name: _text(cells[index]) for name, index in indexes.items()}
        if not all(values.values()):
            _contract_changed("航班資料列")
        departure_date, departure_time = _parse_datetime(
            values["departure_datetime"]
        )
        _arrival_date, arrival_time = _parse_datetime(
            values["arrival_datetime"]
        )
        flights.append(
            Flight(
                date=departure_date,
                airline=values["airline"],
                number=values["number"].replace(" ", "").upper(),
                origin=values["origin"],
                destination=values["destination"],
                departure_time=departure_time,
                arrival_time=arrival_time,
                source_ids=source_ids,
            )
        )
    if not flights:
        _contract_changed("航班資料")
    return tuple(flights)


def _live_header_indexes(cells: list[Tag]) -> dict[str, int]:
    indexes: dict[str, int] = {}
    for index, cell in enumerate(cells):
        heading = _label_text(_text(cell))
        for canonical, aliases in _LIVE_FLIGHT_HEADERS.items():
            if heading not in {_label_text(alias) for alias in aliases}:
                continue
            if canonical in indexes:
                _contract_changed("航班欄位")
            indexes[canonical] = index
    if set(indexes) != set(_LIVE_FLIGHT_HEADERS):
        _contract_changed("航班欄位")
    return indexes


def _parse_live_days(
    root: Tag,
    *,
    departure_date: str,
    day_count: int,
    source_ids: tuple[str, ...],
) -> tuple[ItineraryDay, ...]:
    section = root.select_one("#DailyItinerary")
    if not isinstance(section, Tag):
        _contract_changed("每日行程")
    start = date.fromisoformat(departure_date)
    days: list[ItineraryDay] = []
    for card in section.select(".every_day"):
        number = _parse_live_day_number(card)
        route_node = card.select_one("h4.day_title_right")
        route = _text(route_node) if isinstance(route_node, Tag) else ""
        if not route:
            _contract_changed(f"第{number}天行程")
        hotel_node = card.select_one(".day_hotel p")
        hotel = (
            _first_live_hotel(_text(hotel_node))
            if isinstance(hotel_node, Tag)
            else ""
        )
        if not hotel:
            _contract_changed(f"第{number}天住宿")
        days.append(
            ItineraryDay(
                number=number,
                date=(start + timedelta(days=number - 1)).isoformat(),
                city="",
                attractions=(route,),
                meals=_parse_live_meals(card, number),
                hotel=hotel,
                source_ids=source_ids,
            )
        )
    expected = tuple(range(1, day_count + 1))
    if tuple(day.number for day in days) != expected:
        _contract_changed("行程天數")
    return tuple(days)


def _parse_live_day_number(card: Tag) -> int:
    en_day = card.select_one(".en_day")
    tw_day = card.select_one(".tw_day")
    en_match = re.fullmatch(r"D\s*(\d+)", _text(en_day), re.IGNORECASE)
    tw_match = re.fullmatch(r"第\s*(\d+)\s*天", _text(tw_day))
    if en_match is None or tw_match is None or en_match.group(1) != tw_match.group(1):
        _contract_changed("每日行程天次")
    return int(en_match.group(1))


def _parse_live_meals(card: Tag, number: int) -> tuple[str, ...]:
    meal_list = card.select_one(".day_meal dl")
    if not isinstance(meal_list, Tag):
        _contract_changed(f"第{number}天餐食")
    expected_labels = ("早餐", "午餐", "晚餐")
    values: dict[str, str] = {}
    for term in meal_list.find_all("dt", recursive=False):
        label = _label_text(_text(term))
        if label not in expected_labels or label in values:
            _contract_changed(f"第{number}天餐食")
        detail = term.find_next_sibling("dd")
        if not isinstance(detail, Tag):
            _contract_changed(f"第{number}天餐食")
        values[label] = _text(detail)
    if tuple(values) != expected_labels:
        _contract_changed(f"第{number}天餐食")
    return tuple(values[label] for label in expected_labels)


def _first_live_hotel(value: str) -> str:
    """Return the supplier's first listed hotel, preserving its source spelling."""
    return re.split(r"\s+或\s+", value, maxsplit=1)[0].strip()


def _parse_live_notices(
    root: Tag,
    source_ids: tuple[str, ...],
) -> tuple[Notice, ...]:
    heading = next(
        (
            node
            for node in root.find_all(re.compile(r"^h[1-6]$"))
            if _text(node) == "其他說明"
        ),
        None,
    )
    if not isinstance(heading, Tag) or not isinstance(heading.parent, Tag):
        _contract_changed("其他說明")
    list_root = heading.find_next_sibling("ul") or heading.parent.find("ul")
    if not isinstance(list_root, Tag):
        _contract_changed("其他說明內容")
    notices: list[Notice] = []
    for item in list_root.find_all("li", recursive=False):
        item_heading = item.find(re.compile(r"^h[1-6]$"))
        label = _text(item_heading)
        content = " ".join(
            _text(node) for node in item.find_all("p", recursive=False) if _text(node)
        )
        if not label or not content:
            _contract_changed("其他說明內容")
        category = _NOTICE_CATEGORIES.get(label, "other")
        notices.append(
            Notice(category=category, text=content, source_ids=source_ids)
        )
        notices.extend(
            _extract_explicit_notice_facts(
                content,
                source_ids=source_ids,
                excluded_category=category,
            )
        )
    if not notices:
        _contract_changed("其他說明內容")
    return tuple(notices)


def _extract_explicit_notice_facts(
    text: str,
    *,
    source_ids: tuple[str, ...],
    excluded_category: str,
) -> tuple[Notice, ...]:
    matched: dict[str, list[str]] = {}
    for sentence_match in _NOTICE_SENTENCES.finditer(text):
        sentence = sentence_match.group(0).strip()
        if not sentence:
            continue
        for category, pattern in _EXPLICIT_NOTICE_FACT_PATTERNS.items():
            if category == excluded_category or pattern.search(sentence) is None:
                continue
            matched.setdefault(category, []).append(sentence)
    return tuple(
        Notice(
            category=category,
            text=" ".join(sentences),
            source_ids=source_ids,
        )
        for category, sentences in matched.items()
    )


def _parse_datetime(value: str) -> tuple[str, str]:
    normalized = unicodedata.normalize("NFKC", value).strip()
    match = re.fullmatch(
        r"(\d{4}[./-]\d{1,2}[./-]\d{1,2})\s+(\d{1,2}:\d{2})",
        normalized,
    )
    if match is None:
        _contract_changed("日期時間格式")
    return _parse_date(match.group(1)), _parse_time(match.group(2))


def _strip_brackets(value: str) -> str:
    return value.strip().removeprefix("【").removesuffix("】").strip()


def _required_section(root: Tag, title: str) -> Tag:
    for heading in root.find_all(re.compile(r"^h[1-6]$")):
        if _text(heading) == title:
            section = heading.find_parent("section")
            if isinstance(section, Tag):
                return section
            if isinstance(heading.parent, Tag):
                return heading.parent
    _contract_changed(title)


def _required_value(root: Tag, anchor: str, labels: tuple[str, ...]) -> str:
    normalized_labels = {_label_text(label) for label in labels}
    for node in root.find_all(("dt", "th", "td", "label", "strong", "span")):
        if _label_text(_text(node)) not in normalized_labels:
            continue
        value_node: Tag | None = None
        if node.name == "dt":
            sibling = node.find_next_sibling("dd")
            value_node = sibling if isinstance(sibling, Tag) else None
        elif node.name in {"th", "td"}:
            sibling = node.find_next_sibling(("td", "th"))
            value_node = sibling if isinstance(sibling, Tag) else None
        else:
            sibling = node.find_next_sibling()
            value_node = sibling if isinstance(sibling, Tag) else None
        value = _text(value_node) if value_node is not None else ""
        if value:
            return value
    _contract_changed(anchor)


def _parse_flights(
    section: Tag,
    source_ids: tuple[str, ...],
) -> tuple[Flight, ...]:
    table = section.find("table")
    if not isinstance(table, Tag):
        _contract_changed("航班表格")
    rows = table.find_all("tr")
    if len(rows) < 2:
        _contract_changed("航班資料")
    header_cells = rows[0].find_all(("th", "td"))
    header_indexes: dict[str, int] = {}
    for index, cell in enumerate(header_cells):
        heading = _label_text(_text(cell))
        for canonical, aliases in _FLIGHT_HEADERS.items():
            if heading in {_label_text(alias) for alias in aliases}:
                if canonical in header_indexes:
                    _contract_changed("航班欄位")
                header_indexes[canonical] = index
    if set(header_indexes) != set(_FLIGHT_HEADERS):
        _contract_changed("航班欄位")

    flights: list[Flight] = []
    for row in rows[1:]:
        cells = row.find_all("td")
        if not cells:
            continue
        if len(cells) != len(header_cells):
            _contract_changed("航班資料列")
        values = {
            name: _text(cells[index]) for name, index in header_indexes.items()
        }
        if not all(values.values()):
            _contract_changed("航班資料列")
        flights.append(
            Flight(
                date=_parse_date(values["date"]),
                airline=values["airline"],
                number=values["number"].replace(" ", "").upper(),
                origin=values["origin"].upper(),
                destination=values["destination"].upper(),
                departure_time=_parse_time(values["departure_time"]),
                arrival_time=_parse_time(values["arrival_time"]),
                source_ids=source_ids,
            )
        )
    if not flights:
        _contract_changed("航班資料")
    return tuple(flights)


def _parse_days(
    section: Tag,
    source_ids: tuple[str, ...],
) -> tuple[ItineraryDay, ...]:
    days: list[ItineraryDay] = []
    for article in section.find_all("article"):
        heading = article.find(re.compile(r"^h[1-6]$"))
        match = re.fullmatch(r"第\s*(\d+)\s*天", _text(heading))
        if match is None:
            continue
        number = int(match.group(1))
        attractions = _split_items(
            _required_value(article, f"第{number}天景點", ("景點",))
        )
        hotel = _required_value(article, f"第{number}天住宿", ("住宿", "飯店"))
        if not attractions or not hotel:
            _contract_changed(f"第{number}天行程")
        days.append(
            ItineraryDay(
                number=number,
                date=_parse_date(
                    _required_value(article, f"第{number}天日期", ("日期",))
                ),
                city=_required_value(article, f"第{number}天城市", ("城市",)),
                attractions=attractions,
                meals=_split_items(
                    _required_value(article, f"第{number}天餐食", ("餐食",))
                ),
                hotel=hotel,
                source_ids=source_ids,
            )
        )
    if not days:
        _contract_changed("每日行程資料")
    return tuple(days)


def _parse_notices(
    section: Tag,
    source_ids: tuple[str, ...],
) -> tuple[Notice, ...]:
    notices: list[Notice] = []
    for article in section.find_all("article"):
        heading = article.find(re.compile(r"^h[1-6]$"))
        label = _text(heading)
        if not label:
            continue
        category = _NOTICE_CATEGORIES.get(label, "other")
        content_nodes = article.find_all(("p", "li"))
        text = " ".join(_text(node) for node in content_nodes if _text(node))
        if not text:
            _contract_changed(f"其他說明:{label}")
        notices.append(
            Notice(category=category, text=text, source_ids=source_ids)
        )
    if not notices:
        _contract_changed("其他說明內容")
    return tuple(notices)


def _parse_date(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    match = re.fullmatch(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", normalized)
    if match is None:
        _contract_changed("日期格式")
    year, month, day = (int(part) for part in match.groups())
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        _contract_changed("日期格式")


def _parse_time(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", normalized)
    if match is None:
        _contract_changed("時間格式")
    hour, minute = (int(part) for part in match.groups())
    if hour > 23 or minute > 59:
        _contract_changed("時間格式")
    return f"{hour:02d}:{minute:02d}"


def _parse_day_count(value: str) -> int:
    match = re.search(r"(\d+)\s*天", unicodedata.normalize("NFKC", value))
    if match is None:
        _contract_changed("行程天數")
    count = int(match.group(1))
    if count not in (5, 6, 7):
        _contract_changed("行程天數")
    return count


def _parse_region(product_name: str) -> str:
    regions = tuple(region for region in ("大阪", "東北", "北海道") if region in product_name)
    if len(regions) > 1:
        _contract_changed("產品區域")
    return regions[0] if regions else ""


def _split_items(value: str) -> tuple[str, ...]:
    if _label_text(value) in {"無", "自理", "敬請自理"}:
        return ()
    return tuple(
        item.strip()
        for item in re.split(r"[、,，;/；\n]+", value)
        if item.strip()
    )


def _label_text(value: str) -> str:
    return _text_value(value).rstrip(":：")


def _text(node: Tag | None) -> str:
    return _text_value(node.get_text(" ", strip=True)) if node is not None else ""


def _text_value(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip()


def _contract_changed(anchor: str):
    raise ParseContractChangedError(anchor)
