"""Offline safety harness for the bounded sherpa-onnx runtime proof."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import platform
import re
import subprocess
import tarfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


@dataclass(frozen=True)
class RuntimeAssetSpec:
    release: str
    filename: str
    url: str
    bytes: int
    sha256: str
    expected_root: str


@dataclass(frozen=True)
class VerifiedArchive:
    path: Path
    bytes: int
    sha256: str


@dataclass(frozen=True)
class ArchiveMemberPlan:
    relative_path: str
    size: int
    is_directory: bool


@dataclass(frozen=True)
class ArchivePlan:
    expected_root: str
    members: tuple[ArchiveMemberPlan, ...]
    entry_count: int
    total_uncompressed_bytes: int
    archive_sha256: str


@dataclass(frozen=True)
class SignatureRecord:
    status: str
    status_message: str
    signer_subject: str | None
    signer_issuer: str | None
    signer_thumbprint: str | None
    timestamp_subject: str | None
    timestamp_issuer: str | None
    timestamp_thumbprint: str | None


@dataclass(frozen=True)
class _LoadCandidate:
    relative_path: str
    bytes: int
    sha256: str
    signature: SignatureRecord


@dataclass(frozen=True)
class LoadInventory:
    rows: tuple[_LoadCandidate, ...]
    sha256: str
    mandatory_executable_relative_path: str
    mandatory_executable_sha256: str
    version_executable_relative_path: str | None


@dataclass(frozen=True)
class RuntimePreparation:
    state: str
    safe_code: str | None
    exit_code: int
    asset_spec: RuntimeAssetSpec
    verified_archive: VerifiedArchive
    archive_plan: ArchivePlan
    inventory: LoadInventory
    staging_root: Path
    runtime_target: Path
    runtime_root: Path | None
    proof_dir: Path
    promoted: bool

    def require_unsigned_ack(
        self,
        *,
        ack_not_signed_runtime_once: bool,
        outer_sha256: str,
        inventory_sha256: str,
        executable_sha256: str,
    ) -> None:
        if (
            self.state != "BLOCKED_UNSIGNED"
            or ack_not_signed_runtime_once is not True
            or outer_sha256 != self.verified_archive.sha256
            or inventory_sha256 != self.inventory.sha256
            or executable_sha256
            != self.inventory.mandatory_executable_sha256
        ):
            raise RuntimeProofError("RUNTIME_ACK_MISMATCH")


@dataclass(frozen=True)
class RuntimeProof:
    state: str
    safe_code: str | None
    exit_code: int
    evidence_id: str
    proof_dir: Path
    manifest_sha256: str


class RuntimeProofError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


_WINDOWS_DEVICE_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}

_MAX_ARCHIVE_ENTRIES = 20_000
_MAX_ARCHIVE_FILE_BYTES = 1024**3
_MAX_ARCHIVE_TOTAL_BYTES = 2 * 1024**3
_MAX_CAPTURED_OUTPUT_BYTES = 64 * 1024
_EVIDENCE_SCHEMA = "easytravel.sherpa-runtime-proof.v1"
_EVIDENCE_FILENAME = "runtime-proof.json"
_REQUIRED_HELP_TOKENS = (
    "provider",
    "num-threads",
    "zipvoice-encoder",
    "zipvoice-decoder",
    "reference-audio",
    "reference-text",
    "output-filename",
)

_AUTHENTICODE_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$signature = Get-AuthenticodeSignature -LiteralPath $env:EASYTRAVEL_SIGNATURE_PATH
$result = [ordered]@{
    status = [string]$signature.Status
    status_message = [string]$signature.StatusMessage
    signer_subject = if ($null -ne $signature.SignerCertificate) { [string]$signature.SignerCertificate.Subject } else { $null }
    signer_issuer = if ($null -ne $signature.SignerCertificate) { [string]$signature.SignerCertificate.Issuer } else { $null }
    signer_thumbprint = if ($null -ne $signature.SignerCertificate) { [string]$signature.SignerCertificate.Thumbprint } else { $null }
    timestamp_subject = if ($null -ne $signature.TimeStamperCertificate) { [string]$signature.TimeStamperCertificate.Subject } else { $null }
    timestamp_issuer = if ($null -ne $signature.TimeStamperCertificate) { [string]$signature.TimeStamperCertificate.Issuer } else { $null }
    timestamp_thumbprint = if ($null -ne $signature.TimeStamperCertificate) { [string]$signature.TimeStamperCertificate.Thumbprint } else { $null }
}
$result | ConvertTo-Json -Compress
""".strip()


PINNED_RUNTIME = RuntimeAssetSpec(
    release="v1.13.6",
    filename="sherpa-onnx-v1.13.6-win-x64-shared-MT-Release.tar.bz2",
    url=(
        "https://github.com/k2-fsa/sherpa-onnx/releases/download/v1.13.6/"
        "sherpa-onnx-v1.13.6-win-x64-shared-MT-Release.tar.bz2"
    ),
    bytes=24_497_928,
    sha256="4a296ee44c0997ab9fd4d30d7196446ab77e0ef34f0ce66b5e01b3339fce4613",
    expected_root="sherpa-onnx-v1.13.6-win-x64-shared-MT-Release",
)


@dataclass(frozen=True)
class RuntimeAdapters:
    asset_spec: RuntimeAssetSpec
    repo_root: Path
    per_user_root: Path
    signature_probe: object
    runner: object
    process_probe: object
    listener_probe: object
    event_probe: object


def verify_archive_identity(
    archive_path: Path, *, spec: RuntimeAssetSpec
) -> VerifiedArchive:
    resolved = archive_path.resolve(strict=True)
    byte_count = resolved.stat().st_size
    if byte_count != spec.bytes:
        raise RuntimeProofError("RUNTIME_ASSET_SIZE_MISMATCH")
    digest = hashlib.sha256()
    with resolved.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    sha256 = digest.hexdigest()
    if sha256 != spec.sha256:
        raise RuntimeProofError("RUNTIME_ASSET_SHA256_MISMATCH")
    return VerifiedArchive(path=resolved, bytes=byte_count, sha256=sha256)


def validate_runtime_paths(
    repo_root: Path,
    per_user_root: Path,
    archive_path: Path,
    staging_dir: Path,
    runtime_dir: Path,
    proof_dir: Path,
) -> None:
    resolved_repo = repo_root.resolve(strict=True)
    resolved_private = per_user_root.resolve(strict=True)
    if _is_reparse_point(per_user_root):
        raise RuntimeProofError("RUNTIME_PATH_OUTSIDE_PER_USER_ROOT")
    candidates = (archive_path, staging_dir, runtime_dir, proof_dir)
    resolved_candidates: list[Path] = []
    for candidate in candidates:
        if not candidate.is_absolute():
            raise RuntimeProofError("RUNTIME_PATH_OUTSIDE_PER_USER_ROOT")
        lexical = candidate.absolute()
        if lexical.is_relative_to(resolved_repo):
            raise RuntimeProofError("RUNTIME_PATH_INSIDE_REPOSITORY")
        if not lexical.is_relative_to(resolved_private):
            raise RuntimeProofError("RUNTIME_PATH_OUTSIDE_PER_USER_ROOT")
        _require_no_reparse_chain(resolved_private, lexical)
        resolved = candidate.resolve(strict=False)
        if resolved.is_relative_to(resolved_repo):
            raise RuntimeProofError("RUNTIME_PATH_INSIDE_REPOSITORY")
        if not resolved.is_relative_to(resolved_private):
            raise RuntimeProofError("RUNTIME_PATH_OUTSIDE_PER_USER_ROOT")
        resolved_candidates.append(resolved)
    resolved_archive, resolved_staging, resolved_runtime, resolved_proof = (
        resolved_candidates
    )
    downloads_root = (resolved_private / "downloads").resolve(strict=False)
    staging_root = (resolved_private / "runtime-staging").resolve(strict=False)
    runtime_target = (
        resolved_private / "runtime" / "sherpa-onnx" / "1.13.6"
    ).resolve(strict=False)
    proofs_root = (resolved_private / "proofs").resolve(strict=False)
    if not resolved_archive.is_relative_to(downloads_root):
        raise RuntimeProofError("RUNTIME_PATH_OUTSIDE_PER_USER_ROOT")
    if resolved_staging == staging_root or not resolved_staging.is_relative_to(
        staging_root
    ):
        raise RuntimeProofError("RUNTIME_PATH_OUTSIDE_PER_USER_ROOT")
    if resolved_runtime != runtime_target:
        raise RuntimeProofError("RUNTIME_PATH_OUTSIDE_PER_USER_ROOT")
    if resolved_proof == proofs_root or not resolved_proof.is_relative_to(proofs_root):
        raise RuntimeProofError("RUNTIME_PATH_OUTSIDE_PER_USER_ROOT")
    for output in (staging_dir, runtime_dir, proof_dir):
        if output.exists() or output.is_symlink():
            raise RuntimeProofError("RUNTIME_OUTPUT_EXISTS")


