from __future__ import annotations

import base64
import hashlib
import inspect
import io
import json
import os
import subprocess
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.voice_pilot.runtime_proof as runtime_proof_module
from scripts.voice_pilot.runtime_proof import (
    PINNED_RUNTIME,
    RuntimeAssetSpec,
    RuntimeAdapters,
    RuntimePreparation,
    RuntimeProof,
    RuntimeProofError,
    SignatureRecord,
    build_authenticode_probe_command,
    build_archive_plan,
    build_load_inventory,
    main as runtime_main,
    prepare_runtime,
    parse_authenticode_probe_json,
    run_runtime_proof,
    safe_extract_runtime,
    validate_runtime_paths,
    verify_archive_identity,
    verify_runtime_proof,
)


@pytest.mark.parametrize(
    "script_name",
    [
        "_PROCESS_PROBE_SCRIPT",
        "_LISTENER_PROBE_SCRIPT",
        "_EVENT_PROBE_SCRIPT",
    ],
)
def test_probe_scripts_use_inputobject_array_contract(script_name):
    script = getattr(runtime_proof_module, script_name)

    assert "$rows = @(" in script
    assert "ConvertTo-Json -InputObject $rows -Compress" in script


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        (b"[]", []),
        (b'[{"pid":1}]', [{"pid": 1}]),
        (b'[{"pid":1},{"pid":2}]', [{"pid": 1}, {"pid": 2}]),
        (b'{"pid":1}', [{"pid": 1}]),
    ],
)
def test_probe_decoder_accepts_zero_one_many_arrays_and_legacy_object(
    monkeypatch, stdout, expected
):
    monkeypatch.setattr(
        runtime_proof_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=stdout),
    )

    assert runtime_proof_module._powershell_json_probe("synthetic") == expected


@pytest.mark.parametrize(
    "stdout",
    [
        b"",
        b"null",
        b"0",
        b'"scalar"',
        b"true",
        b"{",
    ],
)
def test_probe_decoder_rejects_empty_null_scalar_or_invalid_stdout(monkeypatch, stdout):
    monkeypatch.setattr(
        runtime_proof_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=stdout),
    )

    with pytest.raises(RuntimeProofError) as failure:
        runtime_proof_module._powershell_json_probe("synthetic")

    assert failure.value.code == "RUNTIME_POSTFLIGHT_DIRTY"


def test_probe_decoder_rejects_oversized_stdout(monkeypatch):
    stdout = b"x" * (1024 * 1024 + 1)
    monkeypatch.setattr(
        runtime_proof_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=stdout),
    )

    with pytest.raises(RuntimeProofError) as failure:
        runtime_proof_module._powershell_json_probe("synthetic")

    assert failure.value.code == "RUNTIME_POSTFLIGHT_DIRTY"


@pytest.mark.parametrize("failure_kind", ["nonzero", "timeout", "encoding", "launch"])
def test_probe_decoder_rejects_nonzero_timeout_encoding_and_launch_failures(
    monkeypatch, failure_kind
):
    def run(*args, **kwargs):
        if failure_kind == "timeout":
            raise subprocess.TimeoutExpired(args[0], 30)
        if failure_kind == "launch":
            raise OSError("synthetic launch failure")
        if failure_kind == "encoding":
            return SimpleNamespace(returncode=0, stdout=b"\xff")
        return SimpleNamespace(returncode=1, stdout=b"[]")

    monkeypatch.setattr(runtime_proof_module.subprocess, "run", run)

    with pytest.raises(RuntimeProofError) as failure:
        runtime_proof_module._powershell_json_probe("synthetic")

    assert failure.value.code == "RUNTIME_POSTFLIGHT_DIRTY"


def _write_synthetic_archive(path, members):
    with tarfile.open(path, "w:bz2") as archive:
        for member, payload in members:
            if payload is None:
                archive.addfile(member)
            else:
                archive.addfile(member, io.BytesIO(payload))
    return verify_archive_identity(path, spec=_spec_for_archive(path))


def _spec_for_archive(path):
    payload = path.read_bytes()
    return RuntimeAssetSpec(
        release="test",
        filename=path.name,
        url="https://example.invalid/runtime.tar.bz2",
        bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        expected_root="runtime",
    )


def _directory_member(name):
    member = tarfile.TarInfo(name)
    member.type = tarfile.DIRTYPE
    return member


def _file_member(name, payload):
    member = tarfile.TarInfo(name)
    member.size = len(payload)
    return member, payload


def _signature(status="Valid", *, message="signature valid"):
    return SignatureRecord(
        status=status,
        status_message=message,
        signer_subject="CN=Synthetic Signer" if status == "Valid" else None,
        signer_issuer="CN=Synthetic Issuer" if status == "Valid" else None,
        signer_thumbprint="AA11" if status == "Valid" else None,
        timestamp_subject="CN=Synthetic Timestamp" if status == "Valid" else None,
        timestamp_issuer="CN=Synthetic Timestamp Issuer" if status == "Valid" else None,
        timestamp_thumbprint="BB22" if status == "Valid" else None,
    )


