from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass

from .models import BriefingDraft


SOURCE_RULE = (
    "Only rewrite the supplied narration input; do not fetch, infer, or add facts."
)

SECTION_ORDER = (
    "product_date",
    "tips_and_group_rules",
    "transport",
    "insurance_and_safety",
    "passport_and_accessibility",
    "diet_and_rooms",
    "voltage_and_weather",
    "closing",
)

_SECTION_TITLES = {
    "product_date": "產品名稱與出發日期",
    "tips_and_group_rules": "小費與團體規範",
    "transport": "行程變動、座位與交通提醒",
    "insurance_and_safety": "保險、安全與個人用藥",
    "passport_and_accessibility": "護照、簽證與行動提醒",
    "diet_and_rooms": "素食、房型與單人房差",
    "voltage_and_weather": "電壓與天氣",
    "closing": "最終提醒",
}

CORE_REQUIRED_FACT_CATEGORIES = (
    "tip",
    "group_size",
    "no_leaving_group",
    "bus_hours",
    "insurance",
    "passport_validity",
    "room_type",
    "vegetarian",
    "voltage",
    "weather_reminder",
)

_NOTICE_SECTIONS = {
    "tip": "tips_and_group_rules",
    "group_size": "tips_and_group_rules",
    "no_leaving_group": "tips_and_group_rules",
    "bus_hours": "transport",
    "itinerary_change": "transport",
    "seat": "transport",
    "insurance": "insurance_and_safety",
    "safety": "insurance_and_safety",
    "medication": "insurance_and_safety",
    "passport_validity": "passport_and_accessibility",
    "visa": "passport_and_accessibility",
    "accessibility": "passport_and_accessibility",
    "room_type": "diet_and_rooms",
    "single_room_supplement": "diet_and_rooms",
    "vegetarian": "diet_and_rooms",
    "voltage": "voltage_and_weather",
    "group_notes": "tips_and_group_rules",
    "general_notice": "closing",
    "time_difference": "closing",
    "communications": "closing",
    "currency": "tips_and_group_rules",
    "weather_notice": "voltage_and_weather",
}

# Container notices preserve the source page's complete evidence in the manifest,
# but their concrete child notices carry the narration facts. Narrating both
# duplicates the same clauses and can more than double the audio duration.
_NON_NARRATED_CONTAINER_CATEGORIES = frozenset({"group_notes"})

_FACT_LABELS = {
    "tip": "小費",
    "group_size": "出團人數",
    "no_leaving_group": "不可脫隊",
    "bus_hours": "巴士行車時間",
    "itinerary_change": "行程變更",
    "seat": "車上座位",
    "insurance": "保險",
    "safety": "安全",
    "medication": "個人用藥",
    "passport_validity": "護照效期",
    "visa": "簽證",
    "accessibility": "行動與高齡提醒",
    "room_type": "房型",
    "single_room_supplement": "單人房差",
    "vegetarian": "素食",
    "voltage": "電壓",
    "group_notes": "出團備註",
    "general_notice": "注意事項",
    "time_difference": "時差",
    "communications": "電話通訊",
    "currency": "幣值",
    "weather_notice": "一般天氣提醒",
}

_WEATHER_REMINDER = (
    "天氣只供一般行前參考，出發前仍須確認最新預報與現場指示。"
)
_CLOSING_REMINDER = "所有內容以最終說明會資料與現場領隊指示為準。"

_KNOWN_JAPANESE_PLACES = frozenset(
    {
        # 大阪／關西
        "大阪",
        "大阪城",
        "京都",
        "清水寺",
        "奈良",
        "奈良公園",
        "神戶",
        "關西",
        "關西機場",
        "宇治",
        "嵐山",
        "琵琶湖",
        "姬路",
        "姬路城",
        "淡路島",
        "道頓堀",
        "心齋橋",
        "梅田",
        "和歌山",
        "高野山",
        # 東北
        "東北",
        "仙台",
        "青森",
        "秋田",
        "盛岡",
        "山形",
        "福島",
        "松島",
        "藏王",
        "奧入瀨",
        "十和田湖",
        "弘前",
        "角館",
        "田澤湖",
        "銀山溫泉",
        "平泉",
        # 北海道
        "北海道",
        "札幌",
        "小樽",
        "函館",
        "登別",
        "洞爺湖",
        "富良野",
        "美瑛",
        "旭川",
        "網走",
        "知床",
        "釧路",
        "帶廣",
        "層雲峽",
        "阿寒湖",
        "摩周湖",
    }
)

