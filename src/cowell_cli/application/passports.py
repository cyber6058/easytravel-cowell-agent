from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ..domain.passport import PassportTraveler, parse_td3_mrz
from ..errors import ValidationError


JSON_FIELDS = {
    "imageName": "image_name",
    "passportNo": "passport_no",
    "idNo": "id_no",
    "englishSurname": "english_surname",
    "englishGiven": "english_given",
    "sex": "sex",
    "chineseSurname": "chinese_surname",
    "chineseGiven": "chinese_given",
    "birthDate": "birth_date",
    "issueDate": "issue_date",
    "expiryDate": "expiry_date",
    "birthPlace": "birth_place",
    "nationality": "nationality",
    "mobile": "mobile",
    "email": "email",
    "taiwanCompatriotPermitNo": "taiwan_compatriot_permit_no",
    "issueCount": "issue_count",
    "permitStartDate": "permit_start_date",
    "permitEndDate": "permit_end_date",
    "mrzLine1": "mrz_line1",
    "mrzLine2": "mrz_line2",
}
REQUIRED_FIELDS = (
    "passport_no",
    "id_no",
    "english_surname",
    "english_given",
    "sex",
    "chinese_surname",
    "chinese_given",
    "birth_date",
    "issue_date",
    "expiry_date",
    "birth_place",
    "nationality",
    "mrz_line1",
    "mrz_line2",
)


@dataclass(frozen=True, slots=True)
class PassportRecordValidation:
    record_id: str
    ready_for_export: bool
    mrz_check_digits_valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PassportValidationReport:
    record_count: int
    ready_count: int
    valid_mrz_count: int
    records: tuple[PassportRecordValidation, ...]

    @property
    def ready_for_export(self) -> bool:
        return self.record_count > 0 and self.ready_count == self.record_count


