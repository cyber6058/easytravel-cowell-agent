import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

from travel_briefing import __version__


REPO = Path(__file__).parents[2]
PACKAGE = REPO / "packaging" / "easytravel-briefing-materials"
PLUGIN_NAME = "easytravel-briefing-materials"
EXPECTED_VERSION = "0.1.0"
REFERENCE_NAMES = {
    "audio-and-template.md",
    "cli.md",
    "narration-policy.md",
    "sources-and-op-review.md",
}
CANONICAL_SKILL = PACKAGE / "shared" / "SKILL.md"
CODEX_SKILL = (
    PACKAGE
    / "plugins"
    / PLUGIN_NAME
    / "skills"
    / PLUGIN_NAME
)
CLAUDE_SKILL = PACKAGE / "claude" / "skills" / PLUGIN_NAME


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_briefing_release_metadata_is_consistent():
    assert __version__ == EXPECTED_VERSION
    app_pyproject = _read(PACKAGE / "app-pyproject.toml")
    build = _read(REPO / "scripts" / "build_easytravel_briefing_package.ps1")
    assert f'version = "{EXPECTED_VERSION}"' in app_pyproject
    assert f'[string]$Version = "{EXPECTED_VERSION}"' in build
    assert _read(PACKAGE / "INSTALL.txt").splitlines()[0] == (
        f"EasyTravel Briefing Materials {EXPECTED_VERSION}"
    )

    plugin = json.loads(
        _read(PACKAGE / "plugins" / PLUGIN_NAME / ".codex-plugin" / "plugin.json")
    )
    assert plugin["name"] == PLUGIN_NAME
    assert plugin["version"] == EXPECTED_VERSION
    assert plugin["skills"] == "./skills/"

    marketplace = json.loads(
        _read(PACKAGE / ".agents" / "plugins" / "marketplace.json")
    )
    assert marketplace["name"] == "easytravel-briefing-local"
    assert marketplace["plugins"] == [
        {
            "name": PLUGIN_NAME,
            "source": {"source": "local", "path": f"./plugins/{PLUGIN_NAME}"},
            "policy": {
                "installation": "AVAILABLE",
                "authentication": "ON_INSTALL",
            },
            "category": "Productivity",
        }
    ]


def test_canonical_skill_and_tool_mirrors_are_byte_identical():
    mirrors = (CODEX_SKILL / "SKILL.md", CLAUDE_SKILL / "SKILL.md")
    canonical_hash = _sha256(CANONICAL_SKILL)
    assert all(_sha256(path) == canonical_hash for path in mirrors)

    canonical_references = PACKAGE / "shared" / "references"
    assert {path.name for path in canonical_references.iterdir()} == REFERENCE_NAMES
    for name in sorted(REFERENCE_NAMES):
        expected = _sha256(canonical_references / name)
        assert _sha256(CODEX_SKILL / "references" / name) == expected
        assert _sha256(CLAUDE_SKILL / "references" / name) == expected


def test_briefing_skill_enforces_the_reviewed_local_workflow():
    skill = _read(CANONICAL_SKILL)
    assert re.search(r"^description: >-\n  Use when", skill, re.MULTILINE)
    ordered_markers = (
        "briefing prepare",
        "briefing check-script",
        "briefing render",
        "--confirm-draft-id",
    )
    positions = [skill.index(marker) for marker in ordered_markers]
    assert positions == sorted(positions)
    for required_text in (
        "Never infer a missing fact",
        "Never send LINE messages",
        "Never use cloud TTS",
        "Microsoft Yating",
        "exact draft ID",
        "current explicit approval",
        "Do not retry an unknown result",
    ):
        assert required_text in skill
    assert "cowell_cli" not in skill


