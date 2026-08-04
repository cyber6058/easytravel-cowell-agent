from pathlib import Path

from cowell_cli.application.rooms import parse_rooming_document
from cowell_cli.infrastructure.rooming_ooxml import OoxmlCell, OoxmlDocument, OoxmlTable


def cell(text="", merge=None):
    return OoxmlCell(text=text, vertical_merge=merge)


def test_parses_vertical_merge_rooms_and_bed_flags():
    document = OoxmlDocument(
        tables=(
            OoxmlTable(
                rows=(
                    (cell("ROOM"), cell("NO"), cell("ENGLISH NAMECHINESE NAME"), cell("REMARK")),
                    (cell("", "restart"), cell("001"), cell("MR. CHEN/DA MING陳大明"), cell("")),
                    (cell("", "continue"), cell("002"), cell("MS. LIN/MEI HUA林美花"), cell("")),
                    (cell("3人房", "restart"), cell("003"), cell("MR. WU/DA WEI吳大偉"), cell("")),
                    (cell("", "continue"), cell("004"), cell("CHD. WU/XIAO AN吳小安"), cell("加床")),
                    (cell("", "continue"), cell("005"), cell("CHD. WU/XIAO LE吳小樂"), cell("不佔床")),
                )
            ),
        ),
        searchable_text="TOUR:TST260701A",
    )

    result = parse_rooming_document(document, source_path=Path("sample.docx"))

    assert result.group_code == "TST260701A"
    assert result.passenger_count == 5
    assert [room.room_id for room in result.rooms] == ["01", "02"]
    assert [room.occupancy for room in result.rooms] == [2, 3]
    assert result.rooms[1].sleeping_occupancy == 2
    assert result.rooms[1].room_type == "triple"
    assert result.rooms[1].members[1].extra_bed is True
    assert result.rooms[1].members[2].no_bed is True
    assert result.rooms[0].members[0].chinese_name == "陳大明"
    assert result.rooms[0].members[0].english_name == "CHEN/DA MING"
    assert len(result.warnings) == 2


def test_parses_spreadsheet_blank_continuations_and_bed_preferences():
    document = OoxmlDocument(
        tables=(
            OoxmlTable(
                rows=(
                    (cell("房號"), cell("No."), cell("姓名"), cell("英文"), cell("房型備註")),
                    (cell("1"), cell("1"), cell("王春花"), cell("WANG/CHUN HUA"), cell("需求二小床")),
                    (cell(""), cell("2"), cell("李夏雨"), cell("LEE/HSIA YU"), cell("")),
                    (cell("2"), cell("3"), cell("陳秋月"), cell("CHEN/CHIU YUEH"), cell("大床房需求")),
                    (cell(""), cell("4"), cell("林冬雪"), cell("LIN/TUNG HSUEH"), cell("")),
                )
            ),
        ),
        searchable_text="團號：ABC260101A 領隊：TEST",
    )

    result = parse_rooming_document(document, source_path=Path("sample.xlsx"))

    assert result.group_code == "ABC260101A"
    assert [room.bed_preference for room in result.rooms] == ["twin", "double"]
    assert result.rooms[0].members[0].chinese_name == "王春花"
    assert result.rooms[0].members[0].english_name == "WANG/CHUN HUA"
    assert result.warnings == ()


def test_parses_chinese_name_before_honorific():
    document = OoxmlDocument(
        tables=(
            OoxmlTable(
                rows=(
                    (cell("房號"), cell("NO"), cell("姓名"), cell("備註")),
                    (cell("001"), cell("001"), cell("蔡小明MR. TSAI/HSIAO MING"), cell("")),
                )
            ),
        ),
        searchable_text="團號：SDJ05260728B",
    )

    result = parse_rooming_document(document, source_path=Path("sample.docx"))

    member = result.rooms[0].members[0]
    assert member.chinese_name == "蔡小明"
    assert member.english_name == "TSAI/HSIAO MING"
    assert member.honorific == "MR"


def test_group_code_does_not_treat_company_name_tourone_as_tour_label():
    document = OoxmlDocument(
        tables=(
            OoxmlTable(
                rows=(
                    (cell("房號"), cell("序號"), cell("姓名")),
                    (cell("01"), cell("001"), cell("MR. CHEN/TEST陳測試")),
                )
            ),
        ),
        searchable_text="ROOMING LIST FOR TOURONE EXPRESS\n團 號:WPNRT06F260301A",
    )

    result = parse_rooming_document(document, source_path=Path("sample.docx"))

    assert result.group_code == "WPNRT06F260301A"
