from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET

from ..domain.rooming import RoomingList
from ..domain.passport import PassportTraveler
from ..errors import ValidationError


SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
CORE_NS = "http://purl.org/dc/elements/1.1/"
OFFICIAL_HEADERS = (
    "圖像名稱",
    "護照號碼",
    "身分證號碼",
    "英文姓",
    "英文名",
    "性別",
    "中文姓",
    "中文名",
    "出生日期",
    "發照日期",
    "截止日期",
    "出生地",
    "國籍",
    "行動電話",
    "E-Mail",
    "台胞簽證號碼",
    "簽發次數",
    "效期起日",
    "效期迄日",
)
COLUMN_LETTERS = tuple(chr(ord("A") + index) for index in range(19))


@dataclass(frozen=True, slots=True)
class PassengerImportWorkbook:
    content: bytes
    sha256: str
    passenger_count: int
    populated_columns: tuple[str, ...]
    missing_gender_count: int


def build_cowell_passenger_workbook(
    template_content: bytes,
    rooming: RoomingList,
) -> PassengerImportWorkbook:
    passengers = [member for room in rooming.rooms for member in room.members]
    if not passengers:
        raise ValidationError("rooming list has no passengers")
    if any(not member.chinese_name or not member.english_name for member in passengers):
        raise ValidationError("every passenger needs Chinese and English names")
    sequences = [member.sequence for member in passengers]
    if any(not sequence for sequence in sequences) or len(set(sequences)) != len(
        sequences
    ):
        raise ValidationError("passenger sequences must be present and unique")

    rows: list[dict[str, str]] = []
    for passenger in passengers:
        english_surname, english_given = _split_english(passenger.english_name or "")
        chinese_surname, chinese_given = _split_chinese(passenger.chinese_name or "")
        rows.append(
            {
                "D": english_surname,
                "E": english_given,
                "G": chinese_surname,
                "H": chinese_given,
            }
        )
    return _build_workbook(
        template_content,
        tuple(rows),
        populated_columns=("英文姓", "英文名", "中文姓", "中文名"),
        missing_gender_count=len(passengers),
    )


def build_cowell_roster_workbook(
    template_content: bytes,
    travelers: Sequence[PassportTraveler],
) -> PassengerImportWorkbook:
    if not travelers:
        raise ValidationError("passport roster has no passengers")
    rows = tuple(
        {
            column: value
            for column, value in zip(COLUMN_LETTERS, _traveler_values(traveler), strict=True)
            if value
        }
        for traveler in travelers
    )
    populated = tuple(
        header
        for index, header in enumerate(OFFICIAL_HEADERS)
        if any(COLUMN_LETTERS[index] in row for row in rows)
    )
    return _build_workbook(
        template_content,
        rows,
        populated_columns=populated,
        missing_gender_count=sum(not traveler.sex for traveler in travelers),
    )


def validate_cowell_roster_template(template_content: bytes) -> None:
    """Validate the official workbook without retaining or logging its contents."""
    try:
        source = ZipFile(BytesIO(template_content))
    except Exception as exc:
        raise ValidationError("Cowell passenger template must be a valid XLSX") from exc
    with source:
        _validate_template_archive(source)


def _build_workbook(
    template_content: bytes,
    rows_to_write: tuple[dict[str, str], ...],
    *,
    populated_columns: tuple[str, ...],
    missing_gender_count: int,
) -> PassengerImportWorkbook:
    try:
        source = ZipFile(BytesIO(template_content))
    except Exception as exc:
        raise ValidationError("Cowell passenger template must be a valid XLSX") from exc

    with source:
        _validate_template_archive(source)
        sheet = ET.fromstring(source.read("xl/worksheets/sheet1.xml"))
        sheet_data = sheet.find(f"{{{SHEET_NS}}}sheetData")
        if sheet_data is None:
            raise ValidationError("Cowell passenger template has no sheet data")
        rows = list(sheet_data.findall(f"{{{SHEET_NS}}}row"))
        style_by_column = _style_map(rows[1] if len(rows) > 1 else None)
        for row in rows[1:]:
            sheet_data.remove(row)

        for index, values in enumerate(rows_to_write, start=2):
            row = ET.SubElement(
                sheet_data,
                f"{{{SHEET_NS}}}row",
                {"r": str(index), "spans": "1:19"},
            )
            for column, value in values.items():
                _append_inline_cell(row, column, index, value, style_by_column)

        dimension = sheet.find(f"{{{SHEET_NS}}}dimension")
        if dimension is not None:
            dimension.set("ref", f"A1:S{len(rows_to_write) + 1}")
        ET.register_namespace("", SHEET_NS)
        sheet_bytes = ET.tostring(sheet, encoding="utf-8", xml_declaration=True)

        output = BytesIO()
        with ZipFile(output, "w", ZIP_DEFLATED) as target:
            for info in source.infolist():
                content = (
                    sheet_bytes
                    if info.filename == "xl/worksheets/sheet1.xml"
                    else source.read(info.filename)
                )
                target.writestr(info, content)

    content = output.getvalue()
    return PassengerImportWorkbook(
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
        passenger_count=len(rows_to_write),
        populated_columns=populated_columns,
        missing_gender_count=missing_gender_count,
    )