_DIGIT_SPOKEN = {
    "0": "零",
    "1": "一",
    "2": "二",
    "3": "三",
    "4": "四",
    "5": "五",
    "6": "六",
    "7": "七",
    "8": "八",
    "9": "九",
}

_CRITICAL_VALUE_PATTERNS = (
    re.compile(r"\d{4}-\d{2}-\d{2}"),
    re.compile(r"\d{4}年\d{1,2}月\d{1,2}日"),
    re.compile(r"(?<!\d)(?:[01]?\d|2[0-3]):[0-5]\d(?!\d)"),
    re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{2,3}\s*-?\s*\d{2,4}[A-Za-z]?(?![A-Za-z0-9])"),
    re.compile(r"(?:NT\$|TWD|JPY|¥|\$)\s*\d[\d,]*(?:\.\d+)?", re.IGNORECASE),
)
_NUMBER_WITH_UNIT_PATTERN = re.compile(
    r"\d[\d,]*(?:\.\d+)?\s*"
    r"(?:萬元|元|人|位|名|小時|分鐘|分|個月|年|月|日|歲|天|晚|次|"
    r"公里|公尺|公斤|件|張|間|床|餐|度|點|%|％|V|v|伏特)"
)


@dataclass(frozen=True, slots=True)
class NarrationSection:
    section_id: str
    title: str
    marker: str


@dataclass(frozen=True, slots=True)
class RequiredFact:
    fact_id: str
    category: str
    section_id: str
    label: str
    protected_text: str
    source_ids: tuple[str, ...]
    critical_values: tuple[str, ...]
    origin: str = "manifest"


@dataclass(frozen=True, slots=True)
class ReviewItem:
    code: str
    message: str
    field: str = ""


@dataclass(frozen=True, slots=True)
class PronunciationEntry:
    written: str
    spoken: str
    kind: str
    source: str


@dataclass(frozen=True, slots=True)
class NarrationInput:
    schema_version: int
    draft_id: str
    source_rule: str
    sections: tuple[NarrationSection, ...]
    required_facts: tuple[RequiredFact, ...]
    prohibited_values: tuple[str, ...]
    pronunciation_entries: tuple[PronunciationEntry, ...]
    review_items: tuple[ReviewItem, ...]

    @property
    def ready(self) -> bool:
        blocking_codes = {
            "EMPTY_REQUIRED_FACT",
            "FACT_SOURCE_MISSING",
            "FACT_SOURCE_UNKNOWN",
            "UNRESOLVED_CONFLICT",
            "BLOCKED_DRAFT",
        }
        return not any(item.code in blocking_codes for item in self.review_items)


