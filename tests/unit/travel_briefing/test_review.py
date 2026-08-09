import pytest

from travel_briefing.models import (
    BriefingDraft,
    Conflict,
    DraftStatus,
    DraftWarning,
    OpField,
    Product,
    SourceEvidence,
)
from travel_briefing.review import redact_sensitive_text, render_review


def review_draft() -> BriefingDraft:
    return BriefingDraft.create(
        status=DraftStatus.BLOCKED,
        generated_at="2026-08-09T12:30:00+08:00",
        product=Product(
            code="OSA-SYN-260901",
            name="合成大阪五日",
            region="大阪",
            day_count=5,
            departure_date="2026-09-01",
            return_date="2026-09-05",
            source_ids=("pdf-p001",),
        ),
        sources=(
            SourceEvidence(
                source_id="pdf-p001",
                kind="pdf_page",
                location=r"C:\private\synthetic.pdf#page=1",
                sha256="a" * 64,
                retrieved_at="2026-08-09T11:00:00+08:00",
                parser_version="pdf-itinerary/1",
            ),
            SourceEvidence(
                source_id="web-1",
                kind="newamazing_html",
                location=(
                    "https://www.newamazing.com.tw/EW/GO/GroupDetail.asp?"
                    "prodCd=OSA-SYN-260901"
                ),
                sha256="b" * 64,
                retrieved_at="2026-08-09T11:05:00+08:00",
                parser_version="newamazing-html/1",
            ),
        ),
        op_fields=(
            OpField(
                name="meeting_place",
                value="桃園機場第一航廈合成集合點",
                source="OP",
                confirmed=True,
            ),
            OpField(
                name="tour_leader_phone",
                value="0912-345-678",
                source="OP",
                confirmed=True,
            ),
        ),
        conflicts=(
            Conflict(
                field="days[1].hotel",
                source_a="pdf-p001",
                value_a="合成甲飯店",
                source_b="web-1",
                value_b="合成乙飯店",
                severity="blocking",
                decision="",
                decided_by="",
            ),
        ),
        warnings=(
            DraftWarning(
                code="MEAL_TEXT_DIFFERENCE",
                message="days[1].meals differs; PDF text retained",
                source_ids=("pdf-p001", "web-1"),
            ),
        ),
    )


def test_review_shows_traceable_questions_but_redacts_sensitive_values():
    draft = review_draft()

    review = render_review(draft)

    assert "# 說明會資料審核" in review
    assert draft.draft_id in review
    assert "BLOCKED" in review
    assert "synthetic.pdf#page=1" in review
    assert r"C:\private" not in review
    assert "https://www.newamazing.com.tw/EW/GO/GroupDetail.asp" in review
    assert "2026-08-09T11:00:00+08:00" in review
    assert "days[1].hotel" in review
    assert "合成甲飯店" in review
    assert "合成乙飯店" in review
    assert "請 OP 決定採用來源 A 或來源 B" in review
    assert "桃園機場第一航廈合成集合點" in review
    assert "0912-345-678" not in review
    assert "[電話已遮蔽]" in review
    assert "MEAL_TEXT_DIFFERENCE" in review


@pytest.mark.parametrize(
    "phone",
    [
        "0912-345-678",
        "+886 912 345 678",
        "02-1234-5678",
        "03 1234567",
    ],
)
def test_review_redacts_common_taiwan_phone_formats(phone):
    assert redact_sensitive_text(f"聯絡電話：{phone}") == "聯絡電話：[電話已遮蔽]"
