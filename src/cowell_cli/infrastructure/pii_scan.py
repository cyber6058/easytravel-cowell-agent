"""Machine PII scan over extracted text (HTML- or PDF-derived).

The scan reports only *how many* hits each PII category has — never the matched
substrings — so a report is always safe to print or log even when the scanned
text contains real passenger data. This is the machine-scan primitive required
by the PDF-safe report workflow gate (docs/specs/2026-07-10-pdf-safe-report-workflow.md).

Patterns mirror the redaction/sanitizer pattern sets but are tagged by category
so a scan can say *which* kind of PII appeared. Keep them in sync with
`infrastructure/redaction.py` and `infrastructure/sanitizer.py`.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass


PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "taiwan_mobile": re.compile(
        r"(?<!\d)(?:\+?886[-\s]?)?09\d{2}[-\s]?\d{3}[-\s]?\d{3}(?!\d)"
    ),
    "taiwan_id": re.compile(r"(?<![A-Z0-9])[A-Z][12]\d{8}(?!\d)"),
    "pnr": re.compile(r"(?i)\b(?:PNR|訂位代號)\s*[:：=]?\s*[A-Z0-9]{5,8}\b"),
    "bearer_token": re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"),
    "private_key": re.compile(
        r"-----BEGIN PRIVATE KEY-----.*?-----END PRIVATE KEY-----", re.DOTALL
    ),
    "credential_assignment": re.compile(
        r"(?i)\b(?:password|passwd|pwd|sessionid|asp\.net_sessionid|token)"
        r"\s*[=:]\s*[^\s;&\"'>]+"
    ),
}


@dataclass(frozen=True, slots=True)
class PiiScanReport:
    """Counts-only result of a PII scan. Carries no matched text by construction."""

    counts: Mapping[str, int]  # only categories with at least one hit
    total: int

    @property
    def clean(self) -> bool:
        return self.total == 0

    def as_dict(self) -> dict[str, object]:
        return {"clean": self.clean, "total": self.total, "counts": dict(self.counts)}


def scan_text_for_pii(
    text: str,
    *,
    patterns: Mapping[str, re.Pattern[str]] | None = None,
) -> PiiScanReport:
    """Count PII hits per category. Returns counts only, never the matched values."""
    active = patterns if patterns is not None else PII_PATTERNS
    counts: dict[str, int] = {}
    total = 0
    for category, pattern in active.items():
        hits = len(pattern.findall(text))
        if hits:
            counts[category] = hits
            total += hits
    return PiiScanReport(counts=counts, total=total)
