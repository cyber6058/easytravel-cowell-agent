import pytest
import respx
from httpx import Response

from cowell_cli.adapters.cowell.http_gateway import CowellHttpGateway
from cowell_cli.adapters.cowell.operation_registry import default_cowell_registry
from cowell_cli.adapters.cowell.read_only_policy import ReadOnlyPolicy
from cowell_cli.adapters.cowell.session_import import ImportedSession
from cowell_cli.errors import ReadOnlyPolicyError


BASE_URL = "https://followme.voyage.com.tw:8443/"


def gateway() -> CowellHttpGateway:
    return CowellHttpGateway(
        base_url=BASE_URL,
        policy=ReadOnlyPolicy(default_cowell_registry(), BASE_URL),
        session=ImportedSession(cookies={"ASP.NET_SessionId": "secret"}),
    )


class FakeClock:
    def __init__(self, start: float = 100.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


DETAIL_PATH = "/B/V_order_detail.asp"
DETAIL_URL = BASE_URL.rstrip("/") + DETAIL_PATH
DETAIL_PARAMS = {"OP_SQ": "12345", "GRUP_CD": "TEST-GROUP"}


def _throttled_gateway(sleeps, clock, *, interval: float = 1.0) -> CowellHttpGateway:
    return CowellHttpGateway(
        base_url=BASE_URL,
        policy=ReadOnlyPolicy(default_cowell_registry(), BASE_URL),
        session=ImportedSession(cookies={"ASP.NET_SessionId": "secret"}),
        min_request_interval=interval,
        sleep=sleeps.append,
        monotonic=clock,
    )


@respx.mock
def test_gateway_throttles_sequential_requests():
    respx.get(DETAIL_URL).mock(
        return_value=Response(200, text="<html>ok</html>")
    )
    sleeps: list[float] = []
    with _throttled_gateway(sleeps, FakeClock()) as client:
        client.get(DETAIL_PATH, params=DETAIL_PARAMS)
        assert sleeps == []  # first request never waits
        client.get(DETAIL_PATH, params=DETAIL_PARAMS)

    assert sleeps == [1.0]  # second immediate request waits the full interval


@respx.mock
def test_gateway_skips_throttle_when_interval_already_elapsed():
    respx.get(DETAIL_URL).mock(
        return_value=Response(200, text="<html>ok</html>")
    )
    sleeps: list[float] = []
    clock = FakeClock()
    with _throttled_gateway(sleeps, clock) as client:
        client.get(DETAIL_PATH, params=DETAIL_PARAMS)
        clock.now += 1.5  # more than the interval passes between requests
        client.get(DETAIL_PATH, params=DETAIL_PARAMS)

    assert sleeps == []


@respx.mock
def test_gateway_blocked_request_does_not_throttle():
    route = respx.get(DETAIL_URL).mock(
        return_value=Response(200, text="<html>ok</html>")
    )
    sleeps: list[float] = []
    with _throttled_gateway(sleeps, FakeClock()) as client:
        with pytest.raises(ReadOnlyPolicyError):
            client.get(DETAIL_PATH, params={**DETAIL_PARAMS, "UPDSEAT": "x"})
        # The blocked request must not arm the throttle, so the next real
        # request is still treated as the first and does not wait.
        client.get(DETAIL_PATH, params=DETAIL_PARAMS)

    assert sleeps == []
    assert route.call_count == 1


@respx.mock
def test_gateway_throttle_can_be_disabled():
    respx.get(DETAIL_URL).mock(
        return_value=Response(200, text="<html>ok</html>")
    )
    sleeps: list[float] = []
    with _throttled_gateway(sleeps, FakeClock(), interval=0) as client:
        client.get(DETAIL_PATH, params=DETAIL_PARAMS)
        client.get(DETAIL_PATH, params=DETAIL_PARAMS)

    assert sleeps == []


@respx.mock
def test_gateway_sends_registered_get_with_session_cookie():
    route = respx.get(
        DETAIL_URL,
        params=DETAIL_PARAMS,
    ).mock(return_value=Response(200, text="<html>ok</html>"))

    with gateway() as client:
        response = client.get(
            DETAIL_PATH,
            params=DETAIL_PARAMS,
        )

    assert response.text == "<html>ok</html>"
    assert route.called
    assert route.calls.last.request.headers["cookie"] == "ASP.NET_SessionId=secret"


@respx.mock
def test_gateway_decodes_cowell_pages_as_utf8():
    respx.get(
        DETAIL_URL,
        params=DETAIL_PARAMS,
    ).mock(
        return_value=Response(
            200,
            content="團體損益明細表".encode("utf-8"),
            headers={"content-type": "text/html; charset=big5"},
        )
    )

    with gateway() as client:
        response = client.get(
            DETAIL_PATH,
            params=DETAIL_PARAMS,
        )

    assert response.text == "團體損益明細表"


@respx.mock
def test_gateway_blocks_unknown_query_before_network():
    route = respx.get(DETAIL_URL).mock(
        return_value=Response(200, text="<html>should not happen</html>")
    )

    with gateway() as client:
        with pytest.raises(ReadOnlyPolicyError):
            client.get(DETAIL_PATH, params={**DETAIL_PARAMS, "UPDSEAT": "x"})

    assert not route.called
