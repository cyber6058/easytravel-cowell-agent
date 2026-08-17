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

import pymupdf as fitz

from .errors import UnknownWordResultError, WordGenerationError
from .template_contract import A4_HEIGHT_POINTS, A4_WIDTH_POINTS
from .word_list import DayPagePlacement


ProcessRunner = Callable[..., subprocess.CompletedProcess[str]]
_PAGE_SIZE_TOLERANCE_POINTS = 2.0


@dataclass(frozen=True, slots=True)
class ListPdfPageInspection:
    page_number: int
    page_width_points: float
    page_height_points: float
    text_character_count: int
    text_block_count: int
    image_count: int


@dataclass(frozen=True, slots=True)
class ListPdfInspection:
    page_count: int
    pages: tuple[ListPdfPageInspection, ...]

    @property
    def page_width_points(self) -> float:
        return self.pages[0].page_width_points

    @property
    def page_height_points(self) -> float:
        return self.pages[0].page_height_points

    @property
    def text_character_count(self) -> int:
        return sum(page.text_character_count for page in self.pages)

    @property
    def text_block_count(self) -> int:
        return sum(page.text_block_count for page in self.pages)

    @property
    def image_count(self) -> int:
        return sum(page.image_count for page in self.pages)


@dataclass(frozen=True, slots=True)
class ListPngRenderResult:
    png_path: Path
    sha256: str
    byte_count: int
    dpi: int


@dataclass(frozen=True, slots=True)
class ListPngPageSetResult:
    pages: tuple[ListPngRenderResult, ...]
    dpi: int


class WordAdapter(Protocol):
    def run(self, job_path: Path, *, timeout_seconds: int) -> None: ...


@dataclass(frozen=True, slots=True)
class ListWordQaResult:
    pdf_path: Path
    png_paths: tuple[Path, ...]
    qa_index_path: Path
    pdf_sha256: str
    qa_index_sha256: str
    pdf_inspection: ListPdfInspection
    computed_page_count: int

    @property
    def png_path(self) -> Path:
        return self.png_paths[0]

    @property
    def png_sha256(self) -> str:
        return _sha256_file(self.png_paths[0])