def _validate_template_archive(source: ZipFile) -> None:
    required = {"docProps/core.xml", "xl/worksheets/sheet1.xml"}
    if not required.issubset(source.namelist()):
        raise ValidationError("Cowell passenger template structure changed")
    core = ET.fromstring(source.read("docProps/core.xml"))
    creator = core.find(f"{{{CORE_NS}}}creator")
    if creator is None or (creator.text or "").strip().lower() != "cowell":
        raise ValidationError("Cowell passenger template author is not Cowell")
    sheet = ET.fromstring(source.read("xl/worksheets/sheet1.xml"))
    _assert_headers(sheet, source)


def _traveler_values(traveler: PassportTraveler) -> tuple[str, ...]:
    return (
        traveler.image_name,
        traveler.passport_no,
        traveler.id_no,
        traveler.english_surname,
        traveler.english_given,
        traveler.sex,
        traveler.chinese_surname,
        traveler.chinese_given,
        traveler.birth_date,
        traveler.issue_date,
        traveler.expiry_date,
        traveler.birth_place,
        traveler.nationality,
        traveler.mobile,
        traveler.email,
        traveler.taiwan_compatriot_permit_no,
        traveler.issue_count,
        traveler.permit_start_date,
        traveler.permit_end_date,
    )


def _assert_headers(sheet: ET.Element, source: ZipFile) -> None:
    shared: list[str] = []
    if "xl/sharedStrings.xml" in source.namelist():
        root = ET.fromstring(source.read("xl/sharedStrings.xml"))
        for item in root.findall(f"{{{SHEET_NS}}}si"):
            shared.append(
                "".join(node.text or "" for node in item.iter(f"{{{SHEET_NS}}}t"))
            )
    sheet_data = sheet.find(f"{{{SHEET_NS}}}sheetData")
    first_row = (
        sheet_data.find(f"{{{SHEET_NS}}}row") if sheet_data is not None else None
    )
    if first_row is None:
        raise ValidationError("Cowell passenger template header row is missing")
    values: list[str] = []
    for cell in first_row.findall(f"{{{SHEET_NS}}}c"):
        value = cell.find(f"{{{SHEET_NS}}}v")
        if value is None or value.text is None:
            values.append("")
        elif cell.get("t") == "s":
            values.append(shared[int(value.text)])
        else:
            values.append(value.text)
    if tuple(values) != OFFICIAL_HEADERS:
        raise ValidationError("Cowell passenger template headers changed")


def _style_map(row: ET.Element | None) -> dict[str, str]:
    if row is None:
        return {}
    return {
        "".join(character for character in (cell.get("r") or "") if character.isalpha()): cell.get("s") or ""
        for cell in row.findall(f"{{{SHEET_NS}}}c")
    }


def _append_inline_cell(
    row: ET.Element,
    column: str,
    row_number: int,
    value: str,
    styles: dict[str, str],
) -> None:
    attributes = {"r": f"{column}{row_number}", "t": "inlineStr"}
    if styles.get(column):
        attributes["s"] = styles[column]
    cell = ET.SubElement(row, f"{{{SHEET_NS}}}c", attributes)
    inline = ET.SubElement(cell, f"{{{SHEET_NS}}}is")
    text = ET.SubElement(inline, f"{{{SHEET_NS}}}t")
    text.text = value


def _split_english(value: str) -> tuple[str, str]:
    parts = [part.strip() for part in value.split("/")]
    if len(parts) != 2 or not all(parts):
        raise ValidationError("English passenger names must use SURNAME/GIVEN format")
    return parts[0].upper(), parts[1].upper()


def _split_chinese(value: str) -> tuple[str, str]:
    normalized = value.strip()
    if len(normalized) < 2:
        raise ValidationError("Chinese passenger names must contain surname and given name")
    compound = {
        "歐陽",
        "司馬",
        "上官",
        "諸葛",
        "夏侯",
        "東方",
        "皇甫",
        "尉遲",
        "公孫",
        "慕容",
        "司徒",
        "令狐",
    }
    surname_length = 2 if normalized[:2] in compound else 1
    return normalized[:surname_length], normalized[surname_length:]
