import json
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from travel_briefing.config import BriefingConfig
from tests.unit.travel_briefing.test_list_calibration import manifest
from travel_briefing.models import BriefingDraft, DraftStatus, Flight, Product
from travel_briefing.workflow import LocalRenderBackend


def config(tmp_path, *, with_ffmpeg=True):
    master = tmp_path / "LIST-master.docx"
    master.write_bytes(b"synthetic master")
    calibrated = manifest()
    manifest_path = tmp_path / "calibration-manifest.json"
    calibrated_payload = calibrated.to_dict()
    master_hash = hashlib.sha256(master.read_bytes()).hexdigest()
    calibrated_payload["master_sha256"] = master_hash
    manifest_text = json.dumps(
        calibrated_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    manifest_path.write_text(manifest_text, encoding="utf-8")
    return BriefingConfig(
        output_root=tmp_path / "briefings",
        master_path=master,
        calibration_manifest_path=manifest_path,
        master_sha256=master_hash,
        calibration_manifest_sha256=hashlib.sha256(
            manifest_path.read_bytes()
        ).hexdigest(),
        master_structure_fingerprint=(
            calibrated.master_structure_fingerprint
        ),
        source_header_qr_candidate_count=(
            calibrated.source_header_qr_candidate_count
        ),
        layout_profiles=tuple(
            item.to_dict() for item in calibrated.layout_profiles
        ),
        calibration_manifest=type(calibrated).from_dict(calibrated_payload),
        ffmpeg_path=(tmp_path / "ffmpeg.exe") if with_ffmpeg else None,
        pdftoppm_path=tmp_path / "pdftoppm.exe",
    )


def draft():
    return BriefingDraft.create(
        status=DraftStatus.DRAFT_READY,
        generated_at="2026-08-12T15:00:00+08:00",
        product=Product(
            code="SYN-OSA-260901",
            name="合成大阪五日",
            region="大阪",
            day_count=5,
            departure_date="2026-09-01",
            return_date="2026-09-05",
        ),
        flights=(
            Flight(
                date="2026-09-01",
                airline="合成航空",
                number="SY100",
                origin="TPE",
                destination="KIX",
                departure_time="08:00",
                arrival_time="12:00",
            ),
        ),
    )


def backend(value):
    return LocalRenderBackend(
        config=value,
        patch_adapter=object(),
        render_adapter=object(),
        speech_adapter=object(),
    )


def test_local_backend_composes_existing_word_build_and_qa(monkeypatch, tmp_path):
    calls = {}

    def build(source, **kwargs):
        calls["build"] = (source, kwargs)
        kwargs["output_docx"].write_bytes(b"docx")
        return SimpleNamespace(
            docx_path=kwargs["output_docx"],
            generator_version="list-word/2",
            computed_page_count=2,
            day_page_map=(),
        )

    def qa(source, **kwargs):
        calls["qa"] = (source, kwargs)
        kwargs["output_pdf"].write_bytes(b"pdf")
        kwargs["output_png_directory"].mkdir(
            parents=True, exist_ok=True
        )
        page_paths = []
        for number in range(1, 3):
            page = (
                kwargs["output_png_directory"]
                / f"page-{number:03d}.png"
            )
            page.write_bytes(f"png-{number}".encode())
            page_paths.append(page)
        kwargs["output_qa_index"].write_bytes(b"index")
        return SimpleNamespace(
            pdf_inspection=SimpleNamespace(page_count=2, image_count=2),
            qa_index_sha256="a" * 64,
            png_paths=tuple(page_paths),
        )

    monkeypatch.setattr("travel_briefing.workflow.build_list_word", build)
    monkeypatch.setattr("travel_briefing.workflow.render_list_word_for_qa", qa)
    value = config(tmp_path)
    outputs = {
        "output_docx": tmp_path / "draft.docx",
        "output_qa_pdf": tmp_path / "qa.pdf",
        "output_qa_directory": tmp_path / "qa",
        "output_qa_index": tmp_path / "qa" / "index.json",
    }

    evidence = backend(value).render_word(draft(), **outputs)

    assert evidence.page_count == 2
    assert len(evidence.page_sha256s) == 2
    assert evidence.qr_image_count == 2
    assert calls["build"][1]["template_path"] == value.master_path
    assert calls["build"][1]["master_sha256"] == value.master_sha256
    assert calls["build"][1]["calibration_manifest_sha256"] == (
        value.calibration_manifest_sha256
    )
    assert calls["build"][1]["normalized_structure_fingerprint"] == (
        value.master_structure_fingerprint
    )
    assert calls["build"][1]["layout_profiles"] == value.layout_profiles
    assert evidence.master_sha256 == value.master_sha256
    assert evidence.calibration_manifest_sha256 == (
        value.calibration_manifest_sha256
    )
    assert calls["qa"][1]["required_text"] == ("SYN-OSA-260901", "SY100")
    assert calls["qa"][1]["continuation_required_text"] == (
        "SYN-OSA-260901",
        "日期",
        "行程簡介",
        "飯店名稱",
        "飯店電話",
        "早",
        "午",
        "晚",
    )
    assert calls["qa"][1]["pdftoppm_path"] == value.pdftoppm_path


@pytest.mark.parametrize("with_ffmpeg", (True, False))
def test_local_backend_composes_yating_and_records_mp3_availability(
    monkeypatch,
    tmp_path,
    with_ffmpeg,
):
    calls = {"convert": 0}

    def synthesize(plan, **kwargs):
        assert plan == "synthetic-plan"
        kwargs["output_wav"].write_bytes(b"wav")
        kwargs["output_srt"].write_text("synthetic srt\n", encoding="utf-8")
        kwargs["output_txt"].write_text("synthetic text\n", encoding="utf-8")
        kwargs["output_metadata"].write_text(
            json.dumps({"schema_version": 1, "mp3": {"status": "unavailable"}}),
            encoding="utf-8",
        )
        return SimpleNamespace(duration_seconds=420.0, segment_count=3)

    def convert(source, **kwargs):
        calls["convert"] += 1
        kwargs["output_mp3"].write_bytes(b"mp3")
        return SimpleNamespace(
            path=kwargs["output_mp3"],
            sha256="b" * 64,
            byte_count=3,
        )

    monkeypatch.setattr(
        "travel_briefing.workflow.narration_text_for_tts",
        lambda script: "合成口語稿。",
    )
    monkeypatch.setattr(
        "travel_briefing.workflow.segment_narration",
        lambda text: "synthetic-plan",
    )
    monkeypatch.setattr("travel_briefing.workflow.synthesize_yating", synthesize)
    monkeypatch.setattr("travel_briefing.workflow.convert_wav_to_mp3", convert)
    value = config(tmp_path, with_ffmpeg=with_ffmpeg)
    outputs = {
        "output_wav": tmp_path / "draft.wav",
        "output_srt": tmp_path / "draft.srt",
        "output_txt": tmp_path / "draft.txt",
        "output_metadata": tmp_path / "metadata.json",
        "output_mp3": tmp_path / "draft.mp3",
    }

    evidence = backend(value).render_audio(draft(), "agent script", **outputs)

    metadata = json.loads(outputs["output_metadata"].read_text(encoding="utf-8"))
    assert evidence.duration_seconds == 420.0
    assert evidence.segment_count == 3
    assert evidence.mp3_completed is with_ffmpeg
    assert calls["convert"] == int(with_ffmpeg)
    assert metadata["mp3"]["status"] == (
        "completed" if with_ffmpeg else "unavailable"
    )
    assert outputs["output_mp3"].is_file() is with_ffmpeg
