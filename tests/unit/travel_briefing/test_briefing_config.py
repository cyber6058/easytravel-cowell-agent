import hashlib
import json
from pathlib import Path

import pytest

from travel_briefing.config import load_config, parse_config
from travel_briefing.errors import BriefingInputError
from tests.unit.travel_briefing.test_list_calibration import manifest


def valid_config(tmp_path):
    private = tmp_path / "private"
    private.mkdir(exist_ok=True)
    template = private / "LIST-master.docx"
    template.write_bytes(b"synthetic master")
    calibrated = manifest()
    manifest_path = private / "calibration-manifest.json"
    payload = calibrated.to_dict()
    payload["master_sha256"] = hashlib.sha256(
        template.read_bytes()
    ).hexdigest()
    manifest_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    ffmpeg = tmp_path / "ffmpeg.exe"
    ffmpeg.write_bytes(b"synthetic executable")
    pdftoppm = tmp_path / "pdftoppm.exe"
    pdftoppm.write_bytes(b"synthetic executable")
    return {
        "output": {"root": str(tmp_path / "output" / "briefings")},
        "template": {
            "master_path": str(template),
            "calibration_manifest": str(manifest_path),
        },
        "tools": {
            "ffmpeg": str(ffmpeg),
            "pdftoppm": str(pdftoppm),
        },
    }


def test_config_contains_only_local_output_template_and_tool_paths(tmp_path):
    config = parse_config(valid_config(tmp_path))

    assert config.output_root == (tmp_path / "output" / "briefings").resolve()
    assert config.master_path == (
        tmp_path / "private" / "LIST-master.docx"
    ).resolve()
    assert config.calibration_manifest_path == (
        tmp_path / "private" / "calibration-manifest.json"
    ).resolve()
    assert config.master_sha256 == hashlib.sha256(
        b"synthetic master"
    ).hexdigest()
    assert config.calibration_manifest_sha256
    assert config.master_structure_fingerprint == (
        config.calibration_manifest.master_structure_fingerprint
    )
    assert config.source_header_qr_candidate_count == 1
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


def test_legacy_template_config_requires_explicit_recalibration(tmp_path):
    raw = valid_config(tmp_path)
    raw["template"] = {
        "path": str(tmp_path / "LIST-private.doc"),
        "layout_fingerprint": "a" * 64,
    }

    with pytest.raises(
        BriefingInputError,
        match="LIST_RECALIBRATION_REQUIRED",
    ):
        parse_config(raw)


def test_config_rejects_changed_master_manifest_and_output_overlap(tmp_path):
    raw = valid_config(tmp_path)
    Path(raw["template"]["master_path"]).write_bytes(b"changed")
    with pytest.raises(BriefingInputError, match="LIST_RECALIBRATION_REQUIRED"):
        parse_config(raw)

    second = tmp_path / "second"
    second.mkdir()
    raw = valid_config(second)
    raw["output"]["root"] = str(tmp_path / "second" / "private")
    with pytest.raises(BriefingInputError, match="private"):
        parse_config(raw)
