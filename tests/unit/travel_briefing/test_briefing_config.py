from pathlib import Path

import pytest

from travel_briefing.config import load_config, parse_config
from travel_briefing.errors import BriefingInputError


def valid_config(tmp_path):
    template = tmp_path / "LIST-private.doc"
    template.write_bytes(b"synthetic template")
    ffmpeg = tmp_path / "ffmpeg.exe"
    ffmpeg.write_bytes(b"synthetic executable")
    pdftoppm = tmp_path / "pdftoppm.exe"
    pdftoppm.write_bytes(b"synthetic executable")
    return {
        "output": {"root": str(tmp_path / "output" / "briefings")},
        "template": {
            "path": str(template),
            "layout_fingerprint": "a" * 64,
        },
        "tools": {
            "ffmpeg": str(ffmpeg),
            "pdftoppm": str(pdftoppm),
        },
    }


def test_config_contains_only_local_output_template_and_tool_paths(tmp_path):
    config = parse_config(valid_config(tmp_path))

    assert config.output_root == (tmp_path / "output" / "briefings").resolve()
    assert config.template_path == (tmp_path / "LIST-private.doc").resolve()
    assert config.template_layout_fingerprint == "a" * 64
    assert config.ffmpeg_path == (tmp_path / "ffmpeg.exe").resolve()
    assert config.pdftoppm_path == (tmp_path / "pdftoppm.exe").resolve()


def test_ffmpeg_may_be_omitted_but_word_qa_inputs_are_required(tmp_path):
    raw = valid_config(tmp_path)
    del raw["tools"]["ffmpeg"]

    config = parse_config(raw)

    assert config.ffmpeg_path is None

    del raw["tools"]["pdftoppm"]
    with pytest.raises(BriefingInputError, match="pdftoppm"):
        parse_config(raw)


def test_config_rejects_unknown_sections_and_fields(tmp_path):
    raw = valid_config(tmp_path)
    raw["network"] = {"url": "https://example.invalid"}

    with pytest.raises(BriefingInputError, match="unknown"):
        parse_config(raw)

    raw = valid_config(tmp_path)
    raw["output"]["publish"] = True
    with pytest.raises(BriefingInputError, match="unknown"):
        parse_config(raw)


def test_load_config_rejects_missing_or_invalid_toml(tmp_path):
    with pytest.raises(BriefingInputError, match="not found"):
        load_config(tmp_path / "missing.toml")

    invalid = tmp_path / "invalid.toml"
    invalid.write_text("[output\n", encoding="utf-8")
    with pytest.raises(BriefingInputError, match="invalid TOML"):
        load_config(invalid)


def test_config_rejects_an_output_root_that_is_already_a_file(tmp_path):
    raw = valid_config(tmp_path)
    output_file = tmp_path / "not-a-directory"
    output_file.write_text("synthetic", encoding="utf-8")
    raw["output"]["root"] = str(output_file)

    with pytest.raises(BriefingInputError, match="output root"):
        parse_config(raw)