def build_narration_input(draft: BriefingDraft) -> NarrationInput:
    sections = tuple(
        NarrationSection(
            section_id=section_id,
            title=_SECTION_TITLES[section_id],
            marker=f"<!-- section:{section_id} -->",
        )
        for section_id in SECTION_ORDER
    )
    facts: list[RequiredFact] = [
        RequiredFact(
            fact_id="product_date-001",
            category="product_date",
            section_id="product_date",
            label="產品與出發日期",
            protected_text=(
                f"本團產品為{draft.product.name}，"
                f"出發日期為{_format_date(draft.product.departure_date)}。"
            ),
            source_ids=draft.product.source_ids,
            critical_values=(_format_date(draft.product.departure_date),),
        )
    ]
    reviews: list[ReviewItem] = []
    category_counts: dict[str, int] = {}

    for notice in draft.notices:
        category = notice.category.strip().casefold()
        if category in _NON_NARRATED_CONTAINER_CATEGORIES:
            continue
        section_id = _NOTICE_SECTIONS.get(category)
        if section_id is None:
            reviews.append(
                ReviewItem(
                    code="UNKNOWN_NOTICE_CATEGORY",
                    message=(
                        "Notice category is not assigned to a narration section; "
                        "do not use it until reviewed."
                    ),
                    field=notice.category,
                )
            )
            continue
        protected_text = notice.text.strip()
        if not protected_text:
            reviews.append(
                ReviewItem(
                    code="EMPTY_REQUIRED_FACT",
                    message="A narration fact has no approved text.",
                    field=category,
                )
            )
            continue
        category_counts[category] = category_counts.get(category, 0) + 1
        facts.append(
            RequiredFact(
                fact_id=f"{category}-{category_counts[category]:03d}",
                category=category,
                section_id=section_id,
                label=_FACT_LABELS[category],
                protected_text=protected_text,
                source_ids=notice.source_ids,
                critical_values=extract_critical_values(protected_text),
            )
        )

    supplied_categories = {fact.category for fact in facts}
    for category in CORE_REQUIRED_FACT_CATEGORIES:
        if category == "weather_reminder":
            continue
        if category not in supplied_categories:
            reviews.append(
                ReviewItem(
                    code="MISSING_REQUIRED_FACT",
                    message="Required narration fact is absent; do not infer a value.",
                    field=category,
                )
            )

    known_source_ids = {source.source_id for source in draft.sources}
    for fact in facts:
        if fact.origin != "manifest":
            continue
        if not fact.source_ids:
            reviews.append(
                ReviewItem(
                    code="FACT_SOURCE_MISSING",
                    message="A variable narration fact has no source evidence.",
                    field=fact.fact_id,
                )
            )
            continue
        if any(source_id not in known_source_ids for source_id in fact.source_ids):
            reviews.append(
                ReviewItem(
                    code="FACT_SOURCE_UNKNOWN",
                    message="A narration fact refers to unknown source evidence.",
                    field=fact.fact_id,
                )
            )

    facts.append(
        RequiredFact(
            fact_id="weather_reminder-001",
            category="weather_reminder",
            section_id="voltage_and_weather",
            label="天氣提醒",
            protected_text=_WEATHER_REMINDER,
            source_ids=(),
            critical_values=(),
            origin="policy",
        )
    )
    if not any(forecast.available for forecast in draft.weather):
        reviews.append(
            ReviewItem(
                code="WEATHER_DATA_UNAVAILABLE",
                message=(
                    "No available forecast is present; keep weather unavailable "
                    "rather than guessing."
                ),
                field="weather",
            )
        )

    facts.append(
        RequiredFact(
            fact_id="closing-001",
            category="closing",
            section_id="closing",
            label="最終提醒",
            protected_text=_CLOSING_REMINDER,
            source_ids=(),
            critical_values=(),
            origin="policy",
        )
    )

    prohibited_values, safety_reviews = _collect_prohibited_values(draft)
    reviews.extend(safety_reviews)
    if draft.status.value == "BLOCKED":
        reviews.append(
            ReviewItem(
                code="BLOCKED_DRAFT",
                message=(
                    "The source manifest is blocked and cannot be narrated as final."
                ),
                field="status",
            )
        )

    pronunciation_entries, pronunciation_reviews = _build_pronunciation_policy(
        draft,
        tuple(facts),
    )
    reviews.extend(pronunciation_reviews)

    return NarrationInput(
        schema_version=1,
        draft_id=draft.draft_id,
        source_rule=SOURCE_RULE,
        sections=sections,
        required_facts=tuple(facts),
        prohibited_values=prohibited_values,
        pronunciation_entries=pronunciation_entries,
        review_items=tuple(reviews),
    )