def build_archive_plan(
    archive_path: Path, *, verified: VerifiedArchive, expected_root: str
) -> ArchivePlan:
    resolved = archive_path.resolve(strict=True)
    if resolved != verified.path:
        raise RuntimeProofError("RUNTIME_ASSET_SHA256_MISMATCH")
    members: list[ArchiveMemberPlan] = []
    seen_paths: set[str] = set()
    roots: set[str] = set()
    total_uncompressed_bytes = 0
    with tarfile.open(resolved, "r:bz2") as archive:
        for member in archive.getmembers():
            if len(members) >= _MAX_ARCHIVE_ENTRIES:
                raise RuntimeProofError("RUNTIME_ARCHIVE_LIMIT_EXCEEDED")
            if member.type not in {tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE}:
                raise RuntimeProofError("RUNTIME_ARCHIVE_UNSAFE_MEMBER")
            normalized_name = _normalize_member_name(
                member.name, is_directory=member.isdir()
            )
            if member.size < 0 or (
                member.isreg() and member.size > _MAX_ARCHIVE_FILE_BYTES
            ):
                raise RuntimeProofError("RUNTIME_ARCHIVE_LIMIT_EXCEEDED")
            total_uncompressed_bytes += member.size
            if total_uncompressed_bytes > _MAX_ARCHIVE_TOTAL_BYTES:
                raise RuntimeProofError("RUNTIME_ARCHIVE_LIMIT_EXCEEDED")
            roots.add(normalized_name.split("/", 1)[0])
            casefold_name = normalized_name.casefold()
            if casefold_name in seen_paths:
                raise RuntimeProofError("RUNTIME_ARCHIVE_UNSAFE_MEMBER")
            seen_paths.add(casefold_name)
            members.append(
                ArchiveMemberPlan(
                    relative_path=normalized_name,
                    size=member.size,
                    is_directory=member.isdir(),
                )
            )
    if roots != {expected_root}:
        raise RuntimeProofError("RUNTIME_ARCHIVE_ROOT_MISMATCH")
    file_paths = {
        member.relative_path.casefold()
        for member in members
        if not member.is_directory
    }
    for member in members:
        components = member.relative_path.casefold().split("/")
        for index in range(1, len(components)):
            if "/".join(components[:index]) in file_paths:
                raise RuntimeProofError("RUNTIME_ARCHIVE_UNSAFE_MEMBER")
    return ArchivePlan(
        expected_root=expected_root,
        members=tuple(members),
        entry_count=len(members),
        total_uncompressed_bytes=total_uncompressed_bytes,
        archive_sha256=verified.sha256,
    )


def safe_extract_runtime(
    archive_path: Path, *, plan: ArchivePlan, staging_dir: Path
) -> Path:
    resolved_archive = archive_path.resolve(strict=True)
    staging = staging_dir.absolute()
    if staging.exists() or staging.is_symlink():
        raise RuntimeProofError("RUNTIME_OUTPUT_EXISTS")
    if _sha256_file(resolved_archive) != plan.archive_sha256:
        raise RuntimeProofError("RUNTIME_EXTRACTION_FAILED")

    staging_parent = staging.parent.resolve(strict=True)
    staging.mkdir()
    resolved_staging = staging.resolve(strict=True)
    if resolved_staging.parent != staging_parent or _is_reparse_point(staging):
        raise RuntimeProofError("RUNTIME_EXTRACTION_FAILED")

    try:
        with tarfile.open(resolved_archive, "r:bz2") as archive:
            actual_members = archive.getmembers()
            if len(actual_members) != len(plan.members):
                raise RuntimeProofError("RUNTIME_EXTRACTION_FAILED")
            for actual, planned in zip(actual_members, plan.members, strict=True):
                if actual.type not in {
                    tarfile.REGTYPE,
                    tarfile.AREGTYPE,
                    tarfile.DIRTYPE,
                }:
                    raise RuntimeProofError("RUNTIME_EXTRACTION_FAILED")
                normalized = _normalize_member_name(
                    actual.name, is_directory=actual.isdir()
                )
                if ArchiveMemberPlan(
                    relative_path=normalized,
                    size=actual.size,
                    is_directory=actual.isdir(),
                ) != planned:
                    raise RuntimeProofError("RUNTIME_EXTRACTION_FAILED")

                target = _resolved_extraction_target(
                    resolved_staging, planned.relative_path
                )
                _make_safe_parents(resolved_staging, target.parent)
                if planned.is_directory:
                    target.mkdir(exist_ok=True)
                    if not target.is_dir() or _is_reparse_point(target):
                        raise RuntimeProofError("RUNTIME_EXTRACTION_FAILED")
                    _resolved_extraction_target(
                        resolved_staging, planned.relative_path, strict=True
                    )
                    continue
                if target.exists() or target.is_symlink():
                    raise RuntimeProofError("RUNTIME_EXTRACTION_FAILED")
                source = archive.extractfile(actual)
                if source is None:
                    raise RuntimeProofError("RUNTIME_EXTRACTION_FAILED")
                copied = 0
                with source, target.open("xb") as destination:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        copied += len(chunk)
                        if copied > planned.size:
                            raise RuntimeProofError("RUNTIME_EXTRACTION_FAILED")
                        destination.write(chunk)
                if copied != planned.size:
                    raise RuntimeProofError("RUNTIME_EXTRACTION_FAILED")
                if _is_reparse_point(target) or not target.is_file():
                    raise RuntimeProofError("RUNTIME_EXTRACTION_FAILED")
                _resolved_extraction_target(
                    resolved_staging, planned.relative_path, strict=True
                )
    except Exception as error:
        _write_extraction_failure(resolved_staging)
        raise RuntimeProofError("RUNTIME_EXTRACTION_FAILED") from error

    return _resolved_extraction_target(
        resolved_staging, plan.expected_root, strict=True
    )


