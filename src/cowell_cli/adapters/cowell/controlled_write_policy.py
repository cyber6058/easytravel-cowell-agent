from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence
from urllib.parse import parse_qsl, urlparse

from ...errors import WritePolicyError


@dataclass(frozen=True, slots=True)
class WriteRequestContract:
    name: str
    method: str
    path: str
    exact_form_fields: frozenset[str]
    required_form_values: Mapping[str, str]
    confirmation: str
    exact_query: str = ""
    exact_query_fields: frozenset[str] = frozenset()
    required_query_values: Mapping[str, str] = None  # type: ignore[assignment]
    exact_form_sequence: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("write contract name is required")
        if self.method.upper() not in {"GET", "POST"}:
            raise ValueError("controlled Cowell contracts must use GET or POST")
        if not self.path.startswith("/"):
            raise ValueError("write contract path must be absolute")
        if self.required_query_values is None:
            object.__setattr__(self, "required_query_values", {})
        if self.method.upper() == "POST" and not self.exact_form_fields:
            raise ValueError("POST contract form fields are required")
        if self.method.upper() == "GET" and self.exact_form_fields:
            raise ValueError("GET contract cannot require form fields")
        unknown_required = set(self.required_form_values) - self.exact_form_fields
        if unknown_required:
            raise ValueError("required form values must be in exact_form_fields")
        unknown_query = set(self.required_query_values) - self.exact_query_fields
        if unknown_query:
            raise ValueError("required query values must be in exact_query_fields")
        if not self.confirmation:
            raise ValueError("write contract confirmation is required")
        if self.exact_form_sequence is not None:
            if set(self.exact_form_sequence) != set(self.exact_form_fields):
                raise ValueError("exact_form_sequence must cover exact_form_fields")


@dataclass(frozen=True, slots=True)
class ScopedTestWriteAuthorization:
    """Standing authorization for one explicitly designated test target."""

    group_code: str
    order_id: str

    def __post_init__(self) -> None:
        if not self.group_code.strip() or not self.order_id.strip():
            raise ValueError("test write scope requires group_code and order_id")

    def assert_target(self, *, group_code: str, order_id: str) -> None:
        if group_code.strip().upper() != self.group_code.strip().upper():
            raise WritePolicyError(
                "Cowell write targets a group outside the authorized test scope"
            )
        if order_id.strip() != self.order_id.strip():
            raise WritePolicyError(
                "Cowell write targets an order outside the authorized test scope"
            )


class ControlledWritePolicy:
    """Fail-closed policy for one exact, explicitly confirmed Cowell POST."""

    def __init__(
        self,
        *,
        allowed_origin: str,
        contract: WriteRequestContract,
    ) -> None:
        parsed = urlparse(allowed_origin)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("allowed_origin must be an HTTPS URL")
        self._allowed_origin = f"{parsed.scheme}://{parsed.netloc}"
        self._contract = contract

    def assert_request_allowed(
        self,
        *,
        method: str,
        url: str,
        form_items: Sequence[tuple[str, str]],
        confirmation: str,
    ) -> str:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin != self._allowed_origin:
            raise WritePolicyError("Cowell write origin is not approved")
        if method.upper() != self._contract.method.upper():
            raise WritePolicyError("Cowell write method is not approved")
        if parsed.path != self._contract.path:
            raise WritePolicyError("Cowell write path or query is not approved")
        query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
        if len({name for name, _value in query_pairs}) != len(query_pairs):
            raise WritePolicyError("Duplicate Cowell query fields are blocked")
        query_items = dict(query_pairs)
        if self._contract.exact_query_fields:
            if set(query_items) != set(self._contract.exact_query_fields):
                raise WritePolicyError("Cowell query field set is not approved")
            changed_query = sorted(
                name
                for name, expected in self._contract.required_query_values.items()
                if query_items.get(name) != expected
            )
            if changed_query:
                raise WritePolicyError(
                    "Cowell required query values changed",
                    {"changed_query_fields": changed_query},
                )
        elif parsed.query != self._contract.exact_query:
            raise WritePolicyError("Cowell write query is not approved")
        if confirmation != self._contract.confirmation:
            raise WritePolicyError("Exact Cowell write confirmation is required")

        if self._contract.method.upper() == "GET":
            if form_items:
                raise WritePolicyError("GET contract cannot carry form fields")
            return self._contract.name

        names = [name for name, _value in form_items]
        if self._contract.exact_form_sequence is None:
            if len(names) != len(set(names)):
                raise WritePolicyError("Duplicate Cowell form fields are blocked")
        elif tuple(names) != self._contract.exact_form_sequence:
            raise WritePolicyError("Cowell form field order or multiplicity changed")
        actual_fields = set(names)
        expected_fields = set(self._contract.exact_form_fields)
        if actual_fields != expected_fields:
            raise WritePolicyError(
                "Cowell form field set does not match the approved contract",
                {
                    "missing_fields": sorted(expected_fields - actual_fields),
                    "extra_fields": sorted(actual_fields - expected_fields),
                },
            )

        values = dict(form_items)
        repeated_required = sorted(
            name
            for name in self._contract.required_form_values
            if names.count(name) != 1
        )
        if repeated_required:
            raise WritePolicyError(
                "Cowell required form fields must occur exactly once",
                {"repeated_required_fields": repeated_required},
            )
        changed_required = sorted(
            name
            for name, expected in self._contract.required_form_values.items()
            if values.get(name) != expected
        )
        if changed_required:
            raise WritePolicyError(
                "Cowell required form values changed after preview",
                {"changed_fields": changed_required},
            )
        return self._contract.name
