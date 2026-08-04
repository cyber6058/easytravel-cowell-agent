from __future__ import annotations

from dataclasses import dataclass


MRZ_WEIGHTS = (7, 3, 1)


@dataclass(frozen=True, slots=True)
class PassportTraveler:
    record_id: str
    image_name: str
    passport_no: str
    id_no: str
    english_surname: str
    english_given: str
    sex: str
    chinese_surname: str
    chinese_given: str
    birth_date: str
    issue_date: str
    expiry_date: str
    birth_place: str
    nationality: str
    mobile: str = ""
    email: str = ""
    taiwan_compatriot_permit_no: str = ""
    issue_count: str = ""
    permit_start_date: str = ""
    permit_end_date: str = ""
    mrz_line1: str = ""
    mrz_line2: str = ""
    uncertainties: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MrzReading:
    document_type: str
    issuing_state: str
    surname: str
    given_names: str
    passport_no: str
    nationality: str
    birth_date_yymmdd: str
    sex: str
    expiry_date_yymmdd: str
    personal_no: str
    passport_check_valid: bool
    birth_date_check_valid: bool
    expiry_date_check_valid: bool
    personal_no_check_valid: bool
    composite_check_valid: bool

    @property
    def all_check_digits_valid(self) -> bool:
        return all(
            (
                self.passport_check_valid,
                self.birth_date_check_valid,
                self.expiry_date_check_valid,
                self.personal_no_check_valid,
                self.composite_check_valid,
            )
        )


def parse_td3_mrz(line1: str, line2: str) -> MrzReading:
    first = _normalize_line(line1)
    second = _normalize_line(line2)
    if len(first) != 44 or len(second) != 44:
        raise ValueError("TD3 MRZ lines must each contain exactly 44 characters")
    if any(
        not (character.isdigit() or character.isalpha() or character == "<")
        for character in first + second
    ):
        raise ValueError("MRZ contains unsupported characters")

    names = first[5:].split("<<", 1)
    surname = _mrz_name(names[0])
    given_names = _mrz_name(names[1] if len(names) == 2 else "")
    personal_field = second[28:42]
    return MrzReading(
        document_type=first[:2].replace("<", ""),
        issuing_state=first[2:5],
        surname=surname,
        given_names=given_names,
        passport_no=second[:9].replace("<", ""),
        nationality=second[10:13],
        birth_date_yymmdd=second[13:19],
        sex=second[20],
        expiry_date_yymmdd=second[21:27],
        personal_no=personal_field.rstrip("<"),
        passport_check_valid=_check_digit(second[:9], second[9]),
        birth_date_check_valid=_check_digit(second[13:19], second[19]),
        expiry_date_check_valid=_check_digit(second[21:27], second[27]),
        personal_no_check_valid=_check_digit(personal_field, second[42]),
        composite_check_valid=_check_digit(
            second[:10] + second[13:20] + second[21:43], second[43]
        ),
    )


def mrz_check_digit(value: str) -> str:
    total = 0
    for index, character in enumerate(value.upper()):
        total += _mrz_value(character) * MRZ_WEIGHTS[index % len(MRZ_WEIGHTS)]
    return str(total % 10)


def _check_digit(value: str, expected: str) -> bool:
    if expected == "<":
        expected = "0"
    return expected.isdigit() and mrz_check_digit(value) == expected


def _mrz_value(character: str) -> int:
    if character == "<":
        return 0
    if character.isdigit():
        return int(character)
    if "A" <= character <= "Z":
        return ord(character) - ord("A") + 10
    raise ValueError(f"Unsupported MRZ character: {character!r}")


def _normalize_line(value: str) -> str:
    return "".join(value.upper().split())


def _mrz_name(value: str) -> str:
    return " ".join(part for part in value.split("<") if part)
