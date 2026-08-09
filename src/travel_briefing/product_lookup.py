from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .errors import BriefingInputError
from .input_validation import validate_newamazing_url


@dataclass(frozen=True, slots=True)
class ProductPageCandidate:
    product_code: str
    url: str
    title: str


@dataclass(frozen=True, slots=True)
class ProductLookupResult:
    status: str
    reason: str
    product_code: str
    candidate: ProductPageCandidate | None
    matching_candidates: tuple[ProductPageCandidate, ...]


def select_unique_product_page(
    product_code: str,
    candidates: tuple[ProductPageCandidate, ...],
) -> ProductLookupResult:
    normalized_code = _normalize_product_code(product_code)
    if not _is_legal_product_code(normalized_code):
        return _blocked("INVALID_PRODUCT_CODE", normalized_code)

    exact = tuple(
        item
        for item in candidates
        if _normalize_product_code(item.product_code) == normalized_code
    )
    normalized_candidates: list[ProductPageCandidate] = []
    seen_urls: set[str] = set()
    for item in exact:
        if not item.title.strip():
            return _blocked("INVALID_PRODUCT_PAGE_URL", normalized_code)
        try:
            validated_url = validate_newamazing_url(item.url)
        except BriefingInputError:
            return _blocked("INVALID_PRODUCT_PAGE_URL", normalized_code)
        if validated_url.value in seen_urls:
            continue
        seen_urls.add(validated_url.value)
        normalized_candidates.append(
            ProductPageCandidate(
                product_code=normalized_code,
                url=validated_url.value,
                title=item.title.strip(),
            )
        )

    matching = tuple(normalized_candidates)
    if not matching:
        return _blocked("PRODUCT_PAGE_NOT_FOUND", normalized_code)
    if len(matching) > 1:
        return ProductLookupResult(
            status="blocked",
            reason="PRODUCT_PAGE_AMBIGUOUS",
            product_code=normalized_code,
            candidate=None,
            matching_candidates=matching,
        )
    return ProductLookupResult(
        status="resolved",
        reason="",
        product_code=normalized_code,
        candidate=matching[0],
        matching_candidates=matching,
    )


def _blocked(reason: str, product_code: str) -> ProductLookupResult:
    return ProductLookupResult(
        status="blocked",
        reason=reason,
        product_code=product_code,
        candidate=None,
        matching_candidates=(),
    )


def _normalize_product_code(value: str) -> str:
    if not isinstance(value, str):
        return ""
    return unicodedata.normalize("NFKC", value).strip().upper()


def _is_legal_product_code(value: str) -> bool:
    return (
        re.fullmatch(r"[A-Z0-9](?:[A-Z0-9-]{3,30})[A-Z0-9]", value)
        is not None
        and "--" not in value
        and any(character.isalpha() for character in value)
        and any(character.isdigit() for character in value)
    )
