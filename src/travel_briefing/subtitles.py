from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SubtitleSegment:
    segment_id: str
    text: str
    frame_count: int
    sample_rate: int

    def __post_init__(self) -> None:
        if self.frame_count < 0:
            raise ValueError("Subtitle frame_count must not be negative")
        if self.sample_rate <= 0:
            raise ValueError("Subtitle sample_rate must be positive")


def build_srt(
    segments: tuple[SubtitleSegment, ...], *, max_line_chars: int = 16
) -> str:
    if not segments:
        raise ValueError("At least one subtitle segment is required")
    if max_line_chars < 4:
        raise ValueError("Subtitle max_line_chars must be at least 4")
    sample_rate = segments[0].sample_rate
    if any(segment.sample_rate != sample_rate for segment in segments):
        raise ValueError("All subtitle segments must use the same sample rate")
    blocks: list[str] = []
    elapsed_frames = 0
    for index, segment in enumerate(segments, start=1):
        start_ms = _frames_to_milliseconds(elapsed_frames, sample_rate)
        elapsed_frames += segment.frame_count
        end_ms = _frames_to_milliseconds(elapsed_frames, sample_rate)
        blocks.append(
            f"{index}\n"
            f"{_format_timestamp(start_ms)} --> {_format_timestamp(end_ms)}\n"
            f"{_wrap_text(segment.text, max_line_chars)}"
        )
    return "\n\n".join(blocks) + "\n"


def _frames_to_milliseconds(frame_count: int, sample_rate: int) -> int:
    return (frame_count * 1_000 + sample_rate // 2) // sample_rate


def _format_timestamp(milliseconds: int) -> str:
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _wrap_text(text: str, max_line_chars: int) -> str:
    if len(text) > max_line_chars * 2:
        raise ValueError("Subtitle segment exceeds the two-line mobile limit")
    return "\n".join(
        text[index : index + max_line_chars]
        for index in range(0, len(text), max_line_chars)
    )
