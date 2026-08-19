import hashlib
import io
import json
import subprocess
from pathlib import Path

import pymupdf as fitz
import pytest
from PIL import Image

from travel_briefing.word_qa import (
    inspect_list_pdf,
    render_list_pdf_to_png,
    render_list_pdf_to_pngs,
    render_list_word_for_qa,
)
from travel_briefing.word_list import DayPagePlacement
from travel_briefing.errors import WordGenerationError


def write_pdf(
    path: Path,
    *,
    pages=1,
    text="OSA-SYN-260901 JX820 JX821",
    include_image=False,
) -> None:
    document = fitz.open()
    for page_number in range(pages):
        page = document.new_page(width=595.28, height=841.89)
        page.insert_text((72, 72), text if page_number == 0 else "second page")
        if include_image:
            image = Image.new("RGB", (16, 16), color="black")
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            page.insert_image(
                fitz.Rect(72, 90, 104, 122),
                stream=buffer.getvalue(),
            )
    document.save(path)
    document.close()


def write_multipage_list_pdf(
    path: Path,
    *,
    pages: int,
    page_width: float = 595.28,
    page_height: float = 841.89,
) -> None:
    document = fitz.open()
    for page_number in range(1, pages + 1):
        page = document.new_page(width=page_width, height=page_height)
        if page_number == 1:
            text = (
                "OSA-SYN-260901 JX820 JX821 "
                "DATE ROUTE HOTEL BREAKFAST LUNCH DINNER 2026-09-01"
            )
        else:
            text = (
                "OSA-SYN-260901 合成大阪行程 "
                "DATE ROUTE HOTEL BREAKFAST LUNCH DINNER "
                f"2026-09-0{page_number}"
            )
        page.insert_text((72, 72), text)
    document.save(path)
    document.close()


@pytest.mark.parametrize("page_count", [1, 2, 3])
def test_pdf_inspection_validates_every_page_and_day_mapping(
    tmp_path, page_count
):
    pdf = tmp_path / "list.pdf"
    write_multipage_list_pdf(pdf, pages=page_count)
    day_map = tuple(
        DayPagePlacement(number, number, number)
        for number in range(1, page_count + 1)
    )
    day_tokens = {
        number: f"2026-09-0{number}"
        for number in range(1, page_count + 1)
    }

    inspection = inspect_list_pdf(
        pdf,
        required_text=("OSA-SYN-260901", "JX820", "JX821"),
        continuation_required_text=(
            "OSA-SYN-260901",
            "DATE",
            "ROUTE",
            "HOTEL",
            "BREAKFAST",
            "LUNCH",
            "DINNER",
        ),
        day_page_map=day_map,
        day_tokens=day_tokens,
    )

    assert inspection.page_count == page_count
    assert len(inspection.pages) == page_count
    assert all(page.image_count == 0 for page in inspection.pages)
    assert tuple(page.page_number for page in inspection.pages) == tuple(
        range(1, page_count + 1)
    )


