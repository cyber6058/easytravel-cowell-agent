import pytest

from cowell_cli.adapters.cowell.live_rooming import (
    _classify_passenger_matches,
    _count_name_matches_from_rows,
    _PassengerSlot,
    _parse_dynamic_import_chain,
    _parse_group_order_ids,
    _query_field_names,
    _room_number_key,
    _room_row_matches_member,
    _select_placeholder_slots,
    _suggest_room_offset,
)
from cowell_cli.application.rooming_workflow import build_rooming_plan_from_list
from cowell_cli.domain.rooming import RoomAssignment, RoomingList, RoomMember
from cowell_cli.errors import ValidationError
from pathlib import Path


def test_parse_group_order_ids_is_unique_and_sorted():
    html = "order 00000002 duplicate 00000002 earlier 00000001"
    assert _parse_group_order_ids(html) == ("00000001", "00000002")


def test_room_number_key_treats_leading_zero_variants_as_same_room():
    assert _room_number_key("01") == _room_number_key("001")


def _plan(*, cabin=None, cabin_map=None, first_honorific="MR"):
    rooming = RoomingList(
        source_path=Path("supplier.docx"),
        source_format="docx",
        group_code=None,
        rooms=(
            RoomAssignment(
                room_id="01",
                source_room_label="01",
                occupancy=1,
                sleeping_occupancy=1,
                room_type="single",
                bed_preference=None,
                members=(RoomMember("1", "王小明", "WANG/HSIAO MING", first_honorific),),
            ),
            RoomAssignment(
                room_id="02",
                source_room_label="02",
                occupancy=1,
                sleeping_occupancy=1,
                room_type="single",
                bed_preference=None,
                members=(RoomMember("2", "陳小華", "CHEN/HSIAO HUA", "MS"),),
            ),
        ),
    )
    return build_rooming_plan_from_list(
        rooming,
        group_code="TEST",
        order_id="1",
        cabin=cabin,
        cabin_map=cabin_map,
        source_sha256="a" * 64,
    )


def test_suggest_room_offset_avoids_existing_rooms():
    assert _suggest_room_offset(_plan(), {"01", "02"}) == 2
    assert _suggest_room_offset(_plan(), {"001", "002"}) == 2
    assert _suggest_room_offset(_plan(), {"05"}) == 0


def test_stage_query_fields_preserve_blank_tp_parameter():
    fields = _query_field_names(
        "https://cowell.example/include/get_xml.asp?TP=&OP_SQ=1&GRUP_CD=TEST"
    )

    assert fields == frozenset({"TP", "OP_SQ", "GRUP_CD"})


def test_name_matching_requires_unique_chinese_and_english_on_same_row():
    plan = _plan()
    rows = (
        ("欄位王小明其他", "WANG HSIAO MING"),
        ("欄位陳小華其他", "CHEN HSIAO HUA"),
    )

    assert _count_name_matches_from_rows(plan, rows) == 2


def test_name_matching_does_not_combine_components_across_rows():
    plan = _plan()
    rows = (
        ("欄位王小明其他", "WANG"),
        ("欄位陳小華其他", "HSIAO MING CHEN HSIAO HUA"),
    )

    assert _count_name_matches_from_rows(plan, rows) == 1


@pytest.mark.parametrize(
    ('matched', 'total', 'requires_import', 'blocker'),
    (
        (0, 4, True, None),
        (4, 4, False, None),
        (2, 4, False, 'source passengers only partially match the Cowell order'),
    ),
)
def test_passenger_match_state_selects_name_import_room_only_or_block(
    matched, total, requires_import, blocker
):
    assert _classify_passenger_matches(matched, total) == (
        requires_import,
        blocker,
    )


def test_room_row_matching_ignores_spacing_between_chinese_characters():
    member = _plan().rooms[0].members[0]

    assert _room_row_matches_member(member, "欄位 王 小 明 其他") is True
    assert _room_row_matches_member(member, "欄位 陳 小 華 其他") is False


def test_single_existing_cabin_is_selected_and_age_mismatch_only_warns():
    selection = _select_placeholder_slots(
        _plan(cabin="Y", first_honorific="CHD"),
        (
            _PassengerSlot("slot-1", "Y", "大人", True),
            _PassengerSlot("slot-2", "Y", "大人", True),
        ),
    )

    assert [slot.value for slot in selection.slots] == ["slot-1", "slot-2"]
    assert selection.blockers == ()
    assert selection.category_mismatch_count == 1
    assert "will be preserved" in selection.warnings[0]