def narration_input_to_dict(value: NarrationInput) -> dict[str, object]:
    return {
        "schema_version": value.schema_version,
        "type": "briefing_narration_input",
        "draft_id": value.draft_id,
        "ready": value.ready,
        "source_rule": value.source_rule,
        "sections": [
            {
                "section_id": section.section_id,
                "title": section.title,
                "marker": section.marker,
            }
            for section in value.sections
        ],
        "required_facts": [
            {
                "fact_id": fact.fact_id,
                "category": fact.category,
                "section_id": fact.section_id,
                "label": fact.label,
                "protected_text": fact.protected_text,
                "source_ids": list(fact.source_ids),
                "critical_values": list(fact.critical_values),
                "origin": fact.origin,
            }
            for fact in value.required_facts
        ],
        "prohibited_values": [
            {
                "sha256": hashlib.sha256(
                    _semantic_value(prohibited).encode("utf-8")
                ).hexdigest(),
                "character_count": len(_semantic_value(prohibited)),
            }
            for prohibited in value.prohibited_values
        ],
        "pronunciation_entries": [
            {
                "written": entry.written,
                "spoken": entry.spoken,
                "kind": entry.kind,
                "source": entry.source,
            }
            for entry in value.pronunciation_entries
        ],
        "review_items": [
            {
                "code": item.code,
                "message": item.message,
                "field": item.field,
            }
            for item in value.review_items
        ],
    }


def dumps_narration_input(value: NarrationInput) -> str:
    return json.dumps(
        narration_input_to_dict(value),
        ensure_ascii=False,
        indent=2,
    )


def _format_date(value: str) -> str:
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", value)
    if match is None:
        return value
    year, month, day = match.groups()
    return f"{year}年{int(month)}月{int(day)}日"


