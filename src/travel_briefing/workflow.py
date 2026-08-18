from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Mapping, Protocol

from .adapters.newamazing import parse_newamazing_html
from .adapters.pdf_itinerary import (
    extract_pdf_pages,
    parse_pdf_itinerary_pages,
)
from .adapters.windows_media_speech import WindowsMediaSpeechAdapter
from .adapters.windows_word import WindowsWordAdapter
from .artifact_store import (
    artifact_record,
    copy_artifact,
    create_run_directory,
    load_run_manifest,
    publish_text,
    verify_artifacts,
    write_manifest,
)
from .audio import convert_wav_to_mp3, synthesize_yating
from .config import BriefingConfig
from .errors import BriefingCliError, BriefingInputError, BriefingSourceError
from .input_validation import validate_newamazing_url, validate_pdf_input
from .merge import merge_briefing_sources
from .models import Artifact, BriefingDraft, DraftStatus, DraftWarning
from .narration import segment_narration
from .op_values import (
    REQUIRED_OP_FIELD_NAMES,
    apply_conflict_decisions,
    apply_op_values,
)
from .review import render_review
from .script_policy import build_narration_input, dumps_narration_input
from .script_validation import (
    ScriptValidationResult,
    check_script,
    dumps_script_validation,
    narration_text_for_tts,
    validate_audio_duration,
)
from .source_fetch import fetch_newamazing_html
from .word_list import (
    LIST_WORD_GENERATOR_VERSION,
    build_list_word,
    format_list_day_date,
)
from .word_qa import render_list_word_for_qa


WORKFLOW_VERSION = "travel-briefing/0.2.1"


@dataclass(frozen=True, slots=True)
class PrepareResult:
    run_directory: Path
    draft: BriefingDraft
    manifest_path: Path
    review_path: Path
    narration_input_path: Path


@dataclass(frozen=True, slots=True)
class ScriptCheckResult:
    ready: bool
    report_path: Path
    validation: ScriptValidationResult


@dataclass(frozen=True, slots=True)
class WordRenderEvidence:
    generator_version: str
    page_count: int
    qr_image_count: int
    header_qr_candidate_count: int
    non_title_font_points: float
    title_font_points_before: float
    title_font_points_after: float
    extra_trailing_paragraph_count: int
    qa_index_sha256: str
    page_sha256s: tuple[str, ...]
    master_sha256: str = ""
    calibration_manifest_sha256: str = ""


@dataclass(frozen=True, slots=True)
class AudioRenderEvidence:
    generator_version: str
    duration_seconds: float
    segment_count: int
    mp3_completed: bool


class RenderBackend(Protocol):
    def render_word(
        self,
        draft: BriefingDraft,
        *,
        output_docx: Path,
        output_qa_pdf: Path,
        output_qa_directory: Path,
        output_qa_index: Path,
    ) -> WordRenderEvidence: ...

    def render_audio(
        self,
        draft: BriefingDraft,
        script: str,
        *,
        output_wav: Path,
        output_srt: Path,
        output_txt: Path,
        output_metadata: Path,
        output_mp3: Path,
    ) -> AudioRenderEvidence: ...


@dataclass(frozen=True, slots=True)
class LocalRenderBackend:
    config: BriefingConfig
    patch_adapter: WindowsWordAdapter
    render_adapter: WindowsWordAdapter
    speech_adapter: WindowsMediaSpeechAdapter

    @classmethod
    def from_config(
        cls,
        config: BriefingConfig,
        *,
        scripts_root: Path,
    ) -> LocalRenderBackend:
        root = scripts_root.expanduser().resolve()
        return cls(
            config=config,
            patch_adapter=WindowsWordAdapter(
                script_path=root / "patch_list_template.ps1"
            ),
            render_adapter=WindowsWordAdapter(
                script_path=root / "render_list_template.ps1"
            ),
            speech_adapter=WindowsMediaSpeechAdapter(
                script_path=root / "synthesize_yating.ps1"
            ),
        )

    def render_word(
        self,
        draft: BriefingDraft,
        *,
        output_docx: Path,
        output_qa_pdf: Path,
        output_qa_directory: Path,
        output_qa_index: Path,
    ) -> WordRenderEvidence:
        built = build_list_word(
            draft,
            template_path=self.config.master_path,
            output_docx=output_docx,
            master_sha256=self.config.master_sha256,
            calibration_manifest_sha256=(
                self.config.calibration_manifest_sha256
            ),
            normalized_structure_fingerprint=(
                self.config.master_structure_fingerprint
            ),
            layout_profiles=self.config.layout_profiles,
            expected_source_header_qr_candidate_count=(
                self.config.source_header_qr_candidate_count
            ),
            adapter=self.patch_adapter,
        )
        required_text = tuple(
            dict.fromkeys(
                (
                    draft.product.code,
                    *(flight.number for flight in draft.flights if flight.number),
                )
            )
        )
        qa = render_list_word_for_qa(
            built.docx_path,
            output_pdf=output_qa_pdf,
            output_png_directory=output_qa_directory,
            output_qa_index=output_qa_index,
            expected_page_count=built.computed_page_count,
            required_text=required_text,
            continuation_required_text=(
                draft.product.code,
                "日期",
                "行程簡介",
                "飯店名稱",
                "飯店電話",
                "早",
                "午",
                "晚",
            ),
            day_page_map=built.day_page_map,
            day_tokens={
                day.number: format_list_day_date(day.date)
                for day in draft.days
                if day.date
            },
            adapter=self.render_adapter,
            pdftoppm_path=self.config.pdftoppm_path,
        )
        return WordRenderEvidence(
            generator_version=built.generator_version,
            page_count=qa.pdf_inspection.page_count,
            qr_image_count=qa.pdf_inspection.image_count,
            header_qr_candidate_count=(
                built.output_header_qr_candidate_count
            ),
            non_title_font_points=built.non_title_font_points,
            title_font_points_before=built.title_font_points_before,
            title_font_points_after=built.title_font_points_after,
            extra_trailing_paragraph_count=(
                built.extra_trailing_paragraph_count
            ),
            qa_index_sha256=qa.qa_index_sha256,
            page_sha256s=tuple(
                _sha256_file(path) for path in qa.png_paths
            ),
            master_sha256=self.config.master_sha256,
            calibration_manifest_sha256=(
                self.config.calibration_manifest_sha256
            ),
        )

    def render_audio(
        self,
        draft: BriefingDraft,
        script: str,
        *,
        output_wav: Path,
        output_srt: Path,
        output_txt: Path,
        output_metadata: Path,
        output_mp3: Path,
    ) -> AudioRenderEvidence:
        del draft
        narration = narration_text_for_tts(script)
        plan = segment_narration(narration)
        with tempfile.TemporaryDirectory(
            prefix="easytravel-briefing-metadata-"
        ) as temporary:
            temporary_metadata = Path(temporary) / "audio-metadata.json"
            built = synthesize_yating(
                plan,
                output_wav=output_wav,
                output_srt=output_srt,
                output_txt=output_txt,
                output_metadata=temporary_metadata,
                adapter=self.speech_adapter,
                timeout_seconds=300,
            )
            metadata = _load_audio_metadata(temporary_metadata)
            mp3_completed = False
            if self.config.ffmpeg_path is not None:
                mp3 = convert_wav_to_mp3(
                    output_wav,
                    output_mp3=output_mp3,
                    ffmpeg_path=self.config.ffmpeg_path,
                )
                metadata["mp3"] = {
                    "status": "completed",
                    "sha256": mp3.sha256,
                    "byte_count": mp3.byte_count,
                }
                mp3_completed = True
            publish_text(
                output_metadata.parent,
                output_metadata.name,
                json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            )
        return AudioRenderEvidence(
            generator_version="yating/1",
            duration_seconds=built.duration_seconds,
            segment_count=built.segment_count,
            mp3_completed=mp3_completed,
        )


