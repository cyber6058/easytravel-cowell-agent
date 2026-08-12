import json
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from travel_briefing.artifact_store import (
    artifact_record,
    create_run_directory,
    publish_text,
    write_manifest,
)
from travel_briefing.errors import BriefingInputError, WordGenerationError
from travel_briefing.adapters.pdf_itinerary import PdfPageText
from travel_briefing.models import (
    BriefingDraft,
    DraftWarning,
    DraftStatus,
    Flight,
    ItineraryDay,
    Notice,
    OpField,
    Product,
    SourceEvidence,
    WeatherForecast,
)
from travel_briefing.op_values import REQUIRED_OP_FIELD_NAMES
from travel_briefing.script_policy import build_narration_input, dumps_narration_input
from travel_briefing.serialization import loads_draft
from travel_briefing.workflow import (
    AudioRenderEvidence,
    WordRenderEvidence,
    check_briefing_script,
    prepare_briefing,
    render_briefing,
)


FIXTURES = Path(__file__).parents[2] / "fixtures" / "travel_briefing"
SOURCE_URL = (
    "https://www.newamazing.com.tw/GroupDetail.asp?GroupNo=OSA-SYN-260901"
)


def test_prepare_from_supplied_html_creates_a_new_reviewable_version(tmp_path):
    html_path = FIXTURES / "synthetic_newamazing_groupdetail.html"

    result = prepare_briefing(
        output_root=tmp_path / "briefings",
        generated_at="2026-08-12T15:30:00+08:00",
        source_url=SOURCE_URL,
        web_html=html_path.read_text(encoding="utf-8"),
    )

    assert result.run_directory == (
        tmp_path
        / "briefings"
        / "OSA-SYN-260901"
        / "20260812T153000+0800"
    ).resolve()
    assert result.draft.status.value == "DRAFT_READY"
    assert result.manifest_path == result.run_directory / "manifest.json"
    assert result.review_path == result.run_directory / "review.md"
    assert result.narration_input_path == (
        result.run_directory / "narration-input.json"
    )
    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    artifacts = {
        artifact["kind"]: artifact
        for artifact in payload["data"]["artifacts"]
    }
    assert artifacts["review"]["status"] == "completed"
    assert artifacts["narration_input"]["status"] == "completed"
    assert artifacts["word"]["status"] == "missing"
    assert artifacts["word_evidence"]["status"] == "missing"
    assert artifacts["word_qa"]["status"] == "missing"
    assert artifacts["word_qa_index"]["status"] == "missing"
    assert not any(
        kind.startswith("word_qa_page_") for kind in artifacts
    )
    assert artifacts["audio_wav"]["status"] == "missing"
    assert artifacts["audio_metadata"]["status"] == "missing"
    assert not any(
        path.suffix.casefold() in {".html", ".xml"}
        for path in result.run_directory.iterdir()
    )
    assert SOURCE_URL in result.review_path.read_text(encoding="utf-8")
    assert "<html" not in result.manifest_path.read_text(encoding="utf-8").casefold()


def test_prepare_applies_only_current_draft_bound_op_values(tmp_path):
    html = (FIXTURES / "synthetic_newamazing_groupdetail.html").read_text(
        encoding="utf-8"
    )
    first = prepare_briefing(
        output_root=tmp_path / "briefings",
        generated_at="2026-08-12T15:30:00+08:00",
        source_url=SOURCE_URL,
        web_html=html,
    )
    op_values = {
        "draft_id": first.draft.draft_id,
        "values": {"meeting_time": "06:30"},
    }

    second = prepare_briefing(
        output_root=tmp_path / "briefings",
        generated_at="2026-08-12T15:31:00+08:00",
        previous_manifest=first.manifest_path,
        op_values=op_values,
    )

    assert second.draft.draft_id != first.draft.draft_id
    meeting_time = next(
        field for field in second.draft.op_fields if field.name == "meeting_time"
    )
    assert meeting_time.value == "06:30"
    assert meeting_time.confirmed is True
    assert first.manifest_path.is_file()

    other = prepare_briefing(
        output_root=tmp_path / "briefings",
        generated_at="2026-08-12T15:32:00+08:00",
        source_url=SOURCE_URL,
        web_html=html.replace("合成大阪五日", "合成大阪精選五日"),
    )
    with pytest.raises(BriefingInputError, match="[Pp]revious manifest"):
        prepare_briefing(
            output_root=tmp_path / "briefings",
            generated_at="2026-08-12T15:33:00+08:00",
            previous_manifest=other.manifest_path,
            op_values=op_values,
        )


