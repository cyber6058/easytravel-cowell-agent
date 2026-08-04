from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

import pytest

from cowell_cli.application.passenger_import import (
    OFFICIAL_HEADERS,
    SHEET_NS,
    build_cowell_passenger_workbook,
    build_cowell_roster_workbook,
    validate_cowell_roster_template,
)
from cowell_cli.domain.passport import PassportTraveler
from cowell_cli.domain.rooming import RoomAssignment, RoomMember, RoomingList
from cowell_cli.errors import ValidationError


def _template(*, creator: str = "Cowell") -> bytes:
    shared = "".join(f"<si><t>{value}</t></si>" for value in OFFICIAL_HEADERS)
    header = "".join(
        f'<c r="{chr(65 + index)}1" t="s"><v>{index}</v></c>'
        for index in range(len(OFFICIAL_HEADERS))
    )
    example = "".join(
        f'<c r="{column}2" t="inlineStr"><is><t>EXAMPLE</t></is></c>'
        for column in ("D", "E", "G", "H")
    )
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr(
            "docProps/core.xml",
            f'<cp:coreProperties xmlns:cp="x" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:creator>{creator}</dc:creator></cp:coreProperties>',
        )
        archive.writestr(
            "xl/sharedStrings.xml",
            f'<sst xmlns="{SHEET_NS}">{shared}</sst>',
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            f'<worksheet xmlns="{SHEET_NS}"><dimension ref="A1:S2"/><sheetData><row r="1">{header}</row><row r="2">{example}</row></sheetData></worksheet>',
        )
    return output.getvalue()


def _rooming() -> RoomingList:
    return RoomingList(
        source_path=Path("source.docx"),
        source_format="docx",
        group_code="TEST",
        rooms=(
            RoomAssignment(
                room_id="room-1",
                source_room_label=None,
                occupancy=2,
                sleeping_occupancy=2,
                room_type="double_or_twin",
                bed_preference=None,
                members=(
                    RoomMember("1", "王小明", "WANG/HSIAO MING", None),
                    RoomMember("2", "歐陽美華", "OUYANG/MEI HUA", None),
                ),
            ),
        ),
    )


def test_builds_name_only_workbook_and_removes_example_rows():
    result = build_cowell_passenger_workbook(_template(), _rooming())

    assert result.passenger_count == 2
    assert result.missing_gender_count == 2
    assert len(result.sha256) == 64
    with ZipFile(BytesIO(result.content)) as archive:
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    rows = sheet.findall(f".//{{{SHEET_NS}}}row")
    assert [row.get("r") for row in rows] == ["1", "2", "3"]
    text = "".join(
        node.text or "" for row in rows[1:] for node in row.iter()
    )
    assert "EXAMPLE" not in text
    assert "WANG" in text
    assert "歐陽" in text


def test_rejects_non_cowell_template_author():
    with pytest.raises(ValidationError):
        build_cowell_passenger_workbook(_template(creator="Other"), _rooming())


def test_validates_official_template_without_building_a_roster():
    validate_cowell_roster_template(_template())

    with pytest.raises(ValidationError, match="author is not Cowell"):
        validate_cowell_roster_template(_template(creator="Other"))


def test_rejects_english_name_without_slash():
    rooming = _rooming()
    bad = RoomingList(
        source_path=rooming.source_path,
        source_format=rooming.source_format,
        group_code=rooming.group_code,
        rooms=(
            RoomAssignment(
                room_id="room-1",
                source_room_label=None,
                occupancy=1,
                sleeping_occupancy=1,
                room_type="single",
                bed_preference=None,
                members=(RoomMember("1", "王小明", "WANG HSIAO MING", None),),
            ),
        ),
    )
    with pytest.raises(ValidationError):
        build_cowell_passenger_workbook(_template(), bad)


def test_builds_full_nineteen_column_passport_roster():
    traveler = PassportTraveler(
        record_id="P001-01",
        image_name="P001-01.jpg",
        passport_no="T00000000",
        id_no="X900000000",
        english_surname="CHEN",
        english_given="TEST USER",
        sex="M",
        chinese_surname="陳",
        chinese_given="測試",
        birth_date="1990/01/01",
        issue_date="2020/01/01",
        expiry_date="2030/01/01",
        birth_place="台灣",
        nationality="台灣",
    )

    result = build_cowell_roster_workbook(_template(), (traveler,))

    assert result.passenger_count == 1
    assert result.missing_gender_count == 0
    assert result.populated_columns == OFFICIAL_HEADERS[:13]
    with ZipFile(BytesIO(result.content)) as archive:
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    values = "".join(node.text or "" for node in sheet.iter())
    assert "T00000000" in values
    assert "X900000000" in values
    assert "2030/01/01" in values