@pytest.mark.parametrize(
    ('source_honorific', 'cowell_category'),
    (
        ('MR', '\u5c0f\u5b69'),
        ('CHD', '\u5b30\u5152'),
        ('INF', '\u5927\u4eba'),
    ),
)
def test_all_age_categories_mismatch_warns_and_preserves_cowell_value(
    source_honorific, cowell_category
):
    selection = _select_placeholder_slots(
        _plan(cabin='Y', first_honorific=source_honorific),
        (
            _PassengerSlot('slot-1', 'Y', cowell_category, True),
            _PassengerSlot('slot-2', 'Y', '\u5927\u4eba', True),
        ),
    )

    assert selection.blockers == ()
    assert selection.category_mismatch_count == 1
    assert selection.slots[0].category == cowell_category
    assert 'will be preserved' in selection.warnings[0]


def test_single_existing_cabin_is_auto_detected_but_must_be_bound_before_write():
    selection = _select_placeholder_slots(
        _plan(),
        (
            _PassengerSlot("slot-1", "Y", "大人", True),
            _PassengerSlot("slot-2", "Y", "大人", True),
        ),
    )

    assert [(item.cabin, item.passenger_slots) for item in selection.selected_cabins] == [
        ("Y", 2)
    ]
    assert "--cabin Y" in selection.blockers[0]


def test_multiple_existing_cabins_require_an_explicit_mapping():
    selection = _select_placeholder_slots(
        _plan(),
        (
            _PassengerSlot("slot-y", "Y", "大人", True),
            _PassengerSlot("slot-c", "C", "大人", True),
        ),
    )

    assert selection.slots == ()
    assert "--cabin-map" in selection.blockers[0]
    assert [(item.cabin, item.passenger_slots) for item in selection.available_cabins] == [
        ("C", 1),
        ("Y", 1),
    ]


def test_sequence_cabin_map_selects_matching_slots_in_source_order():
    selection = _select_placeholder_slots(
        _plan(cabin_map={"1": "Y", "2": "C"}),
        (
            _PassengerSlot("slot-c", "C", "大人", True),
            _PassengerSlot("slot-y", "Y", "大人", True),
        ),
    )

    assert [slot.value for slot in selection.slots] == ["slot-y", "slot-c"]
    assert selection.blockers == ()


def test_parse_dynamic_import_chain_requires_safe_paths_and_matching_stem():
    html = """
    <script>
    $.ajax({url: "/emnet/API/EXCEL_IMPORT_GetXLSX_Author.ashx"});
    SendAJAX("/emnet/API/EXCEL_IMPORT_SaveXMLFILE.ashx");
    var file = "FileName=d:\\webmanager\\web\\upload\\aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.xlsx";
    var faction="/B/received_recp2_su.asp?TP=&OP_SQ=1&GRUP_CD=TEST&PAX_DR=1&mode=A&file_type=xlsx&XML_FILE_NM=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.xml";
    </script>
    """

    apis, stage_file, final_path = _parse_dynamic_import_chain(html)

    assert apis == (
        "/emnet/API/EXCEL_IMPORT_GetXLSX_Author.ashx",
        "/emnet/API/EXCEL_IMPORT_SaveXMLFILE.ashx",
    )
    assert stage_file.endswith("a" * 32 + ".xlsx")
    assert final_path.startswith("/B/received_recp2_su.asp?")


def test_parse_dynamic_import_chain_accepts_changed_absolute_upload_root():
    html = """
    <script>
    $.ajax({url: "/emnet/API/EXCEL_IMPORT_GetXLSX_Author.ashx"});
    SendAJAX("/emnet/API/EXCEL_IMPORT_SaveXMLFILE.ashx");
    var file = "FileName=c:\\inetpub\\cowell\\upload\\bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.xlsx";
    var faction="/B/received_recp2_su.asp?TP=&OP_SQ=1&GRUP_CD=TEST&PAX_DR=1&mode=A&file_type=xlsx&XML_FILE_NM=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.xml";
    </script>
    """

    _apis, stage_file, _final_path = _parse_dynamic_import_chain(html)

    assert stage_file.startswith("c:\\inetpub\\cowell\\upload\\")


@pytest.mark.parametrize(
    "stage_file",
    (
        r"c:\\temp\\bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.xlsx",
        r"c:\\upload\\..\\secret\\bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.xlsx",
        r"relative\\upload\\bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.xlsx",
    ),
)
def test_parse_dynamic_import_chain_rejects_unsafe_upload_roots(stage_file):
    html = f"""
    <script>
    url: "/emnet/API/One.ashx"; url: "/emnet/API/Two.ashx";
    FileName={stage_file}
    var faction="/B/received_recp2_su.asp?XML_FILE_NM=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.xml";
    </script>
    """

    with pytest.raises(ValidationError, match="unsafe temporary workbook path"):
        _parse_dynamic_import_chain(html)


def test_parse_dynamic_import_chain_rejects_unexpected_temp_location():
    html = """
    url: "/emnet/API/One.ashx"; url: "/emnet/API/Two.ashx";
    FileName=c:\\temp\\aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.xlsx
    var faction="/B/received_recp2_su.asp?XML_FILE_NM=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.xml";
    """

    with pytest.raises(ValidationError, match="unsafe temporary workbook path"):
        _parse_dynamic_import_chain(html)