def load_passport_travelers(path: Path) -> tuple[PassportTraveler, ...]:
    source = path.expanduser().resolve()
    if not source.is_file():
        raise ValidationError("Passport data JSON does not exist", {"path": str(source)})
    try:
        payload = json.loads(source.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationError("Passport data must be valid UTF-8 JSON") from error
    rows = payload if isinstance(payload, list) else [payload]
    if not rows or any(not isinstance(row, Mapping) for row in rows):
        raise ValidationError("Passport data JSON must contain one or more objects")
    return tuple(_traveler_from_mapping(row, index) for index, row in enumerate(rows, 1))


def validate_passport_travelers(
    travelers: tuple[PassportTraveler, ...],
) -> PassportValidationReport:
    if not travelers:
        raise ValidationError("Passport data contains no travelers")
    records = tuple(_validate_traveler(traveler) for traveler in travelers)
    duplicate_errors = _duplicate_identity_errors(travelers)
    if duplicate_errors:
        records = tuple(
            PassportRecordValidation(
                record_id=record.record_id,
                ready_for_export=False,
                mrz_check_digits_valid=record.mrz_check_digits_valid,
                errors=record.errors + duplicate_errors.get(record.record_id, ()),
                warnings=record.warnings,
            )
            for record in records
        )
    return PassportValidationReport(
        record_count=len(records),
        ready_count=sum(record.ready_for_export for record in records),
        valid_mrz_count=sum(record.mrz_check_digits_valid for record in records),
        records=records,
    )


def traveler_excel_values(traveler: PassportTraveler) -> tuple[str, ...]:
    return (
        traveler.image_name,
        traveler.passport_no,
        traveler.id_no,
        traveler.english_surname,
        traveler.english_given,
        traveler.sex,
        traveler.chinese_surname,
        traveler.chinese_given,
        traveler.birth_date,
        traveler.issue_date,
        traveler.expiry_date,
        traveler.birth_place,
        traveler.nationality,
        traveler.mobile,
        traveler.email,
        traveler.taiwan_compatriot_permit_no,
        traveler.issue_count,
        traveler.permit_start_date,
        traveler.permit_end_date,
    )


def _traveler_from_mapping(row: Mapping[str, Any], index: int) -> PassportTraveler:
    values: dict[str, Any] = {
        python_name: _string(row.get(json_name, ""))
        for json_name, python_name in JSON_FIELDS.items()
    }
    values["record_id"] = _string(row.get("recordId")) or f"P{index:03d}"
    raw_uncertainties = row.get("uncertainties", ())
    if isinstance(raw_uncertainties, str):
        raw_uncertainties = (raw_uncertainties,)
    values["uncertainties"] = tuple(
        _string(value) for value in raw_uncertainties if _string(value)
    )
    for field in (
        "birth_date",
        "issue_date",
        "expiry_date",
        "permit_start_date",
        "permit_end_date",
    ):
        if values[field]:
            values[field] = _normalize_date(values[field])
    for field in ("passport_no", "id_no", "english_surname", "english_given", "sex"):
        values[field] = values[field].upper()
    return PassportTraveler(**values)


def _validate_traveler(traveler: PassportTraveler) -> PassportRecordValidation:
    errors: list[str] = []
    warnings: list[str] = []
    missing = [field for field in REQUIRED_FIELDS if not getattr(traveler, field)]
    if missing:
        errors.append("missing required fields: " + ", ".join(missing))
    if traveler.uncertainties:
        errors.append("unresolved uncertainties are present")
    if any("?" in getattr(traveler, field) for field in REQUIRED_FIELDS):
        errors.append("required fields contain '?' characters")
    if traveler.sex not in {"M", "F", "X"}:
        errors.append("sex must be M, F, or X")

    mrz_valid = False
    if traveler.mrz_line1 and traveler.mrz_line2:
        try:
            mrz = parse_td3_mrz(traveler.mrz_line1, traveler.mrz_line2)
        except ValueError as error:
            errors.append(str(error))
        else:
            mrz_valid = mrz.all_check_digits_valid
            if not mrz_valid:
                errors.append("one or more MRZ check digits failed")
            comparisons = (
                ("passport number", traveler.passport_no, mrz.passport_no),
                ("English surname", traveler.english_surname, mrz.surname),
                ("English given names", traveler.english_given, mrz.given_names),
                ("sex", traveler.sex, mrz.sex),
                ("birth date", _date_suffix(traveler.birth_date), mrz.birth_date_yymmdd),
                ("expiry date", _date_suffix(traveler.expiry_date), mrz.expiry_date_yymmdd),
                ("personal ID", traveler.id_no, mrz.personal_no),
                ("nationality", _nationality_code(traveler.nationality), mrz.nationality),
            )
            for label, printed, machine in comparisons:
                if _identity_key(printed) != _identity_key(machine):
                    errors.append(f"printed {label} does not match MRZ")
    if not traveler.mobile:
        warnings.append("mobile is blank")
    if not traveler.email:
        warnings.append("email is blank")
    return PassportRecordValidation(
        record_id=traveler.record_id,
        ready_for_export=not errors,
        mrz_check_digits_valid=mrz_valid,
        errors=tuple(dict.fromkeys(errors)),
        warnings=tuple(warnings),
    )


def _duplicate_identity_errors(
    travelers: tuple[PassportTraveler, ...],
) -> dict[str, tuple[str, ...]]:
    errors: dict[str, list[str]] = {}
    for label, getter in (
        ("passport number", lambda item: item.passport_no),
        ("personal ID", lambda item: item.id_no),
    ):
        buckets: dict[str, list[str]] = {}
        for traveler in travelers:
            key = _identity_key(getter(traveler))
            if key:
                buckets.setdefault(key, []).append(traveler.record_id)
        for record_ids in buckets.values():
            if len(record_ids) > 1:
                for record_id in record_ids:
                    errors.setdefault(record_id, []).append(f"duplicate {label}")
    return {key: tuple(value) for key, value in errors.items()}


def _normalize_date(value: str) -> str:
    match = re.fullmatch(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", value.strip())
    if not match:
        return value.strip()
    return f"{match.group(1)}/{match.group(2).zfill(2)}/{match.group(3).zfill(2)}"


def _date_suffix(value: str) -> str:
    digits = "".join(character for character in value if character.isdigit())
    return digits[-6:]


def _nationality_code(value: str) -> str:
    normalized = _identity_key(value)
    if normalized in {"台灣", "TAIWAN", "REPUBLICOFCHINA", "ROC", "TWN"}:
        return "TWN"
    return value


def _identity_key(value: str) -> str:
    return "".join(character for character in value.upper() if character.isalnum())


def _string(value: Any) -> str:
    return str(value or "").strip()