def _prepare_runtime_for_proof(tmp_path, *, include_version=False, status="Valid"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    archive = tmp_path / "runtime.tar.bz2"
    members = [
        (_directory_member("runtime"), None),
        (_directory_member("runtime/bin"), None),
        (_directory_member("runtime/lib"), None),
        _file_member("runtime/bin/sherpa-onnx-offline-tts.exe", b"mandatory"),
        _file_member("runtime/lib/runtime.dll", b"library"),
    ]
    if include_version:
        members.append(
            _file_member("runtime/bin/sherpa-onnx-version.exe", b"version")
        )
    _write_synthetic_archive(archive, members)
    staging = tmp_path / "runtime-staging" / "run"
    runtime = tmp_path / "installed" / "1.13.6"
    proof = tmp_path / "proofs" / "run"
    staging.parent.mkdir()
    runtime.parent.mkdir()
    proof.parent.mkdir()
    return prepare_runtime(
        archive,
        spec=_spec_for_archive(archive),
        staging_dir=staging,
        runtime_dir=runtime,
        proof_dir=proof,
        signature_probe=lambda path: _signature(status, message=f"synthetic {status}"),
    )


class _SyntheticTarView:
    def __init__(self, members):
        self._members = members

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def getmembers(self):
        return self._members


def test_pinned_runtime_asset_matches_approved_contract():
    assert PINNED_RUNTIME.release == "v1.13.6"
    assert (
        PINNED_RUNTIME.filename
        == "sherpa-onnx-v1.13.6-win-x64-shared-MT-Release.tar.bz2"
    )
    assert PINNED_RUNTIME.bytes == 24_497_928
    assert (
        PINNED_RUNTIME.sha256
        == "4a296ee44c0997ab9fd4d30d7196446ab77e0ef34f0ce66b5e01b3339fce4613"
    )
    assert (
        PINNED_RUNTIME.expected_root
        == "sherpa-onnx-v1.13.6-win-x64-shared-MT-Release"
    )


def test_verify_archive_identity_accepts_exact_synthetic_spec(tmp_path):
    payload = b"synthetic-runtime-archive"
    archive = tmp_path / "runtime.tar.bz2"
    archive.write_bytes(payload)
    spec = RuntimeAssetSpec(
        release="test",
        filename=archive.name,
        url="https://example.invalid/runtime.tar.bz2",
        bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        expected_root="runtime",
    )

    verified = verify_archive_identity(archive, spec=spec)

    assert verified.path == archive.resolve()
    assert verified.bytes == len(payload)
    assert verified.sha256 == "c2e4d82a98f5c057fd7f0b22288d9cfcda358c96518ef02b2593391d822ef5ba"


@pytest.mark.parametrize(
    ("byte_delta", "sha256", "expected_code"),
    [
        (1, "c2e4d82a98f5c057fd7f0b22288d9cfcda358c96518ef02b2593391d822ef5ba", "RUNTIME_ASSET_SIZE_MISMATCH"),
        (0, "0" * 64, "RUNTIME_ASSET_SHA256_MISMATCH"),
    ],
)
def test_verify_archive_identity_rejects_size_or_sha256_mismatch(
    tmp_path, byte_delta, sha256, expected_code
):
    payload = b"synthetic-runtime-archive"
    archive = tmp_path / "runtime.tar.bz2"
    archive.write_bytes(payload)
    spec = RuntimeAssetSpec(
        release="test",
        filename=archive.name,
        url="https://example.invalid/runtime.tar.bz2",
        bytes=len(payload) + byte_delta,
        sha256=sha256,
        expected_root="runtime",
    )

    with pytest.raises(RuntimeProofError) as failure:
        verify_archive_identity(archive, spec=spec)

    assert failure.value.code == expected_code


def test_runtime_paths_reject_repo_relative_outside_root_existing_and_reparse_targets(
    tmp_path, monkeypatch
):
    repo_root = tmp_path / "repo"
    per_user_root = tmp_path / "private"
    repo_root.mkdir()
    archive = per_user_root / "downloads" / "runtime.tar.bz2"
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b"synthetic")
    staging = per_user_root / "runtime-staging" / "run"
    runtime = per_user_root / "runtime" / "sherpa-onnx" / "1.13.6"
    proof = per_user_root / "proofs" / "run"

    invalid_cases = [
        (
            Path("relative-staging"),
            runtime,
            proof,
            "RUNTIME_PATH_OUTSIDE_PER_USER_ROOT",
        ),
        (
            tmp_path / "outside-staging",
            runtime,
            proof,
            "RUNTIME_PATH_OUTSIDE_PER_USER_ROOT",
        ),
        (
            repo_root / "staging",
            runtime,
            proof,
            "RUNTIME_PATH_INSIDE_REPOSITORY",
        ),
    ]
    for invalid_staging, valid_runtime, valid_proof, expected_code in invalid_cases:
        with pytest.raises(RuntimeProofError) as failure:
            validate_runtime_paths(
                repo_root,
                per_user_root,
                archive,
                invalid_staging,
                valid_runtime,
                valid_proof,
            )
        assert failure.value.code == expected_code

    existing_proof = per_user_root / "proofs" / "existing"
    existing_proof.mkdir(parents=True)
    with pytest.raises(RuntimeProofError) as failure:
        validate_runtime_paths(
            repo_root,
            per_user_root,
            archive,
            staging,
            runtime,
            existing_proof,
        )
    assert failure.value.code == "RUNTIME_OUTPUT_EXISTS"

    outside_target = tmp_path / "reparse-target"
    outside_target.mkdir()
    reparse_parent = per_user_root / "runtime-staging" / "reparse"
    reparse_parent.parent.mkdir(parents=True, exist_ok=True)
    reparse_child = reparse_parent / "run"
    original_resolve = Path.resolve

    def resolve_reparse(path, strict=False):
        if path == reparse_child:
            return outside_target / "run"
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", resolve_reparse)
    with pytest.raises(RuntimeProofError) as failure:
        validate_runtime_paths(
            repo_root,
            per_user_root,
            archive,
            reparse_child,
            runtime,
            proof,
        )
    assert failure.value.code == "RUNTIME_PATH_OUTSIDE_PER_USER_ROOT"


def test_runtime_paths_accept_only_new_siblings_under_fixed_per_user_root(tmp_path):
    repo_root = tmp_path / "repo"
    per_user_root = tmp_path / "private"
    repo_root.mkdir()
    archive = per_user_root / "downloads" / "runtime.tar.bz2"
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b"synthetic")
    staging = per_user_root / "runtime-staging" / "run"
    runtime = per_user_root / "runtime" / "sherpa-onnx" / "1.13.6"
    proof = per_user_root / "proofs" / "run"

    validate_runtime_paths(
        repo_root,
        per_user_root,
        archive,
        staging,
        runtime,
        proof,
    )

    assert not staging.exists()
    assert not runtime.exists()
    assert not proof.exists()

    with pytest.raises(RuntimeProofError) as failure:
        validate_runtime_paths(
            repo_root,
            per_user_root,
            archive,
            per_user_root / "proofs" / "misrouted-staging",
            runtime,
            proof,
        )
    assert failure.value.code == "RUNTIME_PATH_OUTSIDE_PER_USER_ROOT"


def test_runtime_cli_has_no_download_model_text_reference_or_output_options(capsys):
    with pytest.raises(SystemExit) as prepare_help:
        runtime_main(["prepare-runtime", "--help"])
    assert prepare_help.value.code == 0
    prepare_output = capsys.readouterr().out

    with pytest.raises(SystemExit) as prove_help:
        runtime_main(["prove-runtime", "--help"])
    assert prove_help.value.code == 0
    prove_output = capsys.readouterr().out

    combined_help = prepare_output + prove_output
    assert "--archive" in prepare_output
    assert "--proof-dir" in combined_help
    assert "--runtime-dir" in combined_help
    for forbidden in (
        "download",
        "--model",
        "--text",
        "--reference",
        "--output",
        "--server",
        "--port",
        "--admin",
        "--fallback",
    ):
        assert forbidden not in combined_help


def test_archive_plan_accepts_one_expected_root_with_regular_files_and_directories(
    tmp_path,
):
    archive = tmp_path / "runtime.tar.bz2"
    verified = _write_synthetic_archive(
        archive,
        [
            (_directory_member("runtime"), None),
            _file_member("runtime/bin/tool.exe", b"tool"),
            _file_member("runtime/lib/runtime.dll", b"dll"),
        ],
    )

    plan = build_archive_plan(archive, verified=verified, expected_root="runtime")

    assert plan.expected_root == "runtime"
    assert plan.entry_count == 3
    assert plan.total_uncompressed_bytes == 7
    assert [member.relative_path for member in plan.members] == [
        "runtime",
        "runtime/bin/tool.exe",
        "runtime/lib/runtime.dll",
    ]


@pytest.mark.parametrize(
    "unsafe_name",
    [
        "/runtime/bin/tool.exe",
        "C:/runtime/bin/tool.exe",
        "//server/share/runtime/tool.exe",
        "runtime/../escape.exe",
        r"runtime\..\escape.exe",
        "runtime//bin/tool.exe",
        "runtime/bin/tool.exe:stream",
        "runtime/bin/CON",
        "runtime/bin/aux.txt",
        "runtime/bin/trailing.",
        "runtime/bin/trailing ",
    ],
)
def test_archive_plan_rejects_absolute_drive_unc_parent_ads_device_and_trailing_names(
    tmp_path, unsafe_name
):
    archive = tmp_path / f"unsafe-{hashlib.sha256(unsafe_name.encode()).hexdigest()[:8]}.tar.bz2"
    verified = _write_synthetic_archive(
        archive,
        [
            (_directory_member("runtime"), None),
            _file_member(unsafe_name, b"unsafe"),
        ],
    )

    with pytest.raises(RuntimeProofError) as failure:
        build_archive_plan(archive, verified=verified, expected_root="runtime")

    assert failure.value.code == "RUNTIME_ARCHIVE_UNSAFE_MEMBER"


