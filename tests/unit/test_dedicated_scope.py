import argparse
import ast
import subprocess
import sys
from pathlib import Path

import pytest

from cowell_cli import cli
from cowell_cli.adapters.cowell.operation_registry import default_cowell_registry
from cowell_cli.adapters.cowell.read_only_policy import ReadOnlyPolicy
from cowell_cli.application.auth import auth_status
from cowell_cli.errors import ReadOnlyPolicyError


BASE_URL = "https://cowell.example/"


def test_cli_exposes_only_easytravel_top_level_commands():
    parser = cli.build_parser()
    subparsers = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    assert set(subparsers.choices) == {"doctor", "auth", "passports", "rooms"}


def test_cli_has_no_order_creation_payment_seat_or_report_commands():
    help_text = cli.build_parser().format_help()
    for forbidden in ("orders", "payments", "seats", "reports"):
        assert forbidden not in help_text


def test_travel_briefing_package_does_not_import_cowell_modules():
    package_root = Path(__file__).parents[2] / "src" / "travel_briefing"
    forbidden_imports = []
    for source_path in sorted(package_root.rglob("*.py")):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=source_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                continue
            forbidden_imports.extend(
                f"{source_path.name}:{module}"
                for module in modules
                if module == "cowell_cli" or module.startswith("cowell_cli.")
            )

    assert forbidden_imports == []


def test_documented_module_entrypoint_executes_cli():
    result = subprocess.run(
        [sys.executable, "-m", "cowell_cli.cli", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "doctor,auth,passports,rooms" in result.stdout


def test_registry_contains_exact_easytravel_read_allowlist():
    registry = default_cowell_registry()
    approved = {
        "auth.probe",
        "orders.detail",
        "orders.group_list",
        "orders.passenger_import_form",
        "orders.passenger_import_template",
        "groups.room_edit_form",
    }
    assert {name for name in approved if registry.get(name)} == approved
    assert registry.get("orders.create_form") is None
    assert registry.get("payments.sales_order_list") is None
    assert registry.get("seats.list_page") is None
    assert registry.get("reports.group_print") is None


@pytest.mark.parametrize(
    "path",
    [
        "/B/N_order.asp",
        "/B/L_order.asp",
        "/D/L_gcntl.asp",
        "/D/L_grup_p.asp",
    ],
)
def test_policy_blocks_out_of_scope_cowell_pages(path):
    policy = ReadOnlyPolicy(default_cowell_registry(), BASE_URL)
    with pytest.raises(ReadOnlyPolicyError):
        policy.assert_request_allowed("GET", BASE_URL.rstrip("/") + path)


def test_auth_status_uses_only_home_probe():
    class Response:
        text = "<html>ok</html>"
        url = BASE_URL + "home.asp"

    class Gateway:
        def __init__(self):
            self.paths = []

        def get(self, path):
            self.paths.append(path)
            return Response()

    gateway = Gateway()
    assert auth_status(gateway) == {"valid": True, "probe": "home.asp"}
    assert gateway.paths == ["/home.asp"]
