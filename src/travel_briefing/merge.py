from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass

from .adapters.newamazing import ParsedNewAmazingPage
from .adapters.pdf_itinerary import ParsedPdfItinerary
from .errors import BriefingInputError
from .models import (
    BriefingDraft,
    Conflict,
    DraftWarning,
    SourceEvidence,
    WeatherForecast,
)
from .op_values import build_missing_op_fields
from .validation import (
    status_for_conflicts,
    text_is_equivalent,
    text_sequence_is_equivalent,
)


def merge_briefing_sources(
    *,
    generated_at: str,
    pdf: ParsedPdfItinerary | None = None,
    web: ParsedNewAmazingPage | None = None,
    weather: tuple[WeatherForecast, ...] = (),
) -> BriefingDraft:
    if pdf is None and web is None:
        raise BriefingInputError("At least one parsed itinerary source is required")

    itinerary = pdf if pdf is not None else web
    if itinerary is None:
        raise BriefingInputError("A parsed itinerary source is required")

    sources: list[SourceEvidence] = []
    if pdf is not None:
        sources.extend(pdf.sources)
    if web is not None:
        sources.append(web.source)

    if pdf is not None and web is not None:
        conflicts, warnings = _source_differences(pdf, web)
    elif pdf is not None:
        conflicts = ()
        warnings = (
            DraftWarning(
                code="WEB_NOTICES_MISSING",
                message="官網其他說明尚未取得，需由 OP 確認",
                source_ids=pdf.product.source_ids,
            ),
        )
    else:
        conflicts, warnings = (), ()

    return BriefingDraft.create(
        status=status_for_conflicts(conflicts),
        generated_at=generated_at,
        product=itinerary.product,
        sources=tuple(sources),
        flights=itinerary.flights,
        days=itinerary.days,
        notices=web.notices if web is not None else (),
        op_fields=build_missing_op_fields(),
        weather=weather,
        conflicts=conflicts,
        warnings=warnings,
    )


def _source_differences(
    pdf: ParsedPdfItinerary,
    web: ParsedNewAmazingPage,
) -> tuple[tuple[Conflict, ...], tuple[DraftWarning, ...]]:
    conflicts: list[Conflict] = []
    warnings: list[DraftWarning] = []
    for attribute in ("code", "departure_date", "return_date", "day_count"):
        _add_conflict(
            conflicts,
            field=f"product.{attribute}",
            value_a=getattr(pdf.product, attribute),
            value_b=getattr(web.product, attribute),
            source_a=_source_id(pdf.product.source_ids, pdf.sources[0].source_id),
            source_b=_source_id(web.product.source_ids, web.source.source_id),
        )

    if len(pdf.flights) != len(web.flights):
        _add_conflict(
            conflicts,
            field="flights",
            value_a=pdf.flights,
            value_b=web.flights,
            source_a=pdf.sources[0].source_id,
            source_b=web.source.source_id,
        )
    else:
        for index, (pdf_flight, web_flight) in enumerate(
            zip(pdf.flights, web.flights, strict=True),
            start=1,
        ):
            for attribute in (
                "date",
                "number",
                "origin",
                "destination",
                "departure_time",
                "arrival_time",
            ):
                _add_conflict(
                    conflicts,
                    field=f"flights[{index}].{attribute}",
                    value_a=getattr(pdf_flight, attribute),
                    value_b=getattr(web_flight, attribute),
                    source_a=_source_id(
                        pdf_flight.source_ids,
                        pdf.sources[0].source_id,
                    ),
                    source_b=_source_id(
                        web_flight.source_ids,
                        web.source.source_id,
                    ),
                )

    pdf_days = {day.number: day for day in pdf.days}
    web_days = {day.number: day for day in web.days}
    if set(pdf_days) != set(web_days):
        _add_conflict(
            conflicts,
            field="days",
            value_a=pdf.days,
            value_b=web.days,
            source_a=pdf.sources[0].source_id,
            source_b=web.source.source_id,
        )
    else:
        for number in sorted(pdf_days):
            pdf_day = pdf_days[number]
            web_day = web_days[number]
            _add_conflict(
                conflicts,
                field=f"days[{number}].date",
                value_a=pdf_day.date,
                value_b=web_day.date,
                source_a=_source_id(
                    pdf_day.source_ids,
                    pdf.sources[0].source_id,
                ),
                source_b=_source_id(
                    web_day.source_ids,
                    web.source.source_id,
                ),
            )
            for attribute in ("city", "hotel", "attractions"):
                value_a = getattr(pdf_day, attribute)
                value_b = getattr(web_day, attribute)
                source_a = _source_id(
                    pdf_day.source_ids,
                    pdf.sources[0].source_id,
                )
                source_b = _source_id(
                    web_day.source_ids,
                    web.source.source_id,
                )
                equivalent = (
                    text_sequence_is_equivalent(value_a, value_b)
                    if isinstance(value_a, tuple) and isinstance(value_b, tuple)
                    else text_is_equivalent(str(value_a), str(value_b))
                )
                if value_a != value_b and equivalent:
                    _add_warning(
                        warnings,
                        code="SOURCE_EQUIVALENT_TEXT",
                        field=f"days[{number}].{attribute}",
                        source_a=source_a,
                        source_b=source_b,
                    )
                    continue
                _add_conflict(
                    conflicts,
                    field=f"days[{number}].{attribute}",
                    value_a=value_a,
                    value_b=value_b,
                    source_a=source_a,
                    source_b=source_b,
                )
            if pdf_day.meals != web_day.meals:
                _add_warning(
                    warnings,
                    code="MEAL_TEXT_DIFFERENCE",
                    field=f"days[{number}].meals",
                    source_a=_source_id(
                        pdf_day.source_ids,
                        pdf.sources[0].source_id,
                    ),
                    source_b=_source_id(
                        web_day.source_ids,
                        web.source.source_id,
                    ),
                )
    return tuple(conflicts), tuple(warnings)


def _add_conflict(
    conflicts: list[Conflict],
    *,
    field: str,
    value_a: object,
    value_b: object,
    source_a: str,
    source_b: str,
) -> None:
    if value_a == value_b:
        return
    conflicts.append(
        Conflict(
            field=field,
            source_a=source_a,
            value_a=_encode_value(value_a),
            source_b=source_b,
            value_b=_encode_value(value_b),
            severity="blocking",
            decision="",
            decided_by="",
        )
    )


def _encode_value(value: object) -> str:
    if isinstance(value, tuple):
        return json.dumps(
            [_json_value(item) for item in value],
            ensure_ascii=False,
            separators=(",", ":"),
        )
    return str(value)


def _json_value(value: object) -> object:
    if is_dataclass(value):
        return asdict(value)
    return value


def _add_warning(
    warnings: list[DraftWarning],
    *,
    code: str,
    field: str,
    source_a: str,
    source_b: str,
) -> None:
    warnings.append(
        DraftWarning(
            code=code,
            message=f"{field} differs without changing meaning; PDF text retained",
            source_ids=(source_a, source_b),
        )
    )


def _source_id(source_ids: tuple[str, ...], fallback: str) -> str:
    return source_ids[0] if source_ids else fallback
