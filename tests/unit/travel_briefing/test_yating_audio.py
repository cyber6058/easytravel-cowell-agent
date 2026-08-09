import json
import wave
from pathlib import Path

import pytest

from travel_briefing.audio import synthesize_yating
from travel_briefing.errors import AudioSynthesisError, UnknownAudioResultError
from travel_briefing.narration import segment_narration


class ContractCaptureAdapter:
    def __init__(self) -> None:
        self.job_payload: dict | None = None

    def synthesize(self, job_path, *, timeout_seconds: int) -> None:
        self.job_payload = json.loads(job_path.read_text(encoding="utf-8"))
        raise AudioSynthesisError("stop after contract capture")


class SuccessfulYatingAdapter:
    def __init__(self) -> None:
        self.received_job_path: Path | None = None

    def synthesize(self, job_path, *, timeout_seconds: int) -> None:
        self.received_job_path = job_path
        job = json.loads(job_path.read_text(encoding="utf-8"))
        with wave.open(job["output_wav"], "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(16_000)
            output.writeframes(b"\x00\x00" * 48_000)
        Path(job["output_bookmarks"]).write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "voice": "Microsoft Yating",
                    "markers": [
                        {
                            "type": "Speech:Bookmark",
                            "name": "segment-002",
                            "time_ticks": 10_000_000,
                        },
                        {
                            "type": "Speech:Bookmark",
                            "name": "segment-003",
                            "time_ticks": 25_000_000,
                        },
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )


class MarkerVariantAdapter:
    def __init__(self, markers) -> None:
        self.markers = markers

    def synthesize(self, job_path, *, timeout_seconds: int) -> None:
        job = json.loads(job_path.read_text(encoding="utf-8"))
        with wave.open(job["output_wav"], "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(16_000)
            output.writeframes(b"\x00\x00" * 48_000)
        Path(job["output_bookmarks"]).write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "voice": "Microsoft Yating",
                    "markers": self.markers,
                }
            ),
            encoding="utf-8",
        )


class InvalidWaveAdapter:
    def __init__(self, kind: str) -> None:
        self.kind = kind

    def synthesize(self, job_path, *, timeout_seconds: int) -> None:
        job = json.loads(job_path.read_text(encoding="utf-8"))
        wav_path = Path(job["output_wav"])
        if self.kind == "corrupt":
            wav_path.write_bytes(b"not a wave file")
        else:
            with wave.open(str(wav_path), "wb") as output:
                output.setnchannels(2 if self.kind == "stereo" else 1)
                output.setsampwidth(1 if self.kind == "8-bit" else 2)
                output.setframerate(16_000)
                if self.kind != "empty":
                    output.writeframes(b"\x00\x00" * 16_000)
        Path(job["output_bookmarks"]).write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "voice": "Microsoft Yating",
                    "markers": [],
                }
            ),
            encoding="utf-8",
        )


class PartialTimeoutYatingAdapter:
    def __init__(self) -> None:
        self.call_count = 0

    def synthesize(self, job_path, *, timeout_seconds: int) -> None:
        self.call_count += 1
        job = json.loads(job_path.read_text(encoding="utf-8"))
        with wave.open(job["output_wav"], "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(16_000)
            output.writeframes(b"\x00\x00" * 8_000)
        raise UnknownAudioResultError()


class UnexpectedCallAdapter:
    def __init__(self) -> None:
        self.call_count = 0

    def synthesize(self, job_path, *, timeout_seconds: int) -> None:
        self.call_count += 1
        raise AssertionError("adapter must not be called")


class AlternateSampleRateAdapter:
    def synthesize(self, job_path, *, timeout_seconds: int) -> None:
        job = json.loads(job_path.read_text(encoding="utf-8"))
        with wave.open(job["output_wav"], "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(22_050)
            output.writeframes(b"\x00\x00" * 22_050)
        Path(job["output_bookmarks"]).write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "voice": "Microsoft Yating",
                    "markers": [],
                }
            ),
            encoding="utf-8",
        )


def test_yating_job_is_one_escaped_ssml_utterance_with_segment_bookmarks(tmp_path):
    adapter = ContractCaptureAdapter()
    plan = segment_narration("集合處有 A&B <入口>。第二段。")

    with pytest.raises(AudioSynthesisError, match="contract capture"):
        synthesize_yating(
            plan,
            output_wav=tmp_path / "sample.wav",
            output_srt=tmp_path / "sample.srt",
            output_txt=tmp_path / "sample.txt",
            output_metadata=tmp_path / "sample.json",
            adapter=adapter,
            timeout_seconds=30,
        )

    assert adapter.job_payload is not None
    assert adapter.job_payload["schema_version"] == 1
    assert adapter.job_payload["engine"] == "windows-media-speech"
    assert adapter.job_payload["voice"] == "Microsoft Yating"
    assert adapter.job_payload["language"] == "zh-TW"
    assert adapter.job_payload["ssml"] == (
        '<speak version="1.0" '
        'xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-TW">'
        "集合處有 A&amp;B &lt;入口&gt;。"
        '<mark name="segment-002"/>第二段。'
        "</speak>"
    )
    assert set(adapter.job_payload) == {
        "schema_version",
        "engine",
        "voice",
        "language",
        "ssml",
        "output_wav",
        "output_bookmarks",
    }
    assert not (tmp_path / "sample.wav").exists()
    assert not (tmp_path / "sample.srt").exists()
    assert not (tmp_path / "sample.txt").exists()
    assert not (tmp_path / "sample.json").exists()


