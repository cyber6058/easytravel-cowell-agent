from __future__ import annotations

import hashlib
import re
import shutil
from dataclasses import replace
from pathlib import Path

from .models import Artifact, BriefingDraft
from .serialization import dumps_draft, loads_draft


_PRODUCT_CODE = re.compile(r"[A-Z0-9](?:[A-Z0-9-]{3,30})[A-Z0-9]")
_TIMESTAMP = re.compile(r"[0-9]{8}T[0-9]{6}(?:Z|[+-][0-9]{4})")
_ARTIFACT_STATUS = frozenset({"completed", "blocked", "missing"})


def create_run_directory(
    output_root: Path,
    *,
    product_code: str,
    timestamp: str,
) -> Path:
    code = _validated_product_code(product_code)
    stamp = _validated_timestamp(timestamp)
    root = output_root.expanduser().resolve()
    run = (root / code / stamp).resolve()
    if not run.is_relative_to(root):
        raise ValueError("Briefing run directory escaped the output root")
    root.mkdir(parents=True, exist_ok=True)
    run.parent.mkdir(exist_ok=True)
    try:
        run.mkdir()
    except FileExistsError as error:
        raise FileExistsError(f"Briefing run directory already exists: {run}") from error
    return run


def publish_text(run_directory: Path, name: str, text: str) -> Path:
    if not isinstance(text, str):
        raise TypeError("Briefing artifact content must be text")
    destination = _artifact_path(run_directory, name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with destination.open("x", encoding="utf-8", newline="\n") as output:
            created = True
            output.write(text)
    except BaseException:
        if created:
            destination.unlink(missing_ok=True)
        raise
    return destination


def copy_artifact(
    source: Path,
    run_directory: Path,
    name: str,
) -> Path:
    source_path = source.expanduser().resolve()
    if not source_path.is_file():
        raise ValueError("Briefing artifact source does not exist")
    destination = _artifact_path(run_directory, name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with source_path.open("rb") as input_stream, destination.open("xb") as output:
            created = True
            shutil.copyfileobj(input_stream, output)
    except BaseException:
        if created:
            destination.unlink(missing_ok=True)
        raise
    return destination


def artifact_record(
    run_directory: Path,
    *,
    kind: str,
    expected_name: str,
    status: str,
    generator_version: str,
) -> Artifact:
    if status not in _ARTIFACT_STATUS:
        raise ValueError("Briefing artifact status is unsupported")
    path = _artifact_path(run_directory, expected_name)
    exists = path.is_file()
    if status == "completed" and not exists:
        raise ValueError("Completed briefing artifact does not exist")
    if status == "missing" and exists:
        raise ValueError("Missing briefing artifact unexpectedly exists")
    return Artifact(
        kind=kind,
        expected_path=expected_name,
        actual_path=expected_name if exists else "",
        sha256=_sha256_file(path) if exists else "",
        status=status,
        generator_version=generator_version,
    )


def write_manifest(run_directory: Path, draft: BriefingDraft) -> Path:
    manifest = _artifact_path(run_directory, "manifest.json")
    manifest_draft = replace(draft, artifacts=tuple(draft.artifacts))
    published = publish_text(
        run_directory,
        manifest.name,
        dumps_draft(manifest_draft) + "\n",
    )
    try:
        publish_text(
            run_directory,
            "manifest.sha256",
            _sha256_file(published) + "\n",
        )
    except BaseException:
        published.unlink(missing_ok=True)
        raise
    return published


def load_run_manifest(
    output_root: Path,
    manifest_path: Path,
) -> tuple[Path, BriefingDraft]:
    root = output_root.expanduser().resolve()
    manifest = manifest_path.expanduser().resolve()
    if not manifest.is_file() or manifest.name != "manifest.json":
        raise ValueError("Briefing manifest must be an existing manifest.json")
    run = manifest.parent
    if not run.is_relative_to(root):
        raise ValueError("Briefing manifest is outside the configured output root")
    relative = run.relative_to(root)
    if len(relative.parts) != 2:
        raise ValueError("Briefing manifest does not use the exact run directory shape")
    _validated_product_code(relative.parts[0])
    _validated_timestamp(relative.parts[1])
    digest_path = run / "manifest.sha256"
    try:
        expected_digest = digest_path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError) as error:
        raise ValueError("Briefing manifest hash sidecar is missing") from error
    if re.fullmatch(r"[0-9a-f]{64}", expected_digest) is None:
        raise ValueError("Briefing manifest hash sidecar is invalid")
    if _sha256_file(manifest) != expected_digest:
        raise ValueError("Briefing manifest hash does not match its sidecar")
    try:
        draft = loads_draft(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise ValueError("Briefing manifest is invalid or changed") from error
    if draft.product.code != relative.parts[0]:
        raise ValueError("Briefing manifest product code does not match its directory")
    return run, draft


def verify_artifacts(
    run_directory: Path,
    artifacts: tuple[Artifact, ...],
) -> None:
    run = run_directory.expanduser().resolve()
    if not run.is_dir():
        raise ValueError("Briefing run directory does not exist")
    seen_kinds: set[str] = set()
    for artifact in artifacts:
        if not artifact.kind or artifact.kind in seen_kinds:
            raise ValueError("Briefing artifacts contain an invalid or duplicate kind")
        seen_kinds.add(artifact.kind)
        if artifact.status not in _ARTIFACT_STATUS:
            raise ValueError("Briefing artifact status is unsupported")
        _artifact_path(run, artifact.expected_path)
        if not artifact.actual_path:
            if artifact.status == "completed":
                raise ValueError("Completed briefing artifact has no actual path")
            if artifact.sha256:
                raise ValueError("Missing briefing artifact must not have a hash")
            continue
        if artifact.status == "missing":
            raise ValueError("Missing briefing artifact must not have an actual path")
        path = _artifact_path(run, artifact.actual_path)
        if not path.is_file():
            raise ValueError("Recorded briefing artifact is missing")
        if _sha256_file(path) != artifact.sha256:
            raise ValueError("Briefing artifact hash does not match the manifest")
        if artifact.expected_path != artifact.actual_path:
            raise ValueError("Briefing artifact actual path does not match expected path")


def _validated_product_code(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Briefing product code must be safe path text")
    code = value.strip().upper()
    if (
        _PRODUCT_CODE.fullmatch(code) is None
        or "--" in code
        or not any(character.isalpha() for character in code)
        or not any(character.isdigit() for character in code)
    ):
        raise ValueError("Briefing product code must be a safe product identifier")
    return code


def _validated_timestamp(value: str) -> str:
    if not isinstance(value, str) or _TIMESTAMP.fullmatch(value) is None:
        raise ValueError("Briefing timestamp must use YYYYMMDDTHHMMSS plus timezone")
    return value


def _artifact_path(run_directory: Path, name: str) -> Path:
    run = run_directory.expanduser().resolve()
    if not run.is_dir():
        raise ValueError("Briefing run directory does not exist")
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValueError(
            "Briefing artifact name/path must be safe relative text"
        )
    relative = Path(name)
    if (
        relative.is_absolute()
        or relative.drive
        or any(part in {"", ".", ".."} for part in relative.parts)
        or "//" in name
        or name.startswith("/")
        or name.endswith("/")
    ):
        raise ValueError(
            "Briefing artifact name/path must be safe relative text"
        )
    destination = (run / relative).resolve()
    if not destination.is_relative_to(run):
        raise ValueError("Briefing artifact escaped the run directory")
    return destination


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
