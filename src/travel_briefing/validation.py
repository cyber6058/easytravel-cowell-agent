from __future__ import annotations

import unicodedata
from collections.abc import Iterable

from .models import Conflict, DraftStatus


def status_for_conflicts(conflicts: Iterable[Conflict]) -> DraftStatus:
    if any(
        conflict.severity == "blocking" and not conflict.decision.strip()
        for conflict in conflicts
    ):
        return DraftStatus.BLOCKED
    return DraftStatus.DRAFT_READY


def text_is_equivalent(value_a: str, value_b: str) -> bool:
    key_a = _text_key(value_a)
    key_b = _text_key(value_b)
    if key_a == key_b:
        return True
    return _geographic_key(key_a) == _geographic_key(key_b)


def text_sequence_is_equivalent(
    values_a: tuple[str, ...],
    values_b: tuple[str, ...],
) -> bool:
    return len(values_a) == len(values_b) and all(
        text_is_equivalent(value_a, value_b)
        for value_a, value_b in zip(values_a, values_b, strict=True)
    )


def _text_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(
        character
        for character in normalized
        if not unicodedata.category(character).startswith(("P", "Z"))
    )


def _geographic_key(value: str) -> str:
    for suffix in ("市", "府", "縣"):
        if value.endswith(suffix) and len(value) > len(suffix):
            return value[: -len(suffix)]
    return value
