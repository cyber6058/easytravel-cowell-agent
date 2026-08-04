from cowell_cli.infrastructure.pii_scan import PiiScanReport, scan_text_for_pii


def test_clean_business_text_reports_no_hits():
    text = "團號 BKKVZ260710T 出發 2026年07月10日 總機位 60 可售 12 確認 48"

    report = scan_text_for_pii(text)

    assert report.clean is True
    assert report.total == 0
    assert report.counts == {}


def test_detects_each_pii_category():
    cases = {
        "email": "聯絡 guest@example.com 謝謝",
        "taiwan_mobile": "手機 0912-345-678",
        "taiwan_id": "身分證 A123456789",
        "pnr": "PNR ABC123",
        "bearer_token": "Authorization: Bearer abc.def.ghi",
        "private_key": "-----BEGIN PRIVATE KEY-----xyz-----END PRIVATE KEY-----",
        "credential_assignment": "token=super-secret-value",
    }

    for category, text in cases.items():
        report = scan_text_for_pii(text)
        assert report.counts.get(category, 0) >= 1, f"{category} not detected in {text!r}"
        assert report.clean is False


def test_counts_multiple_hits_of_same_category():
    text = "a@example.com b@example.org 王先生 c@example.net"

    report = scan_text_for_pii(text)

    assert report.counts["email"] == 3
    assert report.total == 3


def test_report_never_contains_matched_pii_values():
    # The report must be safe to print/log even over real PII: only counts leak out.
    text = "身分證 A123456789 手機 0912-345-678 email guest@example.com PNR ABC123"

    report = scan_text_for_pii(text)
    rendered = repr(report) + str(report.as_dict())

    for secret in ("A123456789", "0912-345-678", "guest@example.com", "ABC123"):
        assert secret not in rendered
    assert report.total >= 4


def test_bare_chinese_name_is_not_pattern_detectable():
    # Names have no reliable pattern; removing them is the sanitizer's structural
    # job (whole PII rows/tables), not this text scan's. Document that boundary.
    report = scan_text_for_pii("領隊 王小明 陪同 陳美麗")

    assert report.clean is True


def test_as_dict_shape_is_stable():
    report = PiiScanReport(counts={"email": 2}, total=2)

    assert report.as_dict() == {"clean": False, "total": 2, "counts": {"email": 2}}
