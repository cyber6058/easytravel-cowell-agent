from pathlib import Path

import pytest

from cowell_cli.application.rooming_workflow import build_rooming_plan_from_list
from cowell_cli.domain.rooming import RoomAssignment, RoomingList, RoomMember
from cowell_cli.errors import ValidationError


def _rooming() -> RoomingList:
    return RoomingList(
        source_path=Path("supplier.docx"),
        source_format="docx",
        group_code="SUPPLIER0728",
        rooms=(
            RoomAssignment(
                room_id="01",
                source_room_label="01",
                occupancy=2,
                sleeping_occupancy=2,
                room_type="double_or_twin",
                bed_preference="twin",
                members=(
                    RoomMember("1", "王小明", "WANG/HSIAO MING", "MR"),
                    RoomMember("2", "陳小華", "CHEN/HSIAO HUA", "MS"),
                ),
            ),
        ),
    )


def test_build_rooming_plan_binds_target_source_and_room_mapping():
    plan = build_rooming_plan_from_list(
        _rooming(),
        group_code="test270304a",
        order_id="00000001",
        room_offset=2,
        source_sha256="a" * 64,
    )

    assert plan.target_group_code == "TEST270304A"
    assert plan.target_order_id == "00000001"
    assert plan.rooms[0].target_room_no == "03"
    assert [member.room_sequence for member in plan.rooms[0].members] == ["1", "2"]
    assert plan.passenger_count == 2
    assert plan.confirmation == f"rooms:00000001:TEST270304A:{plan.plan_hash}"


def test_rooming_plan_hash_changes_with_target_or_offset():
    base = build_rooming_plan_from_list(
        _rooming(), group_code="TEST", order_id="1", source_sha256="a" * 64
    )
    shifted = build_rooming_plan_from_list(
        _rooming(),
        group_code="TEST",
        order_id="1",
        room_offset=1,
        source_sha256="a" * 64,
    )
    other_order = build_rooming_plan_from_list(
        _rooming(), group_code="TEST", order_id="2", source_sha256="a" * 64
    )

    assert len({base.plan_hash, shifted.plan_hash, other_order.plan_hash}) == 3


def test_rooming_plan_binds_global_cabin_and_exact_sequence_map():
    global_cabin = build_rooming_plan_from_list(
        _rooming(),
        group_code="TEST",
        order_id="1",
        cabin="y艙",
        source_sha256="a" * 64,
    )
    mapped = build_rooming_plan_from_list(
        _rooming(),
        group_code="TEST",
        order_id="1",
        cabin_map={"1": "Y", "2": "C"},
        source_sha256="a" * 64,
    )

    assert [member.target_cabin for member in global_cabin.rooms[0].members] == [
        "Y",
        "Y",
    ]
    assert [member.target_cabin for member in mapped.rooms[0].members] == ["Y", "C"]
    assert global_cabin.plan_hash != mapped.plan_hash


def test_cabin_map_must_cover_every_source_sequence():
    with pytest.raises(ValidationError, match="cover every passenger sequence"):
        build_rooming_plan_from_list(
            _rooming(),
            group_code="TEST",
            order_id="1",
            cabin_map={"1": "Y"},
            source_sha256="a" * 64,
        )


def test_rooming_plan_rejects_duplicate_passenger_identity():
    rooming = _rooming()
    duplicated = RoomingList(
        source_path=rooming.source_path,
        source_format=rooming.source_format,
        group_code=rooming.group_code,
        rooms=(
            rooming.rooms[0],
            RoomAssignment(
                room_id="02",
                source_room_label="02",
                occupancy=1,
                sleeping_occupancy=1,
                room_type="single",
                bed_preference=None,
                members=(RoomMember("3", "王小明", "WANG/HSIAO MING", "MR"),),
            ),
        ),
    )

    with pytest.raises(ValidationError, match="unique"):
        build_rooming_plan_from_list(
            duplicated,
            group_code="TEST",
            order_id="1",
            source_sha256="a" * 64,
        )