def build_load_inventory(staging_dir: Path, *, signature_probe) -> LoadInventory:
    root = staging_dir.resolve(strict=True)
    if _is_reparse_point(staging_dir) or not root.is_dir():
        raise RuntimeProofError("RUNTIME_EXECUTABLE_MISSING")
    all_files = [path for path in root.rglob("*") if path.is_file()]
    mandatory = [
        path
        for path in all_files
        if path.name.casefold() == "sherpa-onnx-offline-tts.exe"
    ]
    if not mandatory:
        raise RuntimeProofError("RUNTIME_EXECUTABLE_MISSING")
    if len(mandatory) != 1:
        raise RuntimeProofError("RUNTIME_EXECUTABLE_AMBIGUOUS")
    version = [
        path
        for path in all_files
        if path.name.casefold() == "sherpa-onnx-version.exe"
    ]
    if len(version) > 1:
        raise RuntimeProofError("RUNTIME_EXECUTABLE_AMBIGUOUS")
    dlls = [path for path in all_files if path.suffix.casefold() == ".dll"]
    candidates = mandatory + version + dlls
    candidates.sort(
        key=lambda path: path.relative_to(root).as_posix().casefold()
    )

    rows: list[_LoadCandidate] = []
    for path in candidates:
        resolved = path.resolve(strict=True)
        if (
            _is_reparse_point(path)
            or not resolved.is_relative_to(root)
            or not resolved.is_file()
        ):
            raise RuntimeProofError("RUNTIME_EXECUTABLE_MISSING")
        try:
            signature = signature_probe(resolved)
        except Exception as error:
            raise RuntimeProofError("RUNTIME_SIGNATURE_INVALID") from error
        if not isinstance(signature, SignatureRecord):
            raise RuntimeProofError("RUNTIME_SIGNATURE_INVALID")
        rows.append(
            _LoadCandidate(
                relative_path=resolved.relative_to(root).as_posix(),
                bytes=resolved.stat().st_size,
                sha256=_sha256_file(resolved),
                signature=signature,
            )
        )
    canonical_rows = [_load_candidate_dict(row) for row in rows]
    inventory_sha256 = hashlib.sha256(
        _canonical_json_bytes(canonical_rows)
    ).hexdigest()
    mandatory_path = mandatory[0].resolve(strict=True).relative_to(root).as_posix()
    mandatory_row = next(row for row in rows if row.relative_path == mandatory_path)
    version_path = (
        version[0].resolve(strict=True).relative_to(root).as_posix()
        if version
        else None
    )
    return LoadInventory(
        rows=tuple(rows),
        sha256=inventory_sha256,
        mandatory_executable_relative_path=mandatory_path,
        mandatory_executable_sha256=mandatory_row.sha256,
        version_executable_relative_path=version_path,
    )


def build_authenticode_probe_command(
    path: Path,
) -> tuple[tuple[str, ...], dict[str, str]]:
    encoded_script = base64.b64encode(
        _AUTHENTICODE_SCRIPT.encode("utf-16-le")
    ).decode("ascii")
    return (
        (
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-EncodedCommand",
            encoded_script,
        ),
        {"EASYTRAVEL_SIGNATURE_PATH": str(path)},
    )


def parse_authenticode_probe_json(payload: str) -> SignatureRecord:
    if len(payload.encode("utf-8")) > 64 * 1024:
        raise RuntimeProofError("RUNTIME_SIGNATURE_INVALID")
    try:
        value = json.loads(payload)
    except (TypeError, ValueError) as error:
        raise RuntimeProofError("RUNTIME_SIGNATURE_INVALID") from error
    required_strings = ("status", "status_message")
    optional_strings = (
        "signer_subject",
        "signer_issuer",
        "signer_thumbprint",
        "timestamp_subject",
        "timestamp_issuer",
        "timestamp_thumbprint",
    )
    if not isinstance(value, dict) or any(
        not isinstance(value.get(field), str) for field in required_strings
    ):
        raise RuntimeProofError("RUNTIME_SIGNATURE_INVALID")
    if any(
        value.get(field) is not None and not isinstance(value.get(field), str)
        for field in optional_strings
    ):
        raise RuntimeProofError("RUNTIME_SIGNATURE_INVALID")
    return SignatureRecord(
        status=value["status"],
        status_message=value["status_message"],
        signer_subject=value.get("signer_subject"),
        signer_issuer=value.get("signer_issuer"),
        signer_thumbprint=value.get("signer_thumbprint"),
        timestamp_subject=value.get("timestamp_subject"),
        timestamp_issuer=value.get("timestamp_issuer"),
        timestamp_thumbprint=value.get("timestamp_thumbprint"),
    )


def prepare_runtime(
    archive_path: Path,
    *,
    spec: RuntimeAssetSpec,
    staging_dir: Path,
    runtime_dir: Path,
    proof_dir: Path,
    signature_probe,
) -> RuntimePreparation:
    for output in (staging_dir, runtime_dir, proof_dir):
        if output.exists() or output.is_symlink():
            raise RuntimeProofError("RUNTIME_OUTPUT_EXISTS")
    verified = verify_archive_identity(archive_path, spec=spec)
    plan = build_archive_plan(
        archive_path, verified=verified, expected_root=spec.expected_root
    )
    extracted_root = safe_extract_runtime(
        archive_path, plan=plan, staging_dir=staging_dir
    )
    inventory = build_load_inventory(
        extracted_root, signature_probe=signature_probe
    )
    statuses = {row.signature.status for row in inventory.rows}
    if not statuses.issubset({"Valid", "NotSigned"}):
        state = "FAILED"
        safe_code = "RUNTIME_SIGNATURE_INVALID"
        exit_code = 30
    elif "NotSigned" in statuses:
        state = "BLOCKED_UNSIGNED"
        safe_code = "RUNTIME_SIGNATURE_NOT_SIGNED"
        exit_code = 20
    else:
        state = "READY_TO_EXECUTE"
        safe_code = None
        exit_code = 0

    resolved_proof = _create_new_directory(proof_dir)
    runtime_target = runtime_dir.resolve(strict=False)
    if state != "READY_TO_EXECUTE":
        preparation = RuntimePreparation(
            state=state,
            safe_code=safe_code,
            exit_code=exit_code,
            asset_spec=spec,
            verified_archive=verified,
            archive_plan=plan,
            inventory=inventory,
            staging_root=extracted_root,
            runtime_target=runtime_target,
            runtime_root=None,
            proof_dir=resolved_proof,
            promoted=False,
        )
        _write_preparation_evidence(preparation)
        return preparation

    resolved_runtime_parent = runtime_dir.parent.resolve(strict=True)
    extracted_root.replace(runtime_dir)
    resolved_runtime = runtime_dir.resolve(strict=True)
    if (
        resolved_runtime.parent != resolved_runtime_parent
        or _is_reparse_point(runtime_dir)
    ):
        raise RuntimeProofError("RUNTIME_EXTRACTION_FAILED")
    preparation = RuntimePreparation(
        state=state,
        safe_code=safe_code,
        exit_code=exit_code,
        asset_spec=spec,
        verified_archive=verified,
        archive_plan=plan,
        inventory=inventory,
        staging_root=extracted_root,
        runtime_target=runtime_target,
        runtime_root=resolved_runtime,
        proof_dir=resolved_proof,
        promoted=True,
    )
    _write_preparation_evidence(preparation)
    return preparation


