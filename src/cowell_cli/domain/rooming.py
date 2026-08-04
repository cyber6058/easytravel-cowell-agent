from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RoomMember:
    sequence: str | None
    chinese_name: str | None
    english_name: str | None
    honorific: str | None
    notes: tuple[str, ...] = ()
    extra_bed: bool = False
    no_bed: bool = False


@dataclass(frozen=True, slots=True)
class RoomAssignment:
    room_id: str
    source_room_label: str | None
    occupancy: int
    sleeping_occupancy: int
    room_type: str
    bed_preference: str | None
    members: tuple[RoomMember, ...]


@dataclass(frozen=True, slots=True)
class RoomingList:
    source_path: Path
    source_format: str
    group_code: str | None
    rooms: tuple[RoomAssignment, ...]
    warnings: tuple[str, ...] = ()

    @property
    def passenger_count(self) -> int:
        return sum(room.occupancy for room in self.rooms)
