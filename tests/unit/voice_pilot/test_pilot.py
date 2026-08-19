from __future__ import annotations

import hashlib
import json
import re
import struct
import wave
from pathlib import Path

import pytest

from scripts.voice_pilot import pilot as pilot_module
from scripts.voice_pilot.pilot import (
    build_blind_pack,
    freeze_script,
    main as pilot_main,
    normalize_pcm_wav,
    probe_pcm_wav,
    verify_blind_pack,
    verify_frozen_script,
)
from scripts.voice_pilot.synthesize_yating_baseline import (
    main as yating_main,
    synthesize_baseline,
)
from travel_briefing.errors import UnknownAudioResultError
from travel_briefing.narration import segment_narration


def _synthetic_script() -> str:
    return f"{'甲' * 72}\n\n{'乙' * 72}\n\n{'丙' * 72}\n"


class SyntheticYatingAdapter:
    def __init__(self) -> None:
        self.call_count = 0

    def synthesize(self, job_path, *, timeout_seconds: int) -> None:
        self.call_count += 1
        job = json.loads(job_path.read_text(encoding="utf-8"))
        names = re.findall(r'<mark name="([^"]+)"/>', job["ssml"])
        segment_count = len(names) + 1
        with wave.open(job["output_wav"], "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(16_000)
            output.writeframes(b"\x01\x00" * (1_600 * segment_count))
        Path(job["output_bookmarks"]).write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "voice": "Microsoft Yating",
                    "markers": [
                        {
                            "type": "Speech:Bookmark",
                            "name": name,
                            "time_ticks": index * 1_000_000,
                        }
                        for index, name in enumerate(names, start=1)
                    ],
                }
            ),
            encoding="utf-8",
        )


class PartialUnknownYatingAdapter:
    def __init__(self) -> None:
        self.call_count = 0

    def synthesize(self, job_path, *, timeout_seconds: int) -> None:
        self.call_count += 1
        job = json.loads(job_path.read_text(encoding="utf-8"))
        with wave.open(job["output_wav"], "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(16_000)
            output.writeframes(b"\x01\x00" * 1_600)
        raise UnknownAudioResultError()


def _write_pcm_wav(
    path: Path,
    samples: list[int],
    *,
    channels: int = 1,
    sample_rate: int = 16_000,
) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(struct.pack(f"<{len(samples)}h", *samples))


def _write_float_wav(path: Path) -> None:
    sample_rate = 16_000
    sample_bytes = struct.pack("<f", 0.25) * sample_rate
    fmt = struct.pack(
        "<HHIIHH",
        3,
        1,
        sample_rate,
        sample_rate * 4,
        4,
        32,
    )
    body = b"fmt " + struct.pack("<I", len(fmt)) + fmt
    body += b"data" + struct.pack("<I", len(sample_bytes)) + sample_bytes
    path.write_bytes(b"RIFF" + struct.pack("<I", len(body) + 4) + b"WAVE" + body)


def _write_minute_wav(path: Path, first: int, second: int) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16_000)
        output.writeframes(struct.pack("<hh", first, second) * (16_000 * 30))


