import json
import re
from pathlib import Path

from cowell_cli import __version__


REPO = Path(__file__).parents[2]
PACKAGE = REPO / 'packaging' / 'easytravel-cowell-cli'
EXPECTED_VERSION = '0.3.2'


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def test_easytravel_release_version_is_consistent():
    quote = chr(34)
    assert __version__ == EXPECTED_VERSION
    assert f'version = {quote}{EXPECTED_VERSION}{quote}' in _read(
        REPO / 'pyproject.toml'
    )
    assert f'[string]$Version = {quote}{EXPECTED_VERSION}{quote}' in _read(
        REPO / 'scripts' / 'build_easytravel_cowell_package.ps1'
    )
    assert _read(PACKAGE / 'INSTALL.txt').splitlines()[0] == (
        f'EasyTravel Cowell CLI {EXPECTED_VERSION}'
    )
    plugin = json.loads(
        _read(
            PACKAGE
            / 'plugins'
            / 'easytravel-cowell-cli'
            / '.codex-plugin'
            / 'plugin.json'
        )
    )
    assert plugin['version'] == EXPECTED_VERSION


def test_easytravel_skill_requires_an_existing_order_and_never_runs_order_commands():
    skill = _read(
        PACKAGE
        / 'plugins'
        / 'easytravel-cowell-cli'
        / 'skills'
        / 'easytravel-cowell-cli'
        / 'SKILL.md'
    )

    assert re.search(r'^description: .?Use when', skill, re.MULTILINE)
    assert 'exact existing Cowell order ID' in skill
    assert 'Never create a group type, group, order, or passenger slot.' in skill
    assert re.search(r'cowell_cli\.cli\s+orders\b', skill) is None


def test_easytravel_package_uses_existing_order_only_app_readme():
    readme = _read(PACKAGE / 'APP-README.md')
    build = _read(REPO / 'scripts' / 'build_easytravel_cowell_package.ps1')

    assert re.search(r'OP\s+already\s+created', readme)
    assert re.search(r'cowell_cli\.cli\s+orders\b', readme) is None
    assert 'Join-Path $source ' + chr(34) + 'APP-README.md' + chr(34) in build