def test_prepare_keeps_valid_web_when_supplied_pdf_cannot_be_read(tmp_path):
    html = (FIXTURES / "synthetic_newamazing_groupdetail.html").read_text(
        encoding="utf-8"
    )

    result = prepare_briefing(
        output_root=tmp_path / "briefings",
        generated_at="2026-08-12T15:30:00+08:00",
        source_url=SOURCE_URL,
        web_html=html,
        pdf_path=tmp_path / "missing.pdf",
    )

    assert result.draft.status is DraftStatus.DRAFT_READY
    assert {warning.code for warning in result.draft.warnings} >= {
        "PDF_SOURCE_FAILED"
    }
    assert [source.kind for source in result.draft.sources] == [
        "newamazing_html"
    ]


def test_prepare_keeps_valid_pdf_when_supplied_web_contract_changes(
    monkeypatch,
    tmp_path,
):
    fixture = FIXTURES / "synthetic_itinerary_pages.txt"
    pages = tuple(
        PdfPageText(page_number=int(number), text=text.strip())
        for number, text in (
            section.split(" ===\n", 1)
            for section in fixture.read_text(encoding="utf-8").split("=== PAGE ")[1:]
        )
    )
    pdf = tmp_path / "synthetic.pdf"
    pdf.write_bytes(b"%PDF-synthetic")
    monkeypatch.setattr(
        "travel_briefing.workflow.extract_pdf_pages",
        lambda _: pages,
    )

    result = prepare_briefing(
        output_root=tmp_path / "briefings",
        generated_at="2026-08-12T15:30:00+08:00",
        source_url=SOURCE_URL,
        web_html="<html><body>changed</body></html>",
        pdf_path=pdf,
    )

    assert result.draft.status is DraftStatus.DRAFT_READY
    assert {warning.code for warning in result.draft.warnings} >= {
        "WEB_SOURCE_FAILED",
        "WEB_NOTICES_MISSING",
    }
    assert all(source.kind == "pdf_page" for source in result.draft.sources)


def test_prepare_never_uses_pdf_to_bypass_the_url_allowlist(tmp_path):
    pdf = tmp_path / "synthetic.pdf"
    pdf.write_bytes(b"%PDF-synthetic")

    with pytest.raises(BriefingInputError, match="allowlisted"):
        prepare_briefing(
            output_root=tmp_path / "briefings",
            generated_at="2026-08-12T15:30:00+08:00",
            source_url="https://example.invalid/private",
            web_html="<html>synthetic</html>",
            pdf_path=pdf,
        )


def test_check_script_is_manifest_bound_and_publishes_only_a_safe_report(tmp_path):
    html = (FIXTURES / "synthetic_newamazing_groupdetail.html").read_text(
        encoding="utf-8"
    )
    prepared = prepare_briefing(
        output_root=tmp_path / "briefings",
        generated_at="2026-08-12T15:30:00+08:00",
        source_url=SOURCE_URL,
        web_html=html,
    )
    narration_input = json.loads(
        prepared.narration_input_path.read_text(encoding="utf-8")
    )
    script = "\n".join(
        item["marker"] for item in narration_input["sections"]
    ) + "\n"
    script_path = tmp_path / "agent-script.txt"
    script_path.write_text(script, encoding="utf-8")

    result = check_briefing_script(
        output_root=tmp_path / "briefings",
        manifest_path=prepared.manifest_path,
        script_path=script_path,
    )

    assert result.ready is False
    assert result.report_path.parent == prepared.run_directory
    assert result.report_path.name.startswith("script-check-")
    report_text = result.report_path.read_text(encoding="utf-8")
    assert "REQUIRED_FACT_NOT_PRESERVED" in report_text
    assert "合成大阪五日" not in report_text
    assert not (prepared.run_directory / script_path.name).exists()

    script_path.write_text(script + "changed", encoding="utf-8")
    changed = check_briefing_script(
        output_root=tmp_path / "briefings",
        manifest_path=prepared.manifest_path,
        script_path=script_path,
    )
    assert changed.report_path != result.report_path
    assert result.report_path.is_file()
    assert changed.report_path.is_file()

    repeated = check_briefing_script(
        output_root=tmp_path / "briefings",
        manifest_path=prepared.manifest_path,
        script_path=script_path,
    )
    assert repeated.report_path == changed.report_path


