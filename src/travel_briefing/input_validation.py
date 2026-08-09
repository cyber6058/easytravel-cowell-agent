from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import SplitResult, urljoin, urlsplit, urlunsplit

from .errors import BriefingInputError


NEWAMAZING_HOST = "www.newamazing.com.tw"


@dataclass(frozen=True, slots=True)
class ValidatedNewAmazingUrl:
    value: str
    host: str


@dataclass(frozen=True, slots=True)
class ValidatedPdfInput:
    path: Path
    size_bytes: int
    sha256: str


def validate_newamazing_url(value: str) -> ValidatedNewAmazingUrl:
    if not isinstance(value, str) or not value.strip():
        raise BriefingInputError("NewAmazing URL must be non-empty HTTPS text")
    raw = value.strip()
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError as error:
        raise BriefingInputError("NewAmazing URL is malformed") from error

    if parsed.scheme.casefold() != "https":
        raise BriefingInputError("NewAmazing URL must use HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise BriefingInputError("NewAmazing URL must not contain user information")
    if parsed.hostname is None or parsed.hostname.casefold() != NEWAMAZING_HOST:
        raise BriefingInputError("NewAmazing URL host is not allowlisted")
    if port not in (None, 443):
        raise BriefingInputError("NewAmazing URL must use the standard HTTPS port")

    normalized = SplitResult(
        scheme="https",
        netloc=NEWAMAZING_HOST,
        path=parsed.path or "/",
        query=parsed.query,
        fragment="",
    )
    return ValidatedNewAmazingUrl(
        value=urlunsplit(normalized),
        host=NEWAMAZING_HOST,
    )


def validate_newamazing_redirect(
    original: ValidatedNewAmazingUrl,
    redirect_url: str,
) -> ValidatedNewAmazingUrl:
    approved_original = validate_newamazing_url(original.value)
    if approved_original.host != original.host:
        raise BriefingInputError("NewAmazing original URL is not allowlisted")
    if not isinstance(redirect_url, str) or not redirect_url.strip():
        raise BriefingInputError("NewAmazing redirect URL must be non-empty text")

    redirected = validate_newamazing_url(
        urljoin(approved_original.value, redirect_url.strip())
    )
    if redirected.host != approved_original.host:
        raise BriefingInputError("NewAmazing redirect left the approved host")
    return redirected


def validate_pdf_input(value: str | Path) -> ValidatedPdfInput:
    candidate = Path(value)
    if candidate.suffix.casefold() != ".pdf":
        raise BriefingInputError("Itinerary source must use a .pdf extension")
    try:
        path = candidate.resolve(strict=True)
    except OSError as error:
        raise BriefingInputError("Itinerary PDF does not exist") from error
    if not path.is_file():
        raise BriefingInputError("Itinerary PDF must be a regular file")

    hasher = hashlib.sha256()
    size_bytes = 0
    header = b""
    try:
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                if not header:
                    header = chunk[:5]
                size_bytes += len(chunk)
                hasher.update(chunk)
    except OSError as error:
        raise BriefingInputError("Itinerary PDF cannot be read") from error
    if size_bytes == 0:
        raise BriefingInputError("Itinerary PDF is empty")
    if header != b"%PDF-":
        raise BriefingInputError("Itinerary PDF has an invalid signature")

    return ValidatedPdfInput(
        path=path,
        size_bytes=size_bytes,
        sha256=hasher.hexdigest(),
    )
