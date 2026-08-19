from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import secrets
import shutil
import sys
import tempfile
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from travel_briefing.narration import segment_narration


_TEXT_NAME = "script.txt"
_SRT_NAME = "script.srt"
_MANIFEST_NAME = "script-manifest.json"
_SCRIPT_MANIFEST_KEYS = {
    "schema_version",
    "type",
    "script_sha256",
    "non_whitespace_characters",
    "cue_count",
    "spans",
    "artifacts",
}
_SPAN_NAMES = ("opening", "transition", "closing")
_PARAGRAPH_BOUNDARY = re.compile(r"(?:\r?\n)[ \t]*(?:\r?\n)+")
_WHITESPACE = re.compile(r"\s+")
_WAITING_FOR_OP = re.compile(r"待\s*OP\s*確認", re.IGNORECASE)
_SECTION_MARKER = re.compile(r"<!--\s*section\s*:", re.IGNORECASE)
_REVIEW_CODE = re.compile(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+")
_REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class FrozenScript:
    output_dir: Path
    manifest_path: Path
    text_path: Path
    srt_path: Path
    script_sha256: str
    non_whitespace_characters: int
    span_hashes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WaveProbe:
    path: Path
    sha256: str
    frame_count: int
    sample_rate: int
    channels: int
    bits_per_sample: int
    duration_seconds: float
    rms_dbfs: float
    peak_dbfs: float


@dataclass(frozen=True, slots=True)
class BlindPack:
    output_dir: Path
    review_dir: Path
    private_dir: Path
    manifest_path: Path
    scorecard_path: Path
    reveal_path: Path
    source_manifest_path: Path
    script_sha256: str


def freeze_script(input_path: Path, *, output_dir: Path) -> FrozenScript:
    source = input_path.expanduser().resolve()
    if not source.is_file():
        raise ValueError("Voice-pilot input must be an existing UTF-8 text file")
    try:
        raw_text = source.read_bytes().decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("Voice-pilot input must be valid UTF-8") from error
    paragraphs, canonical_text, speech_text = _canonicalize_script(raw_text)

    destination = validate_private_output_location(output_dir)
    destination.mkdir(parents=True, exist_ok=False)
    text_path = destination / _TEXT_NAME
    srt_path = destination / _SRT_NAME
    manifest_path = destination / _MANIFEST_NAME
    text_bytes = canonical_text.encode("utf-8")
    srt_bytes = _build_single_cue_srt(speech_text).encode("utf-8")
    text_path.write_bytes(text_bytes)
    srt_path.write_bytes(srt_bytes)

    span_hashes = tuple(_sha256_text(paragraph) for paragraph in paragraphs)
    manifest = {
        "schema_version": 1,
        "type": "easytravel_voice_pilot_frozen_script",
        "script_sha256": _sha256_text(speech_text),
        "non_whitespace_characters": sum(
            not character.isspace() for character in speech_text
        ),
        "cue_count": 1,
        "spans": [
            {
                "name": name,
                "sha256": span_hash,
                "non_whitespace_characters": sum(
                    not character.isspace() for character in paragraph
                ),
            }
            for name, span_hash, paragraph in zip(
                _SPAN_NAMES, span_hashes, paragraphs, strict=True
            )
        ],
        "artifacts": {
            "text": {"filename": _TEXT_NAME, "sha256": _sha256_bytes(text_bytes)},
            "srt": {"filename": _SRT_NAME, "sha256": _sha256_bytes(srt_bytes)},
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return verify_frozen_script(destination)


def verify_frozen_script(output_dir: Path) -> FrozenScript:
    directory = output_dir.expanduser().resolve()
    manifest_path = directory / _MANIFEST_NAME
    if not manifest_path.is_file():
        raise ValueError("Frozen-script manifest is missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Frozen-script manifest is not valid UTF-8 JSON") from error
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError("Frozen-script manifest schema is unsupported")
    if set(manifest) != _SCRIPT_MANIFEST_KEYS:
        raise ValueError("Frozen-script manifest contract is invalid")
    if manifest.get("type") != "easytravel_voice_pilot_frozen_script":
        raise ValueError("Frozen-script manifest type is invalid")

    text_path = directory / _TEXT_NAME
    srt_path = directory / _SRT_NAME
    if not text_path.is_file() or not srt_path.is_file():
        raise ValueError("Frozen-script artifact is missing")
    text_bytes = text_path.read_bytes()
    try:
        canonical_text = text_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("Frozen-script text is not valid UTF-8") from error
    paragraphs, expected_text, speech_text = _canonicalize_script(canonical_text)
    if canonical_text != expected_text:
        raise ValueError("Frozen-script text is not canonical")
    expected_srt = _build_single_cue_srt(speech_text).encode("utf-8")
    srt_bytes = srt_path.read_bytes()
    if srt_bytes != expected_srt:
        raise ValueError("Frozen-script SRT is not the canonical single cue")

    artifacts = manifest.get("artifacts")
    expected_artifacts = {
        "text": {"filename": _TEXT_NAME, "sha256": _sha256_bytes(text_bytes)},
        "srt": {"filename": _SRT_NAME, "sha256": _sha256_bytes(srt_bytes)},
    }
    if artifacts != expected_artifacts:
        raise ValueError("Frozen-script artifact hash mismatch")
    span_hashes = tuple(_sha256_text(paragraph) for paragraph in paragraphs)
    expected_spans = [
        {
            "name": name,
            "sha256": span_hash,
            "non_whitespace_characters": sum(
                not character.isspace() for character in paragraph
            ),
        }
        for name, span_hash, paragraph in zip(
            _SPAN_NAMES, span_hashes, paragraphs, strict=True
        )
    ]
    non_whitespace_characters = sum(
        not character.isspace() for character in speech_text
    )
    script_sha256 = _sha256_text(speech_text)
    if manifest.get("spans") != expected_spans:
        raise ValueError("Frozen-script span hash mismatch")
    if manifest.get("script_sha256") != script_sha256:
        raise ValueError("Frozen-script text hash mismatch")
    if manifest.get("non_whitespace_characters") != non_whitespace_characters:
        raise ValueError("Frozen-script character count mismatch")
    if manifest.get("cue_count") != 1:
        raise ValueError("Frozen-script cue count is invalid")
    return FrozenScript(
        output_dir=directory,
        manifest_path=manifest_path,
        text_path=text_path,
        srt_path=srt_path,
        script_sha256=script_sha256,
        non_whitespace_characters=non_whitespace_characters,
        span_hashes=span_hashes,
    )


def probe_pcm_wav(
    path: Path,
    *,
    minimum_duration_seconds: float = 60.0,
    maximum_duration_seconds: float = 90.0,
) -> WaveProbe:
    source_path = path.expanduser().resolve()
    if source_path.suffix.lower() != ".wav" or not source_path.is_file():
        raise ValueError("Voice-pilot audio must be an existing PCM WAV file")
    if minimum_duration_seconds < 0 or maximum_duration_seconds <= 0:
        raise ValueError("Voice-pilot duration bounds are invalid")
    if minimum_duration_seconds > maximum_duration_seconds:
        raise ValueError("Voice-pilot duration bounds are invalid")
    try:
        with wave.open(str(source_path), "rb") as source:
            if source.getcomptype() != "NONE":
                raise ValueError("Voice-pilot audio must use uncompressed PCM")
            channels = source.getnchannels()
            sample_width = source.getsampwidth()
            sample_rate = source.getframerate()
            frame_count = source.getnframes()
            frame_bytes = source.readframes(frame_count)
    except (EOFError, wave.Error) as error:
        raise ValueError("Voice-pilot audio must be a valid PCM WAV file") from error
    if channels != 1:
        raise ValueError("Voice-pilot audio must be mono")
    if sample_width != 2:
        raise ValueError("Voice-pilot audio must use 16-bit PCM")
    if not 16_000 <= sample_rate <= 48_000:
        raise ValueError("Voice-pilot sample rate must be between 16 and 48 kHz")
    duration_seconds = frame_count / sample_rate if sample_rate else 0.0
    if not minimum_duration_seconds <= duration_seconds <= maximum_duration_seconds:
        raise ValueError("Voice-pilot duration is outside the allowed range")
    if len(frame_bytes) != frame_count * sample_width:
        raise ValueError("Voice-pilot PCM frame data is incomplete")
    samples = array("h")
    samples.frombytes(frame_bytes)
    if sys.byteorder != "little":
        samples.byteswap()
    if not samples:
        raise ValueError("Voice-pilot audio must have non-zero RMS")
    if any(sample in (-32_768, 32_767) for sample in samples):
        raise ValueError("Voice-pilot audio contains clipped samples")
    squared_sum = sum(sample * sample for sample in samples)
    rms = math.sqrt(squared_sum / len(samples))
    if not math.isfinite(rms) or rms <= 0:
        raise ValueError("Voice-pilot audio must have finite non-zero RMS")
    peak = max(abs(sample) for sample in samples)
    return WaveProbe(
        path=source_path,
        sha256=_sha256_file(source_path),
        frame_count=frame_count,
        sample_rate=sample_rate,
        channels=channels,
        bits_per_sample=sample_width * 8,
        duration_seconds=duration_seconds,
        rms_dbfs=20.0 * math.log10(rms / 32_768.0),
        peak_dbfs=20.0 * math.log10(peak / 32_768.0),
    )


def normalize_pcm_wav(
    input_path: Path,
    *,
    output_path: Path,
    target_rms_dbfs: float = -23.0,
    peak_ceiling_dbfs: float = -1.0,
    minimum_duration_seconds: float = 60.0,
    maximum_duration_seconds: float = 90.0,
) -> WaveProbe:
    source_probe = probe_pcm_wav(
        input_path,
        minimum_duration_seconds=minimum_duration_seconds,
        maximum_duration_seconds=maximum_duration_seconds,
    )
    if target_rms_dbfs >= 0 or peak_ceiling_dbfs >= 0:
        raise ValueError("Voice-pilot normalization levels must be below 0 dBFS")
    gain_db = target_rms_dbfs - source_probe.rms_dbfs
    if source_probe.peak_dbfs + gain_db > peak_ceiling_dbfs + 1e-9:
        raise ValueError("Voice-pilot RMS target conflicts with the peak ceiling")
    gain = 10.0 ** (gain_db / 20.0)
    samples = _read_pcm16_mono_samples(source_probe.path)
    scaled = array("h", (round(sample * gain) for sample in samples))
    if any(sample in (-32_768, 32_767) for sample in scaled):
        raise ValueError("Voice-pilot normalization would clip the output")

    destination = output_path.expanduser().resolve()
    if destination.suffix.lower() != ".wav":
        raise ValueError("Voice-pilot normalized output must use the .wav extension")
    if not destination.parent.is_dir():
        raise ValueError("Voice-pilot normalized output directory does not exist")
    if sys.byteorder != "little":
        scaled.byteswap()
    created = False
    try:
        with destination.open("xb") as raw_output:
            created = True
            with wave.open(raw_output, "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(source_probe.sample_rate)
                output.writeframes(scaled.tobytes())
        result = probe_pcm_wav(
            destination,
            minimum_duration_seconds=minimum_duration_seconds,
            maximum_duration_seconds=maximum_duration_seconds,
        )
        if abs(result.rms_dbfs - target_rms_dbfs) > 0.05:
            raise ValueError("Voice-pilot normalized RMS is outside tolerance")
        if result.peak_dbfs > peak_ceiling_dbfs + 1e-9:
            raise ValueError("Voice-pilot normalized peak exceeds the ceiling")
        return result
    except Exception:
        if created:
            destination.unlink(missing_ok=True)
        raise


def build_blind_pack(
    *,
    baseline_wav: Path,
    candidate_wav: Path,
    script_manifest: Path,
    output_dir: Path,
    chooser: Callable[[tuple[str, str]], str] | None = None,
    minimum_duration_seconds: float = 60.0,
    maximum_duration_seconds: float = 90.0,
) -> BlindPack:
    destination = validate_private_output_location(output_dir)
    if destination.exists():
        raise FileExistsError(f"Blind-pack output already exists: {destination}")
    manifest_path = script_manifest.expanduser().resolve()
    frozen = verify_frozen_script(manifest_path.parent)
    if manifest_path != frozen.manifest_path:
        raise ValueError("Exact frozen-script manifest path is required")
    baseline_path = baseline_wav.expanduser().resolve()
    candidate_path = candidate_wav.expanduser().resolve()
    if baseline_path == candidate_path:
        raise ValueError("Blind-pack sources must be two different WAV files")

    with tempfile.TemporaryDirectory(prefix="easytravel-voice-pilot-blind-") as temp:
        temporary = Path(temp)
        normalized = {
            "baseline": normalize_pcm_wav(
                baseline_path,
                output_path=temporary / "baseline.wav",
                minimum_duration_seconds=minimum_duration_seconds,
                maximum_duration_seconds=maximum_duration_seconds,
            ),
            "candidate": normalize_pcm_wav(
                candidate_path,
                output_path=temporary / "candidate.wav",
                minimum_duration_seconds=minimum_duration_seconds,
                maximum_duration_seconds=maximum_duration_seconds,
            ),
        }
        choose = chooser or secrets.choice
        role_for_a = choose(("baseline", "candidate"))
        if role_for_a not in {"baseline", "candidate"}:
            raise ValueError("Blind-pack chooser returned an invalid role")
        role_for_b = "candidate" if role_for_a == "baseline" else "baseline"
        assignment = {"A": role_for_a, "B": role_for_b}

        review_dir = destination / "review"
        private_dir = destination / "private"
        review_dir.mkdir(parents=True, exist_ok=False)
        private_dir.mkdir(exist_ok=False)
        for label, role in assignment.items():
            shutil.copyfile(normalized[role].path, review_dir / f"{label}.wav")

        canonical_text = frozen.text_path.read_text(encoding="utf-8")
        paragraphs, _, _ = _canonicalize_script(canonical_text)
        scorecard_path = review_dir / "scorecard.md"
        scorecard_path.write_text(
            _build_scorecard(paragraphs, frozen.script_sha256),
            encoding="utf-8",
            newline="\n",
        )
        reveal_path = private_dir / "reveal.json"
        _write_json(
            reveal_path,
            {
                "schema_version": 1,
                "type": "easytravel_voice_pilot_blind_reveal",
                "assignment": assignment,
            },
        )
        source_manifest_path = private_dir / "source-manifest.json"
        _write_json(
            source_manifest_path,
            {
                "schema_version": 1,
                "type": "easytravel_voice_pilot_private_sources",
                "script": {
                    "manifest_path": str(frozen.manifest_path),
                    "manifest_sha256": _sha256_file(frozen.manifest_path),
                    "script_sha256": frozen.script_sha256,
                },
                "sources": {
                    "baseline": {
                        "path": str(baseline_path),
                        "sha256": _sha256_file(baseline_path),
                        "normalized_sha256": normalized["baseline"].sha256,
                    },
                    "candidate": {
                        "path": str(candidate_path),
                        "sha256": _sha256_file(candidate_path),
                        "normalized_sha256": normalized["candidate"].sha256,
                    },
                },
                "reveal": {
                    "filename": reveal_path.name,
                    "sha256": _sha256_file(reveal_path),
                },
            },
        )
        review_probes = {
            label: probe_pcm_wav(
                review_dir / f"{label}.wav",
                minimum_duration_seconds=minimum_duration_seconds,
                maximum_duration_seconds=maximum_duration_seconds,
            )
            for label in ("A", "B")
        }
        review_manifest_path = review_dir / "manifest.json"
        _write_json(
            review_manifest_path,
            {
                "schema_version": 1,
                "type": "easytravel_voice_pilot_blind_review",
                "script_sha256": frozen.script_sha256,
                "span_hashes": list(frozen.span_hashes),
                "duration_bounds": {
                    "minimum_seconds": minimum_duration_seconds,
                    "maximum_seconds": maximum_duration_seconds,
                },
                "normalization": {
                    "target_rms_dbfs": -23.0,
                    "peak_ceiling_dbfs": -1.0,
                },
                "artifacts": {
                    label: _wave_probe_manifest(review_probes[label])
                    for label in ("A", "B")
                },
                "scorecard": {
                    "filename": scorecard_path.name,
                    "sha256": _sha256_file(scorecard_path),
                },
                "private_source_manifest_sha256": _sha256_file(
                    source_manifest_path
                ),
            },
        )
    return verify_blind_pack(destination)


def validate_private_output_location(path: Path) -> Path:
    destination = path.expanduser().resolve()
    repository = Path(_REPO_ROOT).resolve()
    try:
        destination.relative_to(repository)
    except ValueError:
        return destination
    allowed_root = repository / "output" / "voice-pilot"
    try:
        destination.relative_to(allowed_root)
    except ValueError as error:
        raise ValueError(
            "Private voice-pilot output inside the repository must stay under "
            "output/voice-pilot"
        ) from error
    return destination


def verify_blind_pack(output_dir: Path) -> BlindPack:
    directory = output_dir.expanduser().resolve()
    review_dir = directory / "review"
    private_dir = directory / "private"
    expected_files = {
        Path("review/A.wav"),
        Path("review/B.wav"),
        Path("review/scorecard.md"),
        Path("review/manifest.json"),
        Path("private/reveal.json"),
        Path("private/source-manifest.json"),
    }
    actual_files = {
        path.relative_to(directory)
        for path in directory.rglob("*")
        if path.is_file()
    }
    if actual_files != expected_files:
        raise ValueError("Blind-pack file contract is invalid")

    manifest_path = review_dir / "manifest.json"
    scorecard_path = review_dir / "scorecard.md"
    reveal_path = private_dir / "reveal.json"
    source_manifest_path = private_dir / "source-manifest.json"
    review_manifest = _load_json(manifest_path, label="Blind-pack review manifest")
    source_manifest = _load_json(
        source_manifest_path, label="Blind-pack source manifest"
    )
    reveal = _load_json(reveal_path, label="Blind-pack reveal")
    if set(review_manifest) != {
        "schema_version",
        "type",
        "script_sha256",
        "span_hashes",
        "duration_bounds",
        "normalization",
        "artifacts",
        "scorecard",
        "private_source_manifest_sha256",
    }:
        raise ValueError("Blind-pack review manifest contract is invalid")
    if (
        review_manifest.get("schema_version") != 1
        or review_manifest.get("type") != "easytravel_voice_pilot_blind_review"
    ):
        raise ValueError("Blind-pack review manifest schema is invalid")
    if review_manifest.get("private_source_manifest_sha256") != _sha256_file(
        source_manifest_path
    ):
        raise ValueError("Blind-pack private source manifest hash mismatch")
    if set(source_manifest) != {
        "schema_version",
        "type",
        "script",
        "sources",
        "reveal",
    }:
        raise ValueError("Blind-pack source manifest contract is invalid")
    if (
        source_manifest.get("schema_version") != 1
        or source_manifest.get("type")
        != "easytravel_voice_pilot_private_sources"
    ):
        raise ValueError("Blind-pack source manifest schema is invalid")
    if source_manifest.get("reveal") != {
        "filename": reveal_path.name,
        "sha256": _sha256_file(reveal_path),
    }:
        raise ValueError("Blind-pack reveal hash mismatch")
    if (
        reveal.get("schema_version") != 1
        or reveal.get("type") != "easytravel_voice_pilot_blind_reveal"
        or set(reveal.get("assignment", {})) != {"A", "B"}
        or set(reveal["assignment"].values()) != {"baseline", "candidate"}
    ):
        raise ValueError("Blind-pack reveal contract is invalid")

    script = source_manifest.get("script")
    if not isinstance(script, dict):
        raise ValueError("Blind-pack script evidence is invalid")
    frozen_manifest_path = Path(str(script.get("manifest_path", ""))).resolve()
    frozen = verify_frozen_script(frozen_manifest_path.parent)
    if frozen_manifest_path != frozen.manifest_path:
        raise ValueError("Blind-pack frozen manifest path is invalid")
    if script != {
        "manifest_path": str(frozen.manifest_path),
        "manifest_sha256": _sha256_file(frozen.manifest_path),
        "script_sha256": frozen.script_sha256,
    }:
        raise ValueError("Blind-pack frozen script hash mismatch")
    if review_manifest.get("script_sha256") != frozen.script_sha256:
        raise ValueError("Blind-pack review script hash mismatch")
    if review_manifest.get("span_hashes") != list(frozen.span_hashes):
        raise ValueError("Blind-pack review span hash mismatch")

    sources = source_manifest.get("sources")
    if not isinstance(sources, dict) or set(sources) != {"baseline", "candidate"}:
        raise ValueError("Blind-pack source evidence is invalid")
    for role in ("baseline", "candidate"):
        evidence = sources[role]
        if not isinstance(evidence, dict) or set(evidence) != {
            "path",
            "sha256",
            "normalized_sha256",
        }:
            raise ValueError("Blind-pack source evidence contract is invalid")
        source_path = Path(str(evidence["path"])).resolve()
        if evidence["sha256"] != _sha256_file(source_path):
            raise ValueError("Blind-pack source WAV hash mismatch")

    bounds = review_manifest.get("duration_bounds")
    normalization = review_manifest.get("normalization")
    if not isinstance(bounds, dict) or set(bounds) != {
        "minimum_seconds",
        "maximum_seconds",
    }:
        raise ValueError("Blind-pack duration bounds are invalid")
    if normalization != {
        "target_rms_dbfs": -23.0,
        "peak_ceiling_dbfs": -1.0,
    }:
        raise ValueError("Blind-pack normalization contract is invalid")
    minimum = float(bounds["minimum_seconds"])
    maximum = float(bounds["maximum_seconds"])
    artifacts = review_manifest.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != {"A", "B"}:
        raise ValueError("Blind-pack artifact contract is invalid")
    for label in ("A", "B"):
        probe = probe_pcm_wav(
            review_dir / f"{label}.wav",
            minimum_duration_seconds=minimum,
            maximum_duration_seconds=maximum,
        )
        if artifacts[label] != _wave_probe_manifest(probe):
            raise ValueError("Blind-pack review WAV hash or format mismatch")
        role = reveal["assignment"][label]
        if sources[role]["normalized_sha256"] != probe.sha256:
            raise ValueError("Blind-pack reveal does not match review audio")
    if review_manifest.get("scorecard") != {
        "filename": scorecard_path.name,
        "sha256": _sha256_file(scorecard_path),
    }:
        raise ValueError("Blind-pack scorecard hash mismatch")

    review_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (manifest_path, scorecard_path)
    ).casefold()
    forbidden = {"yating", "zipvoice"}
    for role in ("baseline", "candidate"):
        source_path = Path(str(sources[role]["path"]))
        forbidden.add(source_path.name.casefold())
        forbidden.add(source_path.stem.casefold())
    if any(token and token in review_text for token in forbidden):
        raise ValueError("Blind-pack review leaks source identity")
    return BlindPack(
        output_dir=directory,
        review_dir=review_dir,
        private_dir=private_dir,
        manifest_path=manifest_path,
        scorecard_path=scorecard_path,
        reveal_path=reveal_path,
        source_manifest_path=source_manifest_path,
        script_sha256=frozen.script_sha256,
    )


def _canonicalize_script(text: str) -> tuple[tuple[str, ...], str, str]:
    try:
        text.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError("Voice-pilot input contains invalid Unicode") from error
    if (
        "\x00" in text
        or _WAITING_FOR_OP.search(text)
        or _SECTION_MARKER.search(text)
        or _REVIEW_CODE.search(text)
    ):
        raise ValueError("Voice-pilot input contains prohibited review content")
    stripped = text.strip()
    paragraphs = tuple(
        _WHITESPACE.sub(" ", paragraph).strip()
        for paragraph in _PARAGRAPH_BOUNDARY.split(stripped)
        if paragraph.strip()
    )
    if len(paragraphs) != 3:
        raise ValueError("Voice-pilot script must contain exactly three paragraphs")
    canonical_text = "\n\n".join(paragraphs) + "\n"
    narration_plan = segment_narration(canonical_text)
    speech_text = "".join(segment.text for segment in narration_plan.segments)
    non_whitespace_characters = sum(
        not character.isspace() for character in speech_text
    )
    if not 216 <= non_whitespace_characters <= 324:
        raise ValueError(
            "Voice-pilot script must contain 216 to 324 non-whitespace characters"
        )
    return paragraphs, canonical_text, speech_text


def _build_single_cue_srt(speech_text: str) -> str:
    return "1\n00:00:00,000 --> 00:02:00,000\n" + speech_text + "\n"


def _build_scorecard(paragraphs: tuple[str, ...], script_sha256: str) -> str:
    labels = ("開場", "重點提醒與轉場", "收尾")
    sections = []
    for label, paragraph in zip(labels, paragraphs, strict=True):
        sections.append(
            f"## {label}\n\n"
            f"{paragraph}\n\n"
            "- 自然度（1–5）：\n"
            "- 語調過平問題（有／無）：\n"
            "- 接縫問題（有／無）：\n"
            "- 本人相似度（1–5）：\n"
            "- 偏好（A／B／平手）：\n"
        )
    return (
        "# 說明會語音 A／B 盲測評分表\n\n"
        f"Script SHA-256：`{script_sha256}`\n\n"
        "請先完整聽完 A 與 B，再依固定三段評分；評分前不要查看 private 目錄。\n\n"
        + "\n".join(sections)
        + "\n## 正確性與整體判定\n\n"
        "- Critical terms 全部正確（是／否）：\n"
        "- 整體偏好（A／B／平手）：\n"
        "- 備註：\n"
    )


def _wave_probe_manifest(probe: WaveProbe) -> dict[str, object]:
    return {
        "filename": probe.path.name,
        "sha256": probe.sha256,
        "format": "PCM",
        "sample_rate": probe.sample_rate,
        "bits_per_sample": probe.bits_per_sample,
        "channels": probe.channels,
        "frame_count": probe.frame_count,
        "duration_seconds": probe.duration_seconds,
        "rms_dbfs": probe.rms_dbfs,
        "peak_dbfs": probe.peak_dbfs,
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _load_json(path: Path, *, label: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is not valid UTF-8 JSON") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _read_pcm16_mono_samples(path: Path) -> array:
    with wave.open(str(path), "rb") as source:
        frame_bytes = source.readframes(source.getnframes())
    samples = array("h")
    samples.frombytes(frame_bytes)
    if sys.byteorder != "little":
        samples.byteswap()
    return samples


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline EasyTravel voice-pilot tools")
    commands = parser.add_subparsers(dest="command", required=True)
    freeze = commands.add_parser("freeze-script")
    freeze.add_argument("input", type=Path)
    freeze.add_argument("--output-dir", required=True, type=Path)
    verify = commands.add_parser("verify-script")
    verify.add_argument("output_dir", type=Path)
    blind = commands.add_parser("build-blind-pack")
    blind.add_argument("--baseline-wav", required=True, type=Path)
    blind.add_argument("--candidate-wav", required=True, type=Path)
    blind.add_argument("--script-manifest", required=True, type=Path)
    blind.add_argument("--output-dir", required=True, type=Path)
    verify_blind = commands.add_parser("verify-blind-pack")
    verify_blind.add_argument("output_dir", type=Path)
    arguments = parser.parse_args(argv)

    if arguments.command == "freeze-script":
        result = freeze_script(arguments.input, output_dir=arguments.output_dir)
        payload = {
            "status": "frozen",
            "manifest": str(result.manifest_path),
            "script_sha256": result.script_sha256,
            "non_whitespace_characters": result.non_whitespace_characters,
            "cue_count": 1,
        }
    elif arguments.command == "verify-script":
        result = verify_frozen_script(arguments.output_dir)
        payload = {
            "status": "verified",
            "manifest": str(result.manifest_path),
            "script_sha256": result.script_sha256,
            "non_whitespace_characters": result.non_whitespace_characters,
            "cue_count": 1,
        }
    elif arguments.command == "build-blind-pack":
        result = build_blind_pack(
            baseline_wav=arguments.baseline_wav,
            candidate_wav=arguments.candidate_wav,
            script_manifest=arguments.script_manifest,
            output_dir=arguments.output_dir,
        )
        payload = {
            "status": "built",
            "manifest": str(result.manifest_path),
            "scorecard": str(result.scorecard_path),
            "script_sha256": result.script_sha256,
        }
    else:
        result = verify_blind_pack(arguments.output_dir)
        payload = {
            "status": "verified",
            "manifest": str(result.manifest_path),
            "scorecard": str(result.scorecard_path),
            "script_sha256": result.script_sha256,
        }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