@pytest.mark.parametrize(
    "member_type",
    [
        tarfile.SYMTYPE,
        tarfile.LNKTYPE,
        tarfile.CHRTYPE,
        tarfile.BLKTYPE,
        tarfile.FIFOTYPE,
        b"S",
    ],
)
def test_archive_plan_rejects_symlink_hardlink_special_and_unknown_members(
    tmp_path, member_type
):
    archive = tmp_path / f"special-{member_type.hex()}.tar.bz2"
    unsafe_member = tarfile.TarInfo("runtime/unsafe")
    unsafe_member.type = member_type
    if member_type in {tarfile.SYMTYPE, tarfile.LNKTYPE}:
        unsafe_member.linkname = "runtime/target"
    verified = _write_synthetic_archive(
        archive,
        [
            (_directory_member("runtime"), None),
            (unsafe_member, None),
        ],
    )

    with pytest.raises(RuntimeProofError) as failure:
        build_archive_plan(archive, verified=verified, expected_root="runtime")

    assert failure.value.code == "RUNTIME_ARCHIVE_UNSAFE_MEMBER"


@pytest.mark.parametrize(
    "entries",
    [
        [("runtime/bin/tool.exe", False), ("runtime/bin/tool.exe", False)],
        [("runtime/bin/Tool.exe", False), ("runtime/bin/tool.exe", False)],
        [("runtime/bin", False), ("runtime/bin/tool.exe", False)],
    ],
)
def test_archive_plan_rejects_duplicate_casefold_and_file_directory_prefix_collisions(
    tmp_path, entries
):
    archive = tmp_path / "collision.tar.bz2"
    members = [(_directory_member("runtime"), None)]
    for index, (name, is_directory) in enumerate(entries):
        if is_directory:
            members.append((_directory_member(name), None))
        else:
            members.append(_file_member(name, f"file-{index}".encode()))
    verified = _write_synthetic_archive(archive, members)

    with pytest.raises(RuntimeProofError) as failure:
        build_archive_plan(archive, verified=verified, expected_root="runtime")

    assert failure.value.code == "RUNTIME_ARCHIVE_UNSAFE_MEMBER"


def test_archive_plan_rejects_wrong_or_multiple_roots_and_entry_or_size_limits(
    tmp_path, monkeypatch
):
    archive = tmp_path / "limits.tar.bz2"
    verified = _write_synthetic_archive(
        archive,
        [
            (_directory_member("runtime"), None),
            _file_member("runtime/file", b"file"),
        ],
    )

    root_cases = [
        ([_directory_member("other")], "RUNTIME_ARCHIVE_ROOT_MISMATCH"),
        (
            [_directory_member("runtime"), _directory_member("other")],
            "RUNTIME_ARCHIVE_ROOT_MISMATCH",
        ),
    ]
    for members, expected_code in root_cases:
        monkeypatch.setattr(
            tarfile, "open", lambda *args, members=members, **kwargs: _SyntheticTarView(members)
        )
        with pytest.raises(RuntimeProofError) as failure:
            build_archive_plan(archive, verified=verified, expected_root="runtime")
        assert failure.value.code == expected_code

    too_many = [_directory_member("runtime")]
    too_many.extend(
        tarfile.TarInfo(f"runtime/files/{index}") for index in range(20_000)
    )
    oversized = tarfile.TarInfo("runtime/oversized")
    oversized.size = 1_073_741_825
    total_one = tarfile.TarInfo("runtime/total-one")
    total_one.size = 800_000_000
    total_two = tarfile.TarInfo("runtime/total-two")
    total_two.size = 800_000_000
    total_three = tarfile.TarInfo("runtime/total-three")
    total_three.size = 800_000_000
    limit_cases = [
        too_many,
        [_directory_member("runtime"), oversized],
        [_directory_member("runtime"), total_one, total_two, total_three],
    ]
    for members in limit_cases:
        monkeypatch.setattr(
            tarfile, "open", lambda *args, members=members, **kwargs: _SyntheticTarView(members)
        )
        with pytest.raises(RuntimeProofError) as failure:
            build_archive_plan(archive, verified=verified, expected_root="runtime")
        assert failure.value.code == "RUNTIME_ARCHIVE_LIMIT_EXCEEDED"


def test_safe_extract_writes_only_planned_regular_files_without_extractall(
    tmp_path, monkeypatch
):
    archive = tmp_path / "runtime.tar.bz2"
    verified = _write_synthetic_archive(
        archive,
        [
            (_directory_member("runtime"), None),
            (_directory_member("runtime/bin"), None),
            _file_member("runtime/bin/tool.exe", b"synthetic-tool"),
            _file_member("runtime/runtime.dll", b"synthetic-dll"),
        ],
    )
    plan = build_archive_plan(archive, verified=verified, expected_root="runtime")
    staging = tmp_path / "runtime-staging" / "run"
    staging.parent.mkdir()

    def forbidden_extract(*args, **kwargs):
        raise AssertionError("TarFile.extract/extractall must never be called")

    monkeypatch.setattr(tarfile.TarFile, "extract", forbidden_extract)
    monkeypatch.setattr(tarfile.TarFile, "extractall", forbidden_extract)

    extracted_root = safe_extract_runtime(archive, plan=plan, staging_dir=staging)

    assert extracted_root == (staging / "runtime").resolve()
    assert (extracted_root / "bin" / "tool.exe").read_bytes() == b"synthetic-tool"
    assert (extracted_root / "runtime.dll").read_bytes() == b"synthetic-dll"
    assert {
        path.relative_to(staging).as_posix()
        for path in staging.rglob("*")
        if path.is_file()
    } == {"runtime/bin/tool.exe", "runtime/runtime.dll"}


def test_safe_extract_refuses_existing_target_and_reparse_escape(tmp_path, monkeypatch):
    archive = tmp_path / "runtime.tar.bz2"
    verified = _write_synthetic_archive(
        archive,
        [
            (_directory_member("runtime"), None),
            _file_member("runtime/tool.exe", b"synthetic-tool"),
        ],
    )
    plan = build_archive_plan(archive, verified=verified, expected_root="runtime")
    staging_parent = tmp_path / "runtime-staging"
    staging_parent.mkdir()
    existing_staging = staging_parent / "existing"
    existing_staging.mkdir()
    sentinel = existing_staging / "sentinel.txt"
    sentinel.write_text("preserve", encoding="utf-8")

    with pytest.raises(RuntimeProofError) as existing_failure:
        safe_extract_runtime(archive, plan=plan, staging_dir=existing_staging)
    assert existing_failure.value.code == "RUNTIME_OUTPUT_EXISTS"
    assert sentinel.read_text(encoding="utf-8") == "preserve"

    reparse_staging = staging_parent / "reparse"
    reparse_directory = reparse_staging / "runtime"
    original_stat = Path.stat

    def stat_with_reparse_attribute(path, *, follow_symlinks=True):
        result = original_stat(path, follow_symlinks=follow_symlinks)
        if path == reparse_directory and not follow_symlinks:
            return SimpleNamespace(
                st_mode=result.st_mode,
                st_file_attributes=getattr(result, "st_file_attributes", 0) | 0x400,
            )
        return result

    monkeypatch.setattr(Path, "stat", stat_with_reparse_attribute)

    with pytest.raises(RuntimeProofError) as reparse_failure:
        safe_extract_runtime(archive, plan=plan, staging_dir=reparse_staging)
    assert reparse_failure.value.code == "RUNTIME_EXTRACTION_FAILED"
    assert reparse_staging.exists()
    assert not (reparse_directory / "tool.exe").exists()


