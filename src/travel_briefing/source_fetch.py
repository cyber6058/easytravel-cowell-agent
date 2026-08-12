from __future__ import annotations

import hashlib
import tempfile
from dataclasses import dataclass
from pathlib import Path

import httpx

from .errors import BriefingInputError, BriefingSourceError
from .input_validation import (
    ValidatedNewAmazingUrl,
    validate_newamazing_redirect,
    validate_newamazing_url,
)


DEFAULT_MAX_RESPONSE_BYTES = 5 * 1024 * 1024
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_ALLOWED_CONTENT_TYPES = frozenset({"text/html", "application/xhtml+xml"})


@dataclass(frozen=True, slots=True)
class FetchedNewAmazingHtml:
    source_url: str
    html: str
    byte_count: int
    sha256: str


def fetch_newamazing_html(
    source_url: str,
    *,
    transport: httpx.BaseTransport | None = None,
    temp_parent: Path | None = None,
    timeout_seconds: float = 20.0,
    max_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
) -> FetchedNewAmazingHtml:
    """Fetch one allowlisted page, with at most one same-host redirect and no retry."""
    if timeout_seconds <= 0:
        raise BriefingInputError("NewAmazing timeout must be positive")
    if max_bytes <= 0:
        raise BriefingInputError("NewAmazing response size limit must be positive")
    validated = validate_newamazing_url(source_url)
    temp_root = _validated_temp_parent(temp_parent)

    try:
        with tempfile.TemporaryDirectory(
            prefix="easytravel-newamazing-",
            dir=temp_root,
        ) as temporary:
            raw_path = Path(temporary) / "response.html"
            with httpx.Client(
                transport=transport,
                follow_redirects=False,
                timeout=timeout_seconds,
                trust_env=False,
                headers={
                    "Accept": "text/html,application/xhtml+xml",
                    "User-Agent": "EasyTravelBriefing/0.1",
                },
            ) as client:
                response, final_url = _request_once(client, validated)
                if response.status_code in _REDIRECT_STATUSES:
                    try:
                        redirected = _validated_redirect(validated, response)
                    finally:
                        response.close()
                    response, final_url = _request_once(client, redirected)
                    if response.status_code in _REDIRECT_STATUSES:
                        response.close()
                        raise BriefingSourceError(
                            "NewAmazing returned more than one redirect"
                        )
                try:
                    _validate_response(response)
                    byte_count, digest = _stream_to_temp(
                        response,
                        raw_path,
                        max_bytes=max_bytes,
                    )
                    encoding = response.encoding or "utf-8"
                finally:
                    response.close()
            try:
                html = raw_path.read_bytes().decode(encoding)
            except (LookupError, OSError, UnicodeError) as error:
                raise BriefingSourceError(
                    "NewAmazing response text encoding is invalid"
                ) from error
    except (BriefingInputError, BriefingSourceError):
        raise
    except httpx.HTTPError as error:
        raise BriefingSourceError(
            "NewAmazing request failed without retry"
        ) from error

    return FetchedNewAmazingHtml(
        source_url=final_url.value,
        html=html,
        byte_count=byte_count,
        sha256=digest,
    )


def _request_once(
    client: httpx.Client,
    url: ValidatedNewAmazingUrl,
) -> tuple[httpx.Response, ValidatedNewAmazingUrl]:
    request = client.build_request("GET", url.value)
    response = client.send(request, stream=True)
    return response, url


def _validated_redirect(
    original: ValidatedNewAmazingUrl,
    response: httpx.Response,
) -> ValidatedNewAmazingUrl:
    location = response.headers.get("location", "")
    try:
        return validate_newamazing_redirect(original, location)
    except BriefingInputError as error:
        raise BriefingInputError(
            "NewAmazing redirect is invalid or left the approved host"
        ) from error


def _validate_response(response: httpx.Response) -> None:
    if response.status_code != 200:
        raise BriefingSourceError(
            f"NewAmazing returned HTTP {response.status_code} without retry"
        )
    media_type = response.headers.get("content-type", "").partition(";")[0]
    if media_type.strip().casefold() not in _ALLOWED_CONTENT_TYPES:
        raise BriefingSourceError("NewAmazing response is not HTML")


def _stream_to_temp(
    response: httpx.Response,
    destination: Path,
    *,
    max_bytes: int,
) -> tuple[int, str]:
    byte_count = 0
    digest = hashlib.sha256()
    created = False
    try:
        with destination.open("xb") as output:
            created = True
            for chunk in response.iter_bytes():
                byte_count += len(chunk)
                if byte_count > max_bytes:
                    raise BriefingSourceError(
                        "NewAmazing response exceeded the configured size limit"
                    )
                output.write(chunk)
                digest.update(chunk)
    except BaseException:
        if created:
            destination.unlink(missing_ok=True)
        raise
    if byte_count == 0:
        raise BriefingSourceError("NewAmazing returned an empty response")
    return byte_count, digest.hexdigest()


def _validated_temp_parent(value: Path | None) -> str | None:
    if value is None:
        return None
    parent = value.expanduser().resolve()
    if not parent.is_dir():
        raise BriefingInputError("NewAmazing temp parent must be an existing directory")
    return str(parent)
