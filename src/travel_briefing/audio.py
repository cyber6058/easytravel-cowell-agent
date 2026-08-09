from __future__ import annotations

import hashlib
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from .errors import (
    AudioSynthesisError,
    LocalTtsUnavailableError,
    Mp3ConverterUnavailableError,
    UnknownAudioResultError,
)
from .narration import NarrationPlan
from .subtitles import (
    SubtitleSegment,
    TimedSubtitleSegment,
    build_srt,
    build_timed_srt,
)


HANHAN_VOICE = "Microsoft Hanhan Desktop"
YATING_VOICE = "Microsoft Yating"
YATING_LANGUAGE = "zh-TW"
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
class YatingAudioBuildResult:
    wav_path: Path
    srt_path: Path
    txt_path: Path
    metadata_path: Path
    wav_sha256: str
    srt_sha256: str
    txt_sha256: str
    metadata_sha256: str
    duration_seconds: float
    sample_rate: int
    channels: int
    segment_count: int
    bookmark_count: int
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


def synthesize_yating(
    plan: NarrationPlan,
    *,
    output_wav: Path,
    output_srt: Path,
    output_txt: Path,
    output_metadata: Path,
    adapter: SpeechAdapter,
    timeout_seconds: int = 120,
) -> YatingAudioBuildResult:
    if not plan.segments:
        raise ValueError("Narration plan must contain at least one segment")
    wav_path = _new_output(output_wav, ".wav")
    srt_path = _new_output(output_srt, ".srt")
    txt_path = _new_output(output_txt, ".txt")
    metadata_path = _new_output(output_metadata, ".json")
    with tempfile.TemporaryDirectory(prefix="easytravel-briefing-yating-") as temp:
        work_dir = Path(temp)
        job_path = work_dir / "speech-job.json"
        temporary_wav = work_dir / "yating.wav"
        temporary_bookmarks = work_dir / "bookmarks.json"
        job = {
            "schema_version": 1,
            "engine": "windows-media-speech",
            "voice": YATING_VOICE,
            "language": YATING_LANGUAGE,
            "ssml": _build_yating_ssml(plan),
            "output_wav": str(temporary_wav),
            "output_bookmarks": str(temporary_bookmarks),
        }
        job_path.write_text(
            json.dumps(job, ensure_ascii=False, indent=2),
            encoding="utf-8",
            newline="\n",
        )
        try:
            adapter.synthesize(job_path, timeout_seconds=timeout_seconds)
        except UnknownAudioResultError as error:
            _annotate_yating_failure(
                error,
                temporary_wav=temporary_wav,
                temporary_bookmarks=temporary_bookmarks,
            )
            raise
        except (AudioSynthesisError, LocalTtsUnavailableError) as error:
            _annotate_yating_failure(
                error,
                temporary_wav=temporary_wav,
                temporary_bookmarks=temporary_bookmarks,
            )
            raise
        try:
            wave_info = _inspect_wave(temporary_wav)
            _validate_yating_wave(wave_info)
        except ValueError as error:
            failure = AudioSynthesisError(
                "Yating WAV validation failed",
                {"reason": str(error)},
            )
            _annotate_yating_failure(
                failure,
                temporary_wav=temporary_wav,
                temporary_bookmarks=temporary_bookmarks,
            )
            raise failure from error
        try:
            bookmark_milliseconds = _read_yating_bookmarks(
                temporary_bookmarks,
                expected_names=tuple(
                    segment.segment_id for segment in plan.segments[1:]
                ),
                wave_info=wave_info,
            )
        except AudioSynthesisError as error:
            _annotate_yating_failure(
                error,
                temporary_wav=temporary_wav,
                temporary_bookmarks=temporary_bookmarks,
            )
            raise
        duration_ms = _frames_to_milliseconds(
            wave_info.frame_count, wave_info.sample_rate
        )
        starts = (0, *bookmark_milliseconds)
        ends = (*bookmark_milliseconds, duration_ms)
        subtitle_segments = tuple(
            TimedSubtitleSegment(
                segment_id=segment.segment_id,
                text=segment.text,
                start_ms=start_ms,
                end_ms=end_ms,
            )
            for segment, start_ms, end_ms in zip(
                plan.segments, starts, ends, strict=True
            )
        )
        srt_bytes = build_timed_srt(subtitle_segments).encode("utf-8")
        narration_bytes = (
            "".join(segment.text for segment in plan.segments) + "\n"
        ).encode("utf-8")
        wav_sha256 = _sha256_file(temporary_wav)
        srt_sha256 = _sha256_bytes(srt_bytes)
        txt_sha256 = _sha256_bytes(narration_bytes)
        duration_seconds = wave_info.frame_count / wave_info.sample_rate
        metadata = {
            "schema_version": 1,
            "engine": "windows-media-speech",
            "voice": YATING_VOICE,
            "language": YATING_LANGUAGE,
            "narration_text_sha256": plan.text_sha256,
            "segment_count": len(plan.segments),
            "bookmark_count": len(bookmark_milliseconds),
            "audio": {
                "format": "PCM",
                "sample_rate": wave_info.sample_rate,
                "bits_per_sample": wave_info.sample_width * 8,
                "channels": wave_info.channels,
                "frame_count": wave_info.frame_count,
                "duration_seconds": duration_seconds,
            },
            "artifacts": {
                "wav": {"sha256": wav_sha256},
                "srt": {"sha256": srt_sha256},
                "txt": {"sha256": txt_sha256},
            },
            "mp3": {
                "status": "unavailable",
                "reason": "MP3_CONVERTER_UNAVAILABLE",
            },
        }
        metadata_bytes = (
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8")
        _publish_yating_artifacts(
            source_wav=temporary_wav,
            wav_path=wav_path,
            srt_path=srt_path,
            srt_bytes=srt_bytes,
            txt_path=txt_path,
            txt_bytes=narration_bytes,
            metadata_path=metadata_path,
            metadata_bytes=metadata_bytes,
        )
    return YatingAudioBuildResult(
        wav_path=wav_path,
        srt_path=srt_path,
        txt_path=txt_path,
        metadata_path=metadata_path,
        wav_sha256=wav_sha256,
        srt_sha256=srt_sha256,
        txt_sha256=txt_sha256,
        metadata_sha256=_sha256_file(metadata_path),
        duration_seconds=duration_seconds,
        sample_rate=wave_info.sample_rate,
        channels=wave_info.channels,
        segment_count=len(plan.segments),
        bookmark_count=len(bookmark_milliseconds),
        narration_text_sha256=plan.text_sha256,
    )


def _build_yating_ssml(plan: NarrationPlan) -> str:
    body: list[str] = []
    for index, segment in enumerate(plan.segments):
        if index:
            body.append(f'<mark name="{segment.segment_id}"/>')
        body.append(html.escape(segment.text, quote=False))
    return (
        '<speak version="1.0" '
        'xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-TW">'
        + "".join(body)
        + "</speak>"
    )


def _validate_yating_wave(info: _WaveInfo) -> None:
    if (
        info.sample_width != 2
        or info.channels != 1
        or info.sample_rate <= 0
        or info.frame_count <= 0
    ):
        raise ValueError("Yating output must be non-empty 16-bit mono PCM WAV")


def _read_yating_bookmarks(
    path: Path,
    *,
    expected_names: tuple[str, ...],
    wave_info: _WaveInfo,
) -> tuple[int, ...]:
    if not path.is_file():
        raise AudioSynthesisError(
            "Speech adapter did not create Yating bookmarks"
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AudioSynthesisError(
            "Yating bookmarks are not valid UTF-8 JSON"
        ) from error
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != 1
        or payload.get("voice") != YATING_VOICE
        or not isinstance(payload.get("markers"), list)
    ):
        raise AudioSynthesisError(
            "Yating bookmark metadata does not match the contract"
        )
    markers = payload["markers"]
    names = tuple(
        marker.get("name") if isinstance(marker, dict) else None
        for marker in markers
    )
    if names != expected_names:
        raise AudioSynthesisError(
            "Yating bookmarks do not match narration segments"
        )
    milliseconds: list[int] = []
    previous_ticks = 0
    for marker in markers:
        if marker.get("type") != "Speech:Bookmark":
            raise AudioSynthesisError("Yating marker is not a speech bookmark")
        ticks = marker.get("time_ticks")
        if isinstance(ticks, bool) or not isinstance(ticks, int):
            raise AudioSynthesisError(
                "Yating bookmark time_ticks must be an integer"
            )
        if ticks <= previous_ticks:
            raise AudioSynthesisError(
                "Yating bookmarks must be strictly increasing"
            )
        if ticks * wave_info.sample_rate >= wave_info.frame_count * 10_000_000:
            raise AudioSynthesisError(
                "Yating bookmark must occur before WAV end"
            )
        milliseconds.append((ticks + 5_000) // 10_000)
        previous_ticks = ticks
    if any(
        current <= previous
        for previous, current in zip(milliseconds, milliseconds[1:])
    ):
        raise AudioSynthesisError(
            "Rounded Yating bookmark times must be strictly increasing"
        )
    duration_ms = _frames_to_milliseconds(
        wave_info.frame_count, wave_info.sample_rate
    )
    if any(value <= 0 or value >= duration_ms for value in milliseconds):
        raise AudioSynthesisError(
            "Rounded Yating bookmark times must lie strictly inside WAV"
        )
    return tuple(milliseconds)


def _publish_yating_artifacts(
    *,
    source_wav: Path,
    wav_path: Path,
    srt_path: Path,
    srt_bytes: bytes,
    txt_path: Path,
    txt_bytes: bytes,
    metadata_path: Path,
    metadata_bytes: bytes,
) -> None:
    created: list[Path] = []
    try:
        with source_wav.open("rb") as source, wav_path.open("xb") as output:
            created.append(wav_path)
            shutil.copyfileobj(source, output)
        for path, content in (
            (srt_path, srt_bytes),
            (txt_path, txt_bytes),
            (metadata_path, metadata_bytes),
        ):
            with path.open("xb") as output:
                created.append(path)
                output.write(content)
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        raise


def _temporary_output_status(path: Path) -> dict[str, int | bool]:
    exists = path.is_file()
    return {
        "exists": exists,
        "byte_count": path.stat().st_size if exists else 0,
    }


def _annotate_yating_failure(
    error: AudioSynthesisError
    | LocalTtsUnavailableError
    | UnknownAudioResultError,
    *,
    temporary_wav: Path,
    temporary_bookmarks: Path,
) -> None:
    error.details.update(
        voice=YATING_VOICE,
        wav=_temporary_output_status(temporary_wav),
        bookmarks=_temporary_output_status(temporary_bookmarks),
        retry_attempted=False,
        fallback_attempted=False,
    )


def _frames_to_milliseconds(frame_count: int, sample_rate: int) -> int:
    return (frame_count * 1_000 + sample_rate // 2) // sample_rate


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


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
