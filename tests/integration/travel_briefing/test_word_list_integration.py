import json
import os
import sys
from pathlib import Path

import pytest

from travel_briefing.config import parse_config
from travel_briefing.errors import BriefingCliError
from travel_briefing.models import (
    BriefingDraft,
    DraftStatus,
    Flight,
    ItineraryDay,
    Product,
)
from travel_briefing.op_values import build_missing_op_fields
from travel_briefing.workflow import LocalRenderBackend


_TEMPLATE = os.environ.get("EASYTRAVEL_LIST_TEMPLATE_PATH", "")
_MANIFEST = os.environ.get(
    "EASYTRAVEL_LIST_CALIBRATION_MANIFEST_PATH", ""
)
_PDFTOPPM = os.environ.get("EASYTRAVEL_PDFTOPPM_PATH", "")
_OPTED_IN = (
    sys.platform == "win32"
    and os.environ.get("RUN_BRIEFING_WORD_INTEGRATION") == "1"
    and bool(_TEMPLATE)
    and bool(_MANIFEST)
    and bool(_PDFTOPPM)
)

pytestmark = pytest.mark.skipif(
    not _OPTED_IN,
    reason=(
        "set RUN_BRIEFING_WORD_INTEGRATION=1 plus explicit private LIST "
        "master, calibration manifest, and pdftoppm paths"
    ),
)


@pytest.mark.parametrize("day_count", [4, 5, 6, 7, 8, 12])
def test_calibrated_master_renders_gate_v_day_counts(tmp_path, day_count):
    project_root = Path(__file__).parents[3]
    config = parse_config(
        {
            "output": {"root": str(tmp_path)},
            "template": {
                "master_path": _TEMPLATE,
                "calibration_manifest": _MANIFEST,
            },
            "tools": {
                "ffmpeg": None,
                "pdftoppm": _PDFTOPPM,
            },
        }
    )
    backend = LocalRenderBackend.from_config(
        config,
        scripts_root=project_root / "scripts" / "briefing",
    )
    source = synthetic_draft(day_count)
    output = tmp_path / f"day-{day_count:03d}"

    try:
        evidence = backend.render_word(
            source,
            output_docx=output / "LIST.docx",
            output_qa_pdf=output / "LIST-qa.pdf",
            output_qa_directory=output / "pages",
            output_qa_index=output / "pages" / "index.json",
        )
    except BriefingCliError as error:
        pytest.fail(
            json.dumps(
                {
                    "code": error.code,
                    "details": error.details,
                },
                ensure_ascii=True,
                sort_keys=True,
            ),
            pytrace=False,
        )

    index = json.loads(
        (output / "pages" / "index.json").read_text(encoding="utf-8")
    )
    assert (output / "LIST.docx").stat().st_size > 0
    assert (output / "LIST-qa.pdf").stat().st_size > 0
    assert evidence.page_count == index["page_count"]
    if day_count < 8:
        assert evidence.page_count == 1
    else:
        assert evidence.page_count >= 2
    assert evidence.qr_image_count >= 1
    assert len(evidence.page_sha256s) == evidence.page_count
    assert len(index["day_page_map"]) == day_count
    assert [item["day_number"] for item in index["day_page_map"]] == list(
        range(1, day_count + 1)
    )


def synthetic_draft(day_count: int) -> BriefingDraft:
    long_continuation_fixture = day_count >= 8
    days = tuple(
        ItineraryDay(
            number=number,
            date=f"2026-09-{number:02d}",
            city="大阪",
            attractions=(
                (
                    f"合成大阪城與庭園深度參觀行程{number}A"
                    if long_continuation_fixture
                    else f"合成景點{number}A"
                ),
                (
                    f"合成歷史街區文化散策與展望台{number}B"
                    if long_continuation_fixture
                    else f"合成景點{number}B"
                ),
            ),
            meals=("早餐", "午餐", "晚餐"),
            hotel=(
                f"合成大阪灣景觀住宿飯店{number}"
                if long_continuation_fixture
                else f"合成飯店{number}"
            ),
            source_ids=("synthetic",),
        )
        for number in range(1, day_count + 1)
    )
    return BriefingDraft.create(
        status=DraftStatus.DRAFT_READY,
        generated_at="2026-08-12T15:00:00+08:00",
        product=Product(
            code="SYN-LIST-260901",
            name=f"合成大阪{day_count}日",
            region="大阪",
            day_count=day_count,
            departure_date="2026-09-01",
            return_date=f"2026-09-{day_count:02d}",
            source_ids=("synthetic",),
        ),
        flights=(
            Flight(
                date="2026-09-01",
                airline="星宇航空",
                number="JX820",
                origin="TPE",
                destination="KIX",
                departure_time="08:30",
                arrival_time="12:00",
                source_ids=("synthetic",),
            ),
            Flight(
                date=f"2026-09-{day_count:02d}",
                airline="星宇航空",
                number="JX821",
                origin="KIX",
                destination="TPE",
                departure_time="13:00",
                arrival_time="15:25",
                source_ids=("synthetic",),
            ),
        ),
        days=days,
        op_fields=build_missing_op_fields(),
    )
