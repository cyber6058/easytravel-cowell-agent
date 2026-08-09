from travel_briefing.narration import segment_narration


def test_narration_is_segmented_in_order_with_a_stable_text_hash():
    plan = segment_narration(
        "各位旅客您好。這是合成測試內容，請確認集合資訊！"
        "第二段會保留數字 100V 與 JX820。"
    )

    assert [segment.segment_id for segment in plan.segments] == [
        "segment-001",
        "segment-002",
        "segment-003",
    ]
    assert [segment.text for segment in plan.segments] == [
        "各位旅客您好。",
        "這是合成測試內容，請確認集合資訊！",
        "第二段會保留數字 100V 與 JX820。",
    ]
    assert (
        plan.text_sha256
        == "cf2b5133cbf9f6e1109733c79479e14c60fd8d77997961fad27f6252035bf736"
    )


def test_long_sentence_prefers_clause_boundaries_for_mobile_subtitles():
    plan = segment_narration(
        "請攜帶護照，確認集合時間，並依現場領隊指示行動。",
        max_chars=12,
    )

    assert [segment.text for segment in plan.segments] == [
        "請攜帶護照，",
        "確認集合時間，",
        "並依現場領隊指示行動。",
    ]
    assert all(len(segment.text) <= 12 for segment in plan.segments)
    assert "".join(segment.text for segment in plan.segments) == (
        "請攜帶護照，確認集合時間，並依現場領隊指示行動。"
    )