def test_pdf_inspection_blocks_missing_continuation_identity_or_wrong_day_page(
    tmp_path,
):
    pdf = tmp_path / "list.pdf"
    write_multipage_list_pdf(pdf, pages=2)
    day_map = (
        DayPagePlacement(1, 1, 1),
        DayPagePlacement(2, 2, 2),
    )

    with pytest.raises(ValueError, match="continuation"):
        inspect_list_pdf(
            pdf,
            required_text=("OSA-SYN-260901",),
            continuation_required_text=("MISSING-GROUP", "DATE"),
            day_page_map=day_map,
            day_tokens={1: "2026-09-01", 2: "2026-09-02"},
        )
    with pytest.raises(ValueError, match="day page mapping"):
        inspect_list_pdf(
            pdf,
            required_text=("OSA-SYN-260901",),
            continuation_required_text=("OSA-SYN-260901", "DATE"),
            day_page_map=day_map,
            day_tokens={1: "2026-09-02", 2: "2026-09-01"},
        )

    repeated = tmp_path / "repeated-day.pdf"
    write_multipage_list_pdf(repeated, pages=1)
    document = fitz.open(repeated)
    page = document[0]
    page.insert_text((72, 140), "2026-09-01")
    document.save(repeated, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
    document.close()
    with pytest.raises(ValueError, match="day page mapping"):
        inspect_list_pdf(
            repeated,
            required_text=("OSA-SYN-260901",),
            day_page_map=(DayPagePlacement(1, 1, 1),),
            day_tokens={1: "2026-09-01"},
        )


def test_pdf_inspection_allows_identity_only_on_non_daily_continuation_page(
    tmp_path,
):
    pdf = tmp_path / "notes-continuation.pdf"
    document = fitz.open()
    first = document.new_page(width=595.28, height=841.89)
    first.insert_text(
        (72, 72),
        "OSA-SYN-260901 JX820 JX821 DATE ROUTE HOTEL BREAKFAST LUNCH "
        "DINNER 2026-09-01",
    )
    second = document.new_page(width=595.28, height=841.89)
    second.insert_text(
        (72, 72), "OSA-SYN-260901 GROUP TRAVEL NOTES CONTINUATION PAGE"
    )
    document.save(pdf)
    document.close()

    inspection = inspect_list_pdf(
        pdf,
        required_text=("OSA-SYN-260901", "JX820", "JX821"),
        continuation_required_text=(
            "OSA-SYN-260901",
            "DATE",
            "ROUTE",
            "HOTEL",
            "BREAKFAST",
            "LUNCH",
            "DINNER",
        ),
        day_page_map=(DayPagePlacement(1, 1, 1),),
        day_tokens={1: "2026-09-01"},
    )

    assert inspection.page_count == 2


def test_pdf_day_tokens_do_not_prefix_match_two_digit_days(tmp_path):
    pdf = tmp_path / "two-digit-days.pdf"
    document = fitz.open()
    page = document.new_page(width=595.28, height=841.89)
    page.insert_text((72, 72), "OSA-SYN-260901 JX820 JX821 9/1 9/10")
    document.save(pdf)
    document.close()

    inspection = inspect_list_pdf(
        pdf,
        required_text=("OSA-SYN-260901", "JX820", "JX821"),
        day_page_map=(
            DayPagePlacement(1, 1, 1),
            DayPagePlacement(10, 1, 1),
        ),
        day_tokens={1: "9/1", 10: "9/10"},
    )

    assert inspection.page_count == 1


def test_pdf_inspection_requires_a4_text_and_no_images(tmp_path):
    pdf = tmp_path / "list.pdf"
    write_pdf(pdf)

    inspection = inspect_list_pdf(
        pdf,
        required_text=("OSA-SYN-260901", "JX820", "JX821"),
    )

    assert inspection.page_count == 1
    assert inspection.image_count == 0
    assert inspection.text_character_count >= 20
    assert inspection.page_width_points == pytest.approx(595.28, abs=0.1)
    assert inspection.page_height_points == pytest.approx(841.89, abs=0.1)


def test_pdf_inspection_reports_missing_required_text_once_in_input_order(
    tmp_path,
):
    pdf = tmp_path / "list.pdf"
    write_pdf(pdf, text="SYN-LIST-260901 JX820 content long enough")

    with pytest.raises(
        ValueError, match="LIST QA PDF is missing required text"
    ) as captured:
        inspect_list_pdf(
            pdf,
            required_text=(
                "SYN-LIST-260901",
                "JX820",
                "JX821",
                "SERVICE-FEE-TOKEN",
                "JX821",
            ),
        )

    assert captured.value.missing_required_text == (
        "JX821",
        "SERVICE-FEE-TOKEN",
    )
    assert "SYN-LIST-260901" not in str(captured.value)
    assert "JX820" not in str(captured.value)


def test_pdf_inspection_fails_closed_on_page_text_or_image_drift(tmp_path):
    two_pages = tmp_path / "two-pages.pdf"
    write_pdf(two_pages, pages=2)
    with pytest.raises(ValueError, match="insufficient"):
        inspect_list_pdf(two_pages, required_text=("OSA-SYN-260901",))

    missing_text = tmp_path / "missing-text.pdf"
    write_pdf(missing_text, text="different content long enough")
    with pytest.raises(ValueError, match="required text"):
        inspect_list_pdf(missing_text, required_text=("OSA-SYN-260901",))

    unexpected_image = tmp_path / "unexpected-image.pdf"
    write_pdf(unexpected_image, include_image=True)
    with pytest.raises(ValueError, match="image"):
        inspect_list_pdf(
            unexpected_image,
            required_text=("OSA-SYN-260901",),
        )


class PdftoppmRunner:
    def __init__(self, *, return_code=0) -> None:
        self.return_code = return_code
        self.command = None
        self.options = None

    def __call__(self, command, **options):
        self.command = command
        self.options = options
        if self.return_code == 0:
            Path(f"{command[-1]}.png").write_bytes(b"synthetic png")
        return subprocess.CompletedProcess(
            command,
            returncode=self.return_code,
            stdout="",
            stderr="",
        )


class MultiPagePdftoppmRunner:
    def __init__(self, page_count: int, *, extra_page: bool = False) -> None:
        self.page_count = page_count
        self.extra_page = extra_page
        self.calls = []

    def __call__(self, command, **options):
        self.calls.append((command, options))
        prefix = Path(command[-1])
        count = self.page_count + int(self.extra_page)
        for page_number in range(1, count + 1):
            Path(f"{prefix}-{page_number}.png").write_bytes(
                f"page-{page_number}".encode()
            )
        return subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout="",
            stderr="",
        )