@dataclass
class SyntheticRenderBackend:
    word_calls: int = 0
    audio_calls: int = 0
    fail_word: bool = False
    omit_word_page: bool = False
    omit_audio_metadata: bool = False
    word_page_count: int = 2

    def render_word(
        self,
        draft,
        *,
        output_docx,
        output_qa_pdf,
        output_qa_directory,
        output_qa_index,
    ):
        self.word_calls += 1
        output_docx.write_bytes(b"synthetic verified docx")
        if self.fail_word:
            raise WordGenerationError("Synthetic Word QA failed")
        output_qa_pdf.write_bytes(b"synthetic verified pdf")
        output_qa_directory.mkdir(parents=True, exist_ok=True)
        page_hashes = []
        for page_number in range(1, self.word_page_count + 1):
            path = output_qa_directory / f"page-{page_number:03d}.png"
            if not (
                self.omit_word_page
                and page_number == self.word_page_count
            ):
                content = f"synthetic page {page_number}".encode()
                path.write_bytes(content)
                import hashlib

                page_hashes.append(hashlib.sha256(content).hexdigest())
        output_qa_index.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "page_count": self.word_page_count,
                    "pages": [
                        {
                            "page_number": number,
                            "relative_path": f"page-{number:03d}.png",
                            "sha256": page_hashes[number - 1]
                            if number <= len(page_hashes)
                            else "0" * 64,
                            "required_text_check": True,
                        }
                        for number in range(
                            1, self.word_page_count + 1
                        )
                    ],
                    "day_page_map": [
                        {"day_number": number, "page_number": 1}
                        for number in range(1, draft.product.day_count + 1)
                    ],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        import hashlib

        return WordRenderEvidence(
            generator_version="synthetic-word/2",
            page_count=self.word_page_count,
            qr_image_count=1,
            qa_index_sha256=hashlib.sha256(
                output_qa_index.read_bytes()
            ).hexdigest(),
            page_sha256s=tuple(page_hashes),
            master_sha256="a" * 64,
            calibration_manifest_sha256="b" * 64,
        )

    def render_audio(
        self,
        draft,
        script,
        *,
        output_wav,
        output_srt,
        output_txt,
        output_metadata,
        output_mp3,
    ):
        self.audio_calls += 1
        output_wav.write_bytes(b"synthetic verified wav")
        output_srt.write_text("1\n00:00:00,000 --> 00:07:00,000\nSynthetic\n", encoding="utf-8")
        output_txt.write_text("Synthetic narration\n", encoding="utf-8")
        if not self.omit_audio_metadata:
            output_metadata.write_text('{"synthetic": true}\n', encoding="utf-8")
        output_mp3.write_bytes(b"synthetic verified mp3")
        return AudioRenderEvidence(
            generator_version="synthetic-yating/1",
            duration_seconds=420.0,
            segment_count=8,
            mp3_completed=True,
        )


