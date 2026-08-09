import json
import subprocess
import wave
from pathlib import Path

import pytest

from travel_briefing.audio import convert_wav_to_mp3, synthesize_hanhan
from travel_briefing.errors import (
    Mp3ConverterUnavailableError,
    UnknownAudioResultError,
)
from travel_briefing.narration import segment_narration


class FakeSpeechAdapter:
    def __init__(self) -> None:
        self.received_job_path: Path | None = None
        self.received_timeout: int | None = None
        self.job_payload: dict | None = None

    def synthesize(self, job_path: Path, *, timeout_seconds: int) -> None:
        self.received_job_path = job_path
        self.received_timeout = timeout_seconds
        self.job_payload = json.loads(job_path.read_text(encoding="utf-8"))
        for index, segment in enumerate(self.job_payload["segments"], start=1):
            frame_count = index * 22_050
            with wave.open(segment["output_path"], "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(44_100)
                output.writeframes(b"\x00\x00" * frame_count)


class FakeFfmpegRunner:
    def __init__(self) -> None:
        self.command = None

    def __call__(self, command, **options):
        self.command = command
        Path(command[-1]).write_bytes(b"ID3 synthetic mp3")
        return subprocess.CompletedProcess(command, returncode=0, stdout="", stderr="")


class PartialTimeoutSpeechAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def synthesize(self, job_path: Path, *, timeout_seconds: int) -> None:
        self.calls += 1
        job = json.loads(job_path.read_text(encoding="utf-8"))
        first = job["segments"][0]
        with wave.open(first["output_path"], "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(44_100)
            output.writeframes(b"\x00\x00" * 22_050)
        raise UnknownAudioResultError()


class PartialTimeoutFfmpegRunner:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, command, **options):
        self.calls += 1
        Path(command[-1]).write_bytes(b"partial")
        raise subprocess.TimeoutExpired(command, timeout=options["timeout"])


def test_hanhan_pipeline_uses_a_utf8_job_and_actual_pcm_frames(tmp_path):
    adapter = FakeSpeechAdapter()
    plan = segment_narration("各位旅客您好。請確認集合資訊。")
    wav_path = tmp_path / "sample.wav"
    srt_path = tmp_path / "sample.srt"

    result = synthesize_hanhan(
        plan,
        output_wav=wav_path,
        output_srt=srt_path,
        adapter=adapter,
        timeout_seconds=30,
    )

    assert adapter.received_timeout == 30
    assert adapter.received_job_path is not None
    assert adapter.received_job_path.exists() is False
    assert adapter.job_payload is not None
    assert adapter.job_payload["voice"] == "Microsoft Hanhan Desktop"
    assert [item["text"] for item in adapter.job_payload["segments"]] == [
        "各位旅客您好。",
        "請確認集合資訊。",
    ]
    with wave.open(str(wav_path), "rb") as rendered:
        assert rendered.getnchannels() == 1
        assert rendered.getsampwidth() == 2
        assert rendered.getframerate() == 44_100
        assert rendered.getnframes() == 66_150
    assert result.duration_seconds == 1.5
    assert result.sample_rate == 44_100
    assert result.channels == 1
    assert result.segment_count == 2
    assert result.narration_text_sha256 == plan.text_sha256
    assert len(result.wav_sha256) == 64
    assert len(result.srt_sha256) == 64
    assert "00:00:00,000 --> 00:00:00,500" in srt_path.read_text(
        encoding="utf-8"
    )
    assert "00:00:00,500 --> 00:00:01,500" in srt_path.read_text(
        encoding="utf-8"
    )


def test_mp3_conversion_is_blocked_without_a_configured_ffmpeg(tmp_path):
    wav_path = tmp_path / "ready.wav"
    wav_path.write_bytes(b"synthetic wave placeholder")
    mp3_path = tmp_path / "blocked.mp3"

    with pytest.raises(Mp3ConverterUnavailableError) as error:
        convert_wav_to_mp3(
            wav_path,
            output_mp3=mp3_path,
            ffmpeg_path=None,
        )

    assert error.value.code == "MP3_CONVERTER_UNAVAILABLE"
    assert wav_path.read_bytes() == b"synthetic wave placeholder"
    assert mp3_path.exists() is False


def test_configured_ffmpeg_uses_line_mobile_audio_settings(tmp_path):
    ffmpeg = tmp_path / "ffmpeg.exe"
    ffmpeg.write_bytes(b"synthetic executable")
    wav_path = tmp_path / "ready.wav"
    wav_path.write_bytes(b"synthetic wave placeholder")
    mp3_path = tmp_path / "ready.mp3"
    runner = FakeFfmpegRunner()

    result = convert_wav_to_mp3(
        wav_path,
        output_mp3=mp3_path,
        ffmpeg_path=ffmpeg,
        runner=runner,
    )

    assert runner.command is not None
    assert runner.command[0] == str(ffmpeg.resolve())
    assert "-nostdin" in runner.command
    assert "-n" in runner.command
    assert runner.command[runner.command.index("-ac") + 1] == "1"
    assert runner.command[runner.command.index("-ar") + 1] == "44100"
    assert runner.command[runner.command.index("-b:a") + 1] == "128k"
    assert result.path == mp3_path.resolve()
    assert result.byte_count == len(b"ID3 synthetic mp3")
    assert len(result.sha256) == 64


def test_unknown_speech_result_is_inspected_once_and_never_retried(tmp_path):
    adapter = PartialTimeoutSpeechAdapter()
    plan = segment_narration("第一段合成內容。第二段合成內容。")

    with pytest.raises(UnknownAudioResultError) as error:
        synthesize_hanhan(
            plan,
            output_wav=tmp_path / "unknown.wav",
            output_srt=tmp_path / "unknown.srt",
            adapter=adapter,
            timeout_seconds=1,
        )

    assert adapter.calls == 1
    assert error.value.details == {
        "expected_segments": 2,
        "completed_segments": ["segment-001"],
    }
    assert (tmp_path / "unknown.wav").exists() is False
    assert (tmp_path / "unknown.srt").exists() is False


def test_unknown_mp3_result_is_inspected_once_and_never_retried(tmp_path):
    ffmpeg = tmp_path / "ffmpeg.exe"
    ffmpeg.write_bytes(b"synthetic executable")
    wav_path = tmp_path / "ready.wav"
    wav_path.write_bytes(b"synthetic wave placeholder")
    mp3_path = tmp_path / "unknown.mp3"
    runner = PartialTimeoutFfmpegRunner()

    with pytest.raises(UnknownAudioResultError) as error:
        convert_wav_to_mp3(
            wav_path,
            output_mp3=mp3_path,
            ffmpeg_path=ffmpeg,
            runner=runner,
            timeout_seconds=1,
        )

    assert runner.calls == 1
    assert error.value.details == {
        "output_exists": True,
        "byte_count": len(b"partial"),
    }
    assert mp3_path.read_bytes() == b"partial"


def test_hanhan_pipeline_refuses_to_overwrite_an_existing_output(tmp_path):
    adapter = PartialTimeoutSpeechAdapter()
    wav_path = tmp_path / "existing.wav"
    wav_path.write_bytes(b"keep this file")

    with pytest.raises(FileExistsError):
        synthesize_hanhan(
            segment_narration("合成內容。"),
            output_wav=wav_path,
            output_srt=tmp_path / "new.srt",
            adapter=adapter,
        )

    assert adapter.calls == 0
    assert wav_path.read_bytes() == b"keep this file"
