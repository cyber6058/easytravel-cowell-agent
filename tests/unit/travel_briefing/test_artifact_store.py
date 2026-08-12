from pathlib import Path

import pytest

from travel_briefing.artifact_store import (
    artifact_record,
    create_run_directory,
    load_run_manifest,
    publish_text,
    verify_artifacts,
    write_manifest,
)
from travel_briefing.models import Artifact, BriefingDraft, DraftStatus, Product
from travel_briefing.serialization import loads_draft


def test_run_directory_is_new_and_stays_inside_the_configured_output_root(tmp_path):
    output_root = tmp_path / "briefings"

    run = create_run_directory(
        output_root,
        product_code="SYN-OSA-260901",
        timestamp="20260812T153000+0800",
    )

    assert run == (
        output_root / "SYN-OSA-260901" / "20260812T153000+0800"
    ).resolve()
    assert run.is_dir()
    with pytest.raises(FileExistsError, match="already exists"):
        create_run_directory(
            output_root,
            product_code="SYN-OSA-260901",
            timestamp="20260812T153000+0800",
        )


@pytest.mark.parametrize(
    "product_code",
    ("../escape", r"..\escape", "A/B", r"A\B", ".", ""),
)
def test_run_directory_rejects_product_codes_that_can_escape_the_output_root(
    tmp_path,
    product_code,
):
    output_root = tmp_path / "briefings"

    with pytest.raises(ValueError, match="product code"):
        create_run_directory(
            output_root,
            product_code=product_code,
            timestamp="20260812T153000+0800",
        )

    assert not output_root.exists()


def test_manifest_records_completed_blocked_and_missing_artifacts(tmp_path):
    run = create_run_directory(
        tmp_path / "briefings",
        product_code="SYN-OSA-260901",
        timestamp="20260812T153000+0800",
    )
    review = publish_text(run, "review.md", "# Synthetic review\n")
    draft = BriefingDraft.create(
        status=DraftStatus.DRAFT_READY,
        generated_at="2026-08-12T15:30:00+08:00",
        product=Product(
            code="SYN-OSA-260901",
            name="Synthetic Osaka",
            region="Osaka",
            day_count=5,
            departure_date="2026-09-01",
            return_date="2026-09-05",
        ),
        artifacts=(
            artifact_record(
                run,
                kind="review",
                expected_name="review.md",
                status="completed",
                generator_version="travel-briefing/0.1.0",
            ),
            artifact_record(
                run,
                kind="word",
                expected_name="DRAFT_SYN-OSA-260901_briefing.docx",
                status="blocked",
                generator_version="list-word/1",
            ),
            artifact_record(
                run,
                kind="mp3",
                expected_name="DRAFT_SYN-OSA-260901_audio.mp3",
                status="missing",
                generator_version="ffmpeg/unknown",
            ),
        ),
    )

    manifest = write_manifest(run, draft)

    assert review.read_text(encoding="utf-8") == "# Synthetic review\n"
    digest = (run / "manifest.sha256").read_text(encoding="ascii").strip()
    assert len(digest) == 64
    restored = loads_draft(manifest.read_text(encoding="utf-8"))
    assert [artifact.status for artifact in restored.artifacts] == [
        "completed",
        "blocked",
        "missing",
    ]
    assert restored.artifacts[0].actual_path == "review.md"
    assert len(restored.artifacts[0].sha256) == 64
    assert restored.artifacts[1].actual_path == ""
    assert restored.artifacts[1].sha256 == ""
    assert not Path(restored.artifacts[0].actual_path).is_absolute()


def test_store_refuses_path_escape_and_never_overwrites(tmp_path):
    run = create_run_directory(
        tmp_path / "briefings",
        product_code="SYN-OSA-260901",
        timestamp="20260812T153000+0800",
    )

    with pytest.raises(ValueError, match="artifact name"):
        publish_text(run, "../outside.txt", "blocked")

    published = publish_text(run, "review.md", "first\n")
    with pytest.raises(FileExistsError):
        publish_text(run, "review.md", "second\n")

    assert published.read_text(encoding="utf-8") == "first\n"
    assert not (tmp_path / "briefings" / "outside.txt").exists()


