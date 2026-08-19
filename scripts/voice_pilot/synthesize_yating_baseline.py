from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts.voice_pilot.pilot import (
        validate_private_output_location,
        verify_frozen_script,
    )
except ModuleNotFoundError as error:
    if error.name != "scripts" and not str(error.name).startswith("scripts."):
        raise
    from pilot import validate_private_output_location, verify_frozen_script
from travel_briefing.adapters.windows_media_speech import WindowsMediaSpeechAdapter
from travel_briefing.audio import SpeechAdapter, synthesize_yating
from travel_briefing.errors import BriefingCliError
from travel_briefing.narration import segment_narration


@dataclass(frozen=True, slots=True)
class BaselineAttempt:
    output_dir: Path
    attempt_path: Path
    wav_path: Path
    srt_path: Path
    text_path: Path
    metadata_path: Path
    script_sha256: str


def synthesize_baseline(
    script_manifest: Path,
    *,
    output_dir: Path,
    ack_local_yating_once: bool,
    adapter: SpeechAdapter | None = None,
    timeout_seconds: int = 120,
) -> BaselineAttempt:
    if not ack_local_yating_once:
        raise PermissionError("--ack-local-yating-once is required")
    manifest_path = script_manifest.expanduser().resolve()
    frozen = verify_frozen_script(manifest_path.parent)
    if manifest_path != frozen.manifest_path:
        raise ValueError("Exact frozen-script manifest path is required")
    canonical_text = frozen.text_path.read_text(encoding="utf-8")
    narration_plan = segment_narration(canonical_text)
    if narration_plan.text_sha256 != frozen.script_sha256:
        raise ValueError("Frozen-script hash does not match the Yating narration plan")

    destination = validate_private_output_location(output_dir)
    destination.mkdir(parents=True, exist_ok=False)
    attempt_path = destination / "attempt.json"
    wav_path = destination / "baseline.wav"
    srt_path = destination / "baseline.srt"
    text_path = destination / "baseline.txt"
    metadata_path = destination / "baseline-yating.json"
    speech_adapter = adapter or WindowsMediaSpeechAdapter(
        script_path=(
            Path(__file__).resolve().parents[2]
            / "scripts"
            / "briefing"
            / "synthesize_yating.ps1"
        )
    )
    try:
        result = synthesize_yating(
            narration_plan,
            output_wav=wav_path,
            output_srt=srt_path,
            output_txt=text_path,
            output_metadata=metadata_path,
            adapter=speech_adapter,
            timeout_seconds=timeout_seconds,
        )
    except BriefingCliError as error:
        _write_attempt(
            attempt_path,
            {
                "schema_version": 1,
                "status": "unknown" if error.code == "AUDIO_RESULT_UNKNOWN" else "failed",
                "attempt_count": 1,
                "script_sha256": frozen.script_sha256,
                "error_code": error.code,
                "retry_attempted": False,
                "fallback_attempted": False,
                "adapter_evidence": error.details,
            },
        )
        raise
    _write_attempt(
        attempt_path,
        {
            "schema_version": 1,
            "status": "completed",
            "attempt_count": 1,
            "script_sha256": frozen.script_sha256,
            "script_manifest_sha256": _sha256_file(frozen.manifest_path),
            "segment_count": result.segment_count,
            "bookmark_count": result.bookmark_count,
            "duration_seconds": result.duration_seconds,
            "sample_rate": result.sample_rate,
            "channels": result.channels,
            "artifacts": {
                "wav": {"filename": wav_path.name, "sha256": result.wav_sha256},
                "srt": {"filename": srt_path.name, "sha256": result.srt_sha256},
                "text": {"filename": text_path.name, "sha256": result.txt_sha256},
                "metadata": {
                    "filename": metadata_path.name,
                    "sha256": result.metadata_sha256,
                },
            },
            "retry_attempted": False,
            "fallback_attempted": False,
        },
    )
    return BaselineAttempt(
        output_dir=destination,
        attempt_path=attempt_path,
        wav_path=wav_path,
        srt_path=srt_path,
        text_path=text_path,
        metadata_path=metadata_path,
        script_sha256=frozen.script_sha256,
    )


def _write_attempt(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(
    argv: list[str] | None = None,
    *,
    adapter: SpeechAdapter | None = None,
) -> int:
    parser = argparse.ArgumentParser(description="Run one local Yating baseline")
    parser.add_argument("--script-manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--ack-local-yating-once", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    arguments = parser.parse_args(argv)
    result = synthesize_baseline(
        arguments.script_manifest,
        output_dir=arguments.output_dir,
        ack_local_yating_once=arguments.ack_local_yating_once,
        adapter=adapter,
        timeout_seconds=arguments.timeout_seconds,
    )
    print(
        json.dumps(
            {
                "status": "completed",
                "attempt": str(result.attempt_path),
                "script_sha256": result.script_sha256,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
