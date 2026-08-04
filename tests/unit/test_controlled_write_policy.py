from __future__ import annotations

import pytest

from cowell_cli.adapters.cowell.controlled_write_policy import (
    ControlledWritePolicy,
    ScopedTestWriteAuthorization,
    WriteRequestContract,
)
from cowell_cli.errors import WritePolicyError


@pytest.fixture
def contract() -> WriteRequestContract:
    return WriteRequestContract(
        name="groups.open.preview",
        method="POST",
        path="/C/N_crgroupcd.asp",
        exact_form_fields=frozenset(
            {"srcGRUP_CD", "SEL_LEAVDT_1", "SEL_LEAVDT_2", "OBJ_QT"}
        ),
        required_form_values={
            "srcGRUP_CD": "SDJ05JXY",
            "SEL_LEAVDT_1": "2026/07/28",
            "SEL_LEAVDT_2": "2026/07/28",
            "OBJ_QT": "4",
        },
        confirmation="create:SDJ05JXY:2026-07-28:abc123",
    )


@pytest.fixture
def policy(contract: WriteRequestContract) -> ControlledWritePolicy:
    return ControlledWritePolicy(
        allowed_origin="https://followme.voyage.com.tw:8443/",
        contract=contract,
    )


def valid_items() -> list[tuple[str, str]]:
    return [
        ("srcGRUP_CD", "SDJ05JXY"),
        ("SEL_LEAVDT_1", "2026/07/28"),
        ("SEL_LEAVDT_2", "2026/07/28"),
        ("OBJ_QT", "4"),
    ]


def test_allows_only_the_exact_confirmed_request(policy: ControlledWritePolicy):
    assert (
        policy.assert_request_allowed(
            method="POST",
            url="https://followme.voyage.com.tw:8443/C/N_crgroupcd.asp",
            form_items=valid_items(),
            confirmation="create:SDJ05JXY:2026-07-28:abc123",
        )
        == "groups.open.preview"
    )


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("GET", "https://followme.voyage.com.tw:8443/C/N_crgroupcd.asp"),
        ("POST", "https://evil.example/C/N_crgroupcd.asp"),
        ("POST", "https://followme.voyage.com.tw:8443/C/U_group.asp"),
        ("POST", "https://followme.voyage.com.tw:8443/C/N_crgroupcd.asp?save=1"),
    ],
)
def test_blocks_wrong_method_origin_path_or_query(
    policy: ControlledWritePolicy,
    method: str,
    url: str,
):
    with pytest.raises(WritePolicyError):
        policy.assert_request_allowed(
            method=method,
            url=url,
            form_items=valid_items(),
            confirmation="create:SDJ05JXY:2026-07-28:abc123",
        )


@pytest.mark.parametrize(
    "items",
    [
        valid_items() + [("unexpected", "1")],
        valid_items()[:-1],
        valid_items() + [("OBJ_QT", "4")],
        [
            ("srcGRUP_CD", "OTHER"),
            ("SEL_LEAVDT_1", "2026/07/28"),
            ("SEL_LEAVDT_2", "2026/07/28"),
            ("OBJ_QT", "4"),
        ],
    ],
)
def test_blocks_field_set_or_required_value_changes(
    policy: ControlledWritePolicy,
    items: list[tuple[str, str]],
):
    with pytest.raises(WritePolicyError):
        policy.assert_request_allowed(
            method="POST",
            url="https://followme.voyage.com.tw:8443/C/N_crgroupcd.asp",
            form_items=items,
            confirmation="create:SDJ05JXY:2026-07-28:abc123",
        )


def test_blocks_wrong_confirmation(policy: ControlledWritePolicy):
    with pytest.raises(WritePolicyError):
        policy.assert_request_allowed(
            method="POST",
            url="https://followme.voyage.com.tw:8443/C/N_crgroupcd.asp",
            form_items=valid_items(),
            confirmation="yes",
        )


