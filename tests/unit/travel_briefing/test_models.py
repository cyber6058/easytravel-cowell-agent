import json
from dataclasses import replace

import pytest

from travel_briefing.models import (
    Artifact,
    BriefingDraft,
    Conflict,
    DraftStatus,
    DraftWarning,
    Flight,
    ItineraryDay,
    Notice,
    OpField,
    Product,
    SourceEvidence,
    WeatherForecast,
)
from travel_briefing.serialization import dumps_draft, loads_draft


def sample_draft() -> BriefingDraft:
    return BriefingDraft.create(
        status=DraftStatus.DRAFT_READY,
        generated_at="2026-08-09T09:30:00+08:00",
        product=Product(
            code="SYN-OSA-5D",
            name="合成大阪五日",
            region="大阪",
            day_count=5,
            departure_date="2026-09-01",
            return_date="2026-09-05",
            source_ids=("pdf-1",),
        ),
        sources=(
            SourceEvidence(
                source_id="pdf-1",
                kind="pdf",
                location="input.pdf",
                sha256="a" * 64,
                retrieved_at="2026-08-09T09:20:00+08:00",
                parser_version="pdf-itinerary/1",
            ),
        ),
        flights=(
            Flight(
                date="2026-09-01",
                airline="星宇航空",
                number="JX820",
                origin="TPE",
                destination="KIX",
                departure_time="08:30",
                arrival_time="12:10",
                source_ids=("pdf-1",),
            ),
        ),
        days=(
            ItineraryDay(
                number=1,
                date="2026-09-01",
                city="大阪",
                attractions=("大阪城",),
                meals=("機上餐", "敬請自理", "飯店內"),
                hotel="合成飯店",
                source_ids=("pdf-1",),
            ),
        ),
        notices=(
            Notice(
                category="tip",
                text="合成測試小費說明",
                source_ids=("pdf-1",),
            ),
        ),
        op_fields=(
            OpField(
                name="meeting_time",
                value="待 OP 確認",
                source="",
                confirmed=False,
            ),
        ),
        weather=(
            WeatherForecast(
                date="2026-09-01",
                display_city="大阪",
                forecast_area="大阪府",
                condition="晴",
                high_c=30,
                low_c=24,
                precipitation_percent=20,
                issued_at="2026-08-31T17:00:00+09:00",
                retrieved_at="2026-08-31T18:00:00+09:00",
                source_url="https://www.jma.go.jp/example",
                available=True,
            ),
        ),
        conflicts=(
            Conflict(
                field="hotel",
                source_a="pdf-1",
                value_a="合成飯店",
                source_b="url-1",
                value_b="另一合成飯店",
                severity="warning",
                decision="use_pdf",
                decided_by="OP",
            ),
        ),
        warnings=(
            DraftWarning(
                code="SYNTHETIC_WARNING",
                message="僅供合成測試",
                source_ids=("pdf-1",),
            ),
        ),
        artifacts=(
            Artifact(
                kind="manifest",
                expected_path="manifest.json",
                actual_path="manifest.json",
                sha256="b" * 64,
                status="completed",
                generator_version="travel-briefing/0.1",
            ),
        ),
        narration_script_sha256="c" * 64,
    )


def test_briefing_draft_json_round_trip_preserves_the_public_contract():
    draft = sample_draft()

    encoded = dumps_draft(draft)
    restored = loads_draft(encoded)

    envelope = json.loads(encoded)
    assert envelope["schema_version"] == 1
    assert envelope["type"] == "briefing_draft"
    assert envelope["data"]["status"] == "DRAFT_READY"
    assert restored == draft


def test_briefing_draft_rejects_an_unknown_status():
    with pytest.raises(ValueError):
        replace(sample_draft(), status="READY")


def test_draft_id_changes_with_source_weather_script_or_generation_time():
    draft = sample_draft()
    source_changed = replace(
        draft,
        sources=(replace(draft.sources[0], sha256="d" * 64),),
    ).with_recomputed_id()
    weather_changed = replace(
        draft,
        weather=(replace(draft.weather[0], condition="雨"),),
    ).with_recomputed_id()
    script_changed = replace(
        draft,
        narration_script_sha256="e" * 64,
    ).with_recomputed_id()
    generation_changed = replace(
        draft,
        generated_at="2026-08-09T09:31:00+08:00",
    ).with_recomputed_id()

    assert len(
        {
            draft.draft_id,
            source_changed.draft_id,
            weather_changed.draft_id,
            script_changed.draft_id,
            generation_changed.draft_id,
        }
    ) == 5


def test_loading_a_manifest_rejects_content_changed_after_id_generation():
    envelope = json.loads(dumps_draft(sample_draft()))
    envelope["data"]["weather"][0]["condition"] = "雨"

    with pytest.raises(ValueError, match="draft ID"):
        loads_draft(json.dumps(envelope, ensure_ascii=False))