def run_runtime_proof(
    proof_dir: Path,
    *,
    runner,
    process_probe,
    listener_probe,
    event_probe,
    runtime_dir: Path | None = None,
    ack_valid_signed_runtime: bool = False,
    ack_not_signed_runtime_once: bool = False,
    ack_outer_sha256: str | None = None,
    ack_load_inventory_sha256: str | None = None,
    ack_executable_sha256: str | None = None,
) -> RuntimeProof:
    document = _read_evidence(proof_dir)
    try:
        _verify_archive_binding(document)
    except RuntimeProofError:
        return _finish_runtime_proof(
            proof_dir,
            document,
            state="FAILED",
            safe_code="RUNTIME_EVIDENCE_TAMPERED",
            execution={"commands": [], "authorization": "rejected"},
        )
    preparation = document["preparation"]
    inventory = document["inventory"]
    paths = document["paths"]
    preparation_state = preparation.get("state")
    authorization: str
    if preparation_state == "READY_TO_EXECUTE":
        valid_ack = (
            ack_valid_signed_runtime is True
            and ack_not_signed_runtime_once is False
            and all(
                value is None
                for value in (
                    ack_outer_sha256,
                    ack_load_inventory_sha256,
                    ack_executable_sha256,
                )
            )
        )
        recorded_runtime_value = paths.get("runtime_root")
        if not valid_ack or not isinstance(recorded_runtime_value, str):
            return _finish_runtime_proof(
                proof_dir,
                document,
                state="FAILED",
                safe_code="RUNTIME_ACK_MISMATCH",
                execution={"commands": [], "authorization": "rejected"},
            )
        recorded_runtime = Path(recorded_runtime_value).resolve(strict=True)
        authorization = "valid-signature"
    elif preparation_state == "BLOCKED_UNSIGNED":
        valid_ack = (
            ack_valid_signed_runtime is False
            and ack_not_signed_runtime_once is True
            and ack_outer_sha256 == document["asset"]["sha256"]
            and ack_load_inventory_sha256 == inventory["sha256"]
            and ack_executable_sha256
            == inventory["mandatory_executable_sha256"]
        )
        target_value = paths.get("runtime_target")
        staging_value = paths.get("staging_root")
        if (
            not valid_ack
            or not isinstance(target_value, str)
            or not isinstance(staging_value, str)
            or paths.get("runtime_root") is not None
        ):
            return _finish_runtime_proof(
                proof_dir,
                document,
                state="FAILED",
                safe_code="RUNTIME_ACK_MISMATCH",
                execution={"commands": [], "authorization": "rejected"},
            )
        target = Path(target_value).absolute()
        if (
            runtime_dir is not None
            and runtime_dir.resolve(strict=False) != target.resolve(strict=False)
        ):
            return _finish_runtime_proof(
                proof_dir,
                document,
                state="FAILED",
                safe_code="RUNTIME_ACK_MISMATCH",
                execution={"commands": [], "authorization": "rejected"},
            )
        staging_root = Path(staging_value).resolve(strict=True)
        try:
            _verify_inventory_tree(staging_root, inventory)
            if target.exists() or target.is_symlink():
                raise RuntimeProofError("RUNTIME_OUTPUT_EXISTS")
            resolved_target_parent = target.parent.resolve(strict=True)
            staging_root.replace(target)
            recorded_runtime = target.resolve(strict=True)
            if (
                recorded_runtime.parent != resolved_target_parent
                or _is_reparse_point(target)
            ):
                raise RuntimeProofError("RUNTIME_EXTRACTION_FAILED")
        except (OSError, RuntimeProofError):
            return _finish_runtime_proof(
                proof_dir,
                document,
                state="FAILED",
                safe_code="RUNTIME_EXTRACTION_FAILED",
                execution={"commands": [], "authorization": "unsigned-exact-hash"},
            )
        paths = dict(paths)
        paths["runtime_root"] = str(recorded_runtime)
        document["paths"] = paths
        preparation = dict(preparation)
        preparation["initial_state"] = "BLOCKED_UNSIGNED"
        preparation["state"] = "READY_TO_EXECUTE"
        preparation["safe_code"] = None
        preparation["exit_code"] = 0
        preparation["promoted"] = True
        document["preparation"] = preparation
        authorization = "unsigned-exact-hash"
    else:
        return _finish_runtime_proof(
            proof_dir,
            document,
            state="FAILED",
            safe_code="RUNTIME_ACK_MISMATCH",
            execution={"commands": [], "authorization": "rejected"},
        )

    if runtime_dir is not None and runtime_dir.resolve(strict=True) != recorded_runtime:
        return _finish_runtime_proof(
            proof_dir,
            document,
            state="FAILED",
            safe_code="RUNTIME_ACK_MISMATCH",
            execution={"commands": [], "authorization": "rejected"},
        )

    try:
        _verify_inventory_tree(recorded_runtime, inventory)
    except RuntimeProofError:
        return _finish_runtime_proof(
            proof_dir,
            document,
            state="FAILED",
            safe_code="RUNTIME_EVIDENCE_TAMPERED",
            execution={"commands": [], "authorization": authorization},
        )
    mandatory_relative = inventory["mandatory_executable_relative_path"]
    version_relative = inventory["version_executable_relative_path"]
    version_utility = "executed" if version_relative is not None else "not_present"
    command_specs: list[tuple[Path, tuple[str, ...], str]] = []
    if version_relative is not None:
        command_specs.append(
            (recorded_runtime.joinpath(*version_relative.split("/")), (), "version")
        )
    mandatory = recorded_runtime.joinpath(*mandatory_relative.split("/"))
    command_specs.append((mandatory, ("--help",), "help"))
    environment = dict(os.environ)
    path_prefix = [recorded_runtime / "bin", recorded_runtime / "lib"]
    inherited_path = environment.get("PATH")
    environment["PATH"] = os.pathsep.join(
        [
            *(str(path) for path in path_prefix),
            *([inherited_path] if inherited_path else []),
        ]
    )

    commands: list[dict[str, object]] = []
    safe_code: str | None = None
    start_utc = _utc_now().isoformat()
    started = time.monotonic()
    try:
        processes_before = _snapshot(process_probe())
        listeners_before = _snapshot(listener_probe())
    except Exception:
        return _finish_runtime_proof(
            proof_dir,
            document,
            state="FAILED",
            safe_code="RUNTIME_POSTFLIGHT_DIRTY",
            execution={"commands": [], "authorization": authorization},
        )

    for executable, arguments, purpose in command_specs:
        argv = (str(executable), *arguments)
        command_started = time.monotonic()
        try:
            result = runner(
                argv,
                shell=False,
                stdin=subprocess.DEVNULL,
                cwd=executable.parent,
                timeout=30,
                capture_output=True,
                env=environment,
            )
        except subprocess.TimeoutExpired:
            safe_code = "RUNTIME_HELP_TIMEOUT"
            commands.append(
                _command_evidence(
                    argv,
                    executable.parent,
                    purpose,
                    None,
                    b"",
                    b"",
                    time.monotonic() - command_started,
                )
            )
            break
        except Exception:
            safe_code = "RUNTIME_HELP_NONZERO"
            commands.append(
                _command_evidence(
                    argv,
                    executable.parent,
                    purpose,
                    None,
                    b"",
                    b"",
                    time.monotonic() - command_started,
                )
            )
            break
        stdout = _output_bytes(getattr(result, "stdout", b""))
        stderr = _output_bytes(getattr(result, "stderr", b""))
        returncode = getattr(result, "returncode", None)
        commands.append(
            _command_evidence(
                argv,
                executable.parent,
                purpose,
                returncode,
                stdout,
                stderr,
                time.monotonic() - command_started,
            )
        )
        if not isinstance(returncode, int) or returncode != 0:
            safe_code = "RUNTIME_HELP_NONZERO"
            break
        if purpose == "help":
            normalized_output = (stdout + b"\n" + stderr).decode(
                "utf-8", errors="replace"
            ).casefold()
            if any(token not in normalized_output for token in _REQUIRED_HELP_TOKENS):
                safe_code = "RUNTIME_HELP_CONTRACT_MISMATCH"
                break

    end_utc = _utc_now().isoformat()
    try:
        processes_after = _snapshot(process_probe())
        listeners_after = _snapshot(listener_probe())
        event_1000 = _snapshot(event_probe(start_utc, end_utc))
    except Exception:
        processes_after = []
        listeners_after = []
        event_1000 = ["probe-unknown"]
    if (
        _new_snapshot_items(processes_before, processes_after)
        or _new_snapshot_items(listeners_before, listeners_after)
        or event_1000
    ):
        safe_code = safe_code or "RUNTIME_POSTFLIGHT_DIRTY"

    state = "PASSED" if safe_code is None else "FAILED"
    return _finish_runtime_proof(
        proof_dir,
        document,
        state=state,
        safe_code=safe_code,
        execution={
            "authorization": authorization,
            "commands": commands,
            "environment_delta": {
                "path_prepend": [str(path) for path in path_prefix]
            },
            "event_1000": event_1000,
            "listeners_after": listeners_after,
            "listeners_before": listeners_before,
            "processes_after": processes_after,
            "processes_before": processes_before,
            "start_utc": start_utc,
            "end_utc": end_utc,
            "version_utility": version_utility,
            "wall_seconds": round(time.monotonic() - started, 6),
        },
    )


