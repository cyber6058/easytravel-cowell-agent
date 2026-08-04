import json
import struct
import urllib.error

import pytest

from cowell_cli.adapters.cowell import session_import
from cowell_cli.errors import SourceUnavailableError


class FakeSocket:
    def __init__(self, message: bytes):
        self.message = message
        self.sent = b""
        self.closed = False

    def sendall(self, payload: bytes) -> None:
        self.sent += payload

    def recv(self, length: int) -> bytes:
        chunk = self.message[:length]
        self.message = self.message[length:]
        return chunk

    def close(self) -> None:
        self.closed = True


def websocket_frame(payload: dict) -> bytes:
    encoded = json.dumps(payload).encode()
    if len(encoded) < 126:
        return bytes([0x81, len(encoded)]) + encoded
    return bytes([0x81, 126]) + struct.pack(">H", len(encoded)) + encoded


def test_import_cdp_session_filters_cookies_by_domain(monkeypatch):
    fake_socket = FakeSocket(
        websocket_frame(
            {
                "id": 1,
                "result": {
                    "cookies": [
                        {
                            "name": "ASP.NET_SessionId",
                            "value": "secret",
                            "domain": ".followme.voyage.com.tw",
                        },
                        {
                            "name": "other",
                            "value": "ignore",
                            "domain": ".example.test",
                        },
                    ]
                },
            }
        )
    )
    monkeypatch.setattr(session_import, "_ws_url", lambda _cdp_http: "ws://example/devtools")
    monkeypatch.setattr(session_import, "_connect", lambda _url: fake_socket)

    imported = session_import.import_cdp_session(domain_match="voyage.com.tw")

    assert imported.cookies == {"ASP.NET_SessionId": "secret"}
    assert fake_socket.closed


def test_unavailable_controlled_chrome_has_an_actionable_source_error(monkeypatch):
    monkeypatch.setattr(
        session_import,
        "_ws_url",
        lambda _cdp_http: (_ for _ in ()).throw(urllib.error.URLError("offline")),
    )

    with pytest.raises(SourceUnavailableError) as caught:
        session_import.import_cdp_session()

    assert caught.value.code == "SOURCE_UNAVAILABLE"
    assert "start it and log in" in caught.value.message