def test_safe_extract_preserves_incomplete_staging_and_never_promotes_on_failure(
    tmp_path, monkeypatch
):
    archive = tmp_path / "runtime.tar.bz2"
    verified = _write_synthetic_archive(
        archive,
        [
            (_directory_member("runtime"), None),
            _file_member("runtime/first.dll", b"first"),
            _file_member("runtime/second.dll", b"second"),
        ],
    )
    plan = build_archive_plan(archive, verified=verified, expected_root="runtime")
    staging = tmp_path / "runtime-staging" / "run"
    staging.parent.mkdir()
    final_runtime = tmp_path / "runtime" / "sherpa-onnx" / "1.13.6"
    failing_target = staging / "runtime" / "second.dll"
    original_open = Path.open

    def fail_second_write(path, mode="r", *args, **kwargs):
        if path == failing_target and mode == "xb":
            raise OSError("synthetic write failure")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_second_write)

    with pytest.raises(RuntimeProofError) as failure:
        safe_extract_runtime(archive, plan=plan, staging_dir=staging)

    assert failure.value.code == "RUNTIME_EXTRACTION_FAILED"
    assert (staging / "runtime" / "first.dll").read_bytes() == b"first"
    assert not failing_target.exists()
    assert not final_runtime.exists()
    assert json.loads(
        (staging / ".runtime-proof-extraction-failure.json").read_text(
            encoding="utf-8"
        )
    ) == {"safe_code": "RUNTIME_EXTRACTION_FAILED", "state": "FAILED"}