def test_yating_pipeline_builds_continuous_wav_bookmark_srt_and_metadata(tmp_path):
    adapter = SuccessfulYatingAdapter()
    plan = segment_narration("第一段。第二段。第三段。")

    result = synthesize_yating(
        plan,
        output_wav=tmp_path / "sample.wav",
        output_srt=tmp_path / "sample.srt",
        output_txt=tmp_path / "sample.txt",
        output_metadata=tmp_path / "sample.json",
        adapter=adapter,
        timeout_seconds=30,
    )

    assert adapter.received_job_path is not None
    assert adapter.received_job_path.exists() is False
    assert result.wav_path == (tmp_path / "sample.wav").resolve()
    assert result.srt_path == (tmp_path / "sample.srt").resolve()
    assert result.txt_path == (tmp_path / "sample.txt").resolve()
    assert result.metadata_path == (tmp_path / "sample.json").resolve()
    assert result.sample_rate == 16_000
    assert result.channels == 1
    assert result.duration_seconds == 3.0
    assert result.segment_count == 3
    assert result.bookmark_count == 2
    assert result.narration_text_sha256 == plan.text_sha256
    assert all(
        len(value) == 64
        for value in (
            result.wav_sha256,
            result.srt_sha256,
            result.txt_sha256,
            result.metadata_sha256,
        )
    )
    with wave.open(str(result.wav_path), "rb") as rendered:
        assert rendered.getnchannels() == 1
        assert rendered.getsampwidth() == 2
        assert rendered.getframerate() == 16_000
        assert rendered.getnframes() == 48_000
    assert result.srt_path.read_text(encoding="utf-8") == (
        "1\n"
        "00:00:00,000 --> 00:00:01,000\n"
        "第一段。\n\n"
        "2\n"
        "00:00:01,000 --> 00:00:02,500\n"
        "第二段。\n\n"
        "3\n"
        "00:00:02,500 --> 00:00:03,000\n"
        "第三段。\n"
    )
    assert result.txt_path.read_text(encoding="utf-8") == "第一段。第二段。第三段。\n"
    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata == {
        "schema_version": 1,
        "engine": "windows-media-speech",
        "voice": "Microsoft Yating",
        "language": "zh-TW",
        "narration_text_sha256": plan.text_sha256,
        "segment_count": 3,
        "bookmark_count": 2,
        "audio": {
            "format": "PCM",
            "sample_rate": 16_000,
            "bits_per_sample": 16,
            "channels": 1,
            "frame_count": 48_000,
            "duration_seconds": 3.0,
        },
        "artifacts": {
            "wav": {"sha256": result.wav_sha256},
            "srt": {"sha256": result.srt_sha256},
            "txt": {"sha256": result.txt_sha256},
        },
        "mp3": {
            "status": "unavailable",
            "reason": "MP3_CONVERTER_UNAVAILABLE",
        },
    }


def test_yating_uses_the_decoded_wav_sample_rate_instead_of_assuming_16khz(
    tmp_path,
):
    result = synthesize_yating(
        segment_narration("只有一段。"),
        output_wav=tmp_path / "sample.wav",
        output_srt=tmp_path / "sample.srt",
        output_txt=tmp_path / "sample.txt",
        output_metadata=tmp_path / "sample.json",
        adapter=AlternateSampleRateAdapter(),
    )

    assert result.sample_rate == 22_050
    assert result.duration_seconds == 1.0
    assert result.bookmark_count == 0
    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata["audio"]["sample_rate"] == 22_050


