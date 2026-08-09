from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from .errors import (
    AudioSynthesisError,
    Mp3ConverterUnavailableError,
    UnknownAudioResultError,
)
from .narration import NarrationPlan
from .subtitles import SubtitleSegment, build_srt


HANHAN_VOICE = "Microsoft Hanhan Desktop"
SAMPLE_RATE = 44_100
SAMPLE_WIDTH = 2
CHANNELS = 1
ProcessRunner = Callable[..., subprocess.CompletedProcess[str]]


class SpeechAdapter(Protocol):
    def synthesize(self, job_path: Path, *, timeout_seconds: int) -> None: ...


@dataclass(frozen=True, slots=True)
class AudioBuildResult:
    wav_path: Path
    srt_path: Path
    wav_sha256: str
    srt_sha256: str
    duration_seconds: float
    sample_rate: int
    channels: int
    segment_count: int
    narration_text_sha256: str


@dataclass(frozen=True, slots=True)
class Mp3BuildResult:
    path: Path
    sha256: str
    byte_count: int


@dataclass(frozen=True, slots=True)
class _WaveInfo:
    path: Path
    frame_count: int
    sample_rate: int
    channels: int
    sample_width: int


def convert_wav_to_mp3(
    input_wav: Path,
    *,
    output_mp3: Path,
    ffmpeg_path: Path | None,
    runner: ProcessRunner = subprocess.run,
    timeout_seconds: int = 120,
) -> Mp3BuildResult:
    if ffmpeg_path is None or not ffmpeg_path.expanduser().is_file():
        raise Mp3ConverterUnavailableError()
    wav_path = input_wav.expanduser().resolve()
    if not wav_path.is_file() or wav_path.suffix.lower() != ".wav":
        raise ValueError("MP3 input must be an existing WAV file")
    mp3_path = _new_output(output_mp3, ".mp3")
    executable = ffmpeg_path.expanduser().resolve()
    command = [
        str(executable),
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-n",
        "-i",
        str(wav_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "44100",
        "-b:a",
        "128k",
        str(mp3_path),
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
        unknown = UnknownAudioResultError(
            "MP3 conversion timed out; inspect current outputs before retry"
        )
        output_exists = mp3_path.is_file()
        unknown.details.update(
            output_exists=output_exists,
            byte_count=mp3_path.stat().st_size if output_exists else 0,
        )
        raise unknown from error
    except OSError as error:
        raise Mp3ConverterUnavailableError() from error
    if result.returncode != 0:
        raise AudioSynthesisError(
            "Configured ffmpeg conversion failed",
            {"return_code": result.returncode},
        )
    if not mp3_path.is_file() or mp3_path.stat().st_size == 0:
        raise AudioSynthesisError("ffmpeg returned success without an MP3 output")
    return Mp3BuildResult(
        path=mp3_path,
        sha256=_sha256_file(mp3_path),
        byte_count=mp3_path.stat().st_size,
    )


def synthesize_hanhan(
    plan: NarrationPlan,
    *,
    output_wav: Path,
    output_srt: Path,
    adapter: SpeechAdapter,
    timeout_seconds: int = 120,
) -> AudioBuildResult:
    if not plan.segments:
        raise ValueError("Narration plan must contain at least one segment")
    wav_path = _new_output(output_wav, ".wav")
    srt_path = _new_output(output_srt, ".srt")
    with tempfile.TemporaryDirectory(prefix="easytravel-briefing-hanhan-") as temp:
        work_dir = Path(temp)
        segment_paths = tuple(
            work_dir / f"{segment.segment_id}.wav" for segment in plan.segments
        )
        job_path = work_dir / "speech-job.json"
        job = {
            "schema_version": 1,
            "voice": HANHAN_VOICE,
            "rate": -1,
            "audio": {
                "sample_rate": SAMPLE_RATE,
                "bits_per_sample": SAMPLE_WIDTH * 8,
                "channels": CHANNELS,
            },
            "segments": [
                {
                    "segment_id": segment.segment_id,
                    "text": segment.text,
                    "text_sha256": segment.text_sha256,
                    "output_path": str(segment_path),
                }
                for segment, segment_path in zip(
                    plan.segments, segment_paths, strict=True
                )
            ],
        }
        job_path.write_text(
            json.dumps(job, ensure_ascii=False, indent=2),
            encoding="utf-8",
            newline="\n",
        )
        try:
            adapter.synthesize(job_path, timeout_seconds=timeout_seconds)
        except UnknownAudioResultError as error:
            error.details.update(
                expected_segments=len(plan.segments),
                completed_segments=_completed_segment_ids(
                    plan,
                    segment_paths,
                ),
            )
            raise
        wave_infos = tuple(_inspect_wave(path) for path in segment_paths)
        _validate_pcm_contract(wave_infos)
        _write_combined_wav(wav_path, wave_infos)
        subtitle_segments = tuple(
            SubtitleSegment(
                segment_id=segment.segment_id,
                text=segment.text,
                frame_count=info.frame_count,
                sample_rate=info.sample_rate,
            )
            for segment, info in zip(plan.segments, wave_infos, strict=True)
        )
        srt_text = build_srt(subtitle_segments)
        try:
            with srt_path.open("x", encoding="utf-8", newline="\n") as output:
                output.write(srt_text)
        except BaseException:
            wav_path.unlink(missing_ok=True)
            raise
    total_frames = sum(info.frame_count for info in wave_infos)
    return AudioBuildResult(
        wav_path=wav_path,
        srt_path=srt_path,
        wav_sha256=_sha256_file(wav_path),
        srt_sha256=_sha256_file(srt_path),
        duration_seconds=total_frames / SAMPLE_RATE,
        sample_rate=SAMPLE_RATE,
        channels=CHANNELS,
        segment_count=len(wave_infos),
        narration_text_sha256=plan.text_sha256,
    )


def _new_output(path: Path, suffix: str) -> Path:
    output = path.expanduser().resolve()
    if output.suffix.lower() != suffix:
        raise ValueError(f"Output must use the {suffix} extension")
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    if not output.parent.is_dir():
        raise ValueError(f"Output directory does not exist: {output.parent}")
    return output


def _inspect_wave(path: Path) -> _WaveInfo:
    if not path.is_file():
        raise ValueError(f"Speech adapter did not create segment: {path.name}")
    try:
        with wave.open(str(path), "rb") as source:
            if source.getcomptype() != "NONE":
                raise ValueError(f"Speech segment is not PCM: {path.name}")
            return _WaveInfo(
                path=path,
                frame_count=source.getnframes(),
                sample_rate=source.getframerate(),
                channels=source.getnchannels(),
                sample_width=source.getsampwidth(),
            )
    except (EOFError, wave.Error) as error:
        raise ValueError(f"Speech segment is not a valid WAV: {path.name}") from error


def _validate_pcm_contract(wave_infos: tuple[_WaveInfo, ...]) -> None:
    for info in wave_infos:
        actual = (info.sample_rate, info.sample_width, info.channels)
        expected = (SAMPLE_RATE, SAMPLE_WIDTH, CHANNELS)
        if actual != expected:
            raise ValueError(
                f"Speech segment has unexpected PCM format: {info.path.name}"
            )


def _completed_segment_ids(
    plan: NarrationPlan, segment_paths: tuple[Path, ...]
) -> list[str]:
    completed: list[str] = []
    expected = (SAMPLE_RATE, SAMPLE_WIDTH, CHANNELS)
    for segment, path in zip(plan.segments, segment_paths, strict=True):
        try:
            info = _inspect_wave(path)
        except ValueError:
            continue
        actual = (info.sample_rate, info.sample_width, info.channels)
        if actual == expected and info.frame_count > 0:
            completed.append(segment.segment_id)
    return completed


def _write_combined_wav(output: Path, wave_infos: tuple[_WaveInfo, ...]) -> None:
    descriptor = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(descriptor)
    try:
        with wave.open(str(output), "wb") as combined:
            combined.setnchannels(CHANNELS)
            combined.setsampwidth(SAMPLE_WIDTH)
            combined.setframerate(SAMPLE_RATE)
            for info in wave_infos:
                with wave.open(str(info.path), "rb") as segment:
                    while frames := segment.readframes(16_384):
                        combined.writeframesraw(frames)
            combined.writeframes(b"")
    except BaseException:
        output.unlink(missing_ok=True)
        raise


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
