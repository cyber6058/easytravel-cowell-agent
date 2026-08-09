from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import replace

from .errors import BriefingInputError, StaleDraftDecisionError
from .models import BriefingDraft, Flight, ItineraryDay, OpField
from .validation import status_for_conflicts


REQUIRED_OP_FIELD_NAMES = (
    "meeting_time",
    "meeting_place",
    "tour_leader_name",
    "tour_leader_phone",
    "identification_or_luggage_tag",
    "airport_representative",
    "emergency_contact_name",
    "emergency_contact_phone",
    "alternate_hotel",
)


def build_missing_op_fields() -> tuple[OpField, ...]:
    return tuple(_missing_op_field(name) for name in REQUIRED_OP_FIELD_NAMES)


def apply_op_values(
    draft: BriefingDraft,
    payload: Mapping[str, object],
) -> BriefingDraft:
    if payload.get("draft_id") != draft.draft_id:
        raise StaleDraftDecisionError("op_values")
    values = payload.get("values")
    if not isinstance(values, Mapping) or not values:
        raise BriefingInputError("OP values must contain a non-empty values object")

    unknown = sorted(set(values) - set(REQUIRED_OP_FIELD_NAMES))
    if unknown:
        raise BriefingInputError(
            "OP values contain unknown fields",
            details={"fields": unknown},
        )

    existing = {field.name: field for field in draft.op_fields}
    updated_fields: list[OpField] = []
    for name in REQUIRED_OP_FIELD_NAMES:
        current = existing.get(name) or _missing_op_field(name)
        if name not in values:
            updated_fields.append(current)
            continue
        value = values[name]
        if (
            not isinstance(value, str)
            or not value.strip()
            or re.sub(r"\s+", "", value).casefold()
            in {"待op確認", "pending", "unknown"}
        ):
            raise BriefingInputError(
                "OP values must be non-empty text",
                details={"field": name},
            )
        updated_fields.append(
            OpField(
                name=name,
                value=value.strip(),
                source="OP",
                confirmed=True,
                highlight="",
            )
        )

    return replace(
        draft,
        status=status_for_conflicts(draft.conflicts),
        op_fields=tuple(updated_fields),
    ).with_recomputed_id()


def apply_conflict_decisions(
    draft: BriefingDraft,
    payload: Mapping[str, object],
) -> BriefingDraft:
    if payload.get("draft_id") != draft.draft_id:
        raise StaleDraftDecisionError("conflict_decisions")
    decisions = payload.get("decisions")
    if not isinstance(decisions, Mapping) or not decisions:
        raise BriefingInputError(
            "Conflict decisions must contain a non-empty decisions object"
        )
    conflicts_by_field = {conflict.field: conflict for conflict in draft.conflicts}
    unknown = sorted(set(decisions) - set(conflicts_by_field))
    if unknown:
        raise BriefingInputError(
            "Conflict decisions contain unknown fields",
            details={"fields": unknown},
        )

    updated_draft = draft
    updated_conflicts = []
    for conflict in draft.conflicts:
        decision = decisions.get(conflict.field)
        if decision is None:
            updated_conflicts.append(conflict)
            continue
        if decision not in {"use_a", "use_b"}:
            raise BriefingInputError(
                "Conflict decisions must be use_a or use_b",
                details={"field": conflict.field},
            )
        selected_value = (
            conflict.value_a if decision == "use_a" else conflict.value_b
        )
        selected_source = (
            conflict.source_a if decision == "use_a" else conflict.source_b
        )
        updated_draft = _set_selected_value(
            updated_draft,
            field=conflict.field,
            value=selected_value,
            source_id=selected_source,
        )
        updated_conflicts.append(
            replace(conflict, decision=decision, decided_by="OP")
        )

    conflicts = tuple(updated_conflicts)
    return replace(
        updated_draft,
        status=status_for_conflicts(conflicts),
        conflicts=conflicts,
    ).with_recomputed_id()


def _missing_op_field(name: str) -> OpField:
    return OpField(
        name=name,
        value="待 OP 確認",
        source="",
        confirmed=False,
        highlight="yellow",
    )