@pytest.mark.parametrize(
    ("markers", "message"),
    [
        (
            [
                {
                    "type": "Speech:Bookmark",
                    "name": "segment-002",
                    "time_ticks": 10_000_000,
                }
            ],
            "do not match narration segments",
        ),
        (
            [
                {
                    "type": "Speech:Bookmark",
                    "name": "segment-002",
                    "time_ticks": 20_000_000,
                },
                {
                    "type": "Speech:Bookmark",
                    "name": "segment-003",
                    "time_ticks": 10_000_000,
                },
            ],
            "strictly increasing",
        ),
        (
            [
                {
                    "type": "Speech:Bookmark",
                    "name": "segment-002",
                    "time_ticks": 1,
                },
                {
                    "type": "Speech:Bookmark",
                    "name": "segment-003",
                    "time_ticks": 25_000_000,
                },
            ],
            "Yating bookmark times",
        ),
        (
            [
                {
                    "type": "Speech:Bookmark",
                    "name": "segment-002",
                    "time_ticks": 10_000_000,
                },
                {
                    "type": "Speech:Bookmark",
                    "name": "segment-002",
                    "time_ticks": 20_000_000,
                },
                {
                    "type": "Speech:Bookmark",
                    "name": "segment-003",
                    "time_ticks": 25_000_000,
                },
            ],
            "do not match narration segments",
        ),
        (
            [
                {
                    "type": "Speech:Bookmark",
                    "name": "segment-002",
                    "time_ticks": 10_000_000,
                },
                {
                    "type": "Speech:Bookmark",
                    "name": "segment-999",
                    "time_ticks": 20_000_000,
                },
            ],
            "do not match narration segments",
        ),
        (
            [
                {
                    "type": "Speech:Bookmark",
                    "name": "segment-003",
                    "time_ticks": 10_000_000,
                },
                {
                    "type": "Speech:Bookmark",
                    "name": "segment-002",
                    "time_ticks": 20_000_000,
                },
            ],
            "do not match narration segments",
        ),
        (
            [
                {
                    "type": "Speech:Bookmark",
                    "name": "segment-002",
                    "time_ticks": 10_000_000,
                },
                {
                    "type": "Speech:Bookmark",
                    "name": "segment-003",
                    "time_ticks": 30_000_000,
                },
            ],
            "before WAV end",
        ),
    ],
    ids=(
        "missing",
        "reversed-times",
        "rounded-to-zero",
        "duplicate",
        "unknown",
        "reversed-names",
        "at-wav-end",
    ),
)
def test_yating_rejects_untrustworthy_bookmarks_without_artifacts(
    tmp_path, markers, message
):
    plan = segment_narration("第一段。第二段。第三段。")

    with pytest.raises(AudioSynthesisError, match=message) as caught:
        synthesize_yating(
            plan,
            output_wav=tmp_path / "sample.wav",
            output_srt=tmp_path / "sample.srt",
            output_txt=tmp_path / "sample.txt",
            output_metadata=tmp_path / "sample.json",
            adapter=MarkerVariantAdapter(markers),
        )

    assert caught.value.details["voice"] == "Microsoft Yating"
    assert caught.value.details["wav"]["exists"] is True
    assert caught.value.details["bookmarks"]["exists"] is True
    assert caught.value.details["retry_attempted"] is False
    assert caught.value.details["fallback_attempted"] is False
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("kind", ("corrupt", "empty", "stereo", "8-bit"))
def test_yating_rejects_invalid_wav_without_artifacts(tmp_path, kind):
    plan = segment_narration("只有一段。")

    with pytest.raises(AudioSynthesisError, match="Yating WAV validation failed"):
        synthesize_yating(
            plan,
            output_wav=tmp_path / "sample.wav",
            output_srt=tmp_path / "sample.srt",
            output_txt=tmp_path / "sample.txt",
            output_metadata=tmp_path / "sample.json",
            adapter=InvalidWaveAdapter(kind),
        )

    assert list(tmp_path.iterdir()) == []


def test_yating_timeout_inspects_partial_outputs_once_without_retry_or_fallback(
    tmp_path,
):
    adapter = PartialTimeoutYatingAdapter()
    plan = segment_narration("只有一段。")

    with pytest.raises(UnknownAudioResultError) as caught:
        synthesize_yating(
            plan,
            output_wav=tmp_path / "sample.wav",
            output_srt=tmp_path / "sample.srt",
            output_txt=tmp_path / "sample.txt",
            output_metadata=tmp_path / "sample.json",
            adapter=adapter,
            timeout_seconds=1,
        )

    assert adapter.call_count == 1
    assert caught.value.details == {
        "voice": "Microsoft Yating",
        "wav": {"exists": True, "byte_count": 16_044},
        "bookmarks": {"exists": False, "byte_count": 0},
        "retry_attempted": False,
        "fallback_attempted": False,
    }
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("existing_suffix", (".wav", ".srt", ".txt", ".json"))
def test_yating_never_overwrites_an_existing_final_artifact(
    tmp_path, existing_suffix
):
    existing = tmp_path / f"sample{existing_suffix}"
    existing.write_bytes(b"keep me")
    adapter = UnexpectedCallAdapter()

    with pytest.raises(FileExistsError, match="Output already exists"):
        synthesize_yating(
            segment_narration("只有一段。"),
            output_wav=tmp_path / "sample.wav",
            output_srt=tmp_path / "sample.srt",
            output_txt=tmp_path / "sample.txt",
            output_metadata=tmp_path / "sample.json",
            adapter=adapter,
        )

    assert adapter.call_count == 0
    assert existing.read_bytes() == b"keep me"
    assert list(tmp_path.iterdir()) == [existing]
