from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass
from email.parser import BytesParser
from email.policy import default
from pathlib import PureWindowsPath
from typing import Any
from urllib.parse import parse_qsl, quote, quote_plus, urlencode, urlparse

from playwright.sync_api import BrowserContext, Page, Route, sync_playwright

from ...application.passenger_import import build_cowell_passenger_workbook
from ...application.rooming_workflow import PlannedRoomMember, RoomingPlan
from ...errors import ParseContractError, SourceUnavailableError, ValidationError, WritePolicyError
from ...infrastructure.session_lock import SessionLock
from ..cowell.controlled_write_policy import (
    ControlledWritePolicy,
    ScopedTestWriteAuthorization,
    WriteRequestContract,
)
from ..cowell.operation_registry import default_cowell_registry
from ..cowell.read_only_policy import ReadOnlyPolicy


@dataclass(frozen=True, slots=True)
class LiveRoomingPreview:
    group_code: str
    order_id: str
    passenger_count: int
    matched_passenger_count: int
    placeholder_count: int
    existing_room_count: int
    room_collisions: tuple[str, ...]
    suggested_room_offset: int | None
    available_cabins: tuple[CabinAvailability, ...]
    selected_cabins: tuple[CabinAvailability, ...]
    category_mismatch_count: int
    requires_passenger_import: bool
    ready_for_apply: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CabinAvailability:
    cabin: str
    passenger_slots: int


@dataclass(frozen=True, slots=True)
class _PassengerSlot:
    value: str
    cabin: str
    category: str
    is_placeholder: bool


@dataclass(frozen=True, slots=True)
class _PlaceholderSelection:
    slots: tuple[_PassengerSlot, ...]
    available_cabins: tuple[CabinAvailability, ...]
    selected_cabins: tuple[CabinAvailability, ...]
    category_mismatch_count: int
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LiveRoomingResult:
    group_code: str
    order_id: str
    plan_hash: str
    passenger_count: int
    passenger_imported: bool
    passenger_matches_verified: int
    room_assignments_verified: int
    room_notes_verified: int
    room_save_request_count: int
    already_applied: bool