def test_render_builds_a_new_draft_then_confirms_without_rerunning_generators(
    tmp_path,
):
    output_root = tmp_path / "briefings"
    manifest, script_path = ready_manifest_and_script(output_root, tmp_path)
    backend = SyntheticRenderBackend()

    draft_render = render_briefing(
        output_root=output_root,
        manifest_path=manifest,
        script_path=script_path,
        generated_at="2026-08-12T16:00:00+08:00",
        backend=backend,
    )

    assert draft_render.draft.status is DraftStatus.DRAFT_READY
    assert draft_render.draft.draft_id != loads_manifest_id(manifest)
    assert backend.word_calls == 1
    assert backend.audio_calls == 1
    statuses = {item.kind: item.status for item in draft_render.draft.artifacts}
    assert statuses["word"] == "completed"
    assert statuses["word_evidence"] == "completed"
    assert statuses["word_qa"] == "completed"
    assert statuses["word_qa_index"] == "completed"
    assert statuses["word_qa_page_001"] == "completed"
    assert statuses["word_qa_page_002"] == "completed"
    assert statuses["audio_wav"] == "completed"
    assert statuses["audio_mp3"] == "completed"
    word_evidence = json.loads(
        (
            draft_render.run_directory
            / "qa"
            / "word-evidence.json"
        ).read_text(encoding="utf-8")
    )
    assert word_evidence["master_sha256"] == "a" * 64
    assert word_evidence["calibration_manifest_sha256"] == "b" * 64
    assert word_evidence["page_count"] == 2
    assert word_evidence["qa_index_sha256"]
    script_check = json.loads(
        (draft_render.run_directory / "script-check.json").read_text(
            encoding="utf-8"
        )
    )
    assert script_check["draft_id"] == draft_render.draft.draft_id
    assert all(
        path.name.startswith("DRAFT_")
        for path in draft_render.delivery_paths
    )

    confirmed = render_briefing(
        output_root=output_root,
        manifest_path=draft_render.manifest_path,
        script_path=script_path,
        generated_at="2026-08-12T16:01:00+08:00",
        confirm_draft_id=draft_render.draft.draft_id,
        backend=backend,
    )

    assert confirmed.draft.status is DraftStatus.CONFIRMED
    assert confirmed.draft.draft_id == draft_render.draft.draft_id
    assert backend.word_calls == 1
    assert backend.audio_calls == 1
    assert all(
        not path.name.startswith("DRAFT_")
        for path in confirmed.delivery_paths
    )
    assert all(path.is_file() for path in confirmed.delivery_paths)
    confirmed_artifacts = {
        artifact.kind: artifact for artifact in confirmed.draft.artifacts
    }
    assert {
        "review",
        "narration_input",
        "script_check",
        "word_qa_index",
        "word_evidence",
        "word_qa_page_001",
        "word_qa_page_002",
    } <= set(confirmed_artifacts)
    assert confirmed_artifacts["word_qa_page_002"].status == "completed"
    assert (
        confirmed.run_directory / "qa" / "page-002.png"
    ).is_file()
    assert "`CONFIRMED`" in (
        confirmed.run_directory / "review.md"
    ).read_text(encoding="utf-8")


def test_render_keeps_safe_partial_artifacts_and_blocks_confirmation(tmp_path):
    output_root = tmp_path / "briefings"
    manifest, script_path = ready_manifest_and_script(output_root, tmp_path)
    backend = SyntheticRenderBackend(fail_word=True)

    rendered = render_briefing(
        output_root=output_root,
        manifest_path=manifest,
        script_path=script_path,
        generated_at="2026-08-12T16:00:00+08:00",
        backend=backend,
    )

    statuses = {item.kind: item.status for item in rendered.draft.artifacts}
    assert rendered.draft.status is DraftStatus.BLOCKED
    assert statuses["word"] == "blocked"
    assert statuses["word_qa"] == "missing"
    assert statuses["audio_wav"] == "completed"
    error_report = rendered.run_directory / "render-errors.json"
    assert "WORD_GENERATION_FAILED" in error_report.read_text(encoding="utf-8")
    assert (rendered.run_directory / "DRAFT_SYN-READY-260901_說明會資料.docx").is_file()

    with pytest.raises(BriefingInputError, match="successful DRAFT render"):
        render_briefing(
            output_root=output_root,
            manifest_path=rendered.manifest_path,
            script_path=script_path,
            generated_at="2026-08-12T16:01:00+08:00",
            confirm_draft_id=rendered.draft.draft_id,
            backend=backend,
        )

    recovered_backend = SyntheticRenderBackend()
    recovered = render_briefing(
        output_root=output_root,
        manifest_path=rendered.manifest_path,
        script_path=script_path,
        generated_at="2026-08-12T16:02:00+08:00",
        backend=recovered_backend,
    )
    assert recovered.draft.status is DraftStatus.DRAFT_READY
    assert recovered_backend.word_calls == 1
    assert recovered_backend.audio_calls == 1