def test_freeze_script_writes_one_cue_and_preserves_canonical_text(tmp_path):
    input_path = tmp_path / "input.txt"
    input_path.write_text(_synthetic_script(), encoding="utf-8")

    result = freeze_script(input_path, output_dir=tmp_path / "frozen")

    expected_text = _synthetic_script()
    expected_speech = " ".join(("甲" * 72, "乙" * 72, "丙" * 72))
    assert result.text_path.read_text(encoding="utf-8") == expected_text
    assert result.srt_path.read_text(encoding="utf-8") == (
        "1\n"
        "00:00:00,000 --> 00:02:00,000\n"
        f"{expected_speech}\n"
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["non_whitespace_characters"] == 216
    assert manifest["cue_count"] == 1
    assert len(manifest["script_sha256"]) == 64
    assert [item["name"] for item in manifest["spans"]] == [
        "opening",
        "transition",
        "closing",
    ]
    assert verify_frozen_script(result.output_dir) == result


def test_freeze_script_locks_three_review_spans_and_hashes(tmp_path):
    paragraphs = (
        f"{'甲' * 71}。",
        f"{'乙' * 71}。",
        f"{'丙' * 71}。",
    )
    input_path = tmp_path / "input.txt"
    input_path.write_text("\n\n".join(paragraphs), encoding="utf-8")

    result = freeze_script(input_path, output_dir=tmp_path / "frozen")

    canonical_text = result.text_path.read_text(encoding="utf-8")
    narration_plan = segment_narration(canonical_text)
    actual_speech_text = "".join(segment.text for segment in narration_plan.segments)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["script_sha256"] == narration_plan.text_sha256
    assert result.srt_path.read_text(encoding="utf-8").endswith(
        actual_speech_text + "\n"
    )
    assert all(
        paragraph not in result.manifest_path.read_text(encoding="utf-8")
        for paragraph in paragraphs
    )


@pytest.mark.parametrize(
    "forbidden",
    (
        "待 OP 確認",
        "<!-- section:closing -->",
        "UNKNOWN_PRONUNCIATION_TERM",
        "\x00",
    ),
)
def test_freeze_script_rejects_private_placeholders_and_review_codes(
    tmp_path, forbidden
):
    forbidden_characters = sum(not character.isspace() for character in forbidden)
    first_paragraph = forbidden + "甲" * (72 - forbidden_characters)
    input_path = tmp_path / "input.txt"
    input_path.write_text(
        "\n\n".join((first_paragraph, "乙" * 72, "丙" * 72)),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="prohibited"):
        freeze_script(input_path, output_dir=tmp_path / "frozen")

    assert not (tmp_path / "frozen").exists()


def test_freeze_script_rejects_non_utf8_input(tmp_path):
    input_path = tmp_path / "input.txt"
    input_path.write_bytes(b"\xff\xfe\xfa")

    with pytest.raises(ValueError, match="valid UTF-8"):
        freeze_script(input_path, output_dir=tmp_path / "frozen")

    assert not (tmp_path / "frozen").exists()


def test_verify_script_detects_text_or_manifest_tampering(tmp_path):
    input_path = tmp_path / "input.txt"
    input_path.write_text(_synthetic_script(), encoding="utf-8")
    text_result = freeze_script(input_path, output_dir=tmp_path / "text-tamper")
    text_result.text_path.write_text(
        text_result.text_path.read_text(encoding="utf-8") + "甲",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Frozen-script"):
        verify_frozen_script(text_result.output_dir)

    manifest_result = freeze_script(
        input_path, output_dir=tmp_path / "manifest-tamper"
    )
    manifest = json.loads(manifest_result.manifest_path.read_text(encoding="utf-8"))
    manifest["unapproved_field"] = True
    manifest_result.manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="manifest contract"):
        verify_frozen_script(manifest_result.output_dir)


def test_script_cli_freezes_and_verifies_without_private_stdout(tmp_path, capsys):
    private_text = _synthetic_script()
    input_path = tmp_path / "input.txt"
    input_path.write_text(private_text, encoding="utf-8")
    output_dir = tmp_path / "frozen"

    assert (
        pilot_main(
            ["freeze-script", str(input_path), "--output-dir", str(output_dir)]
        )
        == 0
    )
    freeze_output = capsys.readouterr().out
    assert json.loads(freeze_output)["status"] == "frozen"
    assert private_text.strip() not in freeze_output

    assert pilot_main(["verify-script", str(output_dir)]) == 0
    verify_output = capsys.readouterr().out
    assert json.loads(verify_output)["status"] == "verified"
    assert private_text.strip() not in verify_output


def test_yating_wrapper_requires_ack_and_preserves_frozen_hash(tmp_path):
    input_path = tmp_path / "input.txt"
    input_path.write_text(_synthetic_script(), encoding="utf-8")
    frozen = freeze_script(input_path, output_dir=tmp_path / "frozen")
    adapter = SyntheticYatingAdapter()
    baseline_dir = tmp_path / "baseline"

    with pytest.raises(PermissionError, match="ack-local-yating-once"):
        synthesize_baseline(
            frozen.manifest_path,
            output_dir=baseline_dir,
            ack_local_yating_once=False,
            adapter=adapter,
        )

    assert adapter.call_count == 0
    assert not baseline_dir.exists()

    result = synthesize_baseline(
        frozen.manifest_path,
        output_dir=baseline_dir,
        ack_local_yating_once=True,
        adapter=adapter,
    )

    assert adapter.call_count > 1
    assert result.script_sha256 == frozen.script_sha256
    attempt = json.loads(result.attempt_path.read_text(encoding="utf-8"))
    assert attempt["status"] == "completed"
    assert attempt["script_sha256"] == frozen.script_sha256
    assert "甲" * 72 not in result.attempt_path.read_text(encoding="utf-8")
    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata["narration_text_sha256"] == frozen.script_sha256
    assert metadata["synthesis_chunk_count"] == adapter.call_count


def test_yating_wrapper_preserves_unknown_evidence_without_retry_or_overwrite(
    tmp_path,
):
    input_path = tmp_path / "input.txt"
    input_path.write_text(_synthetic_script(), encoding="utf-8")
    frozen = freeze_script(input_path, output_dir=tmp_path / "frozen")
    adapter = PartialUnknownYatingAdapter()
    baseline_dir = tmp_path / "baseline"

    with pytest.raises(UnknownAudioResultError):
        synthesize_baseline(
            frozen.manifest_path,
            output_dir=baseline_dir,
            ack_local_yating_once=True,
            adapter=adapter,
        )

    assert adapter.call_count == 1
    attempt = json.loads((baseline_dir / "attempt.json").read_text(encoding="utf-8"))
    assert attempt["status"] == "unknown"
    assert attempt["attempt_count"] == 1
    assert attempt["adapter_evidence"]["wav"]["exists"] is True
    assert attempt["retry_attempted"] is False
    assert attempt["fallback_attempted"] is False

    second_adapter = SyntheticYatingAdapter()
    with pytest.raises(FileExistsError):
        synthesize_baseline(
            frozen.manifest_path,
            output_dir=baseline_dir,
            ack_local_yating_once=True,
            adapter=second_adapter,
        )
    assert second_adapter.call_count == 0


def test_yating_cli_requires_literal_ack_and_keeps_stdout_private(tmp_path, capsys):
    private_text = _synthetic_script()
    input_path = tmp_path / "input.txt"
    input_path.write_text(private_text, encoding="utf-8")
    frozen = freeze_script(input_path, output_dir=tmp_path / "frozen")
    baseline_dir = tmp_path / "baseline"
    adapter = SyntheticYatingAdapter()

    with pytest.raises(PermissionError, match="ack-local-yating-once"):
        yating_main(
            [
                "--script-manifest",
                str(frozen.manifest_path),
                "--output-dir",
                str(baseline_dir),
            ],
            adapter=adapter,
        )
    assert adapter.call_count == 0
    assert not baseline_dir.exists()

    assert (
        yating_main(
            [
                "--script-manifest",
                str(frozen.manifest_path),
                "--output-dir",
                str(baseline_dir),
                "--ack-local-yating-once",
            ],
            adapter=adapter,
        )
        == 0
    )
    stdout = capsys.readouterr().out
    assert json.loads(stdout)["status"] == "completed"
    assert private_text.strip() not in stdout


def test_probe_rejects_silence_stereo_non_pcm_and_clipping(tmp_path):
    silence = tmp_path / "silence.wav"
    stereo = tmp_path / "stereo.wav"
    non_pcm = tmp_path / "float.wav"
    clipped = tmp_path / "clipped.wav"
    _write_pcm_wav(silence, [0] * 16_000)
    _write_pcm_wav(stereo, [500, -500] * 16_000, channels=2)
    _write_float_wav(non_pcm)
    _write_pcm_wav(clipped, [500] * 15_999 + [32_767])

    with pytest.raises(ValueError, match="non-zero RMS"):
        probe_pcm_wav(silence, minimum_duration_seconds=0.5)
    with pytest.raises(ValueError, match="mono"):
        probe_pcm_wav(stereo, minimum_duration_seconds=0.5)
    with pytest.raises(ValueError, match="PCM"):
        probe_pcm_wav(non_pcm, minimum_duration_seconds=0.5)
    with pytest.raises(ValueError, match="clipped"):
        probe_pcm_wav(clipped, minimum_duration_seconds=0.5)


def test_normalization_matches_minus_23_dbfs_without_touching_inputs(tmp_path):
    source = tmp_path / "source.wav"
    output = tmp_path / "normalized.wav"
    _write_pcm_wav(source, [1_000, -1_000] * 8_000)
    source_before = source.read_bytes()

    result = normalize_pcm_wav(
        source,
        output_path=output,
        minimum_duration_seconds=0.5,
    )

    assert source.read_bytes() == source_before
    assert result.path == output.resolve()
    assert result.sample_rate == 16_000
    assert result.channels == 1
    assert result.bits_per_sample == 16
    assert result.duration_seconds == 1.0
    assert result.rms_dbfs == pytest.approx(-23.0, abs=0.02)
    assert result.peak_dbfs <= -1.0


def test_normalization_fails_when_peak_ceiling_and_rms_target_conflict(tmp_path):
    high_crest = tmp_path / "high-crest.wav"
    _write_pcm_wav(high_crest, [100, -100] * 7_999 + [10_000, -10_000])
    blocked_output = tmp_path / "blocked.wav"

    with pytest.raises(ValueError, match="conflicts with the peak ceiling"):
        normalize_pcm_wav(
            high_crest,
            output_path=blocked_output,
            minimum_duration_seconds=0.5,
        )
    assert not blocked_output.exists()

    normal = tmp_path / "normal.wav"
    _write_pcm_wav(normal, [1_000, -1_000] * 8_000)
    existing = tmp_path / "existing.wav"
    existing.write_bytes(b"existing evidence")
    with pytest.raises(FileExistsError):
        normalize_pcm_wav(
            normal,
            output_path=existing,
            minimum_duration_seconds=0.5,
        )
    assert existing.read_bytes() == b"existing evidence"


def test_blind_pack_hides_engine_identity_and_uses_injected_mapping_in_tests(
    tmp_path,
):
    input_path = tmp_path / "input.txt"
    input_path.write_text(_synthetic_script(), encoding="utf-8")
    frozen = freeze_script(input_path, output_dir=tmp_path / "frozen")
    baseline = tmp_path / "Yating-source.wav"
    candidate = tmp_path / "ZipVoice-source.wav"
    _write_pcm_wav(baseline, [1_000, -1_000] * 8_000)
    _write_pcm_wav(candidate, [800, -1_200] * 8_000)

    result = build_blind_pack(
        baseline_wav=baseline,
        candidate_wav=candidate,
        script_manifest=frozen.manifest_path,
        output_dir=tmp_path / "blind",
        chooser=lambda roles: "candidate",
        minimum_duration_seconds=0.5,
        maximum_duration_seconds=1.5,
    )

    reveal = json.loads(result.reveal_path.read_text(encoding="utf-8"))
    assert reveal["assignment"] == {"A": "candidate", "B": "baseline"}
    review_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in result.review_dir.iterdir()
        if path.suffix in {".json", ".md"}
    ).casefold()
    assert "yating" not in review_text
    assert "zipvoice" not in review_text
    assert baseline.name.casefold() not in review_text
    assert candidate.name.casefold() not in review_text
    assert probe_pcm_wav(
        result.review_dir / "A.wav", minimum_duration_seconds=0.5
    ).rms_dbfs == pytest.approx(-23.0, abs=0.02)
    assert verify_blind_pack(result.output_dir) == result