@pytest.mark.parametrize("page_count", [1, 2, 3])
def test_pdftoppm_renders_all_pages_once_with_contiguous_names(
    tmp_path, page_count
):
    pdf = tmp_path / "list.pdf"
    write_multipage_list_pdf(pdf, pages=page_count)
    executable = tmp_path / "pdftoppm.exe"
    executable.write_bytes(b"synthetic executable")
    output_directory = tmp_path / "qa"
    runner = MultiPagePdftoppmRunner(page_count)

    result = render_list_pdf_to_pngs(
        pdf,
        output_directory=output_directory,
        expected_page_count=page_count,
        pdftoppm_path=executable,
        runner=runner,
    )

    assert len(runner.calls) == 1
    assert [page.png_path.name for page in result.pages] == [
        f"page-{number:03d}.png"
        for number in range(1, page_count + 1)
    ]
    assert all(page.byte_count > 0 for page in result.pages)
    command = runner.calls[0][0]
    assert "-singlefile" not in command
    assert "-f" not in command
    assert "-l" not in command


def test_pdftoppm_rejects_extra_or_existing_page_sets(tmp_path):
    pdf = tmp_path / "list.pdf"
    write_multipage_list_pdf(pdf, pages=2)
    executable = tmp_path / "pdftoppm.exe"
    executable.write_bytes(b"synthetic executable")

    with pytest.raises(WordGenerationError, match="page set"):
        render_list_pdf_to_pngs(
            pdf,
            output_directory=tmp_path / "qa-extra",
            expected_page_count=2,
            pdftoppm_path=executable,
            runner=MultiPagePdftoppmRunner(2, extra_page=True),
        )

    existing = tmp_path / "qa-existing"
    existing.mkdir()
    (existing / "page-001.png").write_bytes(b"user owned")
    with pytest.raises(ValueError, match="must not already exist"):
        render_list_pdf_to_pngs(
            pdf,
            output_directory=existing,
            expected_page_count=2,
            pdftoppm_path=executable,
            runner=MultiPagePdftoppmRunner(2),
        )

    existing_file = tmp_path / "qa-file"
    existing_file.write_bytes(b"user owned")
    with pytest.raises(ValueError, match="must not already exist"):
        render_list_pdf_to_pngs(
            pdf,
            output_directory=existing_file,
            expected_page_count=2,
            pdftoppm_path=executable,
            runner=MultiPagePdftoppmRunner(2),
        )


