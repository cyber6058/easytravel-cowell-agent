from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable
from urllib.parse import parse_qsl, urlparse


class OperationEffect(StrEnum):
    READ = "read"
    WRITE = "write"


@dataclass(frozen=True, slots=True)
class OperationDefinition:
    name: str
    method: str
    path: str
    effect: OperationEffect
    allowed_query_params: frozenset[str] = frozenset()

    def matches(self, method: str, url: str) -> bool:
        parsed = urlparse(url)
        query_names = {name for name, _ in parse_qsl(parsed.query, keep_blank_values=True)}
        return (
            self.method == method.upper()
            and parsed.path == self.path
            and query_names.issubset(self.allowed_query_params)
        )


class OperationRegistry:
    def __init__(self, operations: Iterable[OperationDefinition] = ()) -> None:
        self._operations: dict[str, OperationDefinition] = {}
        for operation in operations:
            self.register(operation)

    def register(self, operation: OperationDefinition) -> None:
        if operation.name in self._operations:
            raise ValueError(f"Duplicate operation name: {operation.name}")
        self._operations[operation.name] = operation

    def get(self, name: str) -> OperationDefinition | None:
        return self._operations.get(name)

    def match(self, method: str, url: str) -> OperationDefinition | None:
        matches = [
            operation
            for operation in self._operations.values()
            if operation.matches(method, url)
        ]
        if len(matches) > 1:
            raise ValueError(f"Ambiguous operation registry match for {method} {url}")
        return matches[0] if matches else None


def default_cowell_registry() -> OperationRegistry:
    """The complete read allowlist for the EasyTravel product."""
    return OperationRegistry(
        [
            OperationDefinition(
                "auth.probe", "GET", "/home.asp", OperationEffect.READ
            ),
            OperationDefinition(
                "orders.detail",
                "GET",
                "/B/V_order_detail.asp",
                OperationEffect.READ,
                frozenset({"OP_SQ", "GRUP_CD"}),
            ),
            OperationDefinition(
                "orders.group_list",
                "GET",
                "/B/L_order_op_window.asp",
                OperationEffect.READ,
                frozenset({"sel_grup_cd"}),
            ),
            OperationDefinition(
                "orders.passenger_import_form",
                "GET",
                "/B/received_recp2.asp",
                OperationEffect.READ,
                frozenset({"OP_SQ", "GRUP_CD", "PAX_DR"}),
            ),
            OperationDefinition(
                "orders.passenger_import_template",
                "GET",
                "/Docu/rect_file.xlsx",
                OperationEffect.READ,
            ),
            OperationDefinition(
                "groups.room_edit_form",
                "GET",
                "/D/U_gruproom.asp",
                OperationEffect.READ,
                frozenset({"grup_cd", "op_sq", "pageSize"}),
            ),
        ]
    )