def verify_runtime_proof(proof_dir: Path) -> RuntimeProof:
    try:
        document = _read_evidence(proof_dir)
        asset = document["asset"]
        archive = document["archive"]
        inventory = document["inventory"]
        paths = document["paths"]
        if not all(
            isinstance(value, dict)
            for value in (asset, archive, inventory, paths)
        ):
            raise ValueError("invalid evidence sections")
        _verify_archive_binding(document)

        runtime_value = paths.get("runtime_root")
        if isinstance(runtime_value, str):
            bound_root = Path(runtime_value)
        else:
            staging_value = paths.get("staging_root")
            if not isinstance(staging_value, str):
                raise ValueError("missing bound runtime")
            bound_root = Path(staging_value)
        _verify_inventory_tree(bound_root, inventory)

        execution = document.get("execution")
        if execution is not None:
            if not isinstance(execution, dict):
                raise ValueError("invalid execution evidence")
            commands = execution.get("commands")
            if not isinstance(commands, list):
                raise ValueError("invalid command evidence")
            for command in commands:
                if not isinstance(command, dict):
                    raise ValueError("invalid command record")
                _validate_captured_output(command.get("stdout"))
                _validate_captured_output(command.get("stderr"))
                argv = command.get("argv")
                purpose = command.get("purpose")
                if not isinstance(argv, list) or not all(
                    isinstance(argument, str) for argument in argv
                ):
                    raise ValueError("invalid command arguments")
                if purpose == "help":
                    expected = [
                        str(
                            bound_root.joinpath(
                                *inventory[
                                    "mandatory_executable_relative_path"
                                ].split("/")
                            )
                        ),
                        "--help",
                    ]
                elif purpose == "version":
                    version_relative = inventory.get(
                        "version_executable_relative_path"
                    )
                    if not isinstance(version_relative, str):
                        raise ValueError("unexpected version command")
                    expected = [
                        str(bound_root.joinpath(*version_relative.split("/")))
                    ]
                else:
                    raise ValueError("unknown command purpose")
                if argv != expected or command.get("cwd") != str(Path(expected[0]).parent):
                    raise ValueError("command contract mismatch")

        state = document.get("state")
        safe_code = document.get("safe_code")
        if state not in {
            "READY_TO_EXECUTE",
            "BLOCKED_UNSIGNED",
            "PASSED",
            "FAILED",
        }:
            raise ValueError("invalid proof state")
        if state == "PASSED" and safe_code is not None:
            raise ValueError("invalid passed state")
        if state == "FAILED" and not isinstance(safe_code, str):
            raise ValueError("invalid failed state")
        manifest_sha256 = document.get("manifest_sha256")
        evidence_id = document.get("evidence_id")
        if not isinstance(manifest_sha256, str) or not isinstance(evidence_id, str):
            raise ValueError("invalid evidence identity")
        return RuntimeProof(
            state=state,
            safe_code=safe_code,
            exit_code=(0 if state in {"READY_TO_EXECUTE", "PASSED"} else 20 if state == "BLOCKED_UNSIGNED" else 30),
            evidence_id=evidence_id,
            proof_dir=proof_dir.resolve(strict=True),
            manifest_sha256=manifest_sha256,
        )
    except RuntimeProofError as error:
        if error.code == "RUNTIME_EVIDENCE_TAMPERED":
            raise
        raise RuntimeProofError("RUNTIME_EVIDENCE_TAMPERED") from error
    except (KeyError, OSError, TypeError, ValueError) as error:
        raise RuntimeProofError("RUNTIME_EVIDENCE_TAMPERED") from error


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_bytes(value) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _load_candidate_dict(row: _LoadCandidate) -> dict[str, object]:
    signature = row.signature
    return {
        "bytes": row.bytes,
        "relative_path": row.relative_path,
        "sha256": row.sha256,
        "signature": {
            "signer_issuer": signature.signer_issuer,
            "signer_subject": signature.signer_subject,
            "signer_thumbprint": signature.signer_thumbprint,
            "status": signature.status,
            "status_message": signature.status_message,
            "timestamp_issuer": signature.timestamp_issuer,
            "timestamp_subject": signature.timestamp_subject,
            "timestamp_thumbprint": signature.timestamp_thumbprint,
        },
    }


def _write_preparation_evidence(preparation: RuntimePreparation) -> None:
    now = _utc_now()
    plan_payload = {
        "archive_sha256": preparation.archive_plan.archive_sha256,
        "entry_count": preparation.archive_plan.entry_count,
        "expected_root": preparation.archive_plan.expected_root,
        "members": [
            {
                "is_directory": member.is_directory,
                "relative_path": member.relative_path,
                "size": member.size,
            }
            for member in preparation.archive_plan.members
        ],
        "total_uncompressed_bytes": preparation.archive_plan.total_uncompressed_bytes,
    }
    inventory_rows = [
        _load_candidate_dict(row) for row in preparation.inventory.rows
    ]
    document: dict[str, object] = {
        "schema": _EVIDENCE_SCHEMA,
        "evidence_id": str(uuid.uuid4()),
        "created_utc": now.isoformat(),
        "created_taipei": now.astimezone(
            timezone(timedelta(hours=8), name="Asia/Taipei")
        ).isoformat(),
        "system": {
            "architecture": platform.machine(),
            "cpu": platform.processor(),
            "cpu_count": os.cpu_count(),
            "os_build": platform.version(),
            "os_edition": platform.system(),
            "os_version": platform.release(),
            "ram_bytes": _physical_ram_bytes(),
        },
        "asset": {
            "bytes": preparation.asset_spec.bytes,
            "filename": preparation.asset_spec.filename,
            "release": preparation.asset_spec.release,
            "sha256": preparation.asset_spec.sha256,
            "url": preparation.asset_spec.url,
        },
        "archive": {
            **plan_payload,
            "plan_sha256": hashlib.sha256(
                _canonical_json_bytes(plan_payload)
            ).hexdigest(),
        },
        "inventory": {
            "mandatory_executable_relative_path": (
                preparation.inventory.mandatory_executable_relative_path
            ),
            "mandatory_executable_sha256": (
                preparation.inventory.mandatory_executable_sha256
            ),
            "rows": inventory_rows,
            "sha256": preparation.inventory.sha256,
            "version_executable_relative_path": (
                preparation.inventory.version_executable_relative_path
            ),
        },
        "paths": {
            "archive": str(preparation.verified_archive.path),
            "runtime_root": (
                str(preparation.runtime_root)
                if preparation.runtime_root is not None
                else None
            ),
            "runtime_target": str(preparation.runtime_target),
            "staging_root": str(preparation.staging_root),
        },
        "preparation": {
            "exit_code": preparation.exit_code,
            "promoted": preparation.promoted,
            "safe_code": preparation.safe_code,
            "state": preparation.state,
        },
        "execution": None,
        "state": preparation.state,
        "safe_code": preparation.safe_code,
    }
    _write_new_evidence(preparation.proof_dir, document)


def _physical_ram_bytes() -> int | None:
    try:
        import ctypes

        class _MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = _MemoryStatus()
        status.dwLength = ctypes.sizeof(_MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.ullTotalPhys)
    except (AttributeError, OSError):
        return None
    return None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _evidence_path(proof_dir: Path) -> Path:
    return proof_dir.resolve(strict=True) / _EVIDENCE_FILENAME


def _with_manifest_hash(document: dict[str, object]) -> dict[str, object]:
    unsigned = dict(document)
    unsigned.pop("manifest_sha256", None)
    signed = dict(unsigned)
    signed["manifest_sha256"] = hashlib.sha256(
        _canonical_json_bytes(unsigned)
    ).hexdigest()
    return signed


