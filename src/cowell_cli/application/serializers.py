from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from ..domain.rooming import RoomingList
from .rooming_workflow import RoomingPlan
from ..adapters.cowell.live_rooming import LiveRoomingPreview, LiveRoomingResult


SCHEMA_VERSION = 1


def serialize_rooming_list(rooming: RoomingList) -> dict[str, Any]:
    data = _to_json_value(rooming)
    data["passenger_count"] = rooming.passenger_count
    return {
        "schema_version": SCHEMA_VERSION,
        "type": "rooming_list",
        "data": data,
    }


def serialize_rooming_plan(plan: RoomingPlan) -> dict[str, Any]:
    data = _to_json_value(plan)
    data["passenger_count"] = plan.passenger_count
    data["room_count"] = len(plan.rooms)
    return {
        "schema_version": SCHEMA_VERSION,
        "type": "rooming_plan",
        "data": data,
    }


def serialize_live_rooming_preview(preview: LiveRoomingPreview) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "type": "live_rooming_preview",
        "data": _to_json_value(preview),
    }


def serialize_live_rooming_result(result: LiveRoomingResult) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "type": "live_rooming_result",
        "data": _to_json_value(result),
    }


def _to_json_value(value: Any) -> Any:
    if is_dataclass(value):
        return {
            key: _to_json_value(item)
            for key, item in asdict(value).items()
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_to_json_value(item) for item in value]
    if isinstance(value, list):
        return [_to_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_json_value(item) for key, item in value.items()}
    return value
