from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import NoReturn

import fitz

from ..errors import (
    BriefingSourceError,
    ParseContractChangedError,
    PdfOcrRequiredError,
)
from ..input_validation import ValidatedPdfInput
from ..models import Flight, ItineraryDay, Product, SourceEvidence


PARSER_VERSION = "pdf-itinerary/2"


@dataclass(frozen=True, slots=True)
class PdfPageText:
    page_number: int
    text: str


@dataclass(frozen=True, slots=True)
class ParsedPdfItinerary:
    sources: tuple[SourceEvidence, ...]
    product: Product
    flights: tuple[Flight, ...]
    days: tuple[ItineraryDay, ...]


def extract_pdf_pages(source: ValidatedPdfInput) -> tuple[PdfPageText, ...]:
    try:
        with fitz.open(source.path) as document:
            if document.needs_pass:
                raise BriefingSourceError("Itinerary PDF is encrypted")
            pages = tuple(
                PdfPageText(
                    page_number=index + 1,
                    text=page.get_text("text", sort=True),
                )
                for index, page in enumerate(document)
            )
    except BriefingSourceError:
        raise
    except (fitz.FileDataError, RuntimeError, ValueError) as error:
        raise BriefingSourceError("Itinerary PDF could not be decoded") from error
    if not pages or not any(page.text.strip() for page in pages):
        raise PdfOcrRequiredError()
    return pages


def parse_pdf_itinerary_pages(
    pages: tuple[PdfPageText, ...],
    *,
    source_path: str | Path,
    pdf_sha256: str,
    retrieved_at: str,
) -> ParsedPdfItinerary:
    ordered_pages = _validated_pages(pages)
    if re.fullmatch(r"[0-9a-f]{64}", pdf_sha256.casefold()) is None:
        _contract_changed("PDF SHA-256")
    source_prefix = f"pdf-{pdf_sha256.casefold()[:16]}"
    sources = tuple(
        SourceEvidence(
            source_id=f"{source_prefix}-p{page.page_number:03d}",
            kind="pdf_page",
            location=f"{source_path}#page={page.page_number}",
            sha256=pdf_sha256.casefold(),
            retrieved_at=retrieved_at,
            parser_version=PARSER_VERSION,
        )
        for page in ordered_pages
    )
    source_by_page = {
        page.page_number: source.source_id
        for page, source in zip(ordered_pages, sources, strict=True)
    }

    product_code, code_pages = _unique_labeled_value(
        ordered_pages,
        "產品代碼",
        ("產品代碼", "行程代碼", "團號"),
    )
    product_name, name_pages = _unique_labeled_value(
        ordered_pages,
        "產品名稱",
        ("產品名稱", "行程名稱"),
    )
    day_count_text, count_pages = _unique_labeled_value(
        ordered_pages,
        "行程天數",
        ("行程天數",),
    )
    departure_text, departure_pages = _unique_labeled_value(
        ordered_pages,
        "出發日期",
        ("出發日期",),
    )
    return_text, return_pages = _unique_labeled_value(
        ordered_pages,
        "回程日期",
        ("回程日期",),
    )
    day_count = _parse_day_count(day_count_text)
    departure_date = _parse_date(departure_text)
    return_date = _parse_date(return_text)
    product_page_numbers = _ordered_unique(
        (*code_pages, *name_pages, *count_pages, *departure_pages, *return_pages)
    )
    product_source_ids = tuple(
        source_by_page[number] for number in product_page_numbers
    )

    flights = _parse_flights(ordered_pages, source_by_page)
    days = _parse_days(ordered_pages, source_by_page)
    if len(days) != day_count or tuple(day.number for day in days) != tuple(
        range(1, day_count + 1)
    ):
        _contract_changed("行程天數")
    if days[0].date != departure_date or days[-1].date != return_date:
        _contract_changed("行程日期")

    return ParsedPdfItinerary(
        sources=sources,
        product=Product(
            code=_text(product_code).upper(),
            name=_text(product_name),
            region=_parse_region(product_name),
            day_count=day_count,
            departure_date=departure_date,
            return_date=return_date,
            source_ids=product_source_ids,
        ),
        flights=flights,
        days=days,
    )


def _validated_pages(pages: tuple[PdfPageText, ...]) -> tuple[PdfPageText, ...]:
    if not pages:
        _contract_changed("PDF pages")
    numbers = [page.page_number for page in pages]
    if any(number < 1 for number in numbers) or len(set(numbers)) != len(numbers):
        _contract_changed("PDF page numbers")
    if not any(page.text.strip() for page in pages):
        raise PdfOcrRequiredError()
    return tuple(sorted(pages, key=lambda page: page.page_number))


def _unique_labeled_value(
    pages: tuple[PdfPageText, ...],
    anchor: str,
    labels: tuple[str, ...],
) -> tuple[str, tuple[int, ...]]:
    label_pattern = "|".join(re.escape(label) for label in labels)
    pattern = re.compile(rf"^(?:{label_pattern})\s*[：:]\s*(.+)$")
    matches: list[tuple[str, int]] = []
    for page in pages:
        for raw_line in page.text.splitlines():
            match = pattern.fullmatch(_text(raw_line))
            if match is not None and _text(match.group(1)):
                matches.append((_text(match.group(1)), page.page_number))
    values = {value for value, _ in matches}
    if len(values) != 1:
        _contract_changed(anchor)
    value = next(iter(values))
    return value, _ordered_unique(
        page_number for matched, page_number in matches if matched == value
    )