def _set_selected_value(
    draft: BriefingDraft,
    *,
    field: str,
    value: str,
    source_id: str,
) -> BriefingDraft:
    if field == "flights":
        return replace(
            draft,
            flights=_decode_flights(value, source_id=source_id),
        )
    if field == "days":
        return replace(
            draft,
            days=_decode_days(value, source_id=source_id),
        )

    product_match = re.fullmatch(r"product\.([a-z_]+)", field)
    if product_match is not None:
        attribute = product_match.group(1)
        if attribute not in {
            "code",
            "name",
            "region",
            "day_count",
            "departure_date",
            "return_date",
        }:
            raise BriefingInputError("Unsupported product conflict field")
        selected = _decode_value(value, getattr(draft.product, attribute))
        product = replace(
            draft.product,
            **{
                attribute: selected,
                "source_ids": _with_source(draft.product.source_ids, source_id),
            },
        )
        return replace(draft, product=product)

    flight_match = re.fullmatch(r"flights\[(\d+)]\.([a-z_]+)", field)
    if flight_match is not None:
        index = int(flight_match.group(1)) - 1
        attribute = flight_match.group(2)
        if index not in range(len(draft.flights)) or attribute not in {
            "date",
            "airline",
            "number",
            "origin",
            "destination",
            "departure_time",
            "arrival_time",
        }:
            raise BriefingInputError("Unsupported flight conflict field")
        current = draft.flights[index]
        selected = _decode_value(value, getattr(current, attribute))
        updated = replace(
            current,
            **{
                attribute: selected,
                "source_ids": _with_source(current.source_ids, source_id),
            },
        )
        flights = (*draft.flights[:index], updated, *draft.flights[index + 1 :])
        return replace(draft, flights=flights)

    day_match = re.fullmatch(r"days\[(\d+)]\.([a-z_]+)", field)
    if day_match is not None:
        number = int(day_match.group(1))
        attribute = day_match.group(2)
        index = next(
            (index for index, day in enumerate(draft.days) if day.number == number),
            -1,
        )
        if index < 0 or attribute not in {
            "date",
            "city",
            "attractions",
            "meals",
            "hotel",
        }:
            raise BriefingInputError("Unsupported itinerary conflict field")
        current = draft.days[index]
        selected = _decode_value(value, getattr(current, attribute))
        updated = replace(
            current,
            **{
                attribute: selected,
                "source_ids": _with_source(current.source_ids, source_id),
            },
        )
        days = (*draft.days[:index], updated, *draft.days[index + 1 :])
        return replace(draft, days=days)

    raise BriefingInputError(
        "Unsupported conflict field",
        details={"field": field},
    )


def _decode_value(value: str, current: object) -> object:
    if isinstance(current, tuple):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as error:
            raise BriefingInputError("Conflict tuple value is invalid JSON") from error
        if not isinstance(decoded, list) or not all(
            isinstance(item, str) for item in decoded
        ):
            raise BriefingInputError("Conflict tuple value must be a text array")
        return tuple(decoded)
    if isinstance(current, int):
        try:
            return int(value)
        except ValueError as error:
            raise BriefingInputError("Conflict integer value is invalid") from error
    return value


def _with_source(source_ids: tuple[str, ...], source_id: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*source_ids, source_id)))


def _decode_flights(value: str, *, source_id: str) -> tuple[Flight, ...]:
    rows = _decode_object_rows(value, "Flight")
    required = {
        "date",
        "airline",
        "number",
        "origin",
        "destination",
        "departure_time",
        "arrival_time",
        "source_ids",
    }
    flights: list[Flight] = []
    for row in rows:
        if set(row) != required:
            raise BriefingInputError("Flight conflict value has invalid fields")
        source_ids = _decode_source_ids(row["source_ids"], source_id)
        text_values = {name: row[name] for name in required - {"source_ids"}}
        if not all(isinstance(item, str) and item for item in text_values.values()):
            raise BriefingInputError("Flight conflict value contains invalid text")
        flights.append(Flight(source_ids=source_ids, **text_values))
    return tuple(flights)


def _decode_days(value: str, *, source_id: str) -> tuple[ItineraryDay, ...]:
    rows = _decode_object_rows(value, "Itinerary day")
    required = {
        "number",
        "date",
        "city",
        "attractions",
        "meals",
        "hotel",
        "source_ids",
    }
    days: list[ItineraryDay] = []
    for row in rows:
        if set(row) != required or not isinstance(row["number"], int):
            raise BriefingInputError("Itinerary conflict value has invalid fields")
        attractions = _decode_text_array(row["attractions"], "attractions")
        meals = _decode_text_array(row["meals"], "meals")
        source_ids = _decode_source_ids(row["source_ids"], source_id)
        text_values = (row["date"], row["city"], row["hotel"])
        if not all(isinstance(item, str) and item for item in text_values):
            raise BriefingInputError("Itinerary conflict value contains invalid text")
        days.append(
            ItineraryDay(
                number=row["number"],
                date=row["date"],
                city=row["city"],
                attractions=attractions,
                meals=meals,
                hotel=row["hotel"],
                source_ids=source_ids,
            )
        )
    return tuple(days)


def _decode_object_rows(value: str, label: str) -> list[dict[str, object]]:
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as error:
        raise BriefingInputError(f"{label} conflict value is invalid JSON") from error
    if not isinstance(decoded, list) or not decoded or not all(
        isinstance(item, dict) for item in decoded
    ):
        raise BriefingInputError(f"{label} conflict value must be an object array")
    return decoded


def _decode_text_array(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) for item in value
    ):
        raise BriefingInputError(f"{label} must be a text array")
    return tuple(value)


def _decode_source_ids(value: object, selected_source: str) -> tuple[str, ...]:
    source_ids = _decode_text_array(value, "source_ids")
    return _with_source(source_ids, selected_source)
