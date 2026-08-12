import os
import sys
from pathlib import Path

import pytest

from travel_briefing.adapters.windows_word import WindowsWordAdapter
from travel_briefing.models import (
    BriefingDraft,
    DraftStatus,
    Flight,
    ItineraryDay,
    Product,
)
from travel_briefing.op_values import build_missing_op_fields
from travel_briefing.word_list import (
    build_list_word,
    inspect_list_template,
    probe_word_capability,
)
from travel_briefing.word_qa import render_list_word_for_qa


_TEMPLATE = os.environ.get("EASYTRAVEL_LIST_TEMPLATE_PATH", "")
_FINGERPRINT = os.environ.get("EASYTRAVEL_LIST_TEMPLATE_FINGERPRINT", "")
_PDFTOPPM = os.environ.get("EASYTRAVEL_PDFTOPPM_PATH", "")
_OPTED_IN = (
    sys.platform == "win32"
    and os.environ.get("RUN_BRIEFING_WORD_INTEGRATION") == "1"
    and bool(_TEMPLATE)
    and bool(_FINGERPRINT)
    and bool(_PDFTOPPM)
)

pytestmark = pytest.mark.skipif(
    not _OPTED_IN,
    reason=(
        "set RUN_BRIEFING_WORD_INTEGRATION=1 plus explicit private LIST "
        "template, approved fingerprint, and pdftoppm paths"
    ),
)


def test_private_list_template_patches_and_renders_one_page(tmp_path):
    project_root = Path(__file__).parents[3]
    patch_adapter = WindowsWordAdapter(
        script_path=project_root
        / "scripts"
        / "briefing"
        / "patch_list_template.ps1"
    )
    render_adapter = WindowsWordAdapter(
        script_path=project_root
        / "scripts"
        / "briefing"
        / "render_list_template.ps1"
    )
    capability = probe_word_capability(patch_adapter)
    assert capability.available is True
    template = inspect_list_template(
        Path(_TEMPLATE),
        adapter=patch_adapter,
        expected_layout_fingerprint=_FINGERPRINT,
    )
    source = synthetic_draft(template.day_count)
    docx = tmp_path / "DRAFT_SYN-LIST-260901_說明會資料.docx"
    built = build_list_word(
        source,
        template_path=Path(_TEMPLATE),
        output_docx=docx,
        expected_layout_fingerprint=_FINGERPRINT,
        adapter=patch_adapter,
    )

    qa = render_list_word_for_qa(
        built.docx_path,
        output_pdf=tmp_path / "qa.pdf",
        output_png=tmp_path / "qa.png",
        required_text=("SYN-LIST-260901", "JX820", "JX821"),
        adapter=render_adapter,
        pdftoppm_path=Path(_PDFTOPPM),
    )

    assert built.byte_count > 0
    assert qa.pdf_inspection.page_count == 1
    assert qa.pdf_inspection.image_count >= 1
    assert qa.png_path.stat().st_size > 0


def synthetic_draft(day_count: int) -> BriefingDraft:
    days = tuple(
        ItineraryDay(
            number=number,
            date=f"2026-09-{number:02d}",
            city="大阪",
            attractions=(f"合成景點{number}A", f"合成景點{number}B"),
            meals=("早餐", "午餐", "晚餐"),
            hotel=f"合成飯店{number}",
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