def _parse_flights(
    pages: tuple[PdfPageText, ...],
    source_by_page: dict[int, str],
) -> tuple[Flight, ...]:
    flights: list[Flight] = []
    for page in pages:
        for raw_line in page.text.splitlines():
            line = _text(raw_line)
            if not line.startswith("航班：") and not line.startswith("航班:"):
                continue
            _, payload = re.split(r"[：:]", line, maxsplit=1)
            parts = tuple(_text(part) for part in re.split(r"[｜|]", payload))
            if len(parts) != 5 or not all(parts):
                _contract_changed("航班資料")
            outbound = re.fullmatch(r"([A-Za-z]{3})\s+(\d{1,2}:\d{2})", parts[3])
            inbound = re.fullmatch(r"([A-Za-z]{3})\s+(\d{1,2}:\d{2})", parts[4])
            if outbound is None or inbound is None:
                _contract_changed("航班機場時間")
            flights.append(
                Flight(
                    date=_parse_date(parts[0]),
                    airline=parts[1],
                    number=parts[2].replace(" ", "").upper(),
                    origin=outbound.group(1).upper(),
                    destination=inbound.group(1).upper(),
                    departure_time=_parse_time(outbound.group(2)),
                    arrival_time=_parse_time(inbound.group(2)),
                    source_ids=(source_by_page[page.page_number],),
                )
            )
    if not flights:
        _contract_changed("航班資料")
    return tuple(flights)


def _parse_days(
    pages: tuple[PdfPageText, ...],
    source_by_page: dict[int, str],
) -> tuple[ItineraryDay, ...]:
    day_header = re.compile(
        r"^第\s*(\d+)\s*天\s*[｜|]\s*([^｜|]+)\s*[｜|]\s*(.+)$"
    )
    current: dict[str, object] | None = None
    blocks: list[dict[str, object]] = []
    for page in pages:
        for raw_line in page.text.splitlines():
            line = _text(raw_line)
            if not line:
                continue
            header = day_header.fullmatch(line)
            if header is not None:
                if current is not None:
                    blocks.append(current)
                current = {
                    "number": int(header.group(1)),
                    "date": _parse_date(header.group(2)),
                    "city": _text(header.group(3)),
                    "page_numbers": [page.page_number],
                }
                continue
            if current is None:
                continue
            field_match = re.fullmatch(r"(景點|餐食|住宿)\s*[：:]\s*(.+)", line)
            if field_match is None:
                continue
            field_name = {"景點": "attractions", "餐食": "meals", "住宿": "hotel"}[
                field_match.group(1)
            ]
            if field_name in current:
                _contract_changed(f"第{current['number']}天{field_match.group(1)}")
            current[field_name] = _text(field_match.group(2))
            page_numbers = current["page_numbers"]
            if not isinstance(page_numbers, list):
                _contract_changed("PDF day page evidence")
            page_numbers.append(page.page_number)
    if current is not None:
        blocks.append(current)
    if not blocks:
        _contract_changed("每日行程資料")

    days: list[ItineraryDay] = []
    for block in blocks:
        number = int(block["number"])
        for field_name, label in (
            ("attractions", "景點"),
            ("meals", "餐食"),
            ("hotel", "住宿"),
        ):
            if field_name not in block:
                _contract_changed(f"第{number}天{label}")
        page_numbers = block["page_numbers"]
        if not isinstance(page_numbers, list):
            _contract_changed("PDF day page evidence")
        source_ids = tuple(
            source_by_page[page_number]
            for page_number in _ordered_unique(page_numbers)
        )
        attractions = _split_items(str(block["attractions"]))
        hotel = _text(str(block["hotel"]))
        if not attractions or not hotel:
            _contract_changed(f"第{number}天行程")
        days.append(
            ItineraryDay(
                number=number,
                date=str(block["date"]),
                city=str(block["city"]),
                attractions=attractions,
                meals=_split_items(str(block["meals"])),
                hotel=hotel,
                source_ids=source_ids,
            )
        )
    return tuple(days)


def _parse_date(value: str) -> str:
    match = re.fullmatch(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", _text(value))
    if match is None:
        _contract_changed("日期格式")
    year, month, day = (int(part) for part in match.groups())
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        _contract_changed("日期格式")


def _parse_time(value: str) -> str:
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", _text(value))
    if match is None:
        _contract_changed("時間格式")
    hour, minute = (int(part) for part in match.groups())
    if hour > 23 or minute > 59:
        _contract_changed("時間格式")
    return f"{hour:02d}:{minute:02d}"


def _parse_day_count(value: str) -> int:
    match = re.search(r"(\d+)\s*天", _text(value))
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
    if _text(value) in {"無", "自理", "敬請自理"}:
        return ()
    return tuple(
        item.strip()
        for item in re.split(r"[、,，;/；\n]+", value)
        if item.strip()
    )


def _ordered_unique(values: Iterable[int]) -> tuple[int, ...]:
    return tuple(dict.fromkeys(values))


def _text(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip()


def _contract_changed(anchor: str) -> NoReturn:
    raise ParseContractChangedError(anchor)