def test_one_generation_request_authorizes_one_bounded_local_draft():
    skill = _read(CANONICAL_SKILL)
    cli_reference = _read(
        PACKAGE / "shared" / "references" / "cli.md"
    )
    template_reference = _read(
        PACKAGE
        / "shared"
        / "references"
        / "audio-and-template.md"
    )

    for required_text in (
        "One-request DRAFT authorization",
        "supplied NewAmazing URL",
        "canonical LIST master",
        "owned hidden Word",
        "pdftoppm",
        "Microsoft Yating",
        "configured ffmpeg",
        "Do not ask for another approval",
        "new generation request",
    ):
        assert required_text in skill
    for excluded_gate in (
        "LIST calibration",
        "live JMA",
        "dependency installation",
        "CONFIRMED",
        "LINE",
        "upload",
        "deploy",
        "publish",
        "Cowell",
    ):
        assert excluded_gate in skill
    assert "5/6/7 template selection" not in skill
    assert "--template" not in cli_reference
    assert "master_path" in template_reference
    assert "calibration_manifest" in template_reference
    assert "every QA page" in template_reference
    assert "WAV, TXT, and SRT" in template_reference


def test_one_request_policy_is_recorded_in_project_rules_and_readme():
    agents = _read(REPO / "AGENTS.md")
    readme = _read(REPO / "README.md")

    assert "one local DRAFT" in agents
    assert "does not expand any Cowell" in agents
    assert "one local DRAFT" in readme
    assert "canonical LIST master" in readme


def test_briefing_app_and_installer_are_isolated_from_cowell():
    app_pyproject = _read(PACKAGE / "app-pyproject.toml")
    installer = _read(PACKAGE / "Install-EasyTravelBriefingMaterials.ps1")
    build = _read(REPO / "scripts" / "build_easytravel_briefing_package.ps1")

    assert 'include = ["travel_briefing*"]' in app_pyproject
    for forbidden in ("cowell_cli", "keyring", "playwright"):
        assert forbidden not in app_pyproject.casefold()
    assert 'Join-Path $repo "src\\travel_briefing"' in build
    assert 'Join-Path $repo "src"' not in build
    assert "synthesize_hanhan.ps1" not in build
    for forbidden in (
        "cowellbaseurl",
        "cowellcli",
        "browser-profile",
        "password",
        "cookie",
    ):
        assert forbidden not in installer.casefold()
    assert "EasyTravelBriefing" in installer
    assert "config.toml" in installer
    assert "if (-not (Test-Path $configPath))" in installer
    assert '$pythonPrefix = @("-3")' in installer
    assert '$pythonPrefix = @("-3.12")' not in installer
    assert installer.index("must not be blank") < installer.index(
        "New-Item -ItemType Directory -Force $installRoot"
    )


def test_supported_render_surface_exposes_only_yating():
    result = subprocess.run(
        [sys.executable, "-m", "travel_briefing.cli", "render", "--help"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "--tts {yating}" in result.stdout
    assert "hanhan" not in result.stdout.casefold()


def test_project_scope_adds_briefing_without_expanding_cowell_writes():
    agents = _read(REPO / "AGENTS.md")
    assert "## Briefing scope" in agents
    assert "NewAmazing" in agents
    assert "Microsoft Yating" in agents
    assert "Never add group creation, order creation, payments" in agents
    assert "Never send LINE" in agents


def test_briefing_package_build_contains_only_allowlisted_surfaces(tmp_path: Path):
    script = REPO / "scripts" / "build_easytravel_briefing_package.ps1"
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-DistRoot",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONUTF8": "1"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    package_zip = tmp_path / f"EasyTravel-Briefing-Materials-{EXPECTED_VERSION}.zip"
    assert package_zip.is_file()

    with zipfile.ZipFile(package_zip) as archive:
        names = {name.replace("\\", "/") for name in archive.namelist()}
        assert ".agents/plugins/marketplace.json" in names
        assert (
            "plugins/easytravel-briefing-materials/.codex-plugin/plugin.json"
            in names
        )
        assert "claude/skills/easytravel-briefing-materials/SKILL.md" in names
        assert "app/src/travel_briefing/__init__.py" in names
        assert "app/src/cowell_cli/__init__.py" not in names
        assert "app/config/briefing.example.toml" in names
        assert "app/config/config.example.toml" not in names
        assert "app/scripts/briefing/synthesize_yating.ps1" in names
        assert "app/scripts/briefing/synthesize_hanhan.ps1" not in names
        assert not any("__pycache__" in name or name.endswith(".pyc") for name in names)
        assert not any(
            Path(name).suffix.casefold()
            in {".doc", ".docx", ".pdf", ".png", ".wav", ".mp3", ".srt"}
            for name in names
        )