def test_load_inventory_includes_allowlisted_executable_and_every_dll_in_canonical_order(
    tmp_path,
):
    runtime_root = tmp_path / "runtime"
    (runtime_root / "bin").mkdir(parents=True)
    (runtime_root / "lib").mkdir()
    (runtime_root / "plugins").mkdir()
    files = {
        "bin/sherpa-onnx-offline-tts.exe": b"mandatory",
        "bin/sherpa-onnx-version.exe": b"version",
        "bin/ignored-tool.exe": b"ignored",
        "lib/B.dll": b"upper",
        "plugins/a.dll": b"lower",
        "README.txt": b"ignored",
    }
    for relative_path, payload in files.items():
        target = runtime_root.joinpath(*relative_path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    probed = []

    def signature_probe(path):
        probed.append(path)
        return _signature()

    inventory = build_load_inventory(runtime_root, signature_probe=signature_probe)

    assert [row.relative_path for row in inventory.rows] == [
        "bin/sherpa-onnx-offline-tts.exe",
        "bin/sherpa-onnx-version.exe",
        "lib/B.dll",
        "plugins/a.dll",
    ]
    assert [row.bytes for row in inventory.rows] == [9, 7, 5, 5]
    assert all(len(row.sha256) == 64 for row in inventory.rows)
    assert all(row.signature.status == "Valid" for row in inventory.rows)
    assert {path.name for path in probed} == {
        "sherpa-onnx-offline-tts.exe",
        "sherpa-onnx-version.exe",
        "B.dll",
        "a.dll",
    }
    assert inventory.mandatory_executable_relative_path == (
        "bin/sherpa-onnx-offline-tts.exe"
    )
    assert inventory.version_executable_relative_path == "bin/sherpa-onnx-version.exe"
    assert len(inventory.sha256) == 64


def test_load_inventory_hash_is_stable_and_changes_on_path_bytes_hash_or_signature_change(
    tmp_path,
):
    def inventory_for(
        name,
        *,
        dll_path="lib/runtime.dll",
        dll_payload=b"runtime",
        signature_status="Valid",
    ):
        root = tmp_path / name
        mandatory = root / "bin" / "sherpa-onnx-offline-tts.exe"
        library = root.joinpath(*dll_path.split("/"))
        mandatory.parent.mkdir(parents=True)
        library.parent.mkdir(parents=True, exist_ok=True)
        mandatory.write_bytes(b"mandatory")
        library.write_bytes(dll_payload)
        return build_load_inventory(
            root,
            signature_probe=lambda path: _signature(signature_status),
        )

    baseline = inventory_for("baseline")
    identical = inventory_for("identical")
    path_changed = inventory_for("path", dll_path="plugins/runtime.dll")
    bytes_changed = inventory_for("bytes", dll_payload=b"runtime-longer")
    hash_only_changed = inventory_for("hash", dll_payload=b"runtimf")
    signature_changed = inventory_for("signature", signature_status="NotSigned")

    assert identical.sha256 == baseline.sha256
    assert path_changed.sha256 != baseline.sha256
    assert bytes_changed.sha256 != baseline.sha256
    assert hash_only_changed.rows[1].bytes == baseline.rows[1].bytes
    assert hash_only_changed.rows[1].sha256 != baseline.rows[1].sha256
    assert hash_only_changed.sha256 != baseline.sha256
    assert signature_changed.sha256 != baseline.sha256


def test_prepare_runtime_returns_ready_only_when_every_load_candidate_is_valid(
    tmp_path,
):
    archive = tmp_path / "runtime.tar.bz2"
    _write_synthetic_archive(
        archive,
        [
            (_directory_member("runtime"), None),
            (_directory_member("runtime/bin"), None),
            _file_member("runtime/bin/sherpa-onnx-offline-tts.exe", b"mandatory"),
            _file_member("runtime/runtime.dll", b"library"),
        ],
    )
    staging = tmp_path / "runtime-staging" / "run"
    runtime = tmp_path / "installed" / "1.13.6"
    proof = tmp_path / "proofs" / "run"
    staging.parent.mkdir()
    runtime.parent.mkdir()
    proof.parent.mkdir()

    preparation = prepare_runtime(
        archive,
        spec=_spec_for_archive(archive),
        staging_dir=staging,
        runtime_dir=runtime,
        proof_dir=proof,
        signature_probe=lambda path: _signature(),
    )

    assert isinstance(preparation, RuntimePreparation)
    assert preparation.state == "READY_TO_EXECUTE"
    assert preparation.safe_code is None
    assert preparation.exit_code == 0
    assert preparation.promoted is True
    assert preparation.runtime_root == runtime.resolve()
    assert (runtime / "bin" / "sherpa-onnx-offline-tts.exe").read_bytes() == (
        b"mandatory"
    )
    assert (runtime / "runtime.dll").read_bytes() == b"library"
    assert not (staging / "runtime").exists()


def test_prepare_runtime_stops_unsigned_before_promotion_or_execution(tmp_path):
    archive = tmp_path / "runtime.tar.bz2"
    _write_synthetic_archive(
        archive,
        [
            (_directory_member("runtime"), None),
            (_directory_member("runtime/bin"), None),
            _file_member("runtime/bin/sherpa-onnx-offline-tts.exe", b"mandatory"),
            _file_member("runtime/runtime.dll", b"library"),
        ],
    )
    staging = tmp_path / "runtime-staging" / "run"
    runtime = tmp_path / "installed" / "1.13.6"
    proof = tmp_path / "proofs" / "run"
    staging.parent.mkdir()
    runtime.parent.mkdir()
    proof.parent.mkdir()

    preparation = prepare_runtime(
        archive,
        spec=_spec_for_archive(archive),
        staging_dir=staging,
        runtime_dir=runtime,
        proof_dir=proof,
        signature_probe=lambda path: (
            _signature("NotSigned", message="not signed")
            if path.suffix.casefold() == ".exe"
            else _signature()
        ),
    )

    assert preparation.state == "BLOCKED_UNSIGNED"
    assert preparation.safe_code == "RUNTIME_SIGNATURE_NOT_SIGNED"
    assert preparation.exit_code == 20
    assert preparation.promoted is False
    assert preparation.runtime_root is None
    assert not runtime.exists()
    assert (staging / "runtime" / "bin" / "sherpa-onnx-offline-tts.exe").exists()
    assert proof.is_dir()


@pytest.mark.parametrize(
    "statuses",
    [
        ("HashMismatch", "Valid"),
        ("NotTrusted", "Valid"),
        ("UnknownError", "Valid"),
        ("UnexpectedStatus", "Valid"),
        ("NotSigned", "HashMismatch"),
    ],
)
def test_prepare_runtime_blocks_invalid_untrusted_unknown_and_mixed_signature_states(
    tmp_path, statuses
):
    archive = tmp_path / "runtime.tar.bz2"
    _write_synthetic_archive(
        archive,
        [
            (_directory_member("runtime"), None),
            _file_member("runtime/sherpa-onnx-offline-tts.exe", b"mandatory"),
            _file_member("runtime/runtime.dll", b"library"),
        ],
    )
    staging = tmp_path / "runtime-staging" / "run"
    runtime = tmp_path / "installed" / "1.13.6"
    proof = tmp_path / "proofs" / "run"
    staging.parent.mkdir()
    runtime.parent.mkdir()
    proof.parent.mkdir()

    def signature_probe(path):
        status = statuses[0] if path.suffix.casefold() == ".exe" else statuses[1]
        return _signature(status, message=f"synthetic {status}")

    preparation = prepare_runtime(
        archive,
        spec=_spec_for_archive(archive),
        staging_dir=staging,
        runtime_dir=runtime,
        proof_dir=proof,
        signature_probe=signature_probe,
    )

    assert preparation.state == "FAILED"
    assert preparation.safe_code == "RUNTIME_SIGNATURE_INVALID"
    assert preparation.exit_code == 30
    assert preparation.promoted is False
    assert not runtime.exists()
    assert (staging / "runtime").is_dir()


def test_prepare_runtime_rejects_missing_duplicate_or_reparsed_mandatory_executable(
    tmp_path, monkeypatch
):
    missing_root = tmp_path / "missing"
    missing_root.mkdir()
    (missing_root / "runtime.dll").write_bytes(b"library")
    with pytest.raises(RuntimeProofError) as missing_failure:
        build_load_inventory(missing_root, signature_probe=lambda path: _signature())
    assert missing_failure.value.code == "RUNTIME_EXECUTABLE_MISSING"

    duplicate_root = tmp_path / "duplicate"
    (duplicate_root / "bin").mkdir(parents=True)
    (duplicate_root / "tools").mkdir()
    (duplicate_root / "bin" / "sherpa-onnx-offline-tts.exe").write_bytes(b"one")
    (duplicate_root / "tools" / "sherpa-onnx-offline-tts.exe").write_bytes(b"two")
    with pytest.raises(RuntimeProofError) as duplicate_failure:
        build_load_inventory(duplicate_root, signature_probe=lambda path: _signature())
    assert duplicate_failure.value.code == "RUNTIME_EXECUTABLE_AMBIGUOUS"

    reparse_root = tmp_path / "reparse"
    reparse_root.mkdir()
    mandatory = reparse_root / "sherpa-onnx-offline-tts.exe"
    mandatory.write_bytes(b"mandatory")
    original_stat = Path.stat

    def stat_with_reparse_attribute(path, *, follow_symlinks=True):
        result = original_stat(path, follow_symlinks=follow_symlinks)
        if path == mandatory and not follow_symlinks:
            return SimpleNamespace(
                st_mode=result.st_mode,
                st_file_attributes=getattr(result, "st_file_attributes", 0) | 0x400,
            )
        return result

    monkeypatch.setattr(Path, "stat", stat_with_reparse_attribute)
    with pytest.raises(RuntimeProofError) as reparse_failure:
        build_load_inventory(reparse_root, signature_probe=lambda path: _signature())
    assert reparse_failure.value.code == "RUNTIME_EXECUTABLE_MISSING"


def test_load_inventory_fails_closed_on_signature_probe_ambiguity(tmp_path):
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    (runtime_root / "sherpa-onnx-offline-tts.exe").write_bytes(b"mandatory")

    ambiguous_probes = [
        lambda path: None,
        lambda path: (_ for _ in ()).throw(OSError("synthetic probe failure")),
    ]
    for signature_probe in ambiguous_probes:
        with pytest.raises(RuntimeProofError) as failure:
            build_load_inventory(runtime_root, signature_probe=signature_probe)
        assert failure.value.code == "RUNTIME_SIGNATURE_INVALID"


def test_unsigned_ack_must_match_outer_inventory_executable_hashes_and_literal(tmp_path):
    archive = tmp_path / "runtime.tar.bz2"
    _write_synthetic_archive(
        archive,
        [
            (_directory_member("runtime"), None),
            _file_member("runtime/sherpa-onnx-offline-tts.exe", b"mandatory"),
            _file_member("runtime/runtime.dll", b"library"),
        ],
    )
    staging = tmp_path / "runtime-staging" / "run"
    runtime = tmp_path / "installed" / "1.13.6"
    proof = tmp_path / "proofs" / "run"
    staging.parent.mkdir()
    runtime.parent.mkdir()
    proof.parent.mkdir()
    preparation = prepare_runtime(
        archive,
        spec=_spec_for_archive(archive),
        staging_dir=staging,
        runtime_dir=runtime,
        proof_dir=proof,
        signature_probe=lambda path: _signature("NotSigned", message="not signed"),
    )
    exact = {
        "ack_not_signed_runtime_once": True,
        "outer_sha256": preparation.verified_archive.sha256,
        "inventory_sha256": preparation.inventory.sha256,
        "executable_sha256": preparation.inventory.mandatory_executable_sha256,
    }

    preparation.require_unsigned_ack(**exact)

    mismatches = [
        {"ack_not_signed_runtime_once": False},
        {"outer_sha256": "0" * 64},
        {"inventory_sha256": "0" * 64},
        {"executable_sha256": "0" * 64},
    ]
    for mismatch in mismatches:
        supplied = exact | mismatch
        with pytest.raises(RuntimeProofError) as failure:
            preparation.require_unsigned_ack(**supplied)
        assert failure.value.code == "RUNTIME_ACK_MISMATCH"


def test_authenticode_adapter_uses_fixed_encoded_script_and_parses_structured_json():
    synthetic_path = Path("C:/synthetic/quote'; Write-Host PWN/runtime.dll")

    argv, environment_delta = build_authenticode_probe_command(synthetic_path)

    assert argv[:4] == (
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-EncodedCommand",
    )
    script = base64.b64decode(argv[4]).decode("utf-16-le")
    assert "Get-AuthenticodeSignature -LiteralPath $env:EASYTRAVEL_SIGNATURE_PATH" in script
    assert str(synthetic_path) not in script
    assert str(synthetic_path) not in " ".join(argv)
    assert environment_delta == {"EASYTRAVEL_SIGNATURE_PATH": str(synthetic_path)}

    payload = json.dumps(
        {
            "status": "Valid",
            "status_message": "signature valid",
            "signer_subject": "CN=Synthetic Signer",
            "signer_issuer": "CN=Synthetic Issuer",
            "signer_thumbprint": "AA11",
            "timestamp_subject": "CN=Synthetic Timestamp",
            "timestamp_issuer": "CN=Synthetic Timestamp Issuer",
            "timestamp_thumbprint": "BB22",
        }
    )
    assert parse_authenticode_probe_json(payload) == _signature()

    for invalid_payload in ("not-json", "[]", '{"status": 7}'):
        with pytest.raises(RuntimeProofError) as failure:
            parse_authenticode_probe_json(invalid_payload)
        assert failure.value.code == "RUNTIME_SIGNATURE_INVALID"


def test_proof_runner_uses_shell_false_closed_stdin_fixed_cwd_and_child_only_path(
    tmp_path,
):
    preparation = _prepare_runtime_for_proof(tmp_path)
    calls = []
    original_path = os.environ.get("PATH")

    def runner(argv, **kwargs):
        calls.append((tuple(argv), kwargs))
        return SimpleNamespace(
            returncode=0,
            stdout=(
                b"provider num-threads zipvoice-encoder zipvoice-decoder "
                b"reference-audio reference-text output-filename"
            ),
            stderr=b"",
        )

    process_snapshots = iter([(), ()])
    listener_snapshots = iter([(), ()])
    proof = run_runtime_proof(
        preparation.proof_dir,
        runner=runner,
        process_probe=lambda: next(process_snapshots),
        listener_probe=lambda: next(listener_snapshots),
        event_probe=lambda start_utc, end_utc: (),
        ack_valid_signed_runtime=True,
    )

    assert isinstance(proof, RuntimeProof)
    assert proof.state == "PASSED"
    assert proof.safe_code is None
    assert proof.exit_code == 0
    assert len(calls) == 1
    argv, kwargs = calls[0]
    executable = preparation.runtime_root / "bin" / "sherpa-onnx-offline-tts.exe"
    assert argv == (str(executable), "--help")
    assert kwargs["shell"] is False
    assert kwargs["stdin"] is subprocess.DEVNULL
    assert kwargs["cwd"] == executable.parent
    assert kwargs["timeout"] == 30
    assert kwargs["capture_output"] is True
    child_path = kwargs["env"]["PATH"].split(os.pathsep)
    assert child_path[:2] == [
        str(preparation.runtime_root / "bin"),
        str(preparation.runtime_root / "lib"),
    ]
    assert os.environ.get("PATH") == original_path


def test_proof_runner_allows_only_offline_tts_help_and_optional_version_utility(
    tmp_path,
):
    preparation = _prepare_runtime_for_proof(tmp_path, include_version=True)
    calls = []

    def runner(argv, **kwargs):
        calls.append(tuple(argv))
        if len(argv) == 1:
            return SimpleNamespace(returncode=0, stdout=b"v1.13.6", stderr=b"")
        return SimpleNamespace(
            returncode=0,
            stdout=(
                b"provider num-threads zipvoice-encoder zipvoice-decoder "
                b"reference-audio reference-text output-filename"
            ),
            stderr=b"",
        )

    process_snapshots = iter([(), ()])
    listener_snapshots = iter([(), ()])
    proof = run_runtime_proof(
        preparation.proof_dir,
        runner=runner,
        process_probe=lambda: next(process_snapshots),
        listener_probe=lambda: next(listener_snapshots),
        event_probe=lambda start_utc, end_utc: (),
        ack_valid_signed_runtime=True,
    )

    version = preparation.runtime_root / "bin" / "sherpa-onnx-version.exe"
    mandatory = preparation.runtime_root / "bin" / "sherpa-onnx-offline-tts.exe"
    assert proof.state == "PASSED"
    assert calls == [(str(version),), (str(mandatory), "--help")]
    evidence = json.loads(
        (preparation.proof_dir / "runtime-proof.json").read_text(encoding="utf-8")
    )
    assert evidence["execution"]["version_utility"] == "executed"
    assert [command["purpose"] for command in evidence["execution"]["commands"]] == [
        "version",
        "help",
    ]


def test_proof_runner_rejects_model_text_reference_output_server_port_and_unknown_args(
    tmp_path, capsys
):
    forbidden_parameters = {
        "model",
        "text",
        "reference",
        "output",
        "server",
        "port",
        "argv",
        "extra_args",
    }
    assert forbidden_parameters.isdisjoint(
        inspect.signature(run_runtime_proof).parameters
    )

    base = [
        "prove-runtime",
        "--proof-dir",
        str(tmp_path / "proof"),
        "--runtime-dir",
        str(tmp_path / "runtime"),
    ]
    for option in (
        "--model",
        "--text",
        "--reference-audio",
        "--output",
        "--server",
        "--port",
        "--unknown",
    ):
        with pytest.raises(SystemExit) as failure:
            runtime_main([*base, option, "synthetic"])
        assert failure.value.code == 2
        capsys.readouterr()


def test_proof_runner_requires_ready_state_or_exact_unsigned_ack_before_promotion(
    tmp_path,
):
    rejected = _prepare_runtime_for_proof(
        tmp_path / "rejected", status="NotSigned"
    )
    runner_calls = []

    rejected_proof = run_runtime_proof(
        rejected.proof_dir,
        runner=lambda *args, **kwargs: runner_calls.append((args, kwargs)),
        process_probe=lambda: (_ for _ in ()).throw(
            AssertionError("probe must not run before exact ack")
        ),
        listener_probe=lambda: (_ for _ in ()).throw(
            AssertionError("probe must not run before exact ack")
        ),
        event_probe=lambda *args: (_ for _ in ()).throw(
            AssertionError("probe must not run before exact ack")
        ),
        runtime_dir=rejected.runtime_target,
        ack_not_signed_runtime_once=True,
        ack_outer_sha256="0" * 64,
        ack_load_inventory_sha256=rejected.inventory.sha256,
        ack_executable_sha256=rejected.inventory.mandatory_executable_sha256,
    )

    assert rejected_proof.state == "FAILED"
    assert rejected_proof.safe_code == "RUNTIME_ACK_MISMATCH"
    assert runner_calls == []
    assert rejected.runtime_root is None
    assert not rejected.runtime_target.exists()
    assert rejected.staging_root.is_dir()

    approved = _prepare_runtime_for_proof(
        tmp_path / "approved", status="NotSigned"
    )

    def runner(argv, **kwargs):
        runner_calls.append((tuple(argv), kwargs))
        return SimpleNamespace(
            returncode=0,
            stdout=(
                b"provider num-threads zipvoice-encoder zipvoice-decoder "
                b"reference-audio reference-text output-filename"
            ),
            stderr=b"",
        )

    process_snapshots = iter([(), ()])
    listener_snapshots = iter([(), ()])
    approved_proof = run_runtime_proof(
        approved.proof_dir,
        runner=runner,
        process_probe=lambda: next(process_snapshots),
        listener_probe=lambda: next(listener_snapshots),
        event_probe=lambda start_utc, end_utc: (),
        runtime_dir=approved.runtime_target,
        ack_not_signed_runtime_once=True,
        ack_outer_sha256=approved.verified_archive.sha256,
        ack_load_inventory_sha256=approved.inventory.sha256,
        ack_executable_sha256=approved.inventory.mandatory_executable_sha256,
    )

    assert approved_proof.state == "PASSED"
    assert approved_proof.safe_code is None
    assert approved.runtime_target.is_dir()
    assert not approved.staging_root.exists()
    assert len(runner_calls) == 1


@pytest.mark.parametrize(
    ("failure_kind", "expected_code"),
    [
        ("timeout", "RUNTIME_HELP_TIMEOUT"),
        ("nonzero", "RUNTIME_HELP_NONZERO"),
        ("crash", "RUNTIME_HELP_NONZERO"),
        ("missing-token", "RUNTIME_HELP_CONTRACT_MISMATCH"),
    ],
)
def test_proof_runner_fails_timeout_nonzero_crash_or_missing_help_tokens_without_retry(
    tmp_path, failure_kind, expected_code
):
    preparation = _prepare_runtime_for_proof(tmp_path)
    calls = []

    def runner(argv, **kwargs):
        calls.append(tuple(argv))
        if failure_kind == "timeout":
            raise subprocess.TimeoutExpired(argv, 30)
        if failure_kind == "crash":
            raise OSError("synthetic process launch failure")
        if failure_kind == "nonzero":
            return SimpleNamespace(returncode=3, stdout=b"", stderr=b"failed")
        return SimpleNamespace(
            returncode=0,
            stdout=(
                b"provider num-threads zipvoice-encoder zipvoice-decoder "
                b"reference-audio reference-text"
            ),
            stderr=b"",
        )

    process_snapshots = iter([(), ()])
    listener_snapshots = iter([(), ()])
    proof = run_runtime_proof(
        preparation.proof_dir,
        runner=runner,
        process_probe=lambda: next(process_snapshots),
        listener_probe=lambda: next(listener_snapshots),
        event_probe=lambda start_utc, end_utc: (),
        ack_valid_signed_runtime=True,
    )

    assert proof.state == "FAILED"
    assert proof.safe_code == expected_code
    assert proof.exit_code == 30
    assert len(calls) == 1


@pytest.mark.parametrize("dirty_kind", ["process", "listener", "event", "unknown"])
def test_proof_runner_fails_new_process_listener_or_event_1000_postflight(
    tmp_path, dirty_kind
):
    preparation = _prepare_runtime_for_proof(tmp_path)

    def runner(argv, **kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout=(
                b"provider num-threads zipvoice-encoder zipvoice-decoder "
                b"reference-audio reference-text output-filename"
            ),
            stderr=b"",
        )

    process_values = [(), ({"pid": 4242},) if dirty_kind == "process" else ()]
    listener_values = [
        (),
        ({"address": "127.0.0.1", "port": 4242},)
        if dirty_kind == "listener"
        else (),
    ]
    process_call_count = 0
    listener_snapshots = iter(listener_values)

    def process_probe():
        nonlocal process_call_count
        process_call_count += 1
        if dirty_kind == "unknown" and process_call_count == 2:
            raise OSError("synthetic postflight probe failure")
        return process_values[process_call_count - 1]

    proof = run_runtime_proof(
        preparation.proof_dir,
        runner=runner,
        process_probe=process_probe,
        listener_probe=lambda: next(listener_snapshots),
        event_probe=lambda start_utc, end_utc: (
            ({"event_id": 1000},) if dirty_kind == "event" else ()
        ),
        ack_valid_signed_runtime=True,
    )

    assert proof.state == "FAILED"
    assert proof.safe_code == "RUNTIME_POSTFLIGHT_DIRTY"
    assert proof.exit_code == 30


def test_proof_evidence_records_bounded_output_hashes_timing_inventory_and_os_facts(
    tmp_path,
):
    preparation = _prepare_runtime_for_proof(tmp_path)
    help_prefix = (
        b"provider num-threads zipvoice-encoder zipvoice-decoder "
        b"reference-audio reference-text output-filename\n"
    )
    stdout = help_prefix + (b"x" * 70_000)
    stderr = b"warning\n" + (b"y" * 70_000)

    process_snapshots = iter([(), ()])
    listener_snapshots = iter([(), ()])
    proof = run_runtime_proof(
        preparation.proof_dir,
        runner=lambda argv, **kwargs: SimpleNamespace(
            returncode=0, stdout=stdout, stderr=stderr
        ),
        process_probe=lambda: next(process_snapshots),
        listener_probe=lambda: next(listener_snapshots),
        event_probe=lambda start_utc, end_utc: (),
        ack_valid_signed_runtime=True,
    )

    evidence = json.loads(
        (preparation.proof_dir / "runtime-proof.json").read_text(encoding="utf-8")
    )
    assert proof.state == "PASSED"
    assert evidence["schema"] == "easytravel.sherpa-runtime-proof.v1"
    assert evidence["asset"]["sha256"] == preparation.verified_archive.sha256
    assert evidence["archive"]["entry_count"] == preparation.archive_plan.entry_count
    assert evidence["archive"]["plan_sha256"]
    assert evidence["inventory"]["sha256"] == preparation.inventory.sha256
    assert evidence["inventory"]["rows"]
    assert evidence["system"]["os_edition"]
    assert "architecture" in evidence["system"]
    assert "ram_bytes" in evidence["system"]
    assert evidence["created_utc"].endswith("+00:00")
    assert evidence["created_taipei"].endswith("+08:00")
    execution = evidence["execution"]
    assert execution["wall_seconds"] >= 0
    command = execution["commands"][0]
    assert command["duration_seconds"] >= 0
    for record, payload in ((command["stdout"], stdout), (command["stderr"], stderr)):
        assert record["full_bytes"] == len(payload)
        assert record["full_sha256"] == hashlib.sha256(payload).hexdigest()
        assert record["retained_bytes"] == 65_536
        assert record["retained_sha256"] == hashlib.sha256(payload[:65_536]).hexdigest()
        assert base64.b64decode(record["bounded_base64"]) == payload[:65_536]
        assert record["truncated"] is True
    assert evidence["manifest_sha256"] == proof.manifest_sha256


def test_proof_evidence_omits_private_content_and_unnecessary_absolute_paths(
    tmp_path, monkeypatch
):
    preparation = _prepare_runtime_for_proof(tmp_path)
    private_token = "PRIVATE-TOKEN-MUST-NOT-BE-RECORDED"
    private_path = r"C:\Private\SecretBin"
    private_reference_text = "本人私密參考逐字稿"
    monkeypatch.setenv("EASYTRAVEL_PRIVATE_TOKEN", private_token)
    monkeypatch.setenv("PATH", private_path)
    process_snapshots = iter([(), ()])
    listener_snapshots = iter([(), ()])

    proof = run_runtime_proof(
        preparation.proof_dir,
        runner=lambda argv, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=(
                b"provider num-threads zipvoice-encoder zipvoice-decoder "
                b"reference-audio reference-text output-filename"
            ),
            stderr=b"",
        ),
        process_probe=lambda: next(process_snapshots),
        listener_probe=lambda: next(listener_snapshots),
        event_probe=lambda start_utc, end_utc: (),
        ack_valid_signed_runtime=True,
    )

    evidence_path = preparation.proof_dir / "runtime-proof.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    serialized = json.dumps(evidence, ensure_ascii=False)
    assert proof.state == "PASSED"
    assert private_token not in serialized
    assert private_path not in serialized
    assert private_reference_text not in serialized
    assert str(preparation.proof_dir) not in serialized
    assert set(evidence["paths"]) == {
        "archive",
        "runtime_root",
        "runtime_target",
        "staging_root",
    }
    assert set(evidence["execution"]["environment_delta"]) == {"path_prepend"}