def test_render_with_unconfirmed_fields_keeps_word_draft_and_skips_audio(tmp_path):
    output_root = tmp_path / "briefings"
    html = (FIXTURES / "synthetic_newamazing_groupdetail.html").read_text(
        encoding="utf-8"
    )
    prepared = prepare_briefing(
        output_root=output_root,
        generated_at="2026-08-12T15:30:00+08:00",
        source_url=SOURCE_URL,
        web_html=html,
    )
    narration_input = json.loads(
        prepared.narration_input_path.read_text(encoding="utf-8")
    )
    script_path = tmp_path / "unready-script.txt"
    script_path.write_text(
        "\n".join(item["marker"] for item in narration_input["sections"]) + "\n",
        encoding="utf-8",
    )
    backend = SyntheticRenderBackend()

    rendered = render_briefing(
        output_root=output_root,
        manifest_path=prepared.manifest_path,
        script_path=script_path,
        generated_at="2026-08-12T16:00:00+08:00",
        backend=backend,
    )

    statuses = {item.kind: item.status for item in rendered.draft.artifacts}
    assert rendered.draft.status is DraftStatus.BLOCKED
    assert backend.word_calls == 1
    assert backend.audio_calls == 0
    assert statuses["word"] == "completed"
    assert statuses["audio_wav"] == "missing"
    assert "SCRIPT_REVIEW_REQUIRED" in (
        rendered.run_directory / "render-errors.json"
    ).read_text(encoding="utf-8")


def test_render_rejects_an_inconsistent_blocked_source(tmp_path):
    output_root = tmp_path / "briefings"
    manifest, script_path = ready_manifest_and_script(output_root, tmp_path)
    source_run = manifest.parent
    source = loads_draft(manifest.read_text(encoding="utf-8"))
    manifest.unlink()
    (source_run / "manifest.sha256").unlink()
    blocked = replace(
        source,
        status=DraftStatus.BLOCKED,
        warnings=(
            *source.warnings,
            DraftWarning(
                code="SYNTHETIC_BLOCKER",
                message="Synthetic unresolved source blocker",
            ),
        ),
    ).with_recomputed_id()
    manifest = write_manifest(source_run, blocked)

    with pytest.raises(BriefingInputError, match="state"):
        render_briefing(
            output_root=output_root,
            manifest_path=manifest,
            script_path=script_path,
            generated_at="2026-08-12T16:00:00+08:00",
            backend=SyntheticRenderBackend(),
        )


@pytest.mark.parametrize(
    ("backend", "missing_kind"),
    (
        (
            SyntheticRenderBackend(omit_word_page=True),
            "word_qa_page_002",
        ),
        (SyntheticRenderBackend(omit_audio_metadata=True), "audio_metadata"),
    ),
)
def test_render_blocks_when_backend_success_evidence_has_missing_files(
    tmp_path,
    backend,
    missing_kind,
):
    output_root = tmp_path / "briefings"
    manifest, script_path = ready_manifest_and_script(output_root, tmp_path)

    rendered = render_briefing(
        output_root=output_root,
        manifest_path=manifest,
        script_path=script_path,
        generated_at="2026-08-12T16:00:00+08:00",
        backend=backend,
    )

    statuses = {item.kind: item.status for item in rendered.draft.artifacts}
    assert rendered.draft.status is DraftStatus.BLOCKED
    assert statuses[missing_kind] == "missing"


def test_prepare_revision_requires_a_hash_bound_manifest_in_the_same_output_root(
    tmp_path,
):
    html = (FIXTURES / "synthetic_newamazing_groupdetail.html").read_text(
        encoding="utf-8"
    )
    first_root = tmp_path / "first" / "briefings"
    first = prepare_briefing(
        output_root=first_root,
        generated_at="2026-08-12T15:30:00+08:00",
        source_url=SOURCE_URL,
        web_html=html,
    )
    decisions = {
        "draft_id": first.draft.draft_id,
        "values": {"meeting_time": "06:30"},
    }

    with pytest.raises(BriefingInputError, match="[Pp]revious manifest"):
        prepare_briefing(
            output_root=tmp_path / "second" / "briefings",
            generated_at="2026-08-12T15:31:00+08:00",
            previous_manifest=first.manifest_path,
            op_values=decisions,
        )

    original = first.manifest_path.read_text(encoding="utf-8")
    first.manifest_path.write_text(original + " ", encoding="utf-8")
    with pytest.raises(BriefingInputError, match="[Pp]revious manifest"):
        prepare_briefing(
            output_root=first_root,
            generated_at="2026-08-12T15:32:00+08:00",
            previous_manifest=first.manifest_path,
            op_values=decisions,
        )