@dataclass(frozen=True, slots=True)
class RenderResult:
    run_directory: Path
    draft: BriefingDraft
    manifest_path: Path
    delivery_paths: tuple[Path, ...]


def prepare_briefing(
    *,
    output_root: Path,
    generated_at: str,
    source_url: str | None = None,
    web_html: str | None = None,
    pdf_path: Path | None = None,
    previous_manifest: Path | None = None,
    op_values: Mapping[str, object] | None = None,
    conflict_decisions: Mapping[str, object] | None = None,
) -> PrepareResult:
    generated = _parse_generated_at(generated_at)
    revision_mode = previous_manifest is not None
    if revision_mode and (source_url is not None or web_html is not None or pdf_path is not None):
        raise BriefingInputError("Manifest revision must not refetch source content")
    if not revision_mode and source_url is None and pdf_path is None:
        raise BriefingInputError("Prepare requires a URL, PDF, or previous manifest")
    if not revision_mode and (op_values is not None or conflict_decisions is not None):
        raise BriefingInputError(
            "OP decisions require the previous manifest being reviewed"
        )
    if source_url is None and web_html is not None:
        raise BriefingInputError("Supplied HTML requires its NewAmazing URL")

    if revision_mode:
        draft = _load_previous_draft(output_root, previous_manifest)
        draft = _apply_decisions(
            draft,
            op_values=op_values,
            conflict_decisions=conflict_decisions,
        )
        draft = replace(
            draft,
            generated_at=generated_at,
            artifacts=(),
            narration_script_sha256="",
        ).with_recomputed_id()
    else:
        draft = _prepare_from_sources(
            generated_at=generated_at,
            source_url=source_url,
            web_html=web_html,
            pdf_path=pdf_path,
        )

    run = create_run_directory(
        output_root,
        product_code=draft.product.code,
        timestamp=generated.strftime("%Y%m%dT%H%M%S%z"),
    )
    review_path = publish_text(run, "review.md", render_review(draft))
    narration = build_narration_input(draft)
    narration_path = publish_text(
        run,
        "narration-input.json",
        dumps_narration_input(narration) + "\n",
    )
    artifacts = _prepare_artifacts(run, draft.product.code)
    final_draft = replace(draft, artifacts=artifacts)
    manifest_path = write_manifest(run, final_draft)
    return PrepareResult(
        run_directory=run,
        draft=final_draft,
        manifest_path=manifest_path,
        review_path=review_path,
        narration_input_path=narration_path,
    )


def check_briefing_script(
    *,
    output_root: Path,
    manifest_path: Path,
    script_path: Path,
) -> ScriptCheckResult:
    run, draft = _load_verified_manifest(output_root, manifest_path)
    script = _read_text_file(script_path, label="Agent narration script")
    narration_input = build_narration_input(draft)
    validation = check_script(narration_input, script)
    report_name = f"script-check-{validation.script_sha256[:12]}.json"
    report = _publish_or_verify_text(
        run,
        report_name,
        dumps_script_validation(validation) + "\n",
    )
    return ScriptCheckResult(
        ready=validation.ready,
        report_path=report,
        validation=validation,
    )


