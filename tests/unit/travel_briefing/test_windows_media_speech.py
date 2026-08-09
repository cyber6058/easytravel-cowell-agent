import subprocess
from pathlib import Path

import pytest

from travel_briefing.adapters.windows_media_speech import WindowsMediaSpeechAdapter
from travel_briefing.errors import (
    AudioSynthesisError,
    LocalTtsUnavailableError,
    UnknownAudioResultError,
)


class RecordingRunner:
    def __init__(self) -> None:
        self.command = None
        self.options = None

    def __call__(self, command, **options):
        self.command = command
        self.options = options
        return subprocess.CompletedProcess(command, returncode=0, stdout="", stderr="")


class ResultRunner:
    def __init__(self, return_code: int) -> None:
        self.return_code = return_code
        self.call_count = 0

    def __call__(self, command, **options):
        self.call_count += 1
        return subprocess.CompletedProcess(
            command,
            returncode=self.return_code,
            stdout="private SSML must stay hidden",
            stderr="private synthesis detail must stay hidden",
        )


class TimeoutRunner:
    def __init__(self) -> None:
        self.call_count = 0

    def __call__(self, command, **options):
        self.call_count += 1
        raise subprocess.TimeoutExpired(command, options["timeout"])


def test_windows_media_speech_command_receives_only_the_utf8_job_path(tmp_path):
    script = tmp_path / "synthesize_yating.ps1"
    script.write_text("# synthetic adapter test", encoding="utf-8")
    job = tmp_path / "speech-job.json"
    private_ssml = "<speak>旅客姓名與私人行程不得出現在 command line</speak>"
    job.write_text(private_ssml, encoding="utf-8")
    runner = RecordingRunner()
    adapter = WindowsMediaSpeechAdapter(
        script_path=script,
        powershell_executable="powershell.exe",
        runner=runner,
    )

    adapter.synthesize(job, timeout_seconds=30)

    assert runner.command == [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script.resolve()),
        "-JobPath",
        str(job.resolve()),
    ]
    assert private_ssml not in " ".join(runner.command)
    assert runner.options["timeout"] == 30
    assert runner.options["capture_output"] is True
    assert runner.options["encoding"] == "utf-8"


def test_windows_media_speech_maps_missing_voice_without_retry(tmp_path):
    script = tmp_path / "synthesize_yating.ps1"
    script.write_text("# synthetic adapter test", encoding="utf-8")
    job = tmp_path / "speech-job.json"
    job.write_text("{}", encoding="utf-8")
    runner = ResultRunner(21)
    adapter = WindowsMediaSpeechAdapter(script_path=script, runner=runner)

    with pytest.raises(LocalTtsUnavailableError) as caught:
        adapter.synthesize(job, timeout_seconds=30)

    assert runner.call_count == 1
    assert caught.value.code == "LOCAL_TTS_UNAVAILABLE"
    assert caught.value.message == "Local Yating TTS is unavailable"


def test_windows_media_speech_maps_failed_synthesis_without_output_leak(tmp_path):
    script = tmp_path / "synthesize_yating.ps1"
    script.write_text("# synthetic adapter test", encoding="utf-8")
    job = tmp_path / "speech-job.json"
    job.write_text("{}", encoding="utf-8")
    runner = ResultRunner(22)
    adapter = WindowsMediaSpeechAdapter(script_path=script, runner=runner)

    with pytest.raises(AudioSynthesisError) as caught:
        adapter.synthesize(job, timeout_seconds=30)

    assert runner.call_count == 1
    assert caught.value.message == "Local Yating synthesis failed"
    assert caught.value.details == {"return_code": 22}
    assert "private" not in str(caught.value.details)


def test_windows_media_speech_timeout_is_unknown_and_not_retried(tmp_path):
    script = tmp_path / "synthesize_yating.ps1"
    script.write_text("# synthetic adapter test", encoding="utf-8")
    job = tmp_path / "speech-job.json"
    job.write_text("{}", encoding="utf-8")
    runner = TimeoutRunner()
    adapter = WindowsMediaSpeechAdapter(script_path=script, runner=runner)

    with pytest.raises(UnknownAudioResultError):
        adapter.synthesize(job, timeout_seconds=1)

    assert runner.call_count == 1


def test_yating_powershell_contract_is_one_local_default_prosody_utterance():
    script = (
        Path(__file__).parents[3]
        / "scripts"
        / "briefing"
        / "synthesize_yating.ps1"
    )

    source = script.read_text(encoding="utf-8")

    assert source.count("SynthesizeSsmlToStreamAsync(") == 1
    assert "[Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices" in source
    assert 'DisplayName -ceq "Microsoft Yating"' in source
    assert 'Language -ceq "zh-TW"' in source
    assert "Windows.Media.IMediaMarker" in source
    assert "Speech:Bookmark" in source
    assert "FileMode]::CreateNew" in source
    assert "Hanhan" not in source
    assert "<prosody" not in source
    assert "Invoke-WebRequest" not in source
    assert "Invoke-RestMethod" not in source
    assert "http://" not in source
    assert "https://" not in source
