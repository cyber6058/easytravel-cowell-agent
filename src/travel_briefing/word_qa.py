from __future__ import annotations

import hashlib
import json
import secrets
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

import fitz

from .errors import UnknownWordResultError, WordGenerationError
from .template_contract import A4_HEIGHT_POINTS, A4_WIDTH_POINTS


ProcessRunner = Callable[..., subprocess.CompletedProcess[str]]
_PAGE_SIZE_TOLERANCE_POINTS = 2.0


@dataclass(frozen=True, slots=True)
class ListPdfInspection:
    page_count: int
    page_width_points: float
    page_height_points: float
    text_character_count: int
    text_block_count: int
    image_count: int


@dataclass(frozen=True, slots=True)
class ListPngRenderResult:
    png_path: Path
    sha256: str
    byte_count: int
    dpi: int


class WordAdapter(Protocol):
    def run(self, job_path: Path, *, timeout_seconds: int) -> None: ...


@dataclass(frozen=True, slots=True)
class ListWordQaResult:
    pdf_path: Path
    png_path: Path
    pdf_sha256: str
    png_sha256: str
    pdf_inspection: ListPdfInspection
    computed_page_count: int


def inspect_list_pdf(
    pdf_path: Path,
    *,
    required_text: tuple[str, ...],
) -> ListPdfInspection:
    path = pdf_path.expanduser().resolve()
    if not path.is_file() or path.suffix.lower() != ".pdf":
        raise ValueError("LIST QA input must be an existing PDF")
    if not required_text or any(
        not isinstance(value, str) or not value for value in required_text
    ):
        raise ValueError("LIST PDF QA requires non-empty expected text")
    try:
        document = fitz.open(path)
    except (OSError, RuntimeError, ValueError) as error:
        raise ValueError("LIST QA PDF cannot be opened") from error
    try:
        if document.page_count != 1:
            raise ValueError("LIST QA PDF must contain exactly one page")
        page = document.load_page(0)
        width = float(page.rect.width)
        height = float(page.rect.height)
        if (
            abs(width - A4_WIDTH_POINTS) > _PAGE_SIZE_TOLERANCE_POINTS
            or abs(height - A4_HEIGHT_POINTS) > _PAGE_SIZE_TOLERANCE_POINTS
        ):
            raise ValueError("LIST QA PDF must use A4 portrait page geometry")
        text = page.get_text("text")
        compact_text = "".join(text.split())
        if len(compact_text) < 20:
            raise ValueError("LIST QA PDF contains insufficient non-empty text")
        missing = [value for value in required_text if value not in text]
        if missing:
            raise ValueError("LIST QA PDF is missing required text")
        blocks = page.get_text("blocks")
        image_count = len(page.get_images(full=True))
        if image_count < 1:
            raise ValueError("LIST QA PDF contains no image for the preserved QR")
        return ListPdfInspection(
            page_count=1,
            page_width_points=round(width, 2),
            page_height_points=round(height, 2),
            text_character_count=len(compact_text),
            text_block_count=len(blocks),
            image_count=image_count,
        )
    finally:
        document.close()


