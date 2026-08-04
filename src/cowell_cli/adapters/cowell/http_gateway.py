from __future__ import annotations

import time
from collections.abc import Callable
from urllib.parse import urljoin

import httpx

from ...errors import SourceUnavailableError
from .read_only_policy import ReadOnlyPolicy
from .session_import import ImportedSession


class CowellHttpGateway:
    def __init__(
        self,
        *,
        base_url: str,
        policy: ReadOnlyPolicy,
        session: ImportedSession,
        timeout: float = 30.0,
        min_request_interval: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        lock: object | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/") + "/"
        self._policy = policy
        # Optional single-session lock; released on close() so the whole Cowell
        # session (gateway lifetime) is guarded, not just one request.
        self._lock = lock
        # Be a good citizen against the production Cowell ERP: sequential
        # requests, at least `min_request_interval` seconds apart (DESIGN §5).
        self._min_request_interval = min_request_interval
        self._sleep = sleep
        self._monotonic = monotonic
        self._last_request_at: float | None = None
        self._client = httpx.Client(
            base_url=self._base_url,
            cookies=session.cookies,
            timeout=timeout,
            follow_redirects=True,
        )

    def _throttle(self) -> None:
        if self._min_request_interval <= 0:
            return
        if self._last_request_at is not None:
            wait = self._min_request_interval - (
                self._monotonic() - self._last_request_at
            )
            if wait > 0:
                self._sleep(wait)
        self._last_request_at = self._monotonic()

    def close(self) -> None:
        self._client.close()
        if self._lock is not None:
            self._lock.release()

    def __enter__(self) -> "CowellHttpGateway":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def get(self, path: str, *, params: dict[str, str] | None = None) -> httpx.Response:
        request = self._client.build_request("GET", path, params=params)
        self._policy.assert_request_allowed(request.method, str(request.url))
        self._throttle()
        try:
            response = self._client.send(request)
            response.raise_for_status()
            response.encoding = "utf-8"
        except httpx.HTTPError as error:
            raise SourceUnavailableError(
                "SOURCE_UNAVAILABLE",
                "Cowell source request failed",
                {"url": str(request.url), "reason": str(error)},
            ) from error
        return response

    def absolute_url(self, path: str) -> str:
        return urljoin(self._base_url, path.lstrip("/"))
