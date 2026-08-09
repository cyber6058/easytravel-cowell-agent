from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


_STRONG_BOUNDARY = re.compile(r".+?(?:[。！？!?；;]+|$)")
_CLAUSE_BOUNDARY = re.compile(r".+?(?:[，、,:：]+|$)")


@dataclass(frozen=True, slots=True)
class NarrationSegment:
    segment_id: str
    text: str
    text_sha256: str


@dataclass(frozen=True, slots=True)
class NarrationPlan:
    segments: tuple[NarrationSegment, ...]
    text_sha256: str


def segment_narration(text: str, *, max_chars: int = 32) -> NarrationPlan:
    if max_chars < 4:
        raise ValueError("Narration max_chars must be at least 4")
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        raise ValueError("Narration text must not be empty")
    sentences = tuple(
        match.group(0).strip()
        for match in _STRONG_BOUNDARY.finditer(normalized)
        if match.group(0).strip()
    )
    pieces = tuple(
        piece
        for sentence in sentences
        for piece in _split_for_length(sentence, max_chars)
    )
    segments = tuple(
        NarrationSegment(
            segment_id=f"segment-{index:03d}",
            text=piece,
            text_sha256=_sha256_text(piece),
        )
        for index, piece in enumerate(pieces, start=1)
    )
    canonical_text = "".join(segment.text for segment in segments)
    return NarrationPlan(
        segments=segments,
        text_sha256=_sha256_text(canonical_text),
    )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _split_for_length(text: str, max_chars: int) -> tuple[str, ...]:
    if len(text) <= max_chars:
        return (text,)
    clauses = tuple(
        match.group(0)
        for match in _CLAUSE_BOUNDARY.finditer(text)
        if match.group(0)
    )
    pieces: list[str] = []
    current = ""
    for clause in clauses:
        if len(clause) > max_chars:
            if current:
                pieces.append(current)
                current = ""
            pieces.extend(
                clause[index : index + max_chars]
                for index in range(0, len(clause), max_chars)
            )
        elif current and len(current) + len(clause) > max_chars:
            pieces.append(current)
            current = clause
        else:
            current += clause
    if current:
        pieces.append(current)
    return tuple(pieces)