def test_manifest_load_and_artifact_verification_are_scoped_and_hash_bound(tmp_path):
    output_root = tmp_path / "briefings"
    run = create_run_directory(
        output_root,
        product_code="SYN-OSA-260901",
        timestamp="20260812T153000+0800",
    )
    publish_text(run, "review.md", "verified content\n")
    draft = BriefingDraft.create(
        status=DraftStatus.DRAFT_READY,
        generated_at="2026-08-12T15:30:00+08:00",
        product=Product(
            code="SYN-OSA-260901",
            name="Synthetic Osaka",
            region="Osaka",
            day_count=5,
            departure_date="2026-09-01",
            return_date="2026-09-05",
        ),
        artifacts=(
            artifact_record(
                run,
                kind="review",
                expected_name="review.md",
                status="completed",
                generator_version="travel-briefing/0.1.0",
            ),
        ),
    )
    manifest = write_manifest(run, draft)

    loaded_run, loaded = load_run_manifest(output_root, manifest)

    assert loaded_run == run
    assert loaded == draft
    verify_artifacts(loaded_run, loaded.artifacts)

    original_manifest = manifest.read_text(encoding="utf-8")
    manifest.write_text(original_manifest + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="manifest hash"):
        load_run_manifest(output_root, manifest)
    manifest.write_text(original_manifest, encoding="utf-8")

    (run / "review.md").write_text("changed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        verify_artifacts(loaded_run, loaded.artifacts)

    outside = tmp_path / "outside" / "manifest.json"
    outside.parent.mkdir()
    outside.write_text(manifest.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(ValueError, match="output root"):
        load_run_manifest(output_root, outside)


def test_blocked_artifact_may_preserve_an_unaccepted_safe_file(tmp_path):
    run = create_run_directory(
        tmp_path / "briefings",
        product_code="SYN-OSA-260901",
        timestamp="20260812T153000+0800",
    )
    publish_text(run, "DRAFT_SYN-OSA-260901.txt", "safe partial output\n")

    artifact = artifact_record(
        run,
        kind="transcript",
        expected_name="DRAFT_SYN-OSA-260901.txt",
        status="blocked",
        generator_version="synthetic/1",
    )

    assert artifact.actual_path == "DRAFT_SYN-OSA-260901.txt"
    assert len(artifact.sha256) == 64
    verify_artifacts(run, (artifact,))


def test_verification_rejects_unsafe_expected_paths_even_when_artifact_is_missing(
    tmp_path,
):
    run = create_run_directory(
        tmp_path / "briefings",
        product_code="SYN-OSA-260901",
        timestamp="20260812T153000+0800",
    )
    unsafe = Artifact(
        kind="word",
        expected_path="../outside.docx",
        actual_path="",
        sha256="",
        status="missing",
        generator_version="synthetic/1",
    )

    with pytest.raises(ValueError, match="artifact name"):
        verify_artifacts(run, (unsafe,))


def test_verification_rejects_status_and_actual_path_contradictions(tmp_path):
    run = create_run_directory(
        tmp_path / "briefings",
        product_code="SYN-OSA-260901",
        timestamp="20260812T153000+0800",
    )
    publish_text(run, "unexpected.docx", "synthetic\n")
    contradictory = Artifact(
        kind="word",
        expected_path="unexpected.docx",
        actual_path="unexpected.docx",
        sha256="0" * 64,
        status="missing",
        generator_version="synthetic/1",
    )

    with pytest.raises(ValueError, match="Missing briefing artifact"):
        verify_artifacts(run, (contradictory,))


def test_manifest_load_requires_exact_run_shape_and_matching_product_code(tmp_path):
    output_root = tmp_path / "briefings"
    run = create_run_directory(
        output_root,
        product_code="SYN-OSA-260901",
        timestamp="20260812T153000+0800",
    )
    draft = BriefingDraft.create(
        status=DraftStatus.DRAFT_READY,
        generated_at="2026-08-12T15:30:00+08:00",
        product=Product(
            code="SYN-OTHER-260901",
            name="Synthetic mismatch",
            region="Osaka",
            day_count=5,
            departure_date="2026-09-01",
            return_date="2026-09-05",
        ),
    )
    manifest = write_manifest(run, draft)

    with pytest.raises(ValueError, match="product code"):
        load_run_manifest(output_root, manifest)
    with pytest.raises(ValueError, match="run directory"):
        load_run_manifest(tmp_path, manifest)


def test_artifact_verification_rejects_duplicate_kinds(tmp_path):
    run = create_run_directory(
        tmp_path / "briefings",
        product_code="SYN-OSA-260901",
        timestamp="20260812T153000+0800",
    )
    first = artifact_record(
        run,
        kind="word",
        expected_name="first.docx",
        status="missing",
        generator_version="synthetic/1",
    )
    second = artifact_record(
        run,
        kind="word",
        expected_name="second.docx",
        status="missing",
        generator_version="synthetic/1",
    )

    with pytest.raises(ValueError, match="duplicate kind"):
        verify_artifacts(run, (first, second))


def test_blocked_artifact_actual_path_must_still_match_expected_path(tmp_path):
    run = create_run_directory(
        tmp_path / "briefings",
        product_code="SYN-OSA-260901",
        timestamp="20260812T153000+0800",
    )
    published = publish_text(run, "actual.docx", "synthetic\n")
    recorded = artifact_record(
        run,
        kind="word",
        expected_name=published.name,
        status="blocked",
        generator_version="synthetic/1",
    )
    contradictory = Artifact(
        kind=recorded.kind,
        expected_path="expected.docx",
        actual_path=recorded.actual_path,
        sha256=recorded.sha256,
        status=recorded.status,
        generator_version=recorded.generator_version,
    )

    with pytest.raises(ValueError, match="expected path"):
        verify_artifacts(run, (contradictory,))
