import subprocess

from travel_briefing.adapters.windows_speech import WindowsSpeechAdapter


class RecordingRunner:
    def __init__(self) -> None:
        self.command = None
        self.options = None

    def __call__(self, command, **options):
        self.command = command
        self.options = options
        return subprocess.CompletedProcess(command, returncode=0, stdout="", stderr="")


def test_windows_speech_command_receives_only_the_utf8_job_path(tmp_path):
    script = tmp_path / "synthesize_hanhan.ps1"
    script.write_text("# synthetic adapter test", encoding="utf-8")
    job = tmp_path / "speech-job.json"
    secret_text = "這段合成講稿不能出現在 command line"
    job.write_text(secret_text, encoding="utf-8")
    runner = RecordingRunner()
    adapter = WindowsSpeechAdapter(
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
    assert secret_text not in " ".join(runner.command)
    assert runner.options["timeout"] == 30