class CowellLiveRooming:
    """Playwright-backed, fail-closed passenger import and room assignment."""

    def __init__(
        self,
        *,
        base_url: str,
        session_lock_path,
        cdp_http: str = "http://127.0.0.1:9333",
        authorization: ScopedTestWriteAuthorization,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._cdp_http = cdp_http
        self._authorization = authorization
        self._read_policy = ReadOnlyPolicy(default_cowell_registry(), self._base_url)
        self._session_lock_path = session_lock_path

    def preview(self, plan: RoomingPlan) -> LiveRoomingPreview:
        lock = SessionLock(self._session_lock_path).acquire()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.connect_over_cdp(
                    self._cdp_http, timeout=30_000
                )
                context = _first_context(browser.contexts)
                return self._preview_in_context(context, plan)
        finally:
            lock.release()

    def apply(self, plan: RoomingPlan, *, confirmation: str) -> LiveRoomingResult:
        if confirmation != plan.confirmation:
            raise WritePolicyError("Exact rooming plan confirmation is required")
        self._authorization.assert_target(
            group_code=plan.target_group_code,
            order_id=plan.target_order_id,
        )

        lock = SessionLock(self._session_lock_path).acquire()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.connect_over_cdp(
                    self._cdp_http, timeout=30_000
                )
                context = _first_context(browser.contexts)
                preview = self._preview_in_context(context, plan)
                if not preview.ready_for_apply:
                    raise ValidationError(
                        "live rooming preview is blocked",
                        {"blockers": list(preview.blockers)},
                    )

                imported = False
                if preview.requires_passenger_import:
                    self._import_passengers(context, plan, confirmation)
                    imported = True

                passenger_matches = self._verify_passenger_names(context, plan)
                room_result = self._apply_rooms(context, plan, confirmation)
                return LiveRoomingResult(
                    group_code=plan.target_group_code,
                    order_id=plan.target_order_id,
                    plan_hash=plan.plan_hash,
                    passenger_count=plan.passenger_count,
                    passenger_imported=imported,
                    passenger_matches_verified=passenger_matches,
                    room_assignments_verified=room_result[0],
                    room_notes_verified=room_result[1],
                    room_save_request_count=room_result[2],
                    already_applied=room_result[3],
                )
        finally:
            lock.release()

    def _preview_in_context(
        self, context: BrowserContext, plan: RoomingPlan
    ) -> LiveRoomingPreview:
        order_page = self._load_order_page(context, plan)
        try:
            matched = _count_name_matches(plan, order_page)
            passenger_slots = _passenger_slots(order_page)
            placeholders = tuple(slot for slot in passenger_slots if slot.is_placeholder)
            selection = _select_placeholder_slots(plan, placeholders)
        finally:
            order_page.close()

        source_members = _all_members(plan)
        occupied_by_other: set[str] = set()
        all_occupied: set[str] = set()
        order_ids = self._group_order_ids(context, plan.target_group_code)
        if plan.target_order_id not in order_ids:
            raise ValidationError("target order disappeared from the Cowell group")
        for order_id in order_ids:
            room_page = self._load_room_page_for_order(
                context,
                group_code=plan.target_group_code,
                order_id=order_id,
            )
            try:
                is_target_order = order_id == plan.target_order_id
                for locator in room_page.locator(
                    'input[name^="SEL_ROOM_NO_"]'
                ).all():
                    value = locator.input_value().strip()
                    if not value:
                        continue
                    all_occupied.add(value)
                    row_text = " ".join(
                        (
                            locator.locator("xpath=ancestor::tr[1]").inner_text()
                            or ""
                        ).split()
                    )
                    if not is_target_order or not any(
                        _room_row_matches_member(member, row_text)
                        for member in source_members
                    ):
                        occupied_by_other.add(value)
            finally:
                room_page.close()

        occupied_keys = {_room_number_key(value) for value in occupied_by_other}
        collisions = tuple(
            sorted(
                room.target_room_no
                for room in plan.rooms
                if _room_number_key(room.target_room_no) in occupied_keys
            )
        )
        blockers: list[str] = []
        requires_passenger_import, passenger_blocker = _classify_passenger_matches(
            matched, plan.passenger_count
        )
        if passenger_blocker:
            blockers.append(passenger_blocker)
        if matched == 0:
            blockers.extend(selection.blockers)
        if collisions:
            blockers.append("target room numbers are already used by other passengers")
        suggested = _suggest_room_offset(plan, occupied_by_other)
        return LiveRoomingPreview(
            group_code=plan.target_group_code,
            order_id=plan.target_order_id,
            passenger_count=plan.passenger_count,
            matched_passenger_count=matched,
            placeholder_count=len(placeholders),
            existing_room_count=len(all_occupied),
            room_collisions=collisions,
            suggested_room_offset=suggested,
            available_cabins=selection.available_cabins,
            selected_cabins=selection.selected_cabins,
            category_mismatch_count=selection.category_mismatch_count,
            requires_passenger_import=requires_passenger_import,
            ready_for_apply=not blockers,
            blockers=tuple(blockers),
            warnings=selection.warnings if matched == 0 else (),
        )

    def _import_passengers(
        self,
        context: BrowserContext,
        plan: RoomingPlan,
        confirmation: str,
    ) -> None:
        self._authorization.assert_target(
            group_code=plan.target_group_code,
            order_id=plan.target_order_id,
        )
        order_page = self._load_order_page(context, plan)
        try:
            placeholders = tuple(
                slot for slot in _passenger_slots(order_page) if slot.is_placeholder
            )
        finally:
            order_page.close()
        selection = _select_placeholder_slots(plan, placeholders)
        if selection.blockers or len(selection.slots) != plan.passenger_count:
            raise ValidationError(
                "placeholder passenger scope changed before import",
                {"blockers": list(selection.blockers)},
            )
        pax_values = [slot.value for slot in selection.slots]

        template_url = self._base_url + "/Docu/rect_file.xlsx"
        self._read_policy.assert_request_allowed("GET", template_url)
        template = context.request.get(template_url, timeout=30_000)
        if not template.ok:
            raise SourceUnavailableError(
                "SOURCE_UNAVAILABLE", "Cowell passenger template request failed"
            )
        rooming = _plan_as_rooming_list(plan)
        workbook = build_cowell_passenger_workbook(template.body(), rooming)

        import_url = self._base_url + "/B/received_recp2.asp?" + urlencode(
            {
                "OP_SQ": plan.target_order_id,
                "GRUP_CD": plan.target_group_code,
                "PAX_DR": ",".join(pax_values),
            },
            quote_via=quote,
        )
        import_page = self._load_exact_read_page(context, import_url)
        try:
            import_page.locator("input[name=mode][value=A]").check()
            import_page.locator("input[name=myFile1]").set_input_files(
                {
                    "name": "cowell_passengers.xlsx",
                    "mimeType": (
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                    "buffer": workbook.content,
                }
            )
            stage_url = self._base_url + "/include/get_xml.asp?" + urlencode(
                {
                    "fitem": "myFile1",
                    "author": "Cowell",
                    "faction": "/B/received_recp2_su.asp",
                    "TP": "",
                    "OP_SQ": plan.target_order_id,
                    "GRUP_CD": plan.target_group_code,
                    "PAX_DR": ",".join(pax_values),
                    "mode": "A",
                    "file_type": "xlsx",
                },
                quote_via=quote,
            )
            stage_contract = WriteRequestContract(
                name="passenger-import-stage",
                method="POST",
                path="/include/get_xml.asp",
                exact_query_fields=_query_field_names(stage_url),
                required_query_values={
                    "OP_SQ": plan.target_order_id,
                    "GRUP_CD": plan.target_group_code,
                    "PAX_DR": ",".join(pax_values),
                    "mode": "A",
                    "file_type": "xlsx",
                },
                exact_form_fields=frozenset(
                    {"FName", "OP_SQ", "SRC_OP_SQ", "mode", "myFile", "myFile1"}
                ),
                required_form_values={
                    "OP_SQ": plan.target_order_id,
                    "mode": "A",
                    "myFile1": workbook.sha256,
                },
                confirmation=confirmation,
            )
            stage_policy = ControlledWritePolicy(
                allowed_origin=self._base_url,
                contract=stage_contract,
            )
            allowed = [0]

            def stage_gate(route: Route, request) -> None:
                if request.method != "POST" or request.url != stage_url or allowed[0]:
                    route.abort()
                    return
                items = _multipart_contract_items(request, workbook.sha256)
                stage_policy.assert_request_allowed(
                    method=request.method,
                    url=request.url,
                    form_items=items,
                    confirmation=confirmation,
                )
                allowed[0] = 1
                route.continue_()

            import_page.route("**/*", stage_gate)
            with import_page.expect_response(
                lambda response: (
                    response.request.method == "POST" and response.url == stage_url
                ),
                timeout=30_000,
            ) as response_info:
                import_page.locator("form#FORM1").evaluate(
                    "(form, action) => { form.action = action; form.submit(); }",
                    stage_url,
                )
            stage_response = response_info.value
            stage_html = stage_response.body().decode("utf-8", errors="replace")
            import_page.unroute("**/*", stage_gate)
            if allowed[0] != 1 or stage_response.status != 200:
                raise SourceUnavailableError(
                    "SOURCE_UNAVAILABLE", "Cowell passenger staging failed"
                )
        finally:
            import_page.close()

        api_paths, stage_file, final_path = _parse_dynamic_import_chain(stage_html)
        self._run_import_chain(
            context,
            plan,
            confirmation,
            api_paths=api_paths,
            stage_file=stage_file,
            final_path=final_path,
        )
        self._verify_passenger_names(context, plan)

    def _run_import_chain(
        self,
        context: BrowserContext,
        plan: RoomingPlan,
        confirmation: str,
        *,
        api_paths: tuple[str, str],
        stage_file: str,
        final_path: str,
    ) -> None:
        body = "FileName=" + quote_plus(stage_file)
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
        }
        for index, api_path in enumerate(api_paths):
            contract = WriteRequestContract(
                name=f"passenger-import-api-{index + 1}",
                method="POST",
                path=api_path,
                exact_form_fields=frozenset({"FileName"}),
                required_form_values={"FileName": stage_file},
                confirmation=confirmation,
            )
            policy = ControlledWritePolicy(
                allowed_origin=self._base_url,
                contract=contract,
            )
            policy.assert_request_allowed(
                method="POST",
                url=self._base_url + api_path,
                form_items=(("FileName", stage_file),),
                confirmation=confirmation,
            )
            response = context.request.post(
                self._base_url + api_path,
                data=body,
                headers=headers,
                timeout=30_000,
            )
            if response.status != 200:
                raise SourceUnavailableError(
                    "SOURCE_UNAVAILABLE", "Cowell passenger conversion API failed"
                )
            if index == 0 and response.text().strip().lower() != "cowell":
                raise ValidationError("Cowell rejected the official workbook author")

        parsed_final = urlparse(final_path)
        query = dict(parse_qsl(parsed_final.query, keep_blank_values=True))
        final_contract = WriteRequestContract(
            name="passenger-import-apply",
            method="GET",
            path="/B/received_recp2_su.asp",
            exact_query_fields=frozenset(query),
            required_query_values={
                "OP_SQ": plan.target_order_id,
                "GRUP_CD": plan.target_group_code,
                "mode": "A",
                "file_type": "xlsx",
            },
            exact_form_fields=frozenset(),
            required_form_values={},
            confirmation=confirmation,
        )
        final_policy = ControlledWritePolicy(
            allowed_origin=self._base_url,
            contract=final_contract,
        )
        final_policy.assert_request_allowed(
            method="GET",
            url=self._base_url + final_path,
            form_items=(),
            confirmation=confirmation,
        )
        final_response = context.request.get(
            self._base_url + final_path, timeout=30_000
        )
        if final_response.status != 200:
            raise SourceUnavailableError(
                "SOURCE_UNAVAILABLE", "Cowell passenger apply failed"
            )

    def _apply_rooms(
        self,
        context: BrowserContext,
        plan: RoomingPlan,
        confirmation: str,
    ) -> tuple[int, int, int, bool]:
        dry_page = self._load_room_page(context, plan)
        try:
            already_applied = _room_values_match(dry_page, plan)
            if already_applied:
                return plan.passenger_count, plan.passenger_count, 0, True
            changed = _fill_room_plan(dry_page, plan)
            captured: list[tuple[str, bytes]] = []

            def dry_gate(route: Route, request) -> None:
                if request.method == "POST":
                    captured.append((request.url, request.post_data_buffer or b""))
                route.abort()

            save_url = self._base_url + "/D/U_gruproom_su.asp"
            dry_page.route("**/*", dry_gate)
            dry_page.locator("form#FORM1").evaluate(
                "(form, url) => { form.action = url; form.submit(); }", save_url
            )
            dry_page.wait_for_timeout(800)
            dry_page.unroute("**/*", dry_gate)
            if len(captured) != 1:
                raise ValidationError("expected exactly one intercepted room save")
            dry_url, dry_body = captured[0]
        finally:
            dry_page.close()

        fields = parse_qsl(dry_body.decode("ascii"), keep_blank_values=True)
        values = dict(fields)
        group_field = "GRUP_CD" if "GRUP_CD" in values else "grup_cd"
        order_field = "OP_SQ" if "OP_SQ" in values else "op_sq"
        self._authorization.assert_target(
            group_code=values.get(group_field, ""),
            order_id=values.get(order_field, ""),
        )
        required = {
            group_field: plan.target_group_code,
            order_field: plan.target_order_id,
        }
        required.update(changed)
        contract = WriteRequestContract(
            name="rooming-save",
            method="POST",
            path="/D/U_gruproom_su.asp",
            exact_form_fields=frozenset(name for name, _value in fields),
            exact_form_sequence=tuple(name for name, _value in fields),
            required_form_values=required,
            confirmation=confirmation,
        )
        policy = ControlledWritePolicy(
            allowed_origin=self._base_url,
            contract=contract,
        )
        policy.assert_request_allowed(
            method="POST",
            url=dry_url,
            form_items=fields,
            confirmation=confirmation,
        )

        live_page = self._load_room_page(context, plan)
        allowed = [0]
        try:
            if _fill_room_plan(live_page, plan) != changed:
                raise ValidationError("fresh Cowell room mapping changed after preview")

            def live_gate(route: Route, request) -> None:
                body = request.post_data_buffer or b""
                if (
                    request.method == "POST"
                    and request.url == dry_url
                    and body == dry_body
                    and allowed[0] == 0
                ):
                    policy.assert_request_allowed(
                        method=request.method,
                        url=request.url,
                        form_items=parse_qsl(body.decode("ascii"), keep_blank_values=True),
                        confirmation=confirmation,
                    )
                    allowed[0] = 1
                    route.continue_()
                else:
                    route.abort()

            live_page.route("**/*", live_gate)
            with live_page.expect_response(
                lambda response: (
                    response.request.method == "POST"
                    and urlparse(response.url).path == "/D/U_gruproom_su.asp"
                ),
                timeout=30_000,
            ):
                live_page.locator("form#FORM1").evaluate(
                    "(form, url) => { form.action = url; form.submit(); }", dry_url
                )
        finally:
            live_page.close()
        if allowed[0] != 1:
            raise ValidationError("room save was not released")

        verify = self._load_room_page(context, plan)
        try:
            assignments, notes = _verified_room_counts(verify, plan)
        finally:
            verify.close()
        if assignments != plan.passenger_count or notes != plan.passenger_count:
            raise ValidationError(
                "Cowell room read-back did not match the complete plan",
                {
                    "passenger_count": plan.passenger_count,
                    "room_assignments_verified": assignments,
                    "room_notes_verified": notes,
                },
            )
        return assignments, notes, allowed[0], False

    def _verify_passenger_names(
        self, context: BrowserContext, plan: RoomingPlan
    ) -> int:
        page = self._load_order_page(context, plan)
        try:
            matches = _count_name_matches(plan, page)
        finally:
            page.close()
        if matches != plan.passenger_count:
            raise ValidationError(
                "Cowell passenger read-back did not match the source",
                {"expected": plan.passenger_count, "matched": matches},
            )
        return matches

    def _load_order_page(self, context: BrowserContext, plan: RoomingPlan) -> Page:
        return self._load_exact_read_page(
            context,
            self._base_url
            + "/B/V_order_detail.asp?"
            + urlencode(
                {"OP_SQ": plan.target_order_id, "GRUP_CD": plan.target_group_code}
            ),
        )

    def _load_room_page(self, context: BrowserContext, plan: RoomingPlan) -> Page:
        return self._load_room_page_for_order(
            context,
            group_code=plan.target_group_code,
            order_id=plan.target_order_id,
        )

    def _load_room_page_for_order(
        self, context: BrowserContext, *, group_code: str, order_id: str
    ) -> Page:
        return self._load_exact_read_page(
            context,
            self._base_url
            + "/D/U_gruproom.asp?"
            + urlencode(
                {
                    "grup_cd": group_code,
                    "op_sq": order_id,
                    "pageSize": "500",
                }
            ),
        )

    def _group_order_ids(
        self, context: BrowserContext, group_code: str
    ) -> tuple[str, ...]:
        url = self._base_url + "/B/L_order_op_window.asp?" + urlencode(
            {"sel_grup_cd": group_code}
        )
        self._read_policy.assert_request_allowed("GET", url)
        response = context.request.get(url, timeout=30_000)
        if response.status != 200:
            raise SourceUnavailableError(
                "SOURCE_UNAVAILABLE", "Cowell group order-list request failed"
            )
        order_ids = _parse_group_order_ids(response.text())
        if not order_ids:
            raise ValidationError("Cowell group has no readable orders")
        return order_ids

    def _load_exact_read_page(self, context: BrowserContext, url: str) -> Page:
        self._read_policy.assert_request_allowed("GET", url)
        expected = _url_signature(url)
        page = context.new_page()

        def gate(route: Route, request) -> None:
            if request.method == "GET" and _url_signature(request.url) == expected:
                self._read_policy.assert_request_allowed("GET", request.url)
                route.continue_()
            else:
                route.abort()

        page.route("**/*", gate)
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            if response is None or response.status != 200:
                raise SourceUnavailableError(
                    "SOURCE_UNAVAILABLE", "Cowell read-only page request failed"
                )
        except BaseException:
            page.close()
            raise
        finally:
            if not page.is_closed():
                page.unroute("**/*", gate)
        return page


def _first_context(contexts: list[BrowserContext]) -> BrowserContext:
    if not contexts:
        raise SourceUnavailableError(
            "SESSION_EXPIRED", "Controlled Chrome has no authenticated context"
        )
    return contexts[0]


def _parse_group_order_ids(html: str) -> tuple[str, ...]:
    return tuple(sorted(set(re.findall(r"\b\d{8}\b", html))))


def _url_signature(url: str) -> tuple[str, str, str, tuple[tuple[str, str], ...]]:
    parsed = urlparse(url)
    return (
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        tuple(parse_qsl(parsed.query, keep_blank_values=True)),
    )


def _all_members(plan: RoomingPlan) -> list[PlannedRoomMember]:
    return [member for room in plan.rooms for member in room.members]


def _count_name_matches(plan: RoomingPlan, page: Page) -> int:
    rows = []
    for checkbox in page.locator('input[name="chkMe"]').all():
        row = checkbox.locator("xpath=ancestor::tr[1]")
        row_text = " ".join((row.inner_text() or "").split())
        cjk_text = "".join(
            character
            for character in row_text
            if "\u4e00" <= character <= "\u9fff"
        )
        title_text = " ".join(
            (field.get_attribute("title") or "")
            for field in row.locator("[title]").all()
        ).upper()
        rows.append((cjk_text, title_text))
    return _count_name_matches_from_rows(plan, tuple(rows))


def _count_name_matches_from_rows(
    plan: RoomingPlan,
    rows: tuple[tuple[str, str], ...],
) -> int:
    used_rows: set[int] = set()
    matches = 0
    for member in _all_members(plan):
        source_cjk = "".join(
            character
            for character in member.chinese_name
            if "\u4e00" <= character <= "\u9fff"
        )
        surname, given = member.english_name.split("/", 1)
        candidates = [
            index
            for index, (row_cjk, row_titles) in enumerate(rows)
            if source_cjk
            and source_cjk in row_cjk
            and surname.upper() in row_titles
            and given.upper() in row_titles
        ]
        if len(candidates) == 1 and candidates[0] not in used_rows:
            used_rows.add(candidates[0])
            matches += 1
    return matches


def _normalize_english(value: str) -> str:
    return "".join(character for character in value.upper() if character.isalpha())


def _query_field_names(url: str) -> frozenset[str]:
    return frozenset(
        name
        for name, _value in parse_qsl(
            urlparse(url).query,
            keep_blank_values=True,
        )
    )


def _placeholder_values(page: Page) -> list[str]:
    return [slot.value for slot in _passenger_slots(page) if slot.is_placeholder]


def _passenger_slots(page: Page) -> tuple[_PassengerSlot, ...]:
    slots: list[_PassengerSlot] = []
    for checkbox in page.locator("input[name=chkMe]").all():
        row = checkbox.locator("xpath=ancestor::tr[1]")
        row_text = " ".join((row.inner_text() or "").split())
        cells = [" ".join(text.split()) for text in row.locator("td").all_inner_texts()]
        if len(cells) <= 7:
            raise ParseContractError("Cowell passenger row structure changed")
        value = (checkbox.get_attribute("value") or "").strip()
        category = cells[5].strip()
        cabin = _normalize_cabin(cells[7])
        if not value or not category or not cabin:
            raise ParseContractError("Cowell passenger slot fields are incomplete")
        slots.append(
            _PassengerSlot(
                value=value,
                cabin=cabin,
                category=category,
                is_placeholder=bool(re.search(r"旅客\s*\d+", row_text)),
            )
        )
    return tuple(slots)


def _select_placeholder_slots(
    plan: RoomingPlan,
    slots: tuple[_PassengerSlot, ...],
) -> _PlaceholderSelection:
    placeholders = tuple(slot for slot in slots if slot.is_placeholder)
    available = _cabin_availability(placeholders)
    members = _all_members(plan)
    targets = [member.target_cabin for member in members]
    blockers: list[str] = []
    selected: list[_PassengerSlot] = []

    if any(targets):
        if not all(targets):
            blockers.append("cabin mapping does not cover every source passenger")
        else:
            unused = list(placeholders)
            for target in targets:
                match_index = next(
                    (
                        index
                        for index, slot in enumerate(unused)
                        if slot.cabin == target
                    ),
                    None,
                )
                if match_index is None:
                    blockers.append(
                        f"not enough placeholder passenger rows in cabin {target}"
                    )
                    break
                selected.append(unused.pop(match_index))
    else:
        cabins = {slot.cabin for slot in placeholders}
        if len(cabins) > 1:
            blockers.append(
                "multiple placeholder cabins require --cabin or --cabin-map"
            )
        elif len(placeholders) < plan.passenger_count:
            blockers.append("not enough placeholder passenger rows for import")
        else:
            selected.extend(placeholders[: plan.passenger_count])
            if cabins:
                cabin = next(iter(cabins))
                blockers.append(
                    f"single placeholder cabin {cabin} detected; rerun with "
                    f"--cabin {cabin} to bind the write plan"
                )

    if not blockers and len(selected) < plan.passenger_count:
        blockers.append("not enough placeholder passenger rows for import")

    mismatch_count = 0
    if not blockers:
        mismatch_count = sum(
            _category_kind(member.source_honorific)
            not in {None, _category_kind(slot.category)}
            and _category_kind(slot.category) is not None
            for member, slot in zip(members, selected, strict=True)
        )
    warnings = (
        (
            f"{mismatch_count} source age-category label(s) differ from Cowell; "
            "Cowell categories will be preserved"
        ),
    ) if mismatch_count else ()
    return _PlaceholderSelection(
        slots=tuple(selected),
        available_cabins=available,
        selected_cabins=_cabin_availability(tuple(selected)),
        category_mismatch_count=mismatch_count,
        blockers=tuple(dict.fromkeys(blockers)),
        warnings=warnings,
    )


def _classify_passenger_matches(
    matched: int, passenger_count: int
) -> tuple[bool, str | None]:
    if matched == 0:
        return True, None
    if matched == passenger_count:
        return False, None
    return False, "source passengers only partially match the Cowell order"


def _cabin_availability(
    slots: tuple[_PassengerSlot, ...],
) -> tuple[CabinAvailability, ...]:
    counts = Counter(slot.cabin for slot in slots)
    return tuple(
        CabinAvailability(cabin=cabin, passenger_slots=counts[cabin])
        for cabin in sorted(counts)
    )


def _normalize_cabin(value: str) -> str:
    return "".join(value.upper().split()).removesuffix("艙")


def _category_kind(value: str | None) -> str | None:
    normalized = "".join((value or "").upper().split())
    if normalized in {"MR", "MS", "MRS", "ADULT", "ADT", "成人", "大人"}:
        return "adult"
    if normalized in {"CHD", "CHILD", "兒童", "小孩", "小童"}:
        return "child"
    if normalized in {"INF", "INFANT", "嬰兒"}:
        return "infant"
    return None


def _suggest_room_offset(plan: RoomingPlan, occupied: set[str]) -> int | None:
    source_ids = [room.source_room_id for room in plan.rooms]
    if any(not value.isdigit() for value in source_ids):
        return None
    occupied_keys = {_room_number_key(value) for value in occupied}
    for offset in range(0, 1000):
        proposed = {
            str(int(value) + offset).zfill(len(value)) for value in source_ids
        }
        if not {_room_number_key(value) for value in proposed} & occupied_keys:
            return offset
    return None


def _room_number_key(value: str) -> tuple[str, str | int]:
    stripped = value.strip()
    if stripped.isdigit():
        return ("numeric", int(stripped))
    return ("text", stripped.casefold())


def _multipart_contract_items(request, workbook_sha256: str) -> tuple[tuple[str, str], ...]:
    content_type = request.headers.get("content-type", "")
    raw = request.post_data_buffer or b""
    message = BytesParser(policy=default).parsebytes(
        (f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n").encode()
        + raw
    )
    items: list[tuple[str, str]] = []
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        value = part.get_payload(decode=True) or b""
        if name == "myFile1":
            rendered = hashlib.sha256(value).hexdigest()
            if rendered != workbook_sha256:
                raise WritePolicyError("Passenger workbook changed before upload")
        else:
            rendered = value.decode(errors="replace")
        items.append((name, rendered))
    return tuple(items)


def _parse_dynamic_import_chain(html: str) -> tuple[tuple[str, str], str, str]:
    api_paths = list(
        dict.fromkeys(
            re.findall(
                r"(?:url:\s*|SendAJAX\()\s*[\"']"
                r"(/emnet/API/[A-Za-z0-9_-]+\.ashx)[\"']",
                html,
                re.I,
            )
        )
    )
    files = re.findall(r"FileName=([^\"';]+\.xlsx)", html, re.I)
    final_paths = re.findall(
        r"var\s+faction=[\"']([^\"']+received_recp2_su\.asp\?[^\"']+)[\"']",
        html,
        re.I,
    )
    if len(api_paths) != 2 or not files or len(final_paths) != 1:
        raise ValidationError("Cowell dynamic passenger-import chain changed")
    stage_file = files[0]
    filename = PureWindowsPath(stage_file).name
    if not re.fullmatch(r"[a-f0-9]{32}\.xlsx", filename, re.I):
        raise ValidationError("Cowell returned an unsafe temporary workbook name")
    stage_path = PureWindowsPath(stage_file)
    parent_parts = tuple(part.lower() for part in stage_path.parts[:-1])
    if (
        not stage_path.is_absolute()
        or not re.fullmatch(r"[A-Za-z]:", stage_path.drive)
        or ".." in stage_path.parts
        or "upload" not in parent_parts
    ):
        raise ValidationError("Cowell returned an unsafe temporary workbook path")

    final_path = final_paths[0].replace("&amp;", "&")
    parsed = urlparse(final_path)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    xml_name = query.get("XML_FILE_NM", "")
    if (
        parsed.path != "/B/received_recp2_su.asp"
        or PureWindowsPath(xml_name).stem.lower()
        != PureWindowsPath(filename).stem.lower()
    ):
        raise ValidationError("Cowell final passenger-import target changed")
    return (api_paths[0], api_paths[1]), stage_file, final_path


def _plan_member_rows(page: Page, plan: RoomingPlan) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    inputs = page.locator('input[name^="SEL_ROOM_NO_"]')
    for room_input in inputs.all():
        name = room_input.get_attribute("name") or ""
        index = name.rsplit("_", 1)[-1]
        row = room_input.locator("xpath=ancestor::tr[1]")
        row_text = " ".join((row.inner_text() or "").split())
        matches = [
            member
            for member in _all_members(plan)
            if _room_row_matches_member(member, row_text)
        ]
        if len(matches) == 1:
            member = matches[0]
            if member.chinese_name in rows:
                raise ValidationError("Cowell has duplicate passenger rows")
            rows[member.chinese_name] = (index, room_input)
    if len(rows) != plan.passenger_count:
        raise ValidationError(
            "Cowell room editor passenger set does not match the source",
            {"expected": plan.passenger_count, "matched": len(rows)},
        )
    return rows


def _room_row_matches_member(member: PlannedRoomMember, row_text: str) -> bool:
    source_cjk = "".join(
        character
        for character in member.chinese_name
        if "\u4e00" <= character <= "\u9fff"
    )
    row_cjk = "".join(
        character
        for character in row_text
        if "\u4e00" <= character <= "\u9fff"
    )
    return bool(source_cjk) and source_cjk in row_cjk


def _fill_room_plan(page: Page, plan: RoomingPlan) -> dict[str, str]:
    rows = _plan_member_rows(page, plan)
    changed: dict[str, str] = {}
    for room in plan.rooms:
        for member in room.members:
            index, room_input = rows[member.chinese_name]
            note = "/".join(member.notes)
            room_input.fill(room.target_room_no)
            page.locator(f'input[name="SEL_ROOM_SQ_{index}"]').fill(
                member.room_sequence
            )
            page.locator(f'input[name="SEL_ROOM_RK_{index}"]').fill(note)
            changed[f"SEL_ROOM_NO_{index}"] = room.target_room_no
            changed[f"SEL_ROOM_SQ_{index}"] = member.room_sequence
            changed[f"SEL_ROOM_RK_{index}"] = note
    return changed


def _verified_room_counts(page: Page, plan: RoomingPlan) -> tuple[int, int]:
    rows = _plan_member_rows(page, plan)
    assignments = 0
    notes = 0
    for room in plan.rooms:
        for member in room.members:
            index, room_input = rows[member.chinese_name]
            if (
                room_input.input_value() == room.target_room_no
                and page.locator(f'input[name="SEL_ROOM_SQ_{index}"]').input_value()
                == member.room_sequence
            ):
                assignments += 1
            if (
                page.locator(f'input[name="SEL_ROOM_RK_{index}"]').input_value()
                == "/".join(member.notes)
            ):
                notes += 1
    return assignments, notes


def _room_values_match(page: Page, plan: RoomingPlan) -> bool:
    try:
        assignments, notes = _verified_room_counts(page, plan)
    except ValidationError:
        return False
    return assignments == plan.passenger_count and notes == plan.passenger_count


def _plan_as_rooming_list(plan: RoomingPlan):
    from pathlib import Path

    from ...domain.rooming import RoomAssignment, RoomingList, RoomMember

    return RoomingList(
        source_path=Path(plan.source_path),
        source_format=Path(plan.source_path).suffix.lstrip("."),
        group_code=plan.source_group_code,
        rooms=tuple(
            RoomAssignment(
                room_id=room.source_room_id,
                source_room_label=room.source_room_id,
                occupancy=len(room.members),
                sleeping_occupancy=len(room.members),
                room_type=room.room_type,
                bed_preference=room.bed_preference,
                members=tuple(
                    RoomMember(
                        sequence=member.source_sequence,
                        chinese_name=member.chinese_name,
                        english_name=member.english_name,
                        honorific=None,
                        notes=member.notes,
                    )
                    for member in room.members
                ),
            )
            for room in plan.rooms
        ),
        warnings=plan.warnings,
    )