def render_briefing(
    *,
    output_root: Path,
    manifest_path: Path,
    script_path: Path,
    generated_at: str,
    backend: RenderBackend,
    confirm_draft_id: str | None = None,
) -> RenderResult:
    generated = _parse_generated_at(generated_at)
    source_run, source_draft = _load_verified_manifest(output_root, manifest_path)
    if (
        confirm_draft_id is not None
        and source_draft.status is not DraftStatus.DRAFT_READY
    ):
        raise BriefingInputError("Confirmation requires a successful DRAFT render")
    if confirm_draft_id is None:
        _validate_renderable_source_state(source_draft)
    script = _read_text_file(script_path, label="Agent narration script")
    validation = check_script(build_narration_input(source_draft), script)
    if confirm_draft_id is not None:
        if not validation.ready:
            raise BriefingInputError(
                "Narration script must pass check-script before confirmation"
            )
        return _confirm_render(
            output_root=output_root,
            source_run=source_run,
            source_draft=source_draft,
            script=script,
            validation=validation,
            generated=generated,
            confirm_draft_id=confirm_draft_id,
        )
    return _render_draft(
        output_root=output_root,
        source_draft=source_draft,
        script=script,
        validation=validation,
        generated=generated,
        backend=backend,
    )


def _render_draft(
    *,
    output_root: Path,
    source_draft: BriefingDraft,
    script: str,
    validation: ScriptValidationResult,
    generated: datetime,
    backend: RenderBackend,
) -> RenderResult:
    base_draft = replace(
        source_draft,
        status=(
            DraftStatus.BLOCKED
            if _has_unresolved_blocking_conflicts(source_draft)
            else DraftStatus.DRAFT_READY
        ),
        generated_at=generated.isoformat(),
        artifacts=(),
        narration_script_sha256=validation.script_sha256,
    ).with_recomputed_id()
    validation = check_script(build_narration_input(base_draft), script)
    run = create_run_directory(
        output_root,
        product_code=base_draft.product.code,
        timestamp=generated.strftime("%Y%m%dT%H%M%S%z"),
    )
    prefix = f"DRAFT_{base_draft.product.code}"
    paths = _render_paths(run, prefix)
    artifacts: list[Artifact] = []
    errors: list[dict[str, str]] = []
    narration_input = build_narration_input(base_draft)
    narration_path = publish_text(
        run,
        "narration-input.json",
        dumps_narration_input(narration_input) + "\n",
    )
    script_check_path = publish_text(
        run,
        "script-check.json",
        dumps_script_validation(validation) + "\n",
    )
    for kind, path in (
        ("narration_input", narration_path),
        ("script_check", script_check_path),
    ):
        artifacts.append(
            artifact_record(
                run,
                kind=kind,
                expected_name=path.name,
                status="completed",
                generator_version=WORKFLOW_VERSION,
            )
        )
    word_evidence = None
    word_accepted = False
    if _has_unresolved_blocking_conflicts(base_draft):
        errors.append(
            {
                "stage": "word",
                "code": "UNRESOLVED_CONFLICTS",
                "message": "Word render requires resolved blocking conflicts",
            }
        )
    else:
        try:
            word_evidence = backend.render_word(
                base_draft,
                output_docx=paths["word"],
                output_qa_pdf=paths["word_qa_pdf"],
                output_qa_directory=paths["word_qa_directory"],
                output_qa_index=paths["word_qa_index"],
            )
            if (
                word_evidence.page_count <= 0
                or not _valid_word_presentation_contract(
                    qr_image_count=word_evidence.qr_image_count,
                    header_qr_candidate_count=(
                        word_evidence.header_qr_candidate_count
                    ),
                    non_title_font_points=(
                        word_evidence.non_title_font_points
                    ),
                    title_font_points_before=(
                        word_evidence.title_font_points_before
                    ),
                    title_font_points_after=(
                        word_evidence.title_font_points_after
                    ),
                    extra_trailing_paragraph_count=(
                        word_evidence.extra_trailing_paragraph_count
                    ),
                )
                or len(word_evidence.page_sha256s)
                != word_evidence.page_count
                or not _valid_sha256_or_legacy_empty(
                    word_evidence.master_sha256
                )
                or not _valid_sha256_or_legacy_empty(
                    word_evidence.calibration_manifest_sha256
                )
            ):
                raise ValueError(
                    "Word QA evidence did not prove normalized QR-free output"
                )
            page_paths = tuple(
                paths["word_qa_directory"]
                / f"page-{number:03d}.png"
                for number in range(1, word_evidence.page_count + 1)
            )
            _require_nonempty_files(
                paths["word"],
                paths["word_qa_pdf"],
                paths["word_qa_index"],
                *page_paths,
            )
            _validate_word_qa_index(
                paths["word_qa_index"],
                page_paths=page_paths,
                evidence=word_evidence,
            )
            _write_word_render_evidence(
                paths["word_evidence"],
                evidence=word_evidence,
            )
            word_accepted = True
        except (BriefingCliError, OSError, ValueError) as error:
            errors.append(_safe_render_error("word", error))
    artifacts.extend(
        _word_artifacts(
            run,
            paths,
            word_evidence,
            accepted=word_accepted,
        )
    )

    audio_evidence = None
    audio_accepted = False
    if not validation.ready:
        errors.append(
            {
                "stage": "audio",
                "code": "SCRIPT_REVIEW_REQUIRED",
                "message": "Audio render requires a script that passes check-script",
            }
        )
    else:
        try:
            audio_evidence = backend.render_audio(
                base_draft,
                script,
                output_wav=paths["audio_wav"],
                output_srt=paths["subtitle"],
                output_txt=paths["transcript"],
                output_metadata=paths["audio_metadata"],
                output_mp3=paths["audio_mp3"],
            )
            duration = validate_audio_duration(
                audio_evidence.duration_seconds,
                revision_count=1,
            )
            if duration.status != "accepted" or audio_evidence.segment_count <= 0:
                raise ValueError(
                    "Audio QA evidence did not pass the final duration contract"
                )
            required_audio_paths = [
                paths["audio_wav"],
                paths["subtitle"],
                paths["transcript"],
                paths["audio_metadata"],
            ]
            if audio_evidence.mp3_completed:
                required_audio_paths.append(paths["audio_mp3"])
            _require_nonempty_files(*required_audio_paths)
            audio_accepted = True
        except (BriefingCliError, OSError, ValueError) as error:
            errors.append(_safe_render_error("audio", error))
    artifacts.extend(
        _audio_artifacts(
            run,
            paths,
            audio_evidence,
            accepted=audio_accepted,
        )
    )

    if errors:
        publish_text(
            run,
            "render-errors.json",
            json.dumps(
                {"schema_version": 1, "status": "blocked", "errors": errors},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
        )
        artifacts.append(
            artifact_record(
                run,
                kind="render_errors",
                expected_name="render-errors.json",
                status="completed",
                generator_version=WORKFLOW_VERSION,
            )
        )
    final_status = DraftStatus.BLOCKED if errors else DraftStatus.DRAFT_READY
    review_draft = replace(
        base_draft,
        status=final_status,
        artifacts=tuple(artifacts),
    )
    review_path = publish_text(run, "review.md", render_review(review_draft))
    artifacts.insert(
        0,
        artifact_record(
            run,
            kind="review",
            expected_name=review_path.name,
            status="completed",
            generator_version=WORKFLOW_VERSION,
        ),
    )
    final_draft = replace(
        base_draft,
        status=final_status,
        artifacts=tuple(artifacts),
    )
    manifest = write_manifest(run, final_draft)
    return RenderResult(
        run_directory=run,
        draft=final_draft,
        manifest_path=manifest,
        delivery_paths=_completed_delivery_paths(run, final_draft.artifacts),
    )


def _confirm_render(
    *,
    output_root: Path,
    source_run: Path,
    source_draft: BriefingDraft,
    script: str,
    validation: ScriptValidationResult,
    generated: datetime,
    confirm_draft_id: str,
) -> RenderResult:
    if source_draft.status is not DraftStatus.DRAFT_READY:
        raise BriefingInputError("Confirmation requires a successful DRAFT render")
    if confirm_draft_id != source_draft.draft_id:
        raise BriefingInputError("Confirmation draft ID does not match the manifest")
    if validation.script_sha256 != source_draft.narration_script_sha256:
        raise BriefingInputError("Confirmation script does not match the DRAFT render")
    if any(
        conflict.severity == "blocking" and not conflict.decision.strip()
        for conflict in source_draft.conflicts
    ):
        raise BriefingInputError("Confirmation contains unresolved blocking conflicts")
    fields = {field.name: field for field in source_draft.op_fields}
    if (
        set(REQUIRED_OP_FIELD_NAMES) - set(fields)
        or any(
            not fields[name].confirmed or fields[name].highlight == "yellow"
            for name in REQUIRED_OP_FIELD_NAMES
        )
        or not source_draft.product.region
    ):
        raise BriefingInputError("Confirmation contains unresolved OP fields")
    if (
        not source_draft.product.departure_date.strip()
        or not source_draft.product.return_date.strip()
        or any(not day.date.strip() for day in source_draft.days)
    ):
        raise BriefingInputError("Confirmation contains unresolved source dates")
    static_required_kinds = {
        "word",
        "word_evidence",
        "word_qa",
        "word_qa_index",
        "audio_wav",
        "audio_mp3",
        "transcript",
        "subtitle",
        "audio_metadata",
    }
    completed = {
        artifact.kind: artifact
        for artifact in source_draft.artifacts
        if artifact.status == "completed"
    }
    if "word_qa_png" in completed and "word_qa_index" not in completed:
        raise BriefingInputError(
            "LEGACY_LIST_QA_REQUIRES_RERENDER: rerender LIST QA pages"
        )
    page_kinds = tuple(
        sorted(
            kind
            for kind in completed
            if kind.startswith("word_qa_page_")
        )
    )
    expected_page_kinds = tuple(
        f"word_qa_page_{number:03d}"
        for number in range(1, len(page_kinds) + 1)
    )
    if (
        not static_required_kinds <= set(completed)
        or not page_kinds
        or page_kinds != expected_page_kinds
    ):
        raise BriefingInputError("Confirmation requires completed Word and audio QA")
    _validate_recorded_word_qa_artifacts(
        source_run,
        completed=completed,
        page_kinds=page_kinds,
    )
    _validate_recorded_word_evidence(
        source_run,
        completed=completed,
        page_kinds=page_kinds,
    )
    required_kinds = static_required_kinds | set(page_kinds)

    run = create_run_directory(
        output_root,
        product_code=source_draft.product.code,
        timestamp=generated.strftime("%Y%m%dT%H%M%S%z"),
    )
    copied: list[Artifact] = []
    for kind in sorted(required_kinds):
        source = completed[kind]
        final_name = source.expected_path.removeprefix("DRAFT_")
        copy_artifact(source_run / source.actual_path, run, final_name)
        copied.append(
            artifact_record(
                run,
                kind=kind,
                expected_name=final_name,
                status="completed",
                generator_version=source.generator_version,
            )
        )
    confirmed_base = replace(
        source_draft,
        status=DraftStatus.CONFIRMED,
        artifacts=(),
    )
    review_path = publish_text(run, "review.md", render_review(confirmed_base))
    narration_path = publish_text(
        run,
        "narration-input.json",
        dumps_narration_input(build_narration_input(confirmed_base)) + "\n",
    )
    script_check_path = publish_text(
        run,
        "script-check.json",
        dumps_script_validation(validation) + "\n",
    )
    for kind, path in (
        ("review", review_path),
        ("narration_input", narration_path),
        ("script_check", script_check_path),
    ):
        copied.append(
            artifact_record(
                run,
                kind=kind,
                expected_name=path.name,
                status="completed",
                generator_version=WORKFLOW_VERSION,
            )
        )
    confirmed = replace(confirmed_base, artifacts=tuple(copied))
    manifest = write_manifest(run, confirmed)
    return RenderResult(
        run_directory=run,
        draft=confirmed,
        manifest_path=manifest,
        delivery_paths=_completed_delivery_paths(run, confirmed.artifacts),
    )


def _prepare_from_sources(
    *,
    generated_at: str,
    source_url: str | None,
    web_html: str | None,
    pdf_path: Path | None,
) -> BriefingDraft:
    if source_url is not None:
        source_url = validate_newamazing_url(source_url).value
    failures: list[tuple[str, BriefingCliError]] = []
    pdf = None
    if pdf_path is not None:
        try:
            validated_pdf = validate_pdf_input(pdf_path)
            pdf = parse_pdf_itinerary_pages(
                extract_pdf_pages(validated_pdf),
                source_path=validated_pdf.path.name,
                pdf_sha256=validated_pdf.sha256,
                retrieved_at=generated_at,
            )
        except BriefingCliError as error:
            if source_url is None:
                raise
            failures.append(("PDF_SOURCE_FAILED", error))

    web = None
    if source_url is not None:
        try:
            if web_html is None:
                fetched = fetch_newamazing_html(source_url)
                source_url = fetched.source_url
                web_html = fetched.html
            web = parse_newamazing_html(
                web_html,
                source_url=source_url,
                retrieved_at=generated_at,
            )
        except BriefingCliError as error:
            if pdf is None:
                if failures:
                    raise BriefingSourceError(
                        "All supplied briefing sources failed validation"
                    ) from error
                raise
            failures.append(("WEB_SOURCE_FAILED", error))

    draft = merge_briefing_sources(
        generated_at=generated_at,
        pdf=pdf,
        web=web,
    )
    if not failures:
        return draft
    warnings = tuple(
        DraftWarning(
            code=code,
            message=_safe_source_failure_message(code, error),
        )
        for code, error in failures
    )
    return replace(draft, warnings=(*draft.warnings, *warnings)).with_recomputed_id()


def _apply_decisions(
    draft: BriefingDraft,
    *,
    op_values: Mapping[str, object] | None,
    conflict_decisions: Mapping[str, object] | None,
) -> BriefingDraft:
    if op_values is None and conflict_decisions is None:
        raise BriefingInputError("Manifest revision requires an OP decision")
    updated = draft
    expected_draft_id = draft.draft_id
    for kind, payload in (
        ("conflict decisions", conflict_decisions),
        ("OP values", op_values),
    ):
        if payload is not None and payload.get("draft_id") != expected_draft_id:
            raise BriefingInputError(f"{kind} must match the previous manifest")
    for kind, payload, apply in (
        ("conflict decisions", conflict_decisions, apply_conflict_decisions),
        ("OP values", op_values, apply_op_values),
    ):
        if payload is None:
            continue
        rebound = dict(payload)
        rebound["draft_id"] = updated.draft_id
        updated = apply(updated, rebound)
    return updated


def _load_previous_draft(
    output_root: Path,
    path: Path | None,
) -> BriefingDraft:
    if path is None:
        raise BriefingInputError("Previous manifest path is required")
    try:
        _, draft = _load_verified_manifest(output_root, path)
    except BriefingInputError as error:
        raise BriefingInputError(
            "Previous manifest is invalid, changed, or outside the output root"
        ) from error
    return replace(draft, artifacts=())


def _prepare_artifacts(run: Path, product_code: str) -> tuple[Artifact, ...]:
    prefix = f"DRAFT_{product_code}"
    definitions = (
        ("review", "review.md", "completed", WORKFLOW_VERSION),
        (
            "narration_input",
            "narration-input.json",
            "completed",
            WORKFLOW_VERSION,
        ),
        (
            "word",
            f"{prefix}_說明會資料.docx",
            "missing",
            LIST_WORD_GENERATOR_VERSION,
        ),
        (
            "word_evidence",
            "qa/word-evidence.json",
            "missing",
            LIST_WORD_GENERATOR_VERSION,
        ),
        (
            "word_qa",
            f"{prefix}_Word-QA.pdf",
            "missing",
            LIST_WORD_GENERATOR_VERSION,
        ),
        (
            "word_qa_index",
            "qa/index.json",
            "missing",
            LIST_WORD_GENERATOR_VERSION,
        ),
        ("audio_mp3", f"{prefix}_說明會語音.mp3", "missing", "ffmpeg/unknown"),
        ("audio_wav", f"{prefix}_說明會語音.wav", "missing", "yating/1"),
        ("transcript", f"{prefix}_逐字稿.txt", "missing", "yating/1"),
        ("subtitle", f"{prefix}_字幕.srt", "missing", "yating/1"),
        (
            "audio_metadata",
            f"{prefix}_audio-metadata.json",
            "missing",
            "yating/1",
        ),
    )
    return tuple(
        artifact_record(
            run,
            kind=kind,
            expected_name=name,
            status=status,
            generator_version=version,
        )
        for kind, name, status, version in definitions
    )


def _render_paths(run: Path, prefix: str) -> dict[str, Path]:
    return {
        "word": run / f"{prefix}_說明會資料.docx",
        "word_qa_pdf": run / f"{prefix}_Word-QA.pdf",
        "word_qa_directory": run / "qa",
        "word_qa_index": run / "qa" / "index.json",
        "word_evidence": run / "qa" / "word-evidence.json",
        "audio_mp3": run / f"{prefix}_說明會語音.mp3",
        "audio_wav": run / f"{prefix}_說明會語音.wav",
        "transcript": run / f"{prefix}_逐字稿.txt",
        "subtitle": run / f"{prefix}_字幕.srt",
        "audio_metadata": run / f"{prefix}_audio-metadata.json",
    }


def _word_artifacts(
    run: Path,
    paths: Mapping[str, Path],
    evidence: WordRenderEvidence | None,
    *,
    accepted: bool,
) -> tuple[Artifact, ...]:
    version = evidence.generator_version if evidence else LIST_WORD_GENERATOR_VERSION
    artifacts = [
        artifact_record(
            run,
            kind="word",
            expected_name=paths["word"].name,
            status=(
                "completed"
                if accepted
                else _incomplete_status(paths["word"])
            ),
            generator_version=version,
        ),
        artifact_record(
            run,
            kind="word_evidence",
            expected_name="qa/word-evidence.json",
            status=(
                "completed"
                if accepted
                else _incomplete_status(paths["word_evidence"])
            ),
            generator_version=version,
        ),
        artifact_record(
            run,
            kind="word_qa",
            expected_name=paths["word_qa_pdf"].name,
            status=(
                "completed"
                if accepted
                else _incomplete_status(paths["word_qa_pdf"])
            ),
            generator_version=version,
        ),
        artifact_record(
            run,
            kind="word_qa_index",
            expected_name="qa/index.json",
            status=(
                "completed"
                if accepted
                else _incomplete_status(paths["word_qa_index"])
            ),
            generator_version=version,
        ),
    ]
    page_count = evidence.page_count if evidence else 0
    for number in range(1, page_count + 1):
        page = paths["word_qa_directory"] / f"page-{number:03d}.png"
        artifacts.append(
            artifact_record(
                run,
                kind=f"word_qa_page_{number:03d}",
                expected_name=f"qa/page-{number:03d}.png",
                status=(
                    "completed"
                    if accepted
                    else _incomplete_status(page)
                ),
                generator_version=version,
            )
        )
    return tuple(artifacts)


def _audio_artifacts(
    run: Path,
    paths: Mapping[str, Path],
    evidence: AudioRenderEvidence | None,
    *,
    accepted: bool,
) -> tuple[Artifact, ...]:
    version = evidence.generator_version if evidence else "yating/1"
    definitions = (
        ("audio_wav", "audio_wav"),
        ("subtitle", "subtitle"),
        ("transcript", "transcript"),
        ("audio_metadata", "audio_metadata"),
        ("audio_mp3", "audio_mp3"),
    )
    return tuple(
        artifact_record(
            run,
            kind=kind,
            expected_name=paths[path_key].name,
            status=(
                "completed"
                if accepted
                and (path_key != "audio_mp3" or evidence.mp3_completed)
                else _incomplete_status(paths[path_key])
            ),
            generator_version=version,
        )
        for kind, path_key in definitions
    )


def _completed_delivery_paths(
    run: Path,
    artifacts: tuple[Artifact, ...],
) -> tuple[Path, ...]:
    delivery_kinds = {
        "word",
        "audio_mp3",
        "audio_wav",
        "transcript",
        "subtitle",
    }
    return tuple(
        run / artifact.actual_path
        for artifact in artifacts
        if (
            artifact.kind in delivery_kinds
            and artifact.status == "completed"
            and artifact.actual_path
        )
    )


def _safe_render_error(stage: str, error: BaseException) -> dict[str, object]:
    code = error.code if isinstance(error, BriefingCliError) else "VALIDATION_FAILED"
    message = (
        "Word rendering or QA did not complete"
        if stage == "word"
        else "Audio rendering or QA did not complete"
    )
    result: dict[str, object] = {
        "stage": stage,
        "code": code,
        "message": message,
        "exception_type": type(error).__name__,
    }
    if isinstance(error, BriefingCliError):
        safe_details = _private_safe_exception_details(error.details)
        if safe_details:
            result["details"] = safe_details
    return result


def _private_safe_exception_details(
    details: Mapping[str, object],
) -> dict[str, object]:
    scalar_keys = {
        "adapter_code",
        "chunk_count",
        "chunk_index",
        "fallback_attempted",
        "hresult",
        "owned_word_process_found",
        "owned_word_process_stopped",
        "retry_attempted",
        "return_code",
        "stage",
        "voice",
    }
    result = {
        key: value
        for key, value in details.items()
        if key in scalar_keys and isinstance(value, (bool, int, str))
    }
    for key in ("wav", "bookmarks"):
        value = details.get(key)
        if not isinstance(value, Mapping):
            continue
        status = {
            child_key: child_value
            for child_key, child_value in value.items()
            if child_key in {"exists", "byte_count"}
            and isinstance(child_value, (bool, int))
        }
        if status:
            result[key] = status
    return result


def _incomplete_status(path: Path) -> str:
    return "blocked" if path.is_file() else "missing"


def _has_unresolved_blocking_conflicts(draft: BriefingDraft) -> bool:
    return any(
        conflict.severity == "blocking" and not conflict.decision.strip()
        for conflict in draft.conflicts
    )


def _require_nonempty_files(*paths: Path) -> None:
    if any(not path.is_file() or path.stat().st_size <= 0 for path in paths):
        raise ValueError("Render backend reported success without required artifacts")


def _validate_word_qa_index(
    index_path: Path,
    *,
    page_paths: tuple[Path, ...],
    evidence: WordRenderEvidence,
) -> None:
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Word QA index is not valid UTF-8 JSON") from error
    expected_keys = {
        "schema_version",
        "page_count",
        "pages",
        "day_page_map",
    }
    if (
        not isinstance(payload, dict)
        or set(payload) != expected_keys
        or payload.get("schema_version") != 2
        or payload.get("page_count") != evidence.page_count
        or not isinstance(payload.get("pages"), list)
        or len(payload["pages"]) != evidence.page_count
        or not isinstance(payload.get("day_page_map"), list)
        or _sha256_file(index_path) != evidence.qa_index_sha256
    ):
        raise ValueError("Word QA index does not match render evidence")
    expected_names = tuple(
        f"page-{number:03d}.png"
        for number in range(1, evidence.page_count + 1)
    )
    observed_names = tuple(
        item.get("relative_path")
        if isinstance(item, dict)
        else None
        for item in payload["pages"]
    )
    observed_hashes = tuple(
        item.get("sha256") if isinstance(item, dict) else None
        for item in payload["pages"]
    )
    actual_hashes = tuple(_sha256_file(path) for path in page_paths)
    if (
        observed_names != expected_names
        or observed_hashes != evidence.page_sha256s
        or actual_hashes != evidence.page_sha256s
    ):
        raise ValueError("Word QA page set does not match its index")


def _validate_recorded_word_qa_artifacts(
    run: Path,
    *,
    completed: Mapping[str, Artifact],
    page_kinds: tuple[str, ...],
) -> None:
    index_record = completed["word_qa_index"]
    index_path = run / index_record.actual_path
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise BriefingInputError("Word QA index is invalid or changed") from error
    expected_keys = {
        "schema_version",
        "page_count",
        "pages",
        "day_page_map",
    }
    pages = payload.get("pages") if isinstance(payload, dict) else None
    day_map = payload.get("day_page_map") if isinstance(payload, dict) else None
    if (
        not isinstance(payload, dict)
        or set(payload) != expected_keys
        or payload.get("schema_version") != 2
        or payload.get("page_count") != len(page_kinds)
        or not isinstance(pages, list)
        or len(pages) != len(page_kinds)
        or not isinstance(day_map, list)
    ):
        raise BriefingInputError(
            "Word QA index does not match recorded page artifacts"
        )
    for number, (kind, page) in enumerate(
        zip(page_kinds, pages, strict=True), start=1
    ):
        record = completed[kind]
        expected_name = f"page-{number:03d}.png"
        expected_path = f"qa/{expected_name}"
        if (
            not isinstance(page, dict)
            or set(page)
            != {
                "page_number",
                "relative_path",
                "sha256",
                "required_text_check",
            }
            or page.get("page_number") != number
            or page.get("relative_path") != expected_name
            or page.get("sha256") != record.sha256
            or page.get("required_text_check") is not True
            or record.expected_path != expected_path
            or record.actual_path != expected_path
        ):
            raise BriefingInputError(
                "Word QA index does not match recorded page artifacts"
            )
    expected_days = tuple(range(1, len(day_map) + 1))
    observed_days = tuple(
        item.get("day_number") if isinstance(item, dict) else None
        for item in day_map
    )
    if observed_days != expected_days or any(
        set(item) != {"day_number", "page_number"}
        or isinstance(item.get("page_number"), bool)
        or not isinstance(item.get("page_number"), int)
        or not 1 <= item["page_number"] <= len(page_kinds)
        for item in day_map
        if isinstance(item, dict)
    ) or any(not isinstance(item, dict) for item in day_map):
        raise BriefingInputError(
            "Word QA index does not match recorded day mapping"
        )


def _write_word_render_evidence(
    path: Path,
    *,
    evidence: WordRenderEvidence,
) -> None:
    payload = {
        "schema_version": 3,
        "generator_version": evidence.generator_version,
        "master_sha256": evidence.master_sha256,
        "calibration_manifest_sha256": (
            evidence.calibration_manifest_sha256
        ),
        "page_count": evidence.page_count,
        "qr_image_count": evidence.qr_image_count,
        "header_qr_candidate_count": evidence.header_qr_candidate_count,
        "non_title_font_points": evidence.non_title_font_points,
        "title_font_points_before": evidence.title_font_points_before,
        "title_font_points_after": evidence.title_font_points_after,
        "extra_trailing_paragraph_count": (
            evidence.extra_trailing_paragraph_count
        ),
        "qa_index_sha256": evidence.qa_index_sha256,
        "page_sha256s": list(evidence.page_sha256s),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )


def _validate_recorded_word_evidence(
    run: Path,
    *,
    completed: Mapping[str, Artifact],
    page_kinds: tuple[str, ...],
) -> None:
    record = completed["word_evidence"]
    try:
        payload = json.loads(
            (run / record.actual_path).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise BriefingInputError("Word render evidence is invalid") from error
    expected_keys = {
        "schema_version",
        "generator_version",
        "master_sha256",
        "calibration_manifest_sha256",
        "page_count",
        "qr_image_count",
        "header_qr_candidate_count",
        "non_title_font_points",
        "title_font_points_before",
        "title_font_points_after",
        "extra_trailing_paragraph_count",
        "qa_index_sha256",
        "page_sha256s",
    }
    pages = payload.get("page_sha256s") if isinstance(payload, dict) else None
    if (
        not isinstance(payload, dict)
        or set(payload) != expected_keys
        or payload.get("schema_version") != 3
        or payload.get("generator_version") != record.generator_version
        or not _valid_sha256(payload.get("master_sha256"))
        or not _valid_sha256(payload.get("calibration_manifest_sha256"))
        or payload.get("page_count") != len(page_kinds)
        or not _valid_word_presentation_contract(
            qr_image_count=payload.get("qr_image_count"),
            header_qr_candidate_count=payload.get(
                "header_qr_candidate_count"
            ),
            non_title_font_points=payload.get("non_title_font_points"),
            title_font_points_before=payload.get(
                "title_font_points_before"
            ),
            title_font_points_after=payload.get(
                "title_font_points_after"
            ),
            extra_trailing_paragraph_count=payload.get(
                "extra_trailing_paragraph_count"
            ),
        )
        or not isinstance(pages, list)
        or pages
        != [completed[kind].sha256 for kind in page_kinds]
        or payload.get("qa_index_sha256")
        != completed["word_qa_index"].sha256
    ):
        raise BriefingInputError(
            "Word render evidence does not match recorded artifacts"
        )


def _load_audio_metadata(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Yating metadata is not valid UTF-8 JSON") from error
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("Yating metadata does not match schema version 1")
    return value


def _publish_or_verify_text(run: Path, name: str, content: str) -> Path:
    try:
        return publish_text(run, name, content)
    except FileExistsError:
        existing = (run / name).resolve()
        try:
            if existing.read_text(encoding="utf-8") == content:
                return existing
        except (OSError, UnicodeError) as error:
            raise ValueError("Existing briefing report cannot be verified") from error
        raise ValueError("Existing briefing report content does not match")


def _load_verified_manifest(
    output_root: Path,
    manifest_path: Path,
) -> tuple[Path, BriefingDraft]:
    try:
        run, draft = load_run_manifest(output_root, manifest_path)
        verify_artifacts(run, draft.artifacts)
    except (OSError, UnicodeError, ValueError) as error:
        raise BriefingInputError(
            "Briefing manifest or recorded artifacts are invalid or changed"
        ) from error
    return run, draft


def _safe_source_failure_message(
    code: str,
    error: BriefingCliError,
) -> str:
    del error
    if code == "PDF_SOURCE_FAILED":
        return "PDF source failed validation; the valid web source was retained"
    return "Web source failed validation; the valid PDF source was retained"


def _validate_renderable_source_state(draft: BriefingDraft) -> None:
    if draft.status is DraftStatus.CONFIRMED:
        raise BriefingInputError("Confirmed briefing state cannot be rendered as a draft")
    if draft.status is not DraftStatus.BLOCKED:
        return
    if _has_unresolved_blocking_conflicts(draft):
        return
    failed_artifacts = {
        artifact.kind
        for artifact in draft.artifacts
        if artifact.status in {"blocked", "missing"}
    }
    render_kinds = {
        "word",
        "word_qa",
        "word_qa_index",
        "word_evidence",
        "audio_wav",
        "audio_mp3",
        "transcript",
        "subtitle",
        "audio_metadata",
    }
    render_kinds.update(
        kind
        for kind in failed_artifacts
        if kind.startswith("word_qa_page_")
    )
    if failed_artifacts & render_kinds:
        return
    raise BriefingInputError("Blocked briefing state has no recoverable render blocker")


def _parse_generated_at(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise BriefingInputError("generated_at must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise BriefingInputError("generated_at must include a timezone offset")
    return parsed


def _read_text_file(path: Path, *, label: str) -> str:
    source = path.expanduser().resolve()
    if not source.is_file():
        raise BriefingInputError(f"{label} was not found")
    try:
        value = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise BriefingInputError(f"{label} must be readable UTF-8 text") from error
    if not value.strip():
        raise BriefingInputError(f"{label} must not be empty")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_sha256_or_legacy_empty(value: str) -> bool:
    return value == "" or (
        len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
        and value != "0" * 64
    )


def _valid_sha256(value: object) -> bool:
    return isinstance(value, str) and _valid_sha256_or_legacy_empty(value) and bool(value)


def _valid_word_presentation_contract(
    *,
    qr_image_count: object,
    header_qr_candidate_count: object,
    non_title_font_points: object,
    title_font_points_before: object,
    title_font_points_after: object,
    extra_trailing_paragraph_count: object,
) -> bool:
    integer_zeroes = (
        qr_image_count,
        header_qr_candidate_count,
        extra_trailing_paragraph_count,
    )
    if any(
        isinstance(value, bool)
        or not isinstance(value, int)
        or value != 0
        for value in integer_zeroes
    ):
        return False
    if (
        isinstance(non_title_font_points, bool)
        or not isinstance(non_title_font_points, (int, float))
        or float(non_title_font_points) != 12.0
    ):
        return False
    if (
        isinstance(title_font_points_before, bool)
        or not isinstance(title_font_points_before, (int, float))
        or float(title_font_points_before) <= 0
    ):
        return False
    return title_font_points_after == title_font_points_before
