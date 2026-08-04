from __future__ import annotations

from urllib.parse import urlparse

from ...errors import ReadOnlyPolicyError
from .operation_registry import OperationEffect, OperationRegistry


class ReadOnlyPolicy:
    def __init__(self, registry: OperationRegistry, allowed_origin: str) -> None:
        self._registry = registry
        parsed = urlparse(allowed_origin)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("allowed_origin must be an HTTPS URL")
        self._allowed_origin = f"{parsed.scheme}://{parsed.netloc}"

    def assert_operation_allowed(self, operation_name: str) -> None:
        operation = self._registry.get(operation_name)
        if operation is None:
            raise ReadOnlyPolicyError(
                "Unknown Cowell operation",
                {"operation": operation_name},
            )
        if operation.effect is not OperationEffect.READ:
            raise ReadOnlyPolicyError(
                "Cowell write operation is blocked in read-only mode",
                {"operation": operation_name, "effect": operation.effect.value},
            )

    def assert_request_allowed(self, method: str, url: str) -> str:
        parsed = urlparse(url)
        request_origin = f"{parsed.scheme}://{parsed.netloc}"
        if request_origin != self._allowed_origin:
            raise ReadOnlyPolicyError(
                "Request to an unapproved origin is blocked",
                {"method": method.upper(), "url": url},
            )
        operation = self._registry.match(method, url)
        if operation is None:
            raise ReadOnlyPolicyError(
                "Unregistered Cowell request is blocked",
                {"method": method.upper(), "url": url},
            )
        self.assert_operation_allowed(operation.name)
        return operation.name