def _write_new_evidence(proof_dir: Path, document: dict[str, object]) -> None:
    destination = _evidence_path(proof_dir)
    signed = _with_manifest_hash(document)
    with destination.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(
            signed,
            output,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )


def _replace_evidence(proof_dir: Path, document: dict[str, object]) -> dict[str, object]:
    destination = _evidence_path(proof_dir)
    temporary = destination.with_suffix(".json.tmp")
    if temporary.exists() or temporary.is_symlink():
        raise RuntimeProofError("RUNTIME_OUTPUT_EXISTS")
    signed = _with_manifest_hash(document)
    with temporary.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(
            signed,
            output,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    temporary.replace(destination)
    return signed


def _read_evidence(proof_dir: Path) -> dict[str, object]:
    source = _evidence_path(proof_dir)
    try:
        raw = source.read_bytes()
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError("oversized evidence")
        document = json.loads(raw.decode("utf-8"))
        if not isinstance(document, dict) or document.get("schema") != _EVIDENCE_SCHEMA:
            raise ValueError("invalid evidence schema")
        expected_hash = document.get("manifest_sha256")
        unsigned = dict(document)
        unsigned.pop("manifest_sha256", None)
        actual_hash = hashlib.sha256(_canonical_json_bytes(unsigned)).hexdigest()
        if not isinstance(expected_hash, str) or expected_hash != actual_hash:
            raise ValueError("invalid evidence hash")
        if not isinstance(document.get("preparation"), dict):
            raise ValueError("invalid preparation evidence")
        if not isinstance(document.get("inventory"), dict):
            raise ValueError("invalid inventory evidence")
        if not isinstance(document.get("paths"), dict):
            raise ValueError("invalid path evidence")
        return document
    except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError) as error:
        raise RuntimeProofError("RUNTIME_EVIDENCE_TAMPERED") from error


def _output_bytes(value) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    raise TypeError("runner output must be bytes or text")


def _captured_output(payload: bytes) -> dict[str, object]:
    retained = payload[:_MAX_CAPTURED_OUTPUT_BYTES]
    return {
        "bounded_base64": base64.b64encode(retained).decode("ascii"),
        "bounded_text": retained.decode("utf-8", errors="replace"),
        "full_bytes": len(payload),
        "full_sha256": hashlib.sha256(payload).hexdigest(),
        "retained_bytes": len(retained),
        "retained_sha256": hashlib.sha256(retained).hexdigest(),
        "truncated": len(payload) > len(retained),
    }


def _validate_captured_output(record) -> None:
    if not isinstance(record, dict):
        raise ValueError("invalid captured output")
    encoded = record.get("bounded_base64")
    if not isinstance(encoded, str):
        raise ValueError("invalid captured output encoding")
    try:
        retained = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError("invalid captured output encoding") from error
    retained_bytes = record.get("retained_bytes")
    full_bytes = record.get("full_bytes")
    truncated = record.get("truncated")
    if (
        not isinstance(retained_bytes, int)
        or isinstance(retained_bytes, bool)
        or retained_bytes != len(retained)
        or retained_bytes > _MAX_CAPTURED_OUTPUT_BYTES
        or not isinstance(full_bytes, int)
        or isinstance(full_bytes, bool)
        or full_bytes < retained_bytes
        or truncated is not (full_bytes > retained_bytes)
        or record.get("retained_sha256")
        != hashlib.sha256(retained).hexdigest()
        or record.get("bounded_text")
        != retained.decode("utf-8", errors="replace")
    ):
        raise ValueError("captured output mismatch")
    if not truncated and (
        record.get("full_sha256") != hashlib.sha256(retained).hexdigest()
        or full_bytes != retained_bytes
    ):
        raise ValueError("full output mismatch")


def _command_evidence(
    argv: tuple[str, ...],
    cwd: Path,
    purpose: str,
    returncode: int | None,
    stdout: bytes,
    stderr: bytes,
    duration_seconds: float,
) -> dict[str, object]:
    return {
        "argv": list(argv),
        "capture_output": True,
        "cwd": str(cwd),
        "duration_seconds": round(duration_seconds, 6),
        "purpose": purpose,
        "returncode": returncode,
        "shell": False,
        "stderr": _captured_output(stderr),
        "stdin": "DEVNULL",
        "stdout": _captured_output(stdout),
        "timeout_seconds": 30,
    }


def _snapshot(value) -> list[object]:
    if isinstance(value, (str, bytes, dict)):
        raise TypeError("probe snapshot must be a sequence")
    items = list(value)
    canonical = sorted(_canonical_json_bytes(item) for item in items)
    return [json.loads(item.decode("utf-8")) for item in canonical]


def _verify_inventory_tree(root: Path, inventory: dict[str, object]) -> None:
    try:
        resolved_root = root.resolve(strict=True)
        if _is_reparse_point(root) or not resolved_root.is_dir():
            raise ValueError("invalid runtime root")
        rows = inventory["rows"]
        if not isinstance(rows, list) or not rows:
            raise ValueError("invalid inventory rows")
        if hashlib.sha256(_canonical_json_bytes(rows)).hexdigest() != inventory.get(
            "sha256"
        ):
            raise ValueError("invalid inventory hash")
        expected_paths: list[str] = []
        mandatory_rows = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("invalid inventory row")
            relative_path = row.get("relative_path")
            if (
                not isinstance(relative_path, str)
                or _normalize_member_name(relative_path, is_directory=False)
                != relative_path
            ):
                raise ValueError("invalid inventory path")
            target = resolved_root.joinpath(*relative_path.split("/"))
            resolved_target = target.resolve(strict=True)
            if (
                not resolved_target.is_relative_to(resolved_root)
                or _is_reparse_point(target)
                or not resolved_target.is_file()
                or resolved_target.stat().st_size != row.get("bytes")
                or _sha256_file(resolved_target) != row.get("sha256")
            ):
                raise ValueError("inventory file mismatch")
            expected_paths.append(relative_path)
            if target.name.casefold() == "sherpa-onnx-offline-tts.exe":
                mandatory_rows.append(row)
        all_files = [path for path in resolved_root.rglob("*") if path.is_file()]
        actual_candidates = [
            path
            for path in all_files
            if path.name.casefold()
            in {"sherpa-onnx-offline-tts.exe", "sherpa-onnx-version.exe"}
            or path.suffix.casefold() == ".dll"
        ]
        actual_paths = [
            path.resolve(strict=True).relative_to(resolved_root).as_posix()
            for path in actual_candidates
        ]
        if sorted(actual_paths, key=str.casefold) != sorted(
            expected_paths, key=str.casefold
        ):
            raise ValueError("load set mismatch")
        if len(mandatory_rows) != 1:
            raise ValueError("mandatory executable mismatch")
        mandatory = mandatory_rows[0]
        if (
            mandatory.get("relative_path")
            != inventory.get("mandatory_executable_relative_path")
            or mandatory.get("sha256")
            != inventory.get("mandatory_executable_sha256")
        ):
            raise ValueError("mandatory binding mismatch")
    except (KeyError, OSError, RuntimeProofError, TypeError, ValueError) as error:
        raise RuntimeProofError("RUNTIME_EVIDENCE_TAMPERED") from error


def _verify_archive_binding(document: dict[str, object]) -> None:
    try:
        asset = document["asset"]
        archive = document["archive"]
        paths = document["paths"]
        if not all(isinstance(value, dict) for value in (asset, archive, paths)):
            raise ValueError("invalid archive evidence")
        archive_path_value = paths.get("archive")
        if not isinstance(archive_path_value, str):
            raise ValueError("invalid archive path")
        unresolved_archive = Path(archive_path_value)
        archive_path = unresolved_archive.resolve(strict=True)
        if (
            _is_reparse_point(unresolved_archive)
            or archive_path.stat().st_size != asset.get("bytes")
            or _sha256_file(archive_path) != asset.get("sha256")
            or archive.get("archive_sha256") != asset.get("sha256")
        ):
            raise ValueError("archive binding mismatch")
        plan_payload = dict(archive)
        plan_sha256 = plan_payload.pop("plan_sha256", None)
        if (
            not isinstance(plan_sha256, str)
            or hashlib.sha256(_canonical_json_bytes(plan_payload)).hexdigest()
            != plan_sha256
        ):
            raise ValueError("archive plan mismatch")
    except (KeyError, OSError, RuntimeProofError, TypeError, ValueError) as error:
        raise RuntimeProofError("RUNTIME_EVIDENCE_TAMPERED") from error


