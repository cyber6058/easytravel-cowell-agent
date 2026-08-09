from travel_briefing.subtitles import SubtitleSegment, build_srt


def test_srt_uses_actual_wave_frames_for_a_continuous_timeline():
    srt = build_srt(
        (
            SubtitleSegment(
                segment_id="segment-001",
                text="各位旅客您好。",
                frame_count=44_100,
                sample_rate=44_100,
            ),
            SubtitleSegment(
                segment_id="segment-002",
                text="請確認集合時間。",
                frame_count=66_150,
                sample_rate=44_100,
            ),
        )
    )

    assert srt == (
        "1\n"
        "00:00:00,000 --> 00:00:01,000\n"
        "各位旅客您好。\n\n"
        "2\n"
        "00:00:01,000 --> 00:00:02,500\n"
        "請確認集合時間。\n"
    )


def test_srt_wraps_mobile_text_to_at_most_two_lines():
    srt = build_srt(
        (
            SubtitleSegment(
                segment_id="segment-001",
                text="12345678901234567890",
                frame_count=44_100,
                sample_rate=44_100,
            ),
        ),
        max_line_chars=10,
    )

    assert "1234567890\n1234567890\n" in srt