def extract_critical_values(text: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKC", text)
    candidates: list[tuple[int, int, str]] = []
    for pattern in (*_CRITICAL_VALUE_PATTERNS, _NUMBER_WITH_UNIT_PATTERN):
        candidates.extend(
            (match.start(), match.end(), match.group(0))
            for match in pattern.finditer(normalized)
        )
    candidates.sort(key=lambda item: (item[0], -(item[1] - item[0])))

    values: list[str] = []
    occupied: list[tuple[int, int]] = []
    for start, end, raw_value in candidates:
        overlaps = any(
            start < occupied_end and end > occupied_start
            for occupied_start, occupied_end in occupied
        )
        if overlaps:
            continue
        occupied.append((start, end))
        value = re.sub(r"\s+|-", "", raw_value)
        if value.endswith("v"):
            value = value[:-1] + "V"
        if value.endswith("％"):
            value = value[:-1] + "%"
        if re.fullmatch(r"[A-Za-z]{2,3}\d{2,4}[A-Za-z]?", value):
            value = value.upper()
        if value not in values:
            values.append(value)
    return tuple(values)


def _collect_prohibited_values(
    draft: BriefingDraft,
) -> tuple[tuple[str, ...], tuple[ReviewItem, ...]]:
    prohibited: list[str] = []
    reviews: list[ReviewItem] = []
    for conflict in draft.conflicts:
        decision = conflict.decision.strip().casefold().replace("-", "_")
        selected_side = _selected_conflict_side(
            decision,
            source_a=conflict.source_a,
            source_b=conflict.source_b,
            value_a=conflict.value_a,
            value_b=conflict.value_b,
        )
        if selected_side == "a":
            _append_nonempty(prohibited, conflict.value_b)
        elif selected_side == "b":
            _append_nonempty(prohibited, conflict.value_a)
        else:
            _append_nonempty(prohibited, conflict.value_a)
            _append_nonempty(prohibited, conflict.value_b)
            reviews.append(
                ReviewItem(
                    code="UNRESOLVED_CONFLICT",
                    message=(
                        "Both disputed values are prohibited until an OP decision "
                        "is recorded."
                    ),
                    field=conflict.field,
                )
            )

    for field in draft.op_fields:
        if field.confirmed:
            continue
        value = field.value.strip()
        if value and value.casefold() not in {
            "待 op 確認",
            "待op確認",
            "pending",
            "unknown",
        }:
            _append_nonempty(prohibited, value)
        reviews.append(
            ReviewItem(
                code="UNCONFIRMED_OP_FIELD",
                message="An unconfirmed OP field must not be narrated.",
                field=field.name,
            )
        )
    return tuple(prohibited), tuple(reviews)


def _selected_conflict_side(
    decision: str,
    *,
    source_a: str,
    source_b: str,
    value_a: str,
    value_b: str,
) -> str:
    if decision in {"a", "use_a", "use_source_a", source_a.casefold()}:
        return "a"
    if decision in {"b", "use_b", "use_source_b", source_b.casefold()}:
        return "b"
    if decision == value_a.strip().casefold() and value_a.strip():
        return "a"
    if decision == value_b.strip().casefold() and value_b.strip():
        return "b"
    if decision == "use_pdf":
        a_is_pdf = "pdf" in source_a.casefold()
        b_is_pdf = "pdf" in source_b.casefold()
        if a_is_pdf != b_is_pdf:
            return "a" if a_is_pdf else "b"
    if decision in {"use_url", "use_web", "use_website"}:
        a_is_web = any(token in source_a.casefold() for token in ("url", "web"))
        b_is_web = any(token in source_b.casefold() for token in ("url", "web"))
        if a_is_web != b_is_web:
            return "a" if a_is_web else "b"
    return ""


def _append_nonempty(values: list[str], value: str) -> None:
    cleaned = value.strip()
    if cleaned and cleaned not in values:
        values.append(cleaned)


def _semantic_value(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in normalized if character.isalnum())


def _build_pronunciation_policy(
    draft: BriefingDraft,
    facts: tuple[RequiredFact, ...],
) -> tuple[tuple[PronunciationEntry, ...], tuple[ReviewItem, ...]]:
    entries: list[PronunciationEntry] = []
    reviews: list[ReviewItem] = []
    seen_entries: set[tuple[str, str]] = set()
    reviewed_terms: set[str] = set()

    def add_entry(written: str, spoken: str, kind: str, source: str) -> None:
        cleaned = written.strip()
        key = (cleaned, kind)
        if not cleaned or key in seen_entries:
            return
        seen_entries.add(key)
        entries.append(
            PronunciationEntry(
                written=cleaned,
                spoken=spoken,
                kind=kind,
                source=source,
            )
        )

    dates = [draft.product.departure_date, draft.product.return_date]
    dates.extend(flight.date for flight in draft.flights)
    dates.extend(day.date for day in draft.days)
    for raw_date in dates:
        written = _format_date(raw_date)
        spoken = _spoken_date(written)
        if spoken:
            add_entry(written, spoken, "date", "manifest")

    for flight in draft.flights:
        spoken = _spoken_flight_number(flight.number)
        if spoken:
            add_entry(
                flight.number,
                spoken,
                "flight_number",
                "manifest:flights",
            )
        for airport_code in (flight.origin, flight.destination):
            code = airport_code.strip().upper()
            if re.fullmatch(r"[A-Z]{3}", code):
                add_entry(
                    code,
                    " ".join(code),
                    "airport_code",
                    "manifest:flights",
                )

    for fact in facts:
        for value in fact.critical_values:
            normalized = unicodedata.normalize("NFKC", value)
            if re.fullmatch(r"\d[\d,]*(?:\.\d+)?萬元", normalized):
                number = normalized.removesuffix("萬元")
                add_entry(
                    value,
                    f"{_spoken_number(number)}萬元",
                    "money",
                    fact.fact_id,
                )
            elif re.fullmatch(r"\d[\d,]*(?:\.\d+)?元", normalized):
                number = normalized.removesuffix("元")
                add_entry(
                    value,
                    f"{_spoken_number(number)}元",
                    "money",
                    fact.fact_id,
                )
            elif re.fullmatch(r"\d[\d,]*(?:\.\d+)?V", normalized):
                number = normalized.removesuffix("V")
                add_entry(
                    value,
                    f"{_spoken_number(number)}伏特",
                    "voltage",
                    fact.fact_id,
                )

    place_candidates: list[str] = [draft.product.region]
    for day in draft.days:
        place_candidates.append(day.city)
        place_candidates.extend(day.attractions)
        if day.hotel:
            place_candidates.append(day.hotel)
    place_candidates.extend(
        forecast.display_city for forecast in draft.weather if forecast.display_city
    )
    for candidate in place_candidates:
        term = candidate.strip()
        if not term:
            continue
        if term in _KNOWN_JAPANESE_PLACES:
            add_entry(
                term,
                term,
                "japanese_place",
                "policy:japanese-places-v1",
            )
        elif term not in reviewed_terms:
            reviewed_terms.add(term)
            reviews.append(
                ReviewItem(
                    code="UNKNOWN_PRONUNCIATION_TERM",
                    message=(
                        "A place or proper name is not in the approved pronunciation "
                        "list; leave it unchanged for review."
                    ),
                    field=term,
                )
            )

    return tuple(entries), tuple(reviews)


def _spoken_flight_number(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().upper()
    match = re.fullmatch(r"([A-Z]{2,3})(\d{2,4})([A-Z]?)", normalized)
    if match is None:
        return ""
    prefix, digits, suffix = match.groups()
    spoken = (
        " ".join(prefix)
        + " "
        + "".join(_DIGIT_SPOKEN[digit] for digit in digits)
    )
    return f"{spoken} {suffix}" if suffix else spoken


def _spoken_date(value: str) -> str:
    match = re.fullmatch(r"(\d{4})年(\d{1,2})月(\d{1,2})日", value)
    if match is None:
        return ""
    year, month, day = match.groups()
    spoken_year = "".join(_DIGIT_SPOKEN[digit] for digit in year)
    return f"{spoken_year}年{_spoken_integer(int(month))}月{_spoken_integer(int(day))}日"


def _spoken_number(value: str) -> str:
    normalized = value.replace(",", "")
    if "." not in normalized:
        return _spoken_integer(int(normalized))
    integer, fraction = normalized.split(".", 1)
    return (
        f"{_spoken_integer(int(integer))}點"
        + "".join(_DIGIT_SPOKEN[digit] for digit in fraction)
    )


def _spoken_integer(value: int) -> str:
    if value < 0:
        raise ValueError("spoken integers must be non-negative")
    if value < 10:
        return _DIGIT_SPOKEN[str(value)]
    if value < 20:
        return "十" + ("" if value == 10 else _spoken_integer(value % 10))
    if value < 100:
        return (
            _spoken_integer(value // 10)
            + "十"
            + ("" if value % 10 == 0 else _spoken_integer(value % 10))
        )
    if value < 1000:
        remainder = value % 100
        return (
            _spoken_integer(value // 100)
            + "百"
            + ("" if remainder == 0 else "零" if remainder < 10 else "")
            + ("" if remainder == 0 else _spoken_integer(remainder))
        )
    if value < 10000:
        remainder = value % 1000
        return (
            _spoken_integer(value // 1000)
            + "千"
            + ("" if remainder == 0 else "零" if remainder < 100 else "")
            + ("" if remainder == 0 else _spoken_integer(remainder))
        )
    if value < 100_000_000:
        remainder = value % 10000
        return (
            _spoken_integer(value // 10000)
            + "萬"
            + ("" if remainder == 0 else "零" if remainder < 1000 else "")
            + ("" if remainder == 0 else _spoken_integer(remainder))
        )
    remainder = value % 100_000_000
    return (
        _spoken_integer(value // 100_000_000)
        + "億"
        + ("" if remainder == 0 else "零" if remainder < 10_000_000 else "")
        + ("" if remainder == 0 else _spoken_integer(remainder))
    )