def _new_snapshot_items(before: list[object], after: list[object]) -> set[bytes]:
    return {
        _canonical_json_bytes(item) for item in after
    } - {_canonical_json_bytes(item) for item in before}


def _finish_runtime_proof(
    proof_dir: Path,
    document: dict[str, object],
    *,
    state: str,
    safe_code: str | None,
    execution: dict[str, object],
) -> RuntimeProof:
    document = dict(document)
    document.pop("manifest_sha256", None)
    document["execution"] = execution
    document["state"] = state
    document["safe_code"] = safe_code
    document["completed_utc"] = _utc_now().isoformat()
    signed = _replace_evidence(proof_dir, document)
    return RuntimeProof(
        state=state,
        safe_code=safe_code,
        exit_code=0 if state == "PASSED" else 30,
        evidence_id=str(signed["evidence_id"]),
        proof_dir=proof_dir.resolve(strict=True),
        manifest_sha256=str(signed["manifest_sha256"]),
    )


def _resolved_extraction_target(
    staging: Path, relative_path: str, *, strict: bool = False
) -> Path:
    target = staging.joinpath(*relative_path.split("/"))
    resolved = target.resolve(strict=strict)
    if not resolved.is_relative_to(staging):
        raise RuntimeProofError("RUNTIME_EXTRACTION_FAILED")
    return resolved


def _make_safe_parents(staging: Path, parent: Path) -> None:
    relative = parent.relative_to(staging)
    current = staging
    for component in relative.parts:
        current = current / component
        if current.exists():
            if _is_reparse_point(current) or not current.is_dir():
                raise RuntimeProofError("RUNTIME_EXTRACTION_FAILED")
        else:
            current.mkdir()
            if _is_reparse_point(current):
                raise RuntimeProofError("RUNTIME_EXTRACTION_FAILED")
        resolved = current.resolve(strict=True)
        if not resolved.is_relative_to(staging):
            raise RuntimeProofError("RUNTIME_EXTRACTION_FAILED")


def _is_reparse_point(path: Path) -> bool:
    try:
        metadata = path.stat(follow_symlinks=False)
    except FileNotFoundError:
        return False
    return path.is_symlink() or bool(
        getattr(metadata, "st_file_attributes", 0) & 0x400
    )


def _create_new_directory(path: Path) -> Path:
    if path.exists() or path.is_symlink():
        raise RuntimeProofError("RUNTIME_OUTPUT_EXISTS")
    resolved_parent = path.parent.resolve(strict=True)
    path.mkdir()
    resolved = path.resolve(strict=True)
    if resolved.parent != resolved_parent or _is_reparse_point(path):
        raise RuntimeProofError("RUNTIME_PATH_OUTSIDE_PER_USER_ROOT")
    return resolved


def _write_extraction_failure(staging: Path) -> None:
    try:
        if _is_reparse_point(staging) or staging.resolve(strict=True) != staging:
            return
        marker = staging / ".runtime-proof-extraction-failure.json"
        if marker.exists() or marker.is_symlink():
            return
        with marker.open("x", encoding="utf-8", newline="\n") as output:
            json.dump(
                {"safe_code": "RUNTIME_EXTRACTION_FAILED", "state": "FAILED"},
                output,
                sort_keys=True,
                separators=(",", ":"),
            )
    except OSError:
        return


def _normalize_member_name(name: str, *, is_directory: bool) -> str:
    normalized = name.replace("\\", "/")
    if is_directory:
        normalized = normalized.rstrip("/")
    if (
        not normalized
        or normalized.startswith("/")
        or normalized.startswith("//")
        or re.match(r"^[A-Za-z]:", normalized)
    ):
        raise RuntimeProofError("RUNTIME_ARCHIVE_UNSAFE_MEMBER")
    components = normalized.split("/")
    for component in components:
        if (
            component in {"", ".", ".."}
            or ":" in component
            or component.endswith((".", " "))
            or any(ord(character) < 32 for character in component)
            or component.split(".", 1)[0].upper() in _WINDOWS_DEVICE_NAMES
        ):
            raise RuntimeProofError("RUNTIME_ARCHIVE_UNSAFE_MEMBER")
    return "/".join(components)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Offline EasyTravel sherpa runtime safety proof"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare-runtime")
    prepare.add_argument("--archive", required=True, type=Path)
    prepare.add_argument("--staging-dir", required=True, type=Path)
    prepare.add_argument("--runtime-dir", required=True, type=Path)
    prepare.add_argument("--proof-dir", required=True, type=Path)
    prove = commands.add_parser("prove-runtime")
    prove.add_argument("--proof-dir", required=True, type=Path)
    prove.add_argument("--runtime-dir", required=True, type=Path)
    prove.add_argument("--ack-valid-signed-runtime", action="store_true")
    prove.add_argument("--ack-not-signed-runtime-once", action="store_true")
    prove.add_argument("--ack-outer-sha256")
    prove.add_argument("--ack-load-inventory-sha256")
    prove.add_argument("--ack-executable-sha256")
    verify = commands.add_parser("verify-runtime-proof")
    verify.add_argument("proof_dir", type=Path)
    return parser


def _default_adapters() -> RuntimeAdapters:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeProofError("RUNTIME_PATH_OUTSIDE_PER_USER_ROOT")
    return RuntimeAdapters(
        asset_spec=PINNED_RUNTIME,
        repo_root=Path(__file__).resolve().parents[2],
        per_user_root=Path(local_app_data) / "EasyTravelVoicePilot",
        signature_probe=_default_signature_probe,
        runner=subprocess.run,
        process_probe=_default_process_probe,
        listener_probe=_default_listener_probe,
        event_probe=_default_event_probe,
    )


def _default_signature_probe(path: Path) -> SignatureRecord:
    argv, environment_delta = build_authenticode_probe_command(path)
    environment = dict(os.environ)
    environment.update(environment_delta)
    try:
        result = subprocess.run(
            argv,
            shell=False,
            stdin=subprocess.DEVNULL,
            cwd=path.parent,
            timeout=30,
            capture_output=True,
            env=environment,
        )
        stdout = _output_bytes(result.stdout)
        if result.returncode != 0 or len(stdout) > 64 * 1024:
            raise RuntimeProofError("RUNTIME_SIGNATURE_INVALID")
        return parse_authenticode_probe_json(stdout.decode("utf-8"))
    except (OSError, subprocess.TimeoutExpired, UnicodeError) as error:
        raise RuntimeProofError("RUNTIME_SIGNATURE_INVALID") from error


_PROCESS_PROBE_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
@(Get-Process | Where-Object { $_.ProcessName -match '^(SmartSub|sherpa)' } |
    Select-Object @{n='pid';e={$_.Id}}, @{n='name';e={$_.ProcessName}}) |
    ConvertTo-Json -Compress
""".strip()

_LISTENER_PROBE_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
@(Get-NetTCPConnection -State Listen |
    Select-Object LocalAddress, LocalPort, OwningProcess) |
    ConvertTo-Json -Compress
""".strip()

_EVENT_PROBE_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$start = [DateTimeOffset]::Parse($env:EASYTRAVEL_EVENT_START).UtcDateTime
$end = [DateTimeOffset]::Parse($env:EASYTRAVEL_EVENT_END).UtcDateTime
@(Get-WinEvent -FilterHashtable @{LogName='Application'; Id=1000; StartTime=$start; EndTime=$end} -ErrorAction SilentlyContinue |
    Select-Object Id, RecordId, ProviderName, TimeCreated) |
    ConvertTo-Json -Compress