def test_blind_pack_rejects_script_hash_or_duration_mismatch(tmp_path):
    input_path = tmp_path / "input.txt"
    input_path.write_text(_synthetic_script(), encoding="utf-8")
    frozen = freeze_script(input_path, output_dir=tmp_path / "frozen")
    baseline = tmp_path / "baseline.wav"
    candidate = tmp_path / "candidate.wav"
    _write_pcm_wav(baseline, [1_000, -1_000] * 8_000)
    _write_pcm_wav(candidate, [800, -1_200] * 16_000)

    frozen.text_path.write_text(
        frozen.text_path.read_text(encoding="utf-8") + "甲",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Frozen-script"):
        build_blind_pack(
            baseline_wav=baseline,
            candidate_wav=candidate,
            script_manifest=frozen.manifest_path,
            output_dir=tmp_path / "script-blocked",
            minimum_duration_seconds=0.5,
            maximum_duration_seconds=1.5,
        )
    assert not (tmp_path / "script-blocked").exists()

    clean_frozen = freeze_script(input_path, output_dir=tmp_path / "clean-frozen")
    with pytest.raises(ValueError, match="duration"):
        build_blind_pack(
            baseline_wav=baseline,
            candidate_wav=candidate,
            script_manifest=clean_frozen.manifest_path,
            output_dir=tmp_path / "duration-blocked",
            minimum_duration_seconds=0.5,
            maximum_duration_seconds=1.5,
        )
    assert not (tmp_path / "duration-blocked").exists()


def test_verify_blind_pack_detects_tampering_and_reveal_leakage(tmp_path):
    input_path = tmp_path / "input.txt"
    input_path.write_text(_synthetic_script(), encoding="utf-8")
    frozen = freeze_script(input_path, output_dir=tmp_path / "frozen")
    baseline = tmp_path / "engine-one.wav"
    candidate = tmp_path / "engine-two.wav"
    _write_pcm_wav(baseline, [1_000, -1_000] * 8_000)
    _write_pcm_wav(candidate, [800, -1_200] * 8_000)

    tampered = build_blind_pack(
        baseline_wav=baseline,
        candidate_wav=candidate,
        script_manifest=frozen.manifest_path,
        output_dir=tmp_path / "tampered",
        chooser=lambda roles: "baseline",
        minimum_duration_seconds=0.5,
        maximum_duration_seconds=1.5,
    )
    audio_path = tampered.review_dir / "A.wav"
    audio_bytes = bytearray(audio_path.read_bytes())
    audio_bytes[-2] ^= 1
    audio_path.write_bytes(audio_bytes)
    with pytest.raises(ValueError, match="WAV hash or format mismatch"):
        verify_blind_pack(tampered.output_dir)

    leaked = build_blind_pack(
        baseline_wav=baseline,
        candidate_wav=candidate,
        script_manifest=frozen.manifest_path,
        output_dir=tmp_path / "leaked",
        chooser=lambda roles: "candidate",
        minimum_duration_seconds=0.5,
        maximum_duration_seconds=1.5,
    )
    leaked.scorecard_path.write_text(
        leaked.scorecard_path.read_text(encoding="utf-8")
        + "\n來源提示：engine-one\n",
        encoding="utf-8",
    )
    manifest = json.loads(leaked.manifest_path.read_text(encoding="utf-8"))
    manifest["scorecard"]["sha256"] = hashlib.sha256(
        leaked.scorecard_path.read_bytes()
    ).hexdigest()
    leaked.manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="leaks source identity"):
        verify_blind_pack(leaked.output_dir)