def test_pdftoppm_render_is_single_page_exclusive_and_bounded(tmp_path):
    pdf = tmp_path / "list.pdf"
    write_pdf(pdf)
    executable = tmp_path / "pdftoppm.exe"
    executable.write_bytes(b"synthetic executable")
    output = tmp_path / "page.png"
    runner = PdftoppmRunner()

    result = render_list_pdf_to_png(
        pdf,
        output_png=output,
        pdftoppm_path=executable,
        runner=runner,
        timeout_seconds=30,
    )

    assert result.png_path == output.resolve()
    assert result.byte_count == len(b"synthetic png")
    assert runner.command == [
        str(executable.resolve()),
        "-f",
        "1",
        "-l",
        "1",
        "-singlefile",
        "-r",
        "150",
        "-png",
        str(pdf.resolve()),
        str(output.with_suffix("").resolve()),
    ]
    assert runner.options["timeout"] == 30


def test_pdftoppm_render_refuses_overwrite_and_failed_or_missing_output(tmp_path):
    pdf = tmp_path / "list.pdf"
    write_pdf(pdf)
    executable = tmp_path / "pdftoppm.exe"
    executable.write_bytes(b"synthetic executable")
    output = tmp_path / "page.png"
    output.write_bytes(b"user owned")

    with pytest.raises(ValueError, match="must not already exist"):
        render_list_pdf_to_png(
            pdf,
            output_png=output,
            pdftoppm_path=executable,
            runner=PdftoppmRunner(),
        )
    assert output.read_bytes() == b"user owned"

    output.unlink()
    with pytest.raises(WordGenerationError, match="failed"):
        render_list_pdf_to_png(
            pdf,
            output_png=output,
            pdftoppm_path=executable,
            runner=PdftoppmRunner(return_code=7),
        )


class SyntheticRenderAdapter:
    def __init__(
        self,
        page_count=1,
        *,
        reported_page_count=None,
        page_width=595.28,
        page_height=841.89,
    ) -> None:
        self.jobs = []
        self.page_count = page_count
        self.page_width = page_width
        self.page_height = page_height
        self.reported_page_count = (
            page_count
            if reported_page_count is None
            else reported_page_count
        )

    def run(self, job_path: Path, *, timeout_seconds: int) -> None:
        self.jobs.append((job_path, timeout_seconds))
        job = json.loads(job_path.read_text(encoding="utf-8"))
        output_pdf = Path(job["output_pdf"])
        write_multipage_list_pdf(
            output_pdf,
            pages=self.page_count,
            page_width=self.page_width,
            page_height=self.page_height,
        )
        Path(job["report_path"]).write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "action": "render",
                    "word_version": "synthetic",
                    "computed_page_count": self.reported_page_count,
                    "output_bytes": output_pdf.stat().st_size,
                }
            ),
            encoding="utf-8",
        )