def test_confirmation_rejects_legacy_single_png_qa_manifest(tmp_path):
    output_root = tmp_path / "briefings"
    manifest, script_path = ready_manifest_and_script(output_root, tmp_path)
    rendered = render_briefing(
        output_root=output_root,
        manifest_path=manifest,
        script_path=script_path,
        generated_at="2026-08-12T16:00:00+08:00",
        backend=SyntheticRenderBackend(),
    )
    run = rendered.run_directory
    source = rendered.draft
    manifest_path = rendered.manifest_path
    manifest_path.unlink()
    (run / "manifest.sha256").unlink()
    legacy = tuple(
        artifact
        for artifact in source.artifacts
        if artifact.kind not in {
            "word_evidence",
            "word_qa_index",
            "word_qa_page_001",
            "word_qa_page_002",
        }
    ) + (
        artifact_record(
            run,
            kind="word_qa_png",
            expected_name="qa/page-001.png",
            status="completed",
            generator_version="list-word/1",
        ),
    )
    legacy_manifest = write_manifest(
        run,
        replace(source, artifacts=legacy),
    )

    with pytest.raises(
        BriefingInputError,
        match="LEGACY_LIST_QA_REQUIRES_RERENDER",
    ):
        render_briefing(
            output_root=output_root,
            manifest_path=legacy_manifest,
            script_path=script_path,
            generated_at="2026-08-12T16:01:00+08:00",
            confirm_draft_id=source.draft_id,
            backend=SyntheticRenderBackend(),
        )


def test_confirmation_rejects_semantically_inconsistent_qa_index(tmp_path):
    output_root = tmp_path / "briefings"
    manifest, script_path = ready_manifest_and_script(output_root, tmp_path)
    rendered = render_briefing(
        output_root=output_root,
        manifest_path=manifest,
        script_path=script_path,
        generated_at="2026-08-12T16:00:00+08:00",
        backend=SyntheticRenderBackend(),
    )
    run = rendered.run_directory
    index_path = run / "qa" / "index.json"
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    payload["pages"][1]["relative_path"] = "page-999.png"
    index_path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    source = rendered.draft
    changed_artifacts = tuple(
        artifact_record(
            run,
            kind=item.kind,
            expected_name=item.expected_path,
            status=item.status,
            generator_version=item.generator_version,
        )
        if item.kind == "word_qa_index"
        else item
        for item in source.artifacts
    )
    rendered.manifest_path.unlink()
    (run / "manifest.sha256").unlink()
    changed = replace(source, artifacts=changed_artifacts).with_recomputed_id()
    changed_manifest = write_manifest(run, changed)

    with pytest.raises(BriefingInputError, match="Word QA index"):
        render_briefing(
            output_root=output_root,
            manifest_path=changed_manifest,
            script_path=script_path,
            generated_at="2026-08-12T16:01:00+08:00",
            confirm_draft_id=changed.draft_id,
            backend=SyntheticRenderBackend(),
        )

def test_prepare_revision_clears_prior_render_artifacts_and_script_binding(tmp_path):
    output_root = tmp_path / "briefings"
    manifest, script_path = ready_manifest_and_script(output_root, tmp_path)
    rendered = render_briefing(
        output_root=output_root,
        manifest_path=manifest,
        script_path=script_path,
        generated_at="2026-08-12T16:00:00+08:00",
        backend=SyntheticRenderBackend(),
    )

    revised = prepare_briefing(
        output_root=output_root,
        generated_at="2026-08-12T16:01:00+08:00",
        previous_manifest=rendered.manifest_path,
        op_values={
            "draft_id": rendered.draft.draft_id,
            "values": {"meeting_time": "07:00"},
        },
    )

    assert revised.draft.narration_script_sha256 == ""
    statuses = {artifact.kind: artifact.status for artifact in revised.draft.artifacts}
    assert statuses["word"] == "missing"
    assert statuses["audio_wav"] == "missing"