def test_blind_pack_cli_builds_and_verifies_with_production_duration_bounds(
    tmp_path, capsys
):
    private_text = _synthetic_script()
    input_path = tmp_path / "input.txt"
    input_path.write_text(private_text, encoding="utf-8")
    frozen = freeze_script(input_path, output_dir=tmp_path / "frozen")
    baseline = tmp_path / "engine-one.wav"
    candidate = tmp_path / "engine-two.wav"
    _write_minute_wav(baseline, 1_000, -1_000)
    _write_minute_wav(candidate, 800, -1_200)
    output_dir = tmp_path / "blind"

    assert (
        pilot_main(
            [
                "build-blind-pack",
                "--baseline-wav",
                str(baseline),
                "--candidate-wav",
                str(candidate),
                "--script-manifest",
                str(frozen.manifest_path),
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )
    build_stdout = capsys.readouterr().out
    assert json.loads(build_stdout)["status"] == "built"
    assert private_text.strip() not in build_stdout

    assert pilot_main(["verify-blind-pack", str(output_dir)]) == 0
    verify_stdout = capsys.readouterr().out
    assert json.loads(verify_stdout)["status"] == "verified"
    assert private_text.strip() not in verify_stdout


def test_private_outputs_inside_repo_must_stay_under_ignored_root(
    tmp_path, monkeypatch
):
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    monkeypatch.setattr(pilot_module, "_REPO_ROOT", fake_repo)
    input_path = tmp_path / "input.txt"
    input_path.write_text(_synthetic_script(), encoding="utf-8")
    unsafe_output = fake_repo / "docs" / "private-voice"

    with pytest.raises(ValueError, match="output/voice-pilot"):
        freeze_script(input_path, output_dir=unsafe_output)
    assert not unsafe_output.exists()

    allowed = freeze_script(
        input_path,
        output_dir=fake_repo / "output" / "voice-pilot" / "safe-run",
    )
    assert allowed.output_dir.is_dir()