@pytest.mark.parametrize("page_count", [1, 2, 3])
def test_word_pdf_render_publishes_every_page_and_hash_bound_index(
    tmp_path, page_count
):
    docx = tmp_path / "list.docx"
    docx.write_bytes(b"synthetic docx")
    pdftoppm = tmp_path / "pdftoppm.exe"
    pdftoppm.write_bytes(b"synthetic executable")
    output_pdf = tmp_path / "qa" / "list.pdf"
    output_pages = tmp_path / "qa"
    output_index = output_pages / "index.json"
    word = SyntheticRenderAdapter(page_count)
    raster = MultiPagePdftoppmRunner(page_count)
    day_map = tuple(
        DayPagePlacement(number, number, number)
        for number in range(1, page_count + 1)
    )

    result = render_list_word_for_qa(
        docx,
        output_pdf=output_pdf,
        output_png_directory=output_pages,
        output_qa_index=output_index,
        expected_page_count=page_count,
        required_text=("OSA-SYN-260901", "JX820", "JX821"),
        continuation_required_text=("OSA-SYN-260901", "DATE"),
        day_page_map=day_map,
        day_tokens={
            number: f"2026-09-0{number}"
            for number in range(1, page_count + 1)
        },
        adapter=word,
        pdftoppm_path=pdftoppm,
        pdftoppm_runner=raster,
        timeout_seconds=90,
    )

    assert result.pdf_path == output_pdf.resolve()
    assert result.qa_index_path == output_index.resolve()
    assert result.pdf_inspection.page_count == page_count
    assert result.pdf_inspection.image_count == 0
    assert [path.name for path in result.png_paths] == [
        f"page-{number:03d}.png"
        for number in range(1, page_count + 1)
    ]
    assert output_pdf.stat().st_size > 0
    index = json.loads(output_index.read_text(encoding="utf-8"))
    assert index["schema_version"] == 2
    assert index["page_count"] == page_count
    assert [item["relative_path"] for item in index["pages"]] == [
        f"page-{number:03d}.png"
        for number in range(1, page_count + 1)
    ]
    assert len({item["sha256"] for item in index["pages"]}) == page_count
    assert not (output_pdf.parent / "failed-qa").exists()
    assert "OSA-SYN-260901" not in output_index.read_text(
        encoding="utf-8"
    )
    received_job, timeout = word.jobs[0]
    assert timeout == 90
    assert not received_job.exists()


def test_word_pdf_render_uses_inspected_pdf_count_without_independent_expectation(
    tmp_path,
):
    docx = tmp_path / "list.docx"
    docx.write_bytes(b"synthetic docx")
    pdftoppm = tmp_path / "pdftoppm.exe"
    pdftoppm.write_bytes(b"synthetic executable")
    output_pdf = tmp_path / "qa" / "list.pdf"
    output_pages = tmp_path / "qa"
    output_index = output_pages / "index.json"
    word = SyntheticRenderAdapter(page_count=1, reported_page_count=2)
    raster = MultiPagePdftoppmRunner(1)

    result = render_list_word_for_qa(
        docx,
        output_pdf=output_pdf,
        output_png_directory=output_pages,
        output_qa_index=output_index,
        required_text=("OSA-SYN-260901", "JX820", "JX821"),
        adapter=word,
        pdftoppm_path=pdftoppm,
        pdftoppm_runner=raster,
        timeout_seconds=90,
    )

    assert result.pdf_inspection.page_count == 1
    assert result.computed_page_count == 2
    assert [path.name for path in result.png_paths] == ["page-001.png"]
    assert output_pdf.stat().st_size > 0
    index = json.loads(output_index.read_text(encoding="utf-8"))
    assert index["page_count"] == 1
    assert len(index["pages"]) == 1
    assert len(raster.calls) == 1
    received_job, timeout = word.jobs[0]
    assert timeout == 90
    assert not received_job.exists()


