from pathlib import Path

import pymupdf as fitz
import pytest

from travel_briefing.adapters.pdf_itinerary import (
    PdfPageText,
    extract_pdf_pages,
    parse_pdf_itinerary_pages,
)
from travel_briefing.errors import ParseContractChangedError, PdfOcrRequiredError
from travel_briefing.input_validation import validate_pdf_input


FIXTURE = (
    Path(__file__).parents[2]
    / "fixtures"
    / "travel_briefing"
    / "synthetic_itinerary_pages.txt"
)


def fixture_pages() -> tuple[PdfPageText, ...]:
    sections = FIXTURE.read_text(encoding="utf-8").split("=== PAGE ")[1:]
    pages: list[PdfPageText] = []
    for section in sections:
        number_text, text = section.split(" ===\n", 1)
        pages.append(PdfPageText(page_number=int(number_text), text=text.strip()))
    return tuple(pages)


def test_pdf_text_parser_preserves_page_level_source_evidence():
    parsed = parse_pdf_itinerary_pages(
        fixture_pages(),
        source_path="synthetic-itinerary.pdf",
        pdf_sha256="a" * 64,
        retrieved_at="2026-08-09T10:45:00+08:00",
    )

    assert len(parsed.sources) == 3
    assert parsed.sources[0].kind == "pdf_page"
    assert parsed.sources[0].location == "synthetic-itinerary.pdf#page=1"
    assert parsed.sources[0].parser_version == "pdf-itinerary/2"
    assert parsed.product.code == "TOH-SYN-260901"
    assert parsed.product.name == "合成東北五日"
    assert parsed.product.region == "東北"
    assert parsed.product.departure_date == "2026-09-01"
    assert parsed.product.return_date == "2026-09-05"
    assert parsed.product.source_ids == (parsed.sources[0].source_id,)
    assert [flight.number for flight in parsed.flights] == ["JX862", "JX863"]
    assert all(
        flight.source_ids == (parsed.sources[0].source_id,)
        for flight in parsed.flights
    )
    assert [day.number for day in parsed.days] == [1, 2, 3, 4, 5]
    assert parsed.days[1].source_ids == (parsed.sources[1].source_id,)
    assert parsed.days[2].source_ids == (parsed.sources[2].source_id,)
    assert parsed.days[2].attractions == ("奧入瀨", "十和田湖")
    assert parsed.days[3].meals == ("早餐", "晚餐")


def test_pdf_text_parser_keeps_region_blank_when_the_source_does_not_publish_it():
    pages = tuple(
        PdfPageText(
            page_number=page.page_number,
            text=page.text.replace("合成東北五日", "合成日本五日"),
        )
        for page in fixture_pages()
    )

    parsed = parse_pdf_itinerary_pages(
        pages,
        source_path="synthetic-itinerary.pdf",
        pdf_sha256="a" * 64,
        retrieved_at="2026-08-09T10:45:00+08:00",
    )

    assert parsed.product.name == "合成日本五日"
    assert parsed.product.region == ""


def test_pdf_text_parser_rejects_multiple_published_regions():
    pages = tuple(
        PdfPageText(
            page_number=page.page_number,
            text=page.text.replace("合成東北五日", "合成大阪北海道五日"),
        )
        for page in fixture_pages()
    )

    with pytest.raises(ParseContractChangedError) as captured:
        parse_pdf_itinerary_pages(
            pages,
            source_path="synthetic-itinerary.pdf",
            pdf_sha256="a" * 64,
            retrieved_at="2026-08-09T10:45:00+08:00",
        )

    assert captured.value.details == {"anchor": "產品區域"}


def test_pdf_text_parser_rejects_multiple_product_codes():
    pages = list(fixture_pages())
    pages[0] = PdfPageText(
        page_number=1,
        text=pages[0].text + "\n產品代碼：TOH-OTHER-260901",
    )

    with pytest.raises(ParseContractChangedError) as captured:
        parse_pdf_itinerary_pages(
            tuple(pages),
            source_path="synthetic-itinerary.pdf",
            pdf_sha256="a" * 64,
            retrieved_at="2026-08-09T10:45:00+08:00",
        )

    assert captured.value.code == "PARSE_CONTRACT_CHANGED"
    assert captured.value.details == {"anchor": "產品代碼"}


def test_pdf_text_parser_rejects_missing_day_anchors():
    pages = tuple(
        PdfPageText(
            page_number=page.page_number,
            text=page.text.replace("住宿：合成秋田飯店", "飯店資訊已改版"),
        )
        for page in fixture_pages()
    )

    with pytest.raises(ParseContractChangedError) as captured:
        parse_pdf_itinerary_pages(
            pages,
            source_path="synthetic-itinerary.pdf",
            pdf_sha256="a" * 64,
            retrieved_at="2026-08-09T10:45:00+08:00",
        )

    assert captured.value.details == {"anchor": "第4天住宿"}


def test_pdf_extractor_reads_text_without_modifying_the_source(tmp_path):
    source = tmp_path / "synthetic.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "SYNTHETIC ITINERARY")
    document.save(source)
    document.close()
    validated = validate_pdf_input(source)
    before = source.read_bytes()

    pages = extract_pdf_pages(validated)

    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert "SYNTHETIC ITINERARY" in pages[0].text
    assert source.read_bytes() == before


def test_pdf_extractor_marks_a_textless_scan_as_needing_ocr(tmp_path):
    source = tmp_path / "scan.pdf"
    document = fitz.open()
    document.new_page()
    document.save(source)
    document.close()

    with pytest.raises(PdfOcrRequiredError) as captured:
        extract_pdf_pages(validate_pdf_input(source))

    assert captured.value.code == "PDF_OCR_REQUIRED"
