"""Recognise a Cowell response that is really an expired-session redirect.

Cowell does not answer an expired session with a status code. It answers with
the login page, or with a script that navigates to it, under the URL that was
requested. Every screen parser must therefore ask this question before it tries
to read a record, or an expired session parses as an empty result.

The markers here were derived from live seat work, not from payment discovery.
"""
from __future__ import annotations


LOGIN_PATHS = ("/default_standard.asp", "/default.asp")


def looks_like_login_page(body: str, url: str) -> bool:
    lower_body = body.lower()
    lower_url = url.lower()
    return (
        any(lower_url.endswith(path) for path in LOGIN_PATHS)
        or 'location.href="/default.asp"' in lower_body
        or "location.href='/default.asp'" in lower_body
        or 'top.location.href="/default.asp"' in lower_body
        or "top.location.href='/default.asp'" in lower_body
        or ('name="login"' in lower_body and 'name="pwd"' in lower_body)
    )