def test_word_pdf_render_preserves_failed_pdf_and_token_report_before_raising(
    tmp_path,
):
    docx = tmp_path / "list.docx"
    docx.write_bytes(b"synthetic docx")
    pdftoppm = tmp_path / "pdftoppm.exe"
    pdftoppm.write_bytes(b"synthetic executable")
    output_pdf = tmp_path / "qa" / "LIST-qa.pdf"
    output_pages = tmp_path / "qa" / "pages"
    output_index = output_pages / "index.json"
    word = SyntheticRenderAdapter(page_count=1)

    with pytest.raises(WordGenerationError) as captured:
        render_list_word_for_qa(
            docx,
            output_pdf=output_pdf,
            output_png_directory=output_pages,
            output_qa_index=output_index,
            required_text=(
                "OSA-SYN-260901",
                "JX820",
                "JX821",
                "SERVICE-FEE-TOKEN",
            ),
            adapter=word,
            pdftoppm_path=pdftoppm,
            pdftoppm_runner=MultiPagePdftoppmRunner(1),
        )

    failed_directory = output_pdf.parent / "failed-qa"
    failed_pdf = failed_directory / "LIST-qa.failed.pdf"
    failure_report = failed_directory / "failure.json"
    payload = json.loads(failure_report.read_text(encoding="utf-8"))

    assert len(word.jobs) == 1
    assert failed_pdf.stat().st_size > 0
    assert set(payload) == {
        "schema_version",
        "status",
        "stage",
        "error_code",
        "message",
        "missing_required_text",
        "pdf",
    }
    assert payload == {
        "schema_version": 1,
        "status": "failed",
        "stage": "pdf-inspection",
        "error_code": "LIST_PDF_REQUIRED_TEXT_MISSING",
        "message": "LIST QA PDF is missing required text",
        "missing_required_text": ["SERVICE-FEE-TOKEN"],
        "pdf": {
            "relative_path": "LIST-qa.failed.pdf",
            "bytes": failed_pdf.stat().st_size,
            "sha256": hashlib.sha256(failed_pdf.read_bytes()).hexdigest(),
        },
    }
    assert captured.value.code == "WORD_GENERATION_FAILED"
    assert captured.value.details == {
        "stage": "pdf-inspection",
        "error_code": "LIST_PDF_REQUIRED_TEXT_MISSING",
        "missing_required_text": ["SERVICE-FEE-TOKEN"],
        "failed_pdf": "failed-qa/LIST-qa.failed.pdf",
        "failure_report": "failed-qa/failure.json",
    }
    assert not output_pdf.exists()
    assert not output_pages.exists()
    assert not output_index.exists()
    received_job, _ = word.jobs[0]
    assert not received_job.exists()


def test_word_pdf_render_preserves_generic_inspection_failure_without_token_dump(
    tmp_path,
):
    docx = tmp_path / "list.docx"
    docx.write_bytes(b"synthetic docx")
    pdftoppm = tmp_path / "pdftoppm.exe"
    pdftoppm.write_bytes(b"synthetic executable")
    output_pdf = tmp_path / "qa" / "LIST-qa.pdf"
    output_pages = tmp_path / "qa" / "pages"
    output_index = output_pages / "index.json"
    word = SyntheticRenderAdapter(page_width=500.0, page_height=700.0)

    with pytest.raises(WordGenerationError) as captured:
        render_list_word_for_qa(
            docx,
            output_pdf=output_pdf,
            output_png_directory=output_pages,
            output_qa_index=output_index,
            required_text=("OSA-SYN-260901", "JX820", "JX821"),
            adapter=word,
            pdftoppm_path=pdftoppm,
            pdftoppm_runner=MultiPagePdftoppmRunner(1),
        )

    failed_directory = output_pdf.parent / "failed-qa"
    failed_pdf = failed_directory / "LIST-qa.failed.pdf"
    payload = json.loads(
        (failed_directory / "failure.json").read_text(encoding="utf-8")
    )

    assert failed_pdf.stat().st_size > 0
    assert payload["error_code"] == "LIST_PDF_INSPECTION_FAILED"
    assert payload["message"] == (
        "LIST QA PDF must use A4 portrait page geometry"
    )
    assert payload["missing_required_text"] == []
    assert captured.value.details == {
        "stage": "pdf-inspection",
        "error_code": "LIST_PDF_INSPECTION_FAILED",
        "missing_required_text": [],
        "failed_pdf": "failed-qa/LIST-qa.failed.pdf",
        "failure_report": "failed-qa/failure.json",
    }
    assert not output_pdf.exists()
    assert not output_pages.exists()
    assert not output_index.exists()


