from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from ..domain.rooming import RoomMember, RoomingList
from ..errors import ValidationError
from .rooms import parse_rooming_list


@dataclass(frozen=True, slots=True)
class PlannedRoomMember:
    source_sequence: str
    room_sequence: str
    chinese_name: str
    english_name: str
    notes: tuple[str, ...]
    source_honorific: str | None
    target_cabin: str | None


@dataclass(frozen=True, slots=True)
class PlannedRoom:
    source_room_id: str
    target_room_no: str
    room_type: str
    bed_preference: str | None
    members: tuple[PlannedRoomMember, ...]


@dataclass(frozen=True, slots=True)
class RoomingPlan:
    source_path: Path
    source_sha256: str
    source_group_code: str | None
    target_group_code: str
    target_order_id: str
    room_offset: int
    rooms: tuple[PlannedRoom, ...]
    warnings: tuple[str, ...]
    plan_hash: str
    confirmation: str

    @property
    def passenger_count(self) -> int:
        return sum(len(room.members) for room in self.rooms)


def build_rooming_plan(
    source_path: Path,
    *,
    group_code: str,
    order_id: str,
    room_offset: int = 0,
    cabin: str | None = None,
    cabin_map: Mapping[str, str] | None = None,
) -> RoomingPlan:
    path = source_path.expanduser().resolve()
    rooming = parse_rooming_list(path)
    return build_rooming_plan_from_list(
        rooming,
        group_code=group_code,
        order_id=order_id,
        room_offset=room_offset,
        cabin=cabin,
        cabin_map=cabin_map,
        source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def build_rooming_plan_from_list(
    rooming: RoomingList,
    *,
    group_code: str,
    order_id: str,
    room_offset: int = 0,
    cabin: str | None = None,
    cabin_map: Mapping[str, str] | None = None,
    source_sha256: str = "0" * 64,
) -> RoomingPlan:
    target_group = group_code.strip().upper()
    target_order = order_id.strip()
    if not target_group or not target_order:
        raise ValidationError("target group_code and order_id are required")
    if room_offset < 0:
        raise ValidationError("room_offset cannot be negative")
    if len(source_sha256) != 64:
        raise ValidationError("source_sha256 must contain 64 hexadecimal characters")
    if cabin and cabin_map:
        raise ValidationError("Use either cabin or cabin_map, not both")
    normalized_cabin = _normalize_cabin(cabin) if cabin else None
    normalized_cabin_map = {
        str(sequence).strip(): _normalize_cabin(value)
        for sequence, value in (cabin_map or {}).items()
    }

    seen_chinese: set[str] = set()
    seen_english: set[str] = set()
    seen_sequences: set[str] = set()
    planned_rooms: list[PlannedRoom] = []
    for room in rooming.rooms:
        target_room = _offset_room_number(room.room_id, room_offset)
        members: list[PlannedRoomMember] = []
        for room_sequence, member in enumerate(room.members, 1):
            chinese, english, source_sequence = _required_identity(member)
            normalized_english = _normalize_english(english)
            if chinese in seen_chinese or normalized_english in seen_english:
                raise ValidationError(
                    "passenger names must be unique for one-to-one Cowell matching"
                )
            seen_chinese.add(chinese)
            seen_english.add(normalized_english)
            if source_sequence in seen_sequences:
                raise ValidationError("passenger sequences must be unique")
            seen_sequences.add(source_sequence)
            members.append(
                PlannedRoomMember(
                    source_sequence=source_sequence,
                    room_sequence=str(room_sequence),
                    chinese_name=chinese,
                    english_name=english,
                    notes=member.notes,
                    source_honorific=member.honorific,
                    target_cabin=(
                        normalized_cabin
                        or normalized_cabin_map.get(source_sequence)
                    ),
                )
            )
        planned_rooms.append(
            PlannedRoom(
                source_room_id=room.room_id,
                target_room_no=target_room,
                room_type=room.room_type,
                bed_preference=room.bed_preference,
                members=tuple(members),
            )
        )

    target_rooms = [room.target_room_no for room in planned_rooms]
    if len(target_rooms) != len(set(target_rooms)):
        raise ValidationError("room mapping produced duplicate target room numbers")
    if normalized_cabin_map:
        missing = sorted(seen_sequences - set(normalized_cabin_map))
        extra = sorted(set(normalized_cabin_map) - seen_sequences)
        if missing or extra:
            raise ValidationError(
                "cabin_map must cover every passenger sequence exactly once",
                {"missing_sequences": missing, "extra_sequences": extra},
            )

    canonical = {
        "source_sha256": source_sha256.lower(),
        "target_group_code": target_group,
        "target_order_id": target_order,
        "room_offset": room_offset,
        "rooms": [
            {
                "source_room_id": room.source_room_id,
                "target_room_no": room.target_room_no,
                "members": [
                    {
                        "source_sequence": member.source_sequence,
                        "room_sequence": member.room_sequence,
                        "chinese_name": member.chinese_name,
                        "english_name": _normalize_english(member.english_name),
                        "notes": list(member.notes),
                        "target_cabin": member.target_cabin,
                    }
                    for member in room.members
                ],
            }
            for room in planned_rooms
        ],
    }
    plan_hash = hashlib.sha256(
        json.dumps(
            canonical,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:16]
    confirmation = f"rooms:{target_order}:{target_group}:{plan_hash}"
    return RoomingPlan(
        source_path=rooming.source_path,
        source_sha256=source_sha256.lower(),
        source_group_code=rooming.group_code,
        target_group_code=target_group,
        target_order_id=target_order,
        room_offset=room_offset,
        rooms=tuple(planned_rooms),
        warnings=rooming.warnings,
        plan_hash=plan_hash,
        confirmation=confirmation,
    )


def _required_identity(member: RoomMember) -> tuple[str, str, str]:
    chinese = (member.chinese_name or "").strip()
    english = (member.english_name or "").strip()
    sequence = (member.sequence or "").strip()
    if not chinese or not english or not sequence:
        raise ValidationError(
            "every passenger needs a sequence plus Chinese and English names"
        )
    if "/" not in english:
        raise ValidationError("English passenger names must use SURNAME/GIVEN format")
    return chinese, english, sequence


def _offset_room_number(room_id: str, offset: int) -> str:
    value = room_id.strip()
    if offset == 0:
        return value
    if not value.isdigit():
        raise ValidationError(
            "room_offset requires numeric source room IDs",
            {"source_room_id": value},
        )
    return str(int(value) + offset).zfill(len(value))


def _normalize_english(value: str) -> str:
    return "".join(character for character in value.upper() if character.isalpha())


def _normalize_cabin(value: str) -> str:
    normalized = "".join(str(value).upper().split()).removesuffix("艙")
    if not normalized or len(normalized) > 12:
        raise ValidationError("cabin value is invalid", {"cabin": str(value)})
    return normalized
