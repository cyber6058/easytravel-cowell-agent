import io
import json
import subprocess
from pathlib import Path

import fitz
import pytest
from PIL import Image

from travel_briefing.word_qa import (
    inspect_list_pdf,
    render_list_pdf_to_png,
    render_list_word_for_qa,
)
from travel_briefing.errors import WordGenerationError


def write_pdf(path: Path, *, pages=1, text="OSA-SYN-260901 JX820 JX821") -> None:
    document = fitz.open()
    for page_number in range(pages):
        page = document.new_page(width=595.28, height=841.89)
        page.insert_text((72, 72), text if page_number == 0 else "second page")
        image = Image.new("RGB", (16, 16), color="black")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        page.insert_image(fitz.Rect(72, 90, 104, 122), stream=buffer.getvalue())
    document.save(path)
    document.close()


def test_pdf_inspection_requires_one_a4_page_text_and_an_image(tmp_path):
    pdf = tmp_path / "list.pdf"
    write_pdf(pdf)

    inspection = inspect_list_pdf(
        pdf,
        required_text=("OSA-SYN-260901", "JX820", "JX821"),
    )

    assert inspection.page_count == 1
    assert inspection.image_count == 1
    assert inspection.text_character_count >= 20
    assert inspection.page_width_points == pytest.approx(595.28, abs=0.1)
    assert inspection.page_height_points == pytest.approx(841.89, abs=0.1)


def test_pdf_inspection_fails_closed_on_page_text_or_qr_drift(tmp_path):
    two_pages = tmp_path / "two-pages.pdf"
    write_pdf(two_pages, pages=2)
    with pytest.raises(ValueError, match="one page"):
        inspect_list_pdf(two_pages, required_text=("OSA-SYN-260901",))

    missing_text = tmp_path / "missing-text.pdf"
    write_pdf(missing_text, text="different content long enough")
    with pytest.raises(ValueError, match="required text"):
        inspect_list_pdf(missing_text, required_text=("OSA-SYN-260901",))

    no_image = tmp_path / "no-image.pdf"
    document = fitz.open()
    page = document.new_page(width=595.28, height=841.89)
    page.insert_text((72, 72), "OSA-SYN-260901 sufficiently long text")
    document.save(no_image)
    document.close()
    with pytest.raises(ValueError, match="image"):
        inspect_list_pdf(no_image, required_text=("OSA-SYN-260901",))


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
    def __init__(self) -> None:
        self.jobs = []

    def run(self, job_path: Path, *, timeout_seconds: int) -> None:
        self.jobs.append((job_path, timeout_seconds))
        job = json.loads(job_path.read_text(encoding="utf-8"))
        output_pdf = Path(job["output_pdf"])
        write_pdf(output_pdf)
        Path(job["report_path"]).write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "action": "render",
                    "word_version": "synthetic",
                    "computed_page_count": 1,
                    "output_bytes": output_pdf.stat().st_size,
                }
            ),
            encoding="utf-8",
        )


def test_word_pdf_render_runs_qa_before_publishing_pdf_and_png(tmp_path):
    docx = tmp_path / "list.docx"
    docx.write_bytes(b"synthetic docx")
    pdftoppm = tmp_path / "pdftoppm.exe"
    pdftoppm.write_bytes(b"synthetic executable")
    output_pdf = tmp_path / "qa" / "list.pdf"
    output_png = tmp_path / "qa" / "list.png"
    word = SyntheticRenderAdapter()
    raster = PdftoppmRunner()

    result = render_list_word_for_qa(
        docx,
        output_pdf=output_pdf,
        output_png=output_png,
        required_text=("OSA-SYN-260901", "JX820", "JX821"),
        adapter=word,
        pdftoppm_path=pdftoppm,
        pdftoppm_runner=raster,
        timeout_seconds=90,
    )

    assert result.pdf_path == output_pdf.resolve()
    assert result.png_path == output_png.resolve()
    assert result.pdf_inspection.page_count == 1
    assert result.pdf_inspection.image_count == 1
    assert output_pdf.stat().st_size > 0
    assert output_png.read_bytes() == b"synthetic png"
    received_job, timeout = word.jobs[0]
    assert timeout == 90
    assert not received_job.exists()