def inspect_list_pdf(
    pdf_path: Path,
    *,
    required_text: tuple[str, ...],
    continuation_required_text: tuple[str, ...] = (),
    day_page_map: tuple[DayPagePlacement, ...] = (),
    day_tokens: dict[int, str] | None = None,
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
        if document.page_count <= 0:
            raise ValueError("LIST QA PDF must contain at least one page")
        pages = []
        page_texts = []
        for index in range(document.page_count):
            page = document.load_page(index)
            width = float(page.rect.width)
            height = float(page.rect.height)
            if (
                abs(width - A4_WIDTH_POINTS)
                > _PAGE_SIZE_TOLERANCE_POINTS
                or abs(height - A4_HEIGHT_POINTS)
                > _PAGE_SIZE_TOLERANCE_POINTS
            ):
                raise ValueError(
                    "LIST QA PDF must use A4 portrait page geometry"
                )
            text = page.get_text("text")
            page_texts.append(text)
            compact_text = "".join(text.split())
            if len(compact_text) < 20:
                raise ValueError(
                    "LIST QA PDF contains insufficient non-empty text"
                )
            image_count = len(page.get_images(full=True))
            if index == 0 and image_count < 1:
                raise ValueError(
                    "LIST QA PDF contains no image for the preserved QR"
                )
            pages.append(
                ListPdfPageInspection(
                    page_number=index + 1,
                    page_width_points=round(width, 2),
                    page_height_points=round(height, 2),
                    text_character_count=len(compact_text),
                    text_block_count=len(page.get_text("blocks")),
                    image_count=image_count,
                )
            )
        whole_text = "\n".join(page_texts)
        if any(value not in whole_text for value in required_text):
            raise ValueError("LIST QA PDF is missing required text")
        if continuation_required_text:
            identity_text = continuation_required_text[0]
            daily_header_text = continuation_required_text[1:]
            daily_continuation_pages = (
                {
                    item.start_page
                    for item in day_page_map
                    if item.start_page > 1
                }
                if day_page_map
                else set(range(2, document.page_count + 1))
            )
            for page_number, text in enumerate(page_texts[1:], start=2):
                if identity_text not in text or (
                    page_number in daily_continuation_pages
                    and any(value not in text for value in daily_header_text)
                ):
                    raise ValueError(
                        "LIST QA PDF continuation page is missing identity or header"
                    )
        if day_page_map or day_tokens:
            tokens = day_tokens or {}
            if (
                len(day_page_map) != len(tokens)
                or set(tokens)
                != {item.day_number for item in day_page_map}
            ):
                raise ValueError("LIST QA day page mapping is invalid")
            for item in day_page_map:
                token = tokens[item.day_number]
                if (
                    item.start_page != item.end_page
                    or not 1 <= item.start_page <= document.page_count
                ):
                    raise ValueError("LIST QA day page mapping is invalid")
                occurrences = [
                    number
                    for number, text in enumerate(page_texts, start=1)
                    if token in text
                ]
                occurrence_count = sum(
                    text.count(token) for text in page_texts
                )
                if (
                    occurrences != [item.start_page]
                    or occurrence_count != 1
                ):
                    raise ValueError(
                        "LIST QA day page mapping does not match PDF"
                    )
        return ListPdfInspection(
            page_count=document.page_count,
            pages=tuple(pages),
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


def render_list_pdf_to_pngs(
    pdf_path: Path,
    *,
    output_directory: Path,
    expected_page_count: int,
    pdftoppm_path: Path,
    runner: ProcessRunner = subprocess.run,
    timeout_seconds: int = 60,
) -> ListPngPageSetResult:
    pdf = pdf_path.expanduser().resolve()
    output = output_directory.expanduser().resolve()
    executable = pdftoppm_path.expanduser().resolve()
    if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
        raise ValueError("LIST render input must be an existing PDF")
    if not executable.is_file():
        raise ValueError(
            "LIST render requires an explicit pdftoppm executable"
        )
    if (
        isinstance(expected_page_count, bool)
        or not isinstance(expected_page_count, int)
        or expected_page_count <= 0
    ):
        raise ValueError("LIST render page count must be positive")
    if timeout_seconds <= 0:
        raise ValueError("LIST render timeout must be positive")
    if output.exists() and (
        not output.is_dir() or any(output.iterdir())
    ):
        raise ValueError(
            "LIST rendered page set must not already exist"
        )
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="easytravel-list-pages-"
    ) as temp:
        temporary = Path(temp)
        prefix = temporary / "page"
        command = [
            str(executable),
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
        if (
            sys.platform == "win32"
            and hasattr(subprocess, "CREATE_NO_WINDOW")
        ):
            options["creationflags"] = subprocess.CREATE_NO_WINDOW
        try:
            result = runner(command, **options)
        except subprocess.TimeoutExpired as error:
            raise UnknownWordResultError(
                "pdftoppm timed out after one attempt; inspect current output before retry",
                details={
                    "temporary_page_count": len(
                        tuple(temporary.glob("page-*.png"))
                    )
                },
            ) from error
        except OSError as error:
            raise WordGenerationError(
                "Configured pdftoppm is unavailable"
            ) from error
        if result.returncode != 0:
            raise WordGenerationError(
                "Configured pdftoppm render failed",
                {"return_code": result.returncode},
            )
        rendered = tuple(
            sorted(
                temporary.glob("page-*.png"),
                key=lambda path: path.name,
            )
        )
        expected_names = tuple(
            f"page-{number}.png"
            for number in range(1, expected_page_count + 1)
        )
        if (
            tuple(path.name for path in rendered) != expected_names
            or any(path.stat().st_size <= 0 for path in rendered)
        ):
            raise WordGenerationError(
                "pdftoppm rendered an unexpected LIST page set"
            )
        published = []
        try:
            for number, source in enumerate(rendered, start=1):
                destination = output / f"page-{number:03d}.png"
                _copy_exclusive(source, destination)
                published.append(destination)
        except BaseException:
            for path in reversed(published):
                path.unlink(missing_ok=True)
            raise
    pages = tuple(
        ListPngRenderResult(
            png_path=path,
            sha256=_sha256_file(path),
            byte_count=path.stat().st_size,
            dpi=150,
        )
        for path in published
    )
    return ListPngPageSetResult(pages=pages, dpi=150)


def render_list_word_for_qa(
    input_docx: Path,
    *,
    output_pdf: Path,
    output_png: Path | None = None,
    output_png_directory: Path | None = None,
    output_qa_index: Path | None = None,
    expected_page_count: int | None = None,
    required_text: tuple[str, ...],
    continuation_required_text: tuple[str, ...] = (),
    day_page_map: tuple[DayPagePlacement, ...] = (),
    day_tokens: dict[int, str] | None = None,
    adapter: WordAdapter,
    pdftoppm_path: Path,
    pdftoppm_runner: ProcessRunner = subprocess.run,
    timeout_seconds: int = 120,
) -> ListWordQaResult:
    docx = input_docx.expanduser().resolve()
    pdf = output_pdf.expanduser().resolve()
    legacy_png = (
        output_png.expanduser().resolve()
        if output_png is not None
        else None
    )
    pages_directory = (
        output_png_directory.expanduser().resolve()
        if output_png_directory is not None
        else None
    )
    index_destination = (
        output_qa_index.expanduser().resolve()
        if output_qa_index is not None
        else None
    )
    if not docx.is_file() or docx.suffix.lower() != ".docx":
        raise ValueError("LIST Word QA input must be an existing DOCX")
    legacy_mode = legacy_png is not None
    if legacy_mode == (pages_directory is not None or index_destination is not None):
        raise ValueError(
            "LIST Word QA requires either one legacy PNG or page-set outputs"
        )
    if pdf.suffix.lower() != ".pdf":
        raise ValueError("LIST Word QA output must be PDF")
    if legacy_mode and legacy_png.suffix.lower() != ".png":
        raise ValueError("LIST Word QA legacy output must be PNG")
    if not legacy_mode and (
        pages_directory is None or index_destination is None
    ):
        raise ValueError("LIST Word QA page set paths are required")
    if pdf.exists() or (
        legacy_png is not None and legacy_png.exists()
    ) or (
        index_destination is not None and index_destination.exists()
    ):
        raise ValueError("LIST Word QA outputs must not already exist")
    if timeout_seconds <= 0:
        raise ValueError("LIST Word QA timeout must be positive")
    pdf.parent.mkdir(parents=True, exist_ok=True)
    if legacy_png is not None:
        legacy_png.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="easytravel-list-render-") as temp:
        work_dir = Path(temp)
        temporary_pdf = work_dir / "list.pdf"
        temporary_png = work_dir / "list.png"
        temporary_pages = work_dir / "pages"
        temporary_index = work_dir / "index.json"
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
        required_page_count = (
            expected_page_count
            if expected_page_count is not None
            else report["computed_page_count"]
        )
        if report["computed_page_count"] != required_page_count:
            raise ValueError(
                "Word, PDF, and expected LIST page count do not match"
            )
        if not temporary_pdf.is_file() or temporary_pdf.stat().st_size == 0:
            raise WordGenerationError(
                "Word render returned success without a PDF output"
            )
        if report["output_bytes"] != temporary_pdf.stat().st_size:
            raise WordGenerationError("Word PDF size does not match its report")
        inspection = inspect_list_pdf(
            temporary_pdf,
            required_text=required_text,
            continuation_required_text=continuation_required_text,
            day_page_map=day_page_map,
            day_tokens=day_tokens,
        )
        if inspection.page_count != required_page_count:
            raise ValueError(
                "Word report and PDF LIST page count do not match"
            )
        if legacy_mode:
            if required_page_count != 1:
                raise ValueError(
                    "legacy LIST PNG output supports one page only"
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
                output_png=legacy_png,
            )
            published_pngs = (legacy_png,)
            index_path = legacy_png
        else:
            page_set = render_list_pdf_to_pngs(
                temporary_pdf,
                output_directory=temporary_pages,
                expected_page_count=required_page_count,
                pdftoppm_path=pdftoppm_path,
                runner=pdftoppm_runner,
            )
            index_payload = {
                "schema_version": 2,
                "page_count": required_page_count,
                "pages": [
                    {
                        "page_number": number,
                        "relative_path": f"page-{number:03d}.png",
                        "sha256": page.sha256,
                        "required_text_check": True,
                    }
                    for number, page in enumerate(
                        page_set.pages, start=1
                    )
                ],
                "day_page_map": [
                    {
                        "day_number": item.day_number,
                        "page_number": item.start_page,
                    }
                    for item in day_page_map
                ],
            }
            temporary_index.write_text(
                json.dumps(
                    index_payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n",
                encoding="utf-8",
                newline="\n",
            )
            assert pages_directory is not None
            assert index_destination is not None
            published_pngs = _publish_qa_page_set(
                source_pdf=temporary_pdf,
                output_pdf=pdf,
                source_pages=tuple(
                    item.png_path for item in page_set.pages
                ),
                output_directory=pages_directory,
                source_index=temporary_index,
                output_index=index_destination,
            )
            index_path = index_destination
    return ListWordQaResult(
        pdf_path=pdf,
        png_paths=published_pngs,
        qa_index_path=index_path,
        pdf_sha256=_sha256_file(pdf),
        qa_index_sha256=_sha256_file(index_path),
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
        or isinstance(payload.get("computed_page_count"), bool)
        or not isinstance(payload.get("computed_page_count"), int)
        or payload["computed_page_count"] <= 0
        or isinstance(payload.get("output_bytes"), bool)
        or not isinstance(payload.get("output_bytes"), int)
        or payload["output_bytes"] <= 0
    ):
        raise WordGenerationError("Word render report does not match schema version 1")
    return payload


def _publish_qa_page_set(
    *,
    source_pdf: Path,
    output_pdf: Path,
    source_pages: tuple[Path, ...],
    output_directory: Path,
    source_index: Path,
    output_index: Path,
) -> tuple[Path, ...]:
    if output_directory != output_index.parent:
        raise ValueError(
            "LIST QA index must be inside the page output directory"
        )
    output_directory.mkdir(parents=True, exist_ok=True)
    destinations = tuple(
        output_directory / f"page-{number:03d}.png"
        for number in range(1, len(source_pages) + 1)
    )
    if any(path.exists() for path in (*destinations, output_index)):
        raise ValueError("LIST QA page set must not already exist")
    created: list[Path] = []
    try:
        _copy_exclusive(source_pdf, output_pdf)
        created.append(output_pdf)
        for source, destination in zip(
            source_pages, destinations, strict=True
        ):
            _copy_exclusive(source, destination)
            created.append(destination)
        _copy_exclusive(source_index, output_index)
        created.append(output_index)
    except BaseException:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise
    return destinations


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
