from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


REDACTED = "[REDACTED]"
SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "cookies",
    "csrf",
    "csrf_token",
    "password",
    "private_key",
    "secret",
    "session",
    "session_id",
    "token",
}

PATTERNS = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(password|passwd|pwd)\s*[=:]\s*[^\s;&]+"),
    re.compile(r"(?i)(sessionid|asp\.net_sessionid|token)\s*[=:]\s*[^\s;]+"),
    re.compile(r"-----BEGIN PRIVATE KEY-----.*?-----END PRIVATE KEY-----", re.DOTALL),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"(?<!\d)(?:\+?886[-\s]?)?09\d{2}[-\s]?\d{3}[-\s]?\d{3}(?!\d)"),
    re.compile(r"(?<![A-Z0-9])[A-Z][12]\d{8}(?!\d)"),
)


def redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted = {}
        for key, item in value.items():
            normalized_key = str(key).lower().replace("-", "_")
            if normalized_key == "session" and isinstance(item, Mapping):
                redacted[str(key)] = redact(item)
            else:
                redacted[str(key)] = REDACTED if _is_sensitive_key(str(key)) else redact(item)
        return redacted
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        redacted_items = [redact(item) for item in value]
        return tuple(redacted_items) if isinstance(value, tuple) else redacted_items
    return value


def redact_text(value: str) -> str:
    result = value
    for pattern in PATTERNS:
        result = pattern.sub(REDACTED, result)
    return result


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return normalized in SENSITIVE_KEYS or any(
        normalized.endswith(f"_{sensitive}") for sensitive in SENSITIVE_KEYS
    )
