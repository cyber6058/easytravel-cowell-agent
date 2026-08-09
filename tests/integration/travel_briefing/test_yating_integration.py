import json
import os
import sys
import wave
from pathlib import Path

import pytest

from travel_briefing.adapters.windows_media_speech import WindowsMediaSpeechAdapter
from travel_briefing.audio import synthesize_yating
from travel_briefing.narration import segment_narration


_OPTED_IN = (
    sys.platform == "win32"
    and os.environ.get("RUN_BRIEFING_YATING_INTEGRATION") == "1"
)

pytestmark = pytest.mark.skipif(
    not _OPTED_IN,
    reason=(
        "set RUN_BRIEFING_YATING_INTEGRATION=1 on Windows with "
        "Microsoft Yating installed"
    ),
)


def test_real_yating_pipeline_decodes_wav_and_validates_bookmark_srt(tmp_path):
    script = (
        Path(__file__).parents[3]
        / "scripts"
        / "briefing"
        / "synthesize_yating.ps1"
    )
    plan = segment_narration(
        "各位旅客您好。今天說明集合時間與行李規定。"
        "出發前請再次確認護照與隨身物品。"
    )

    result = synthesize_yating(
        plan,
        output_wav=tmp_path / "yating.wav",
        output_srt=tmp_path / "yating.srt",
        output_txt=tmp_path / "yating.txt",
        output_metadata=tmp_path / "yating.json",
        adapter=WindowsMediaSpeechAdapter(script_path=script),
        timeout_seconds=60,
    )

    with wave.open(str(result.wav_path), "rb") as rendered:
        assert rendered.getcomptype() == "NONE"
        assert rendered.getsampwidth() == 2
        assert rendered.getnchannels() == 1
        assert rendered.getframerate() > 0
        assert rendered.getnframes() > 0
        end_ms = (
            rendered.getnframes() * 1_000 + rendered.getframerate() // 2
        ) // rendered.getframerate()
    assert result.bookmark_count == len(plan.segments) - 1
    assert result.duration_seconds > 0
    srt = result.srt_path.read_text(encoding="utf-8")
    assert srt.startswith("1\n00:00:00,000 --> ")
    assert srt.count(" --> ") == len(plan.segments)
    hours, remainder = divmod(end_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    assert (
        f" --> {hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}\n"
        in srt
    )
    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata["voice"] == "Microsoft Yating"
    assert metadata["bookmark_count"] == len(plan.segments) - 1
