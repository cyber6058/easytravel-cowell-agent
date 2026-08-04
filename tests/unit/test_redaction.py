from cowell_cli.infrastructure.redaction import REDACTED, redact, redact_text


def test_redacts_sensitive_keys_recursively():
    source = {
        "password": "secret",
        "nested": {
            "session_id": "abc",
            "safe": "visible",
        },
    }

    assert redact(source) == {
        "password": REDACTED,
        "nested": {
            "session_id": REDACTED,
            "safe": "visible",
        },
    }


def test_session_status_mapping_keeps_public_fields_but_redacts_nested_secret():
    source = {
        "session": {
            "valid": True,
            "probe": "home.asp",
            "session_id": "secret",
        }
    }

    assert redact(source) == {
        "session": {
            "valid": True,
            "probe": "home.asp",
            "session_id": REDACTED,
        }
    }


def test_redacts_tokens_email_phone_and_taiwan_id():
    text = (
        "Authorization: Bearer abc.def "
        "user@example.com 0912-345-678 A123456789 "
        "ASP.NET_SessionId=secret"
    )
    output = redact_text(text)

    assert "abc.def" not in output
    assert "user@example.com" not in output
    assert "0912-345-678" not in output
    assert "A123456789" not in output
    assert "secret" not in output


def test_does_not_change_normal_business_values():
    assert redact_text("KIX 2026-07-01 capacity 20") == "KIX 2026-07-01 capacity 20"