def test_verify_runtime_proof_detects_archive_inventory_runtime_output_or_manifest_tampering(
    tmp_path,
):
    def completed(case_name):
        preparation = _prepare_runtime_for_proof(tmp_path / case_name)
        process_snapshots = iter([(), ()])
        listener_snapshots = iter([(), ()])
        run_runtime_proof(
            preparation.proof_dir,
            runner=lambda argv, **kwargs: SimpleNamespace(
                returncode=0,
                stdout=(
                    b"provider num-threads zipvoice-encoder zipvoice-decoder "
                    b"reference-audio reference-text output-filename"
                ),
                stderr=b"",
            ),
            process_probe=lambda: next(process_snapshots),
            listener_probe=lambda: next(listener_snapshots),
            event_probe=lambda start_utc, end_utc: (),
            ack_valid_signed_runtime=True,
        )
        return preparation

    def resign(document):
        unsigned = dict(document)
        unsigned.pop("manifest_sha256", None)
        document["manifest_sha256"] = hashlib.sha256(
            json.dumps(
                unsigned,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()

    pristine = completed("pristine")
    verified = verify_runtime_proof(pristine.proof_dir)
    assert verified.state == "PASSED"

    archive_case = completed("archive")
    archive_case.verified_archive.path.write_bytes(b"tampered archive")

    inventory_case = completed("inventory")
    inventory_path = inventory_case.proof_dir / "runtime-proof.json"
    inventory_evidence = json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory_evidence["inventory"]["rows"][0]["bytes"] += 1
    resign(inventory_evidence)
    inventory_path.write_text(
        json.dumps(inventory_evidence, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )

    runtime_case = completed("runtime")
    mandatory = runtime_case.runtime_root.joinpath(
        *runtime_case.inventory.mandatory_executable_relative_path.split("/")
    )
    mandatory.write_bytes(b"tampered runtime")

    output_case = completed("output")
    output_path = output_case.proof_dir / "runtime-proof.json"
    output_evidence = json.loads(output_path.read_text(encoding="utf-8"))
    output_evidence["execution"]["commands"][0]["stdout"]["bounded_base64"] = (
        base64.b64encode(b"tampered output").decode("ascii")
    )
    resign(output_evidence)
    output_path.write_text(
        json.dumps(output_evidence, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )

    manifest_case = completed("manifest")
    manifest_path = manifest_case.proof_dir / "runtime-proof.json"
    manifest_evidence = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_evidence["state"] = "FAILED"
    manifest_path.write_text(json.dumps(manifest_evidence), encoding="utf-8")

    for preparation in (
        archive_case,
        inventory_case,
        runtime_case,
        output_case,
        manifest_case,
    ):
        with pytest.raises(RuntimeProofError) as failure:
            verify_runtime_proof(preparation.proof_dir)
        assert failure.value.code == "RUNTIME_EVIDENCE_TAMPERED"


def test_proof_runner_refuses_archive_tampering_before_any_probe_or_execution(tmp_path):
    preparation = _prepare_runtime_for_proof(tmp_path)
    preparation.verified_archive.path.write_bytes(b"tampered before execution")
    calls = []

    proof = run_runtime_proof(
        preparation.proof_dir,
        runner=lambda *args, **kwargs: calls.append((args, kwargs)),
        process_probe=lambda: calls.append("process"),
        listener_probe=lambda: calls.append("listener"),
        event_probe=lambda *args: calls.append("event"),
        ack_valid_signed_runtime=True,
    )

    assert proof.state == "FAILED"
    assert proof.safe_code == "RUNTIME_EVIDENCE_TAMPERED"
    assert proof.exit_code == 30
    assert calls == []


def test_cli_stdout_is_bounded_json_and_never_contains_third_party_output(
    tmp_path, capsys
):
    repo_root = tmp_path / "repo"
    per_user_root = tmp_path / "private"
    repo_root.mkdir()
    archive = per_user_root / "downloads" / "runtime.tar.bz2"
    archive.parent.mkdir(parents=True)
    _write_synthetic_archive(
        archive,
        [
            (_directory_member("runtime"), None),
            (_directory_member("runtime/bin"), None),
            _file_member("runtime/bin/sherpa-onnx-offline-tts.exe", b"mandatory"),
            _file_member("runtime/runtime.dll", b"library"),
        ],
    )
    staging = per_user_root / "runtime-staging" / "run"
    runtime = per_user_root / "runtime" / "sherpa-onnx" / "1.13.6"
    proof_dir = per_user_root / "proofs" / "run"
    staging.parent.mkdir()
    runtime.parent.mkdir(parents=True)
    proof_dir.parent.mkdir()
    preparation = prepare_runtime(
        archive,
        spec=_spec_for_archive(archive),
        staging_dir=staging,
        runtime_dir=runtime,
        proof_dir=proof_dir,
        signature_probe=lambda path: _signature(),
    )
    private_output = "PRIVATE THIRD PARTY OUTPUT MUST NOT REACH CLI"
    process_snapshots = iter([(), ()])
    listener_snapshots = iter([(), ()])
    adapters = RuntimeAdapters(
        asset_spec=_spec_for_archive(archive),
        repo_root=repo_root,
        per_user_root=per_user_root,
        signature_probe=lambda path: (_ for _ in ()).throw(
            AssertionError("prove command must not re-run signature probe")
        ),
        runner=lambda argv, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=(
                b"provider num-threads zipvoice-encoder zipvoice-decoder "
                b"reference-audio reference-text output-filename\n"
                + private_output.encode("utf-8")
            ),
            stderr=b"",
        ),
        process_probe=lambda: next(process_snapshots),
        listener_probe=lambda: next(listener_snapshots),
        event_probe=lambda start_utc, end_utc: (),
    )

    exit_code = runtime_main(
        [
            "prove-runtime",
            "--proof-dir",
            str(preparation.proof_dir),
            "--runtime-dir",
            str(preparation.runtime_root),
            "--ack-valid-signed-runtime",
        ],
        adapters=adapters,
    )

    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert len(captured.out.encode("utf-8")) < 2_048
    assert private_output not in captured.out
    assert summary["state"] == "PASSED"
    assert summary["safe_code"] is None
    assert summary["outer_sha256"] == preparation.verified_archive.sha256
    assert summary["load_inventory_sha256"] == preparation.inventory.sha256
    assert summary["executable_sha256"] == (
        preparation.inventory.mandatory_executable_sha256
    )
    assert set(summary) == {
        "evidence_id",
        "executable_sha256",
        "load_inventory_sha256",
        "next_step",
        "outer_sha256",
        "safe_code",
        "state",
    }