def ready_manifest_and_script(output_root: Path, tmp_path: Path):
    source_id = "synthetic-source"
    days = tuple(
        ItineraryDay(
            number=number,
            date=f"2026-09-{number:02d}",
            city="大阪",
            attractions=("大阪城",),
            meals=("早餐", "午餐", "晚餐"),
            hotel="大阪",
            source_ids=(source_id,),
        )
        for number in range(1, 6)
    )
    notices = tuple(
        Notice(category=category, text=text, source_ids=(source_id,))
        for category, text in (
            ("tip", "小費每人每天300元。"),
            ("group_size", "本團共30人。"),
            ("no_leaving_group", "旅途中不可擅自脫隊。"),
            ("bus_hours", "每日巴士行車時間約4小時。"),
            ("insurance", "責任保險每人250萬元。"),
            ("passport_validity", "護照效期須有6個月以上。"),
            ("room_type", "房型以兩人一室為主。"),
            ("vegetarian", "素食旅客請於出發前告知。"),
            ("voltage", "日本電壓為100V。"),
        )
    )
    draft = BriefingDraft.create(
        status=DraftStatus.DRAFT_READY,
        generated_at="2026-08-12T15:59:00+08:00",
        product=Product(
            code="SYN-READY-260901",
            name="合成大阪五日",
            region="大阪",
            day_count=5,
            departure_date="2026-09-01",
            return_date="2026-09-05",
            source_ids=(source_id,),
        ),
        sources=(
            SourceEvidence(
                source_id=source_id,
                kind="synthetic",
                location="synthetic-input",
                sha256="a" * 64,
                retrieved_at="2026-08-12T15:59:00+08:00",
                parser_version="synthetic/1",
            ),
        ),
        flights=(
            Flight(
                date="2026-09-01",
                airline="星宇航空",
                number="JX820",
                origin="TPE",
                destination="KIX",
                departure_time="08:30",
                arrival_time="12:00",
                source_ids=(source_id,),
            ),
            Flight(
                date="2026-09-05",
                airline="星宇航空",
                number="JX821",
                origin="KIX",
                destination="TPE",
                departure_time="13:00",
                arrival_time="15:25",
                source_ids=(source_id,),
            ),
        ),
        days=days,
        notices=notices,
        op_fields=tuple(
            OpField(
                name=name,
                value=f"合成-{name}",
                source="OP",
                confirmed=True,
            )
            for name in REQUIRED_OP_FIELD_NAMES
        ),
        weather=tuple(
            WeatherForecast(
                date=day.date,
                display_city="大阪",
                forecast_area="大阪府",
                condition="晴",
                high_c=30,
                low_c=24,
                precipitation_percent=20,
                issued_at="2026-08-31T17:00:00+09:00",
                retrieved_at="2026-08-31T18:00:00+09:00",
                source_url="https://www.jma.go.jp/synthetic",
                available=True,
            )
            for day in days
        ),
    )
    run = create_run_directory(
        output_root,
        product_code=draft.product.code,
        timestamp="20260812T155900+0800",
    )
    review = publish_text(run, "review.md", "# Synthetic review\n")
    narration = build_narration_input(draft)
    narration_path = publish_text(
        run,
        "narration-input.json",
        dumps_narration_input(narration) + "\n",
    )
    draft = BriefingDraft.create(
        **{
            field: getattr(draft, field)
            for field in draft.__dataclass_fields__
            if field not in {"draft_id", "artifacts"}
        },
        artifacts=(
            artifact_record(
                run,
                kind="review",
                expected_name=review.name,
                status="completed",
                generator_version="synthetic/1",
            ),
            artifact_record(
                run,
                kind="narration_input",
                expected_name=narration_path.name,
                status="completed",
                generator_version="synthetic/1",
            ),
        ),
    )
    manifest = write_manifest(run, draft)
    lines = []
    for section in narration.sections:
        lines.append(section.marker)
        lines.extend(
            fact.protected_text
            for fact in narration.required_facts
            if fact.section_id == section.section_id
        )
    script_path = tmp_path / "ready-script.txt"
    script_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest, script_path


def loads_manifest_id(path: Path) -> str:
    return json.loads(path.read_text(encoding="utf-8"))["data"]["draft_id"]
