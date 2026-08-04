import json

from cowell_cli.application.passports import (
    load_passport_travelers,
    validate_passport_travelers,
)
from cowell_cli.domain.passport import mrz_check_digit, parse_td3_mrz


def _mrz() -> tuple[str, str]:
    line1 = "P<TWNCHEN<<TEST<USER".ljust(44, "<")
    passport = "T00000000"
    birth = "900101"
    expiry = "300101"
    personal = "X900000000".ljust(14, "<")
    line2_without_composite = (
        passport
        + mrz_check_digit(passport)
        + "TWN"
        + birth
        + mrz_check_digit(birth)
        + "M"
        + expiry
        + mrz_check_digit(expiry)
        + personal
        + mrz_check_digit(personal)
    )
    composite_source = (
        line2_without_composite[:10]
        + line2_without_composite[13:20]
        + line2_without_composite[21:43]
    )
    return line1, line2_without_composite + mrz_check_digit(composite_source)


def _record() -> dict:
    line1, line2 = _mrz()
    return {
        "recordId": "P001-01",
        "imageName": "P001-01.jpg",
        "passportNo": "T00000000",
        "idNo": "X900000000",
        "englishSurname": "CHEN",
        "englishGiven": "TEST USER",
        "sex": "M",
        "chineseSurname": "陳",
        "chineseGiven": "測試",
        "birthDate": "1990/01/01",
        "issueDate": "2020/01/01",
        "expiryDate": "2030/01/01",
        "birthPlace": "台灣",
        "nationality": "台灣",
        "mrzLine1": line1,
        "mrzLine2": line2,
    }


def test_td3_mrz_validates_all_check_digits():
    line1, line2 = _mrz()

    reading = parse_td3_mrz(line1, line2)

    assert reading.all_check_digits_valid is True
    assert reading.passport_no == "T00000000"
    assert reading.personal_no == "X900000000"
    assert reading.surname == "CHEN"
    assert reading.given_names == "TEST USER"


def test_passport_json_is_ready_only_when_printed_fields_match_valid_mrz(tmp_path):
    path = tmp_path / "travelers.json"
    path.write_text(json.dumps([_record()], ensure_ascii=False), encoding="utf-8")

    report = validate_passport_travelers(load_passport_travelers(path))

    assert report.record_count == 1
    assert report.ready_count == 1
    assert report.valid_mrz_count == 1
    assert report.ready_for_export is True


def test_check_digit_failure_and_question_mark_are_blocking(tmp_path):
    record = _record()
    record["mrzLine2"] = record["mrzLine2"][:-1] + (
        "0" if record["mrzLine2"][-1] != "0" else "1"
    )
    record["passportNo"] = "T0000?000"
    path = tmp_path / "travelers.json"
    path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")

    report = validate_passport_travelers(load_passport_travelers(path))

    assert report.ready_for_export is False
    assert report.valid_mrz_count == 0
    assert any("check digits failed" in item for item in report.records[0].errors)
    assert any("'?'" in item for item in report.records[0].errors)


def test_duplicate_passport_numbers_block_both_records(tmp_path):
    first = _record()
    second = {**first, "recordId": "P001-02"}
    path = tmp_path / "travelers.json"
    path.write_text(json.dumps([first, second], ensure_ascii=False), encoding="utf-8")

    report = validate_passport_travelers(load_passport_travelers(path))

    assert report.ready_count == 0
    assert all("duplicate passport number" in row.errors for row in report.records)
