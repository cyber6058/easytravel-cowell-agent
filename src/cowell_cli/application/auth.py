from __future__ import annotations

from typing import Protocol

from ..adapters.cowell.session_state import looks_like_login_page


class AuthGateway(Protocol):
    def get(self, path: str): ...


def auth_status(gateway: AuthGateway) -> dict[str, object]:
    """Probe only the registered Cowell home page for session validity."""
    response = gateway.get("/home.asp")
    return {
        "valid": not looks_like_login_page(response.text, str(response.url)),
        "probe": "home.asp",
    }