def test_word_pdf_render_blocks_existing_failed_qa_directory_before_adapter(
    tmp_path,
):
    docx = tmp_path / "list.docx"
    docx.write_bytes(b"synthetic docx")
    pdftoppm = tmp_path / "pdftoppm.exe"
    pdftoppm.write_bytes(b"synthetic executable")
    output_pdf = tmp_path / "qa" / "LIST-qa.pdf"
    output_pages = tmp_path / "qa" / "pages"
    output_index = output_pages / "index.json"
    failed_directory = output_pdf.parent / "failed-qa"
    failed_directory.mkdir(parents=True)
    sentinel = failed_directory / "sentinel.txt"
    sentinel.write_bytes(b"prior evidence")
    word = SyntheticRenderAdapter()

    with pytest.raises(ValueError, match="failed QA evidence"):
        render_list_word_for_qa(
            docx,
            output_pdf=output_pdf,
            output_png_directory=output_pages,
            output_qa_index=output_index,
            required_text=("OSA-SYN-260901", "JX820", "JX821"),
            adapter=word,
            pdftoppm_path=pdftoppm,
            pdftoppm_runner=MultiPagePdftoppmRunner(1),
        )

    assert word.jobs == []
    assert sentinel.read_bytes() == b"prior evidence"
    assert not output_pdf.exists()
    assert not output_pages.exists()
    assert not output_index.exists()


def test_failed_pdf_evidence_rolls_back_fresh_paths_when_report_write_fails(
    tmp_path,
    monkeypatch,
):
    docx = tmp_path / "list.docx"
    docx.write_bytes(b"synthetic docx")
    pdftoppm = tmp_path / "pdftoppm.exe"
    pdftoppm.write_bytes(b"synthetic executable")
    output_pdf = tmp_path / "qa" / "LIST-qa.pdf"
    output_pdf.parent.mkdir()
    sentinel = output_pdf.parent / "sentinel.txt"
    sentinel.write_bytes(b"keep me")
    output_pages = tmp_path / "qa" / "pages"
    output_index = output_pages / "index.json"
    word = SyntheticRenderAdapter()

    def fail_report_write(path, payload):
        del path, payload
        raise OSError("synthetic failure report write")

    monkeypatch.setattr(
        "travel_briefing.word_qa._write_json_exclusive",
        fail_report_write,
    )

    with pytest.raises(OSError, match="synthetic failure report write"):
        render_list_word_for_qa(
            docx,
            output_pdf=output_pdf,
            output_png_directory=output_pages,
            output_qa_index=output_index,
            required_text=(
                "OSA-SYN-260901",
                "JX820",
                "JX821",
                "SERVICE-FEE-TOKEN",
            ),
            adapter=word,
            pdftoppm_path=pdftoppm,
            pdftoppm_runner=MultiPagePdftoppmRunner(1),
        )

    assert not (output_pdf.parent / "failed-qa").exists()
    assert not output_pdf.exists()
    assert not output_pages.exists()
    assert not output_index.exists()
    assert sentinel.read_bytes() == b"keep me"


def test_word_pdf_render_rejects_page_count_mismatch_before_publish(tmp_path):
    docx = tmp_path / "list.docx"
    docx.write_bytes(b"synthetic docx")
    pdftoppm = tmp_path / "pdftoppm.exe"
    pdftoppm.write_bytes(b"synthetic executable")

    with pytest.raises(ValueError, match="page count"):
        render_list_word_for_qa(
            docx,
            output_pdf=tmp_path / "list.pdf",
            output_png_directory=tmp_path / "qa",
            output_qa_index=tmp_path / "qa" / "index.json",
            expected_page_count=2,
            required_text=("OSA-SYN-260901",),
            adapter=SyntheticRenderAdapter(page_count=1),
            pdftoppm_path=pdftoppm,
            pdftoppm_runner=MultiPagePdftoppmRunner(1),
        )

    assert not (tmp_path / "list.pdf").exists()
    assert not (tmp_path / "qa" / "index.json").exists()