def render_list_pdf_to_png(
    pdf_path: Path,
    *,
    output_png: Path,
    pdftoppm_path: Path,
    runner: ProcessRunner = subprocess.run,
    timeout_seconds: int = 60,
) -> ListPngRenderResult:
    pdf = pdf_path.expanduser().resolve()
    output = output_png.expanduser().resolve()
    executable = pdftoppm_path.expanduser().resolve()
    if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
        raise ValueError("LIST render input must be an existing PDF")
    if not executable.is_file():
        raise ValueError("LIST render requires an explicit pdftoppm executable")
    if output.suffix.lower() != ".png":
        raise ValueError("LIST rendered page must use a .png path")
    if output.exists():
        raise ValueError("LIST rendered PNG must not already exist")
    if timeout_seconds <= 0:
        raise ValueError("LIST render timeout must be positive")
    output.parent.mkdir(parents=True, exist_ok=True)
    prefix = output.with_suffix("")
    command = [
        str(executable),
        "-f",
        "1",
        "-l",
        "1",
        "-singlefile",
        "-r",
        "150",
        "-png",
        str(pdf),
        str(prefix),
    ]
    options: dict[str, Any] = {
        "check": False,
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": timeout_seconds,
    }
    if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        options["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        result = runner(command, **options)
    except subprocess.TimeoutExpired as error:
        exists = output.is_file()
        raise UnknownWordResultError(
            "pdftoppm timed out after one attempt; inspect current output before retry",
            details={
                "output_exists": exists,
                "output_bytes": output.stat().st_size if exists else 0,
            },
        ) from error
    except OSError as error:
        raise WordGenerationError("Configured pdftoppm is unavailable") from error
    if result.returncode != 0:
        raise WordGenerationError(
            "Configured pdftoppm render failed",
            {"return_code": result.returncode},
        )
    if not output.is_file() or output.stat().st_size == 0:
        raise WordGenerationError(
            "pdftoppm returned success without a rendered PNG"
        )
    return ListPngRenderResult(
        png_path=output,
        sha256=_sha256_file(output),
        byte_count=output.stat().st_size,
        dpi=150,
    )


def render_list_word_for_qa(
    input_docx: Path,
    *,
    output_pdf: Path,
    output_png: Path,
    required_text: tuple[str, ...],
    adapter: WordAdapter,
    pdftoppm_path: Path,
    pdftoppm_runner: ProcessRunner = subprocess.run,
    timeout_seconds: int = 120,
) -> ListWordQaResult:
    docx = input_docx.expanduser().resolve()
    pdf = output_pdf.expanduser().resolve()
    png = output_png.expanduser().resolve()
    if not docx.is_file() or docx.suffix.lower() != ".docx":
        raise ValueError("LIST Word QA input must be an existing DOCX")
    if pdf.suffix.lower() != ".pdf" or png.suffix.lower() != ".png":
        raise ValueError("LIST Word QA outputs must be PDF and PNG")
    if pdf.exists() or png.exists():
        raise ValueError("LIST Word QA outputs must not already exist")
    if timeout_seconds <= 0:
        raise ValueError("LIST Word QA timeout must be positive")
    pdf.parent.mkdir(parents=True, exist_ok=True)
    png.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="easytravel-list-render-") as temp:
        work_dir = Path(temp)
        temporary_pdf = work_dir / "list.pdf"
        temporary_png = work_dir / "list.png"
        report_path = work_dir / "render-report.json"
        job_path = work_dir / "word-job.json"
        pid_path = work_dir / "word-owner.json"
        job = {
            "schema_version": 1,
            "action": "render",
            "ownership_nonce": secrets.token_hex(16),
            "word_pid_path": str(pid_path),
            "input_docx": str(docx),
            "output_pdf": str(temporary_pdf),
            "report_path": str(report_path),
        }
        job_path.write_text(
            json.dumps(job, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        try:
            adapter.run(job_path, timeout_seconds=timeout_seconds)
        except UnknownWordResultError as error:
            error.details.update(
                temporary_pdf_exists=temporary_pdf.is_file(),
                temporary_pdf_bytes=(
                    temporary_pdf.stat().st_size if temporary_pdf.is_file() else 0
                ),
                report_exists=report_path.is_file(),
            )
            raise
        report = _read_render_report(report_path)
        if not temporary_pdf.is_file() or temporary_pdf.stat().st_size == 0:
            raise WordGenerationError(
                "Word render returned success without a PDF output"
            )
        if report["output_bytes"] != temporary_pdf.stat().st_size:
            raise WordGenerationError("Word PDF size does not match its report")
        inspection = inspect_list_pdf(
            temporary_pdf,
            required_text=required_text,
        )
        png_result = render_list_pdf_to_png(
            temporary_pdf,
            output_png=temporary_png,
            pdftoppm_path=pdftoppm_path,
            runner=pdftoppm_runner,
        )
        _publish_qa_artifacts(
            source_pdf=temporary_pdf,
            output_pdf=pdf,
            source_png=png_result.png_path,
            output_png=png,
        )
    return ListWordQaResult(
        pdf_path=pdf,
        png_path=png,
        pdf_sha256=_sha256_file(pdf),
        png_sha256=_sha256_file(png),
        pdf_inspection=inspection,
        computed_page_count=report["computed_page_count"],
    )


def _read_render_report(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise WordGenerationError("Word render report is not valid UTF-8 JSON") from error
    expected_keys = {
        "schema_version",
        "action",
        "word_version",
        "computed_page_count",
        "output_bytes",
    }
    if (
        not isinstance(payload, dict)
        or set(payload) != expected_keys
        or payload.get("schema_version") != 1
        or payload.get("action") != "render"
        or not isinstance(payload.get("word_version"), str)
        or not payload["word_version"]
        or payload.get("computed_page_count") != 1
        or isinstance(payload.get("output_bytes"), bool)
        or not isinstance(payload.get("output_bytes"), int)
        or payload["output_bytes"] <= 0
    ):
        raise WordGenerationError("Word render report does not match schema version 1")
    return payload


def _publish_qa_artifacts(
    *,
    source_pdf: Path,
    output_pdf: Path,
    source_png: Path,
    output_png: Path,
) -> None:
    created: list[Path] = []
    try:
        _copy_exclusive(source_pdf, output_pdf)
        created.append(output_pdf)
        _copy_exclusive(source_png, output_png)
        created.append(output_png)
    except BaseException:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise


def _copy_exclusive(source: Path, destination: Path) -> None:
    created = False
    try:
        with source.open("rb") as input_stream, destination.open("xb") as output_stream:
            created = True
            shutil.copyfileobj(input_stream, output_stream)
    except BaseException:
        if created:
            destination.unlink(missing_ok=True)
        raise


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
