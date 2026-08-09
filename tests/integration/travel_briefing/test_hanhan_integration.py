import os
import sys
from pathlib import Path

import pytest

from travel_briefing.adapters.windows_speech import WindowsSpeechAdapter
from travel_briefing.audio import synthesize_hanhan
from travel_briefing.narration import segment_narration


pytestmark = pytest.mark.skipif(
    sys.platform != "win32"
    or os.environ.get("RUN_BRIEFING_HANHAN_INTEGRATION") != "1",
    reason="set RUN_BRIEFING_HANHAN_INTEGRATION=1 on Windows with Hanhan installed",
)


def test_real_hanhan_adapter_creates_valid_pcm_and_frame_timed_srt(tmp_path):
    project_root = Path(__file__).parents[3]
    adapter = WindowsSpeechAdapter(
        script_path=project_root / "scripts" / "briefing" / "synthesize_hanhan.ps1"
    )
    plan = segment_narration("這是合成的本機語音整合測試。")

    result = synthesize_hanhan(
        plan,
        output_wav=tmp_path / "hanhan-integration.wav",
        output_srt=tmp_path / "hanhan-integration.srt",
        adapter=adapter,
        timeout_seconds=30,
    )

    assert result.sample_rate == 44_100
    assert result.channels == 1
    assert result.duration_seconds > 0
    assert result.wav_path.stat().st_size > 44
    assert "00:00:00,000 -->" in result.srt_path.read_text(encoding="utf-8")