def test_allows_only_the_exact_contract_query():
    contract = WriteRequestContract(
        name="groups.open.persist",
        method="POST",
        path="/C/N_crgroupcd_su.asp",
        exact_form_fields=frozenset({"myGRUP_CD2"}),
        required_form_values={"myGRUP_CD2": "SDJ05JXY260728A"},
        confirmation="create:SDJ05JXY260728A:abc123",
        exact_query="MGPUB_FG=N",
    )
    policy = ControlledWritePolicy(
        allowed_origin="https://followme.voyage.com.tw:8443/",
        contract=contract,
    )

    assert (
        policy.assert_request_allowed(
            method="POST",
            url="https://followme.voyage.com.tw:8443/C/N_crgroupcd_su.asp?MGPUB_FG=N",
            form_items=[("myGRUP_CD2", "SDJ05JXY260728A")],
            confirmation="create:SDJ05JXY260728A:abc123",
        )
        == "groups.open.persist"
    )
    with pytest.raises(WritePolicyError):
        policy.assert_request_allowed(
            method="POST",
            url="https://followme.voyage.com.tw:8443/C/N_crgroupcd_su.asp?MGPUB_FG=Y",
            form_items=[("myGRUP_CD2", "SDJ05JXY260728A")],
            confirmation="create:SDJ05JXY260728A:abc123",
        )


def test_allows_side_effect_get_only_with_exact_query_fields_and_values():
    contract = WriteRequestContract(
        name="groups.open.execute",
        method="GET",
        path="/C/N_crgroupcd_list.asp",
        exact_form_fields=frozenset(),
        required_form_values={},
        confirmation="create-execute:SDJ05JXY260728A:abc123",
        exact_query_fields=frozenset({"GRUP_CD", "LEAV_DT", "OBJ_QT"}),
        required_query_values={
            "GRUP_CD": "SDJ05JXY260728A",
            "LEAV_DT": "2026/7/28",
            "OBJ_QT": "4",
        },
    )
    policy = ControlledWritePolicy(
        allowed_origin="https://followme.voyage.com.tw:8443/",
        contract=contract,
    )
    url = (
        "https://followme.voyage.com.tw:8443/C/N_crgroupcd_list.asp"
        "?GRUP_CD=SDJ05JXY260728A&LEAV_DT=2026%2F7%2F28&OBJ_QT=4"
    )

    assert (
        policy.assert_request_allowed(
            method="GET",
            url=url,
            form_items=[],
            confirmation="create-execute:SDJ05JXY260728A:abc123",
        )
        == "groups.open.execute"
    )
    for changed_url in (
        url + "&save=1",
        url.replace("OBJ_QT=4", "OBJ_QT=5"),
        url.replace("&OBJ_QT=4", ""),
        url + "&OBJ_QT=4",
    ):
        with pytest.raises(WritePolicyError):
            policy.assert_request_allowed(
                method="GET",
                url=changed_url,
                form_items=[],
                confirmation="create-execute:SDJ05JXY260728A:abc123",
            )


def test_scoped_test_write_authorization_allows_only_exact_group_and_order():
    scope = ScopedTestWriteAuthorization(
        group_code="SDJ05JXY270304A",
        order_id="00040391",
    )

    scope.assert_target(
        group_code="sdj05jxy270304a",
        order_id="00040391",
    )
    with pytest.raises(WritePolicyError):
        scope.assert_target(
            group_code="OTHER270304A",
            order_id="00040391",
        )
    with pytest.raises(WritePolicyError):
        scope.assert_target(
            group_code="SDJ05JXY270304A",
            order_id="00040392",
        )


def test_allows_repeated_fields_only_when_exact_sequence_is_bound():
    contract = WriteRequestContract(
        name="room-save",
        method="POST",
        path="/D/U_gruproom_su.asp",
        exact_form_fields=frozenset({"GRUP_CD", "PAX_CNM"}),
        exact_form_sequence=("GRUP_CD", "PAX_CNM", "PAX_CNM"),
        required_form_values={"GRUP_CD": "TEST270304A"},
        confirmation="rooms:test",
    )
    policy = ControlledWritePolicy(
        allowed_origin="https://cowell.example",
        contract=contract,
    )

    assert policy.assert_request_allowed(
        method="POST",
        url="https://cowell.example/D/U_gruproom_su.asp",
        form_items=(
            ("GRUP_CD", "TEST270304A"),
            ("PAX_CNM", "one"),
            ("PAX_CNM", "two"),
        ),
        confirmation="rooms:test",
    ) == "room-save"

    with pytest.raises(WritePolicyError, match="order or multiplicity"):
        policy.assert_request_allowed(
            method="POST",
            url="https://cowell.example/D/U_gruproom_su.asp",
            form_items=(
                ("GRUP_CD", "TEST270304A"),
                ("PAX_CNM", "one"),
            ),
            confirmation="rooms:test",
        )
