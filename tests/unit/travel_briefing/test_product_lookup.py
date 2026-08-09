import pytest

from travel_briefing.product_lookup import (
    ProductPageCandidate,
    select_unique_product_page,
)


PRODUCT_CODE = "TOH-SYN-260901"


def candidate(
    *,
    code: str = PRODUCT_CODE,
    url: str = (
        "https://www.newamazing.com.tw/GroupDetail.asp?GroupNo=TOH-SYN-260901"
    ),
    title: str = "合成東北五日",
) -> ProductPageCandidate:
    return ProductPageCandidate(product_code=code, url=url, title=title)


def test_product_lookup_resolves_one_exact_allowlisted_candidate():
    result = select_unique_product_page(
        PRODUCT_CODE,
        (
            candidate(code="TOH-SYN-OTHER"),
            candidate(),
        ),
    )

    assert result.status == "resolved"
    assert result.reason == ""
    assert result.product_code == PRODUCT_CODE
    assert result.candidate == candidate()
    assert result.matching_candidates == (candidate(),)


@pytest.mark.parametrize(
    ("candidates", "reason"),
    [
        ((), "PRODUCT_PAGE_NOT_FOUND"),
        ((candidate(code="TOH-SYN-OTHER"),), "PRODUCT_PAGE_NOT_FOUND"),
        (
            (
                candidate(),
                candidate(
                    url=(
                        "https://www.newamazing.com.tw/print/GroupDetail.asp?"
                        "GroupNo=TOH-SYN-260901"
                    )
                ),
            ),
            "PRODUCT_PAGE_AMBIGUOUS",
        ),
    ],
)
def test_product_lookup_blocks_zero_or_multiple_exact_candidates(
    candidates,
    reason,
):
    result = select_unique_product_page(PRODUCT_CODE, candidates)

    assert result.status == "blocked"
    assert result.reason == reason
    assert result.candidate is None


@pytest.mark.parametrize(
    "product_code",
    ["", "JX!820", "無數字代碼", "123456", "A" * 33],
)
def test_product_lookup_blocks_invalid_pdf_product_codes(product_code):
    result = select_unique_product_page(product_code, (candidate(),))

    assert result.status == "blocked"
    assert result.reason == "INVALID_PRODUCT_CODE"
    assert result.candidate is None
    assert result.matching_candidates == ()


def test_product_lookup_blocks_an_exact_candidate_with_a_non_allowlisted_url():
    result = select_unique_product_page(
        PRODUCT_CODE,
        (candidate(url="https://example.invalid/GroupDetail.asp"),),
    )

    assert result.status == "blocked"
    assert result.reason == "INVALID_PRODUCT_PAGE_URL"
    assert result.candidate is None


def test_product_lookup_deduplicates_the_same_exact_url():
    duplicate = candidate()

    result = select_unique_product_page(PRODUCT_CODE, (duplicate, duplicate))

    assert result.status == "resolved"
    assert result.candidate == duplicate
    assert result.matching_candidates == (duplicate,)
