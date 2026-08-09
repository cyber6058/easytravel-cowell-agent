from pathlib import Path

import pytest

from travel_briefing.errors import BriefingInputError
from travel_briefing.input_validation import (
    validate_newamazing_redirect,
    validate_newamazing_url,
    validate_pdf_input,
)


def test_newamazing_url_accepts_only_the_canonical_https_host():
    validated = validate_newamazing_url(
        "  https://WWW.NEWAMAZING.COM.TW/GroupDetail.asp?GroupNo=SYN001  "
    )

    assert validated.value == (
        "https://www.newamazing.com.tw/GroupDetail.asp?GroupNo=SYN001"
    )
    assert validated.host == "www.newamazing.com.tw"


@pytest.mark.parametrize(
    "url",
    [
        "http://www.newamazing.com.tw/GroupDetail.asp?GroupNo=SYN001",
        "https://newamazing.com.tw/GroupDetail.asp?GroupNo=SYN001",
        "https://www.newamazing.com.tw.evil.example/GroupDetail.asp",
        "https://127.0.0.1/GroupDetail.asp",
        "https://user@www.newamazing.com.tw/GroupDetail.asp",
        "https://www.newamazing.com.tw:444/GroupDetail.asp",
        "//www.newamazing.com.tw/GroupDetail.asp",
        "",
    ],
)
def test_newamazing_url_rejects_non_allowlisted_or_ambiguous_targets(url):
    with pytest.raises(BriefingInputError):
        validate_newamazing_url(url)


def test_newamazing_redirect_must_remain_on_the_same_allowlisted_host():
    original = validate_newamazing_url(
        "https://www.newamazing.com.tw/GroupDetail.asp?GroupNo=SYN001"
    )

    redirected = validate_newamazing_redirect(
        original,
        "/print/GroupDetail.asp?GroupNo=SYN001",
    )
    assert redirected.host == original.host
    assert redirected.value == (
        "https://www.newamazing.com.tw/print/GroupDetail.asp?GroupNo=SYN001"
    )

    with pytest.raises(BriefingInputError):
        validate_newamazing_redirect(
            original,
            "https://example.invalid/print/GroupDetail.asp?GroupNo=SYN001",
        )


def test_pdf_input_is_read_only_and_records_a_stable_sha256(tmp_path):
    source = tmp_path / "synthetic-itinerary.PDF"
    source.write_bytes(b"%PDF-1.7\n% synthetic input only\n")
    before = source.stat()

    validated = validate_pdf_input(source)

    assert validated.path == source.resolve()
    assert validated.size_bytes == 32
    assert validated.sha256 == (
        "db5c2b5871fbd45353b9c81dc698450d88d3d025f083a7a03473bc508fe7a45a"
    )
    assert source.stat().st_mtime_ns == before.st_mtime_ns
    assert source.read_bytes() == b"%PDF-1.7\n% synthetic input only\n"


@pytest.mark.parametrize("name", ["missing.pdf", "source.txt"])
def test_pdf_input_rejects_missing_or_non_pdf_paths(tmp_path, name):
    source = tmp_path / name
    if source.suffix.casefold() != ".pdf":
        source.write_text("not a PDF", encoding="utf-8")

    with pytest.raises(BriefingInputError):
        validate_pdf_input(source)


def test_pdf_input_rejects_empty_or_invalid_pdf_signatures(tmp_path):
    empty = tmp_path / "empty.pdf"
    empty.write_bytes(b"")
    invalid = tmp_path / "invalid.pdf"
    invalid.write_bytes(b"not-pdf")

    with pytest.raises(BriefingInputError):
        validate_pdf_input(empty)
    with pytest.raises(BriefingInputError):
        validate_pdf_input(invalid)