""".strip()


def _powershell_json_probe(
    script: str, *, environment_delta: dict[str, str] | None = None
) -> list[object]:
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    environment = dict(os.environ)
    if environment_delta:
        environment.update(environment_delta)
    try:
        result = subprocess.run(
            (
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-EncodedCommand",
                encoded,
            ),
            shell=False,
            stdin=subprocess.DEVNULL,
            timeout=30,
            capture_output=True,
            env=environment,
        )
        stdout = _output_bytes(result.stdout)
        if result.returncode != 0 or len(stdout) > 1024 * 1024:
            raise RuntimeProofError("RUNTIME_POSTFLIGHT_DIRTY")
        value = json.loads(stdout.decode("utf-8"))
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return [value]
        raise RuntimeProofError("RUNTIME_POSTFLIGHT_DIRTY")
    except (
        OSError,
        subprocess.TimeoutExpired,
        UnicodeError,
        ValueError,
    ) as error:
        raise RuntimeProofError("RUNTIME_POSTFLIGHT_DIRTY") from error


def _default_process_probe() -> list[object]:
    return _powershell_json_probe(_PROCESS_PROBE_SCRIPT)


def _default_listener_probe() -> list[object]:
    return _powershell_json_probe(_LISTENER_PROBE_SCRIPT)


def _default_event_probe(start_utc: str, end_utc: str) -> list[object]:
    return _powershell_json_probe(
        _EVENT_PROBE_SCRIPT,
        environment_delta={
            "EASYTRAVEL_EVENT_START": start_utc,
            "EASYTRAVEL_EVENT_END": end_utc,
        },
    )


def _validate_existing_proof_paths(
    repo_root: Path,
    per_user_root: Path,
    proof_dir: Path,
    runtime_dir: Path | None = None,
) -> None:
    if not proof_dir.is_absolute() or (
        runtime_dir is not None and not runtime_dir.is_absolute()
    ):
        raise RuntimeProofError("RUNTIME_PATH_OUTSIDE_PER_USER_ROOT")
    resolved_repo = repo_root.resolve(strict=True)
    resolved_private = per_user_root.resolve(strict=True)
    if _is_reparse_point(per_user_root):
        raise RuntimeProofError("RUNTIME_PATH_OUTSIDE_PER_USER_ROOT")
    lexical_proof = proof_dir.absolute()
    if not lexical_proof.is_relative_to(resolved_private):
        raise RuntimeProofError("RUNTIME_PATH_OUTSIDE_PER_USER_ROOT")
    _require_no_reparse_chain(resolved_private, lexical_proof)
    resolved_proof = proof_dir.resolve(strict=True)
    proofs_root = (resolved_private / "proofs").resolve(strict=True)
    if (
        resolved_proof == proofs_root
        or not resolved_proof.is_relative_to(proofs_root)
        or resolved_proof.is_relative_to(resolved_repo)
    ):
        raise RuntimeProofError("RUNTIME_PATH_OUTSIDE_PER_USER_ROOT")
    if runtime_dir is not None:
        lexical_runtime = runtime_dir.absolute()
        if not lexical_runtime.is_relative_to(resolved_private):
            raise RuntimeProofError("RUNTIME_PATH_OUTSIDE_PER_USER_ROOT")
        _require_no_reparse_chain(resolved_private, lexical_runtime)
        resolved_runtime = runtime_dir.resolve(strict=False)
        expected_runtime = (
            resolved_private / "runtime" / "sherpa-onnx" / "1.13.6"
        ).resolve(strict=False)
        if (
            resolved_runtime != expected_runtime
            or resolved_runtime.is_relative_to(resolved_repo)
        ):
            raise RuntimeProofError("RUNTIME_PATH_OUTSIDE_PER_USER_ROOT")


def _require_no_reparse_chain(root: Path, target: Path) -> None:
    relative = target.relative_to(root)
    current = root
    if _is_reparse_point(current):
        raise RuntimeProofError("RUNTIME_PATH_OUTSIDE_PER_USER_ROOT")
    for component in relative.parts:
        current = current / component
        if current.exists() and _is_reparse_point(current):
            raise RuntimeProofError("RUNTIME_PATH_OUTSIDE_PER_USER_ROOT")


def _cli_summary(document: dict[str, object]) -> dict[str, object]:
    inventory = document.get("inventory")
    asset = document.get("asset")
    state = document.get("state")
    next_step = {
        "READY_TO_EXECUTE": "run-prove-runtime-only-under-current-gate",
        "BLOCKED_UNSIGNED": "stop-and-request-exact-hash-gate",
        "PASSED": "stop",
        "FAILED": "stop",
    }.get(state, "stop")
    return {
        "evidence_id": document.get("evidence_id"),
        "executable_sha256": (
            inventory.get("mandatory_executable_sha256")
            if isinstance(inventory, dict)
            else None
        ),
        "load_inventory_sha256": (
            inventory.get("sha256") if isinstance(inventory, dict) else None
        ),
        "next_step": next_step,
        "outer_sha256": asset.get("sha256") if isinstance(asset, dict) else None,
        "safe_code": document.get("safe_code"),
        "state": state,
    }


def _emit_cli_json(payload: dict[str, object]) -> None:
    print(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    )


def main(
    argv: list[str] | None = None, *, adapters: RuntimeAdapters | None = None
) -> int:
    arguments = _build_parser().parse_args(argv)
    try:
        active = adapters if adapters is not None else _default_adapters()
        if arguments.command == "prepare-runtime":
            validate_runtime_paths(
                active.repo_root,
                active.per_user_root,
                arguments.archive,
                arguments.staging_dir,
                arguments.runtime_dir,
                arguments.proof_dir,
            )
            preparation = prepare_runtime(
                arguments.archive,
                spec=active.asset_spec,
                staging_dir=arguments.staging_dir,
                runtime_dir=arguments.runtime_dir,
                proof_dir=arguments.proof_dir,
                signature_probe=active.signature_probe,
            )
            document = _read_evidence(preparation.proof_dir)
            _emit_cli_json(_cli_summary(document))
            return preparation.exit_code
        if arguments.command == "prove-runtime":
            _validate_existing_proof_paths(
                active.repo_root,
                active.per_user_root,
                arguments.proof_dir,
                arguments.runtime_dir,
            )
            proof = run_runtime_proof(
                arguments.proof_dir,
                runner=active.runner,
                process_probe=active.process_probe,
                listener_probe=active.listener_probe,
                event_probe=active.event_probe,
                runtime_dir=arguments.runtime_dir,
                ack_valid_signed_runtime=arguments.ack_valid_signed_runtime,
                ack_not_signed_runtime_once=arguments.ack_not_signed_runtime_once,
                ack_outer_sha256=arguments.ack_outer_sha256,
                ack_load_inventory_sha256=arguments.ack_load_inventory_sha256,
                ack_executable_sha256=arguments.ack_executable_sha256,
            )
            document = _read_evidence(proof.proof_dir)
            _emit_cli_json(_cli_summary(document))
            return proof.exit_code
        _validate_existing_proof_paths(
            active.repo_root,
            active.per_user_root,
            arguments.proof_dir,
        )
        proof = verify_runtime_proof(arguments.proof_dir)
        document = _read_evidence(proof.proof_dir)
        _emit_cli_json(_cli_summary(document))
        return proof.exit_code
    except RuntimeProofError as error:
        _emit_cli_json(
            {
                "evidence_id": None,
                "executable_sha256": None,
                "load_inventory_sha256": None,
                "next_step": "stop",
                "outer_sha256": None,
                "safe_code": error.code,
                "state": "FAILED",
            }
        )
        return 30


if __name__ == "__main__":
    raise SystemExit(main())
