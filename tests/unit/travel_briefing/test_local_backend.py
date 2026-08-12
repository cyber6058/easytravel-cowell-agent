import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from travel_briefing.config import BriefingConfig
from travel_briefing.models import BriefingDraft, DraftStatus, Flight, Product
from travel_briefing.workflow import LocalRenderBackend


def config(tmp_path, *, with_ffmpeg=True):
    return BriefingConfig(
        output_root=tmp_path / "briefings",
        template_path=tmp_path / "LIST.doc",
        template_layout_fingerprint="a" * 64,
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
            generator_version="list-word/1",
        )

    def qa(source, **kwargs):
        calls["qa"] = (source, kwargs)
        kwargs["output_pdf"].write_bytes(b"pdf")
        kwargs["output_png"].write_bytes(b"png")
        return SimpleNamespace(
            pdf_inspection=SimpleNamespace(page_count=1, image_count=2),
        )

    monkeypatch.setattr("travel_briefing.workflow.build_list_word", build)
    monkeypatch.setattr("travel_briefing.workflow.render_list_word_for_qa", qa)
    value = config(tmp_path)
    outputs = {
        "output_docx": tmp_path / "draft.docx",
        "output_qa_pdf": tmp_path / "qa.pdf",
        "output_qa_png": tmp_path / "qa.png",
    }

    evidence = backend(value).render_word(draft(), **outputs)

    assert evidence.page_count == 1
    assert evidence.qr_image_count == 2
    assert calls["build"][1]["template_path"] == value.template_path
    assert calls["qa"][1]["required_text"] == ("SYN-OSA-260901", "SY100")
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
