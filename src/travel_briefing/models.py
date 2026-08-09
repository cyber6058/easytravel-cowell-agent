from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from enum import Enum
from typing import Any


class DraftStatus(str, Enum):
    DRAFT_READY = "DRAFT_READY"
    BLOCKED = "BLOCKED"
    CONFIRMED = "CONFIRMED"


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    source_id: str
    kind: str
    location: str
    sha256: str
    retrieved_at: str
    parser_version: str


@dataclass(frozen=True, slots=True)
class Product:
    code: str
    name: str
    region: str
    day_count: int
    departure_date: str
    return_date: str
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Flight:
    date: str
    airline: str
    number: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ItineraryDay:
    number: int
    date: str
    city: str
    attractions: tuple[str, ...]
    meals: tuple[str, ...]
    hotel: str
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Notice:
    category: str
    text: str
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OpField:
    name: str
    value: str
    source: str
    confirmed: bool
    highlight: str = ""


@dataclass(frozen=True, slots=True)
class WeatherForecast:
    date: str
    display_city: str
    forecast_area: str
    condition: str
    high_c: int | None
    low_c: int | None
    precipitation_percent: int | None
    issued_at: str
    retrieved_at: str
    source_url: str
    available: bool


@dataclass(frozen=True, slots=True)
class Conflict:
    field: str
    source_a: str
    value_a: str
    source_b: str
    value_b: str
    severity: str
    decision: str
    decided_by: str


@dataclass(frozen=True, slots=True)
class DraftWarning:
    code: str
    message: str
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Artifact:
    kind: str
    expected_path: str
    actual_path: str
    sha256: str
    status: str
    generator_version: str


@dataclass(frozen=True, slots=True)
class BriefingDraft:
    draft_id: str
    status: DraftStatus
    generated_at: str
    product: Product
    sources: tuple[SourceEvidence, ...] = ()
    flights: tuple[Flight, ...] = ()
    days: tuple[ItineraryDay, ...] = ()
    notices: tuple[Notice, ...] = ()
    op_fields: tuple[OpField, ...] = ()
    weather: tuple[WeatherForecast, ...] = ()
    conflicts: tuple[Conflict, ...] = ()
    warnings: tuple[DraftWarning, ...] = ()
    artifacts: tuple[Artifact, ...] = ()
    narration_script_sha256: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.status, DraftStatus):
            object.__setattr__(self, "status", DraftStatus(self.status))

    @classmethod
    def create(cls, **values: Any) -> BriefingDraft:
        return cls(draft_id="", **values).with_recomputed_id()

    def with_recomputed_id(self) -> BriefingDraft:
        payload = asdict(self)
        payload.pop("draft_id")
        payload.pop("status")
        payload.pop("artifacts")
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return replace(self, draft_id=hashlib.sha256(canonical).hexdigest())
