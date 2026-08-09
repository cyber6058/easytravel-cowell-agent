from travel_briefing import capabilities
from travel_briefing.capabilities import configured_executable, tool_check


def test_cloud_or_mp3_tools_require_an_explicit_existing_executable(tmp_path):
    executable = tmp_path / "ffmpeg.exe"

    assert configured_executable(None) is None
    assert configured_executable(executable) is None

    executable.write_bytes(b"synthetic executable")

    assert configured_executable(executable) == executable.resolve()


def test_ffmpeg_found_on_path_is_reported_but_not_usable_without_configuration(
    monkeypatch, tmp_path
):
    executable = tmp_path / "ffmpeg.exe"
    executable.write_bytes(b"synthetic executable")
    monkeypatch.setattr(capabilities.shutil, "which", lambda _: str(executable))

    check = tool_check("ffmpeg", require_configured=True)

    assert check == {
        "status": "warning",
        "available": True,
        "usable": False,
        "configured_path": False,
        "discovery": "path",
    }
