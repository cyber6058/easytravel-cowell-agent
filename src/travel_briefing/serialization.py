from __future__ import annotations

import json
import types
from dataclasses import MISSING, fields, is_dataclass
from enum import Enum
from typing import Any, Union, get_args, get_origin, get_type_hints

from .models import BriefingDraft


SCHEMA_VERSION = 1


def draft_to_dict(draft: BriefingDraft) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "type": "briefing_draft",
        "data": _to_json_value(draft),
    }


def draft_from_dict(payload: dict[str, Any]) -> BriefingDraft:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported briefing manifest schema version")
    if payload.get("type") != "briefing_draft":
        raise ValueError("JSON is not a briefing draft manifest")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("Briefing draft data must be a JSON object")
    draft = _decode_dataclass(BriefingDraft, data)
    if draft.draft_id != draft.with_recomputed_id().draft_id:
        raise ValueError("Briefing draft ID does not match its canonical content")
    return draft


def dumps_draft(draft: BriefingDraft) -> str:
    return json.dumps(draft_to_dict(draft), ensure_ascii=False, indent=2)


def loads_draft(value: str) -> BriefingDraft:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError("Briefing manifest must be valid UTF-8 JSON") from error
    if not isinstance(payload, dict):
        raise ValueError("Briefing manifest must be a JSON object")
    return draft_from_dict(payload)


def _to_json_value(value: Any) -> Any:
    if is_dataclass(value):
        return {
            field.name: _to_json_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_to_json_value(item) for item in value]
    if isinstance(value, list):
        return [_to_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_json_value(item) for key, item in value.items()}
    return value


def _decode_dataclass(model_type: type[Any], data: dict[str, Any]) -> Any:
    if not isinstance(data, dict):
        raise ValueError(f"{model_type.__name__} must be a JSON object")
    model_fields = {field.name: field for field in fields(model_type)}
    unknown = sorted(set(data) - set(model_fields))
    if unknown:
        raise ValueError(
            f"{model_type.__name__} contains unknown fields: {', '.join(unknown)}"
        )
    hints = get_type_hints(model_type)
    values: dict[str, Any] = {}
    for name, field in model_fields.items():
        if name in data:
            values[name] = _decode_value(hints[name], data[name])
        elif field.default is MISSING and field.default_factory is MISSING:
            raise ValueError(f"{model_type.__name__} is missing field: {name}")
    return model_type(**values)


def _decode_value(annotation: Any, value: Any) -> Any:
    origin = get_origin(annotation)
    if origin is tuple:
        item_type = get_args(annotation)[0]
        if not isinstance(value, list):
            raise ValueError("Tuple fields must be encoded as JSON arrays")
        return tuple(_decode_value(item_type, item) for item in value)
    if origin in (Union, types.UnionType):
        if value is None and type(None) in get_args(annotation):
            return None
        value_types = [item for item in get_args(annotation) if item is not type(None)]
        if len(value_types) == 1:
            return _decode_value(value_types[0], value)
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation(value)
    if isinstance(annotation, type) and is_dataclass(annotation):
        return _decode_dataclass(annotation, value)
    return value
