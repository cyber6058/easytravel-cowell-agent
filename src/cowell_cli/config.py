from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from .errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class AppConfig:
    cowell_base_url: str
    browser_profile: Path
    database_path: Path


def default_config_path() -> Path:
    configured = os.environ.get("COWELL_CONFIG")
    if configured:
        return Path(os.path.expandvars(configured)).expanduser()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise ConfigurationError("LOCALAPPDATA is not configured")
    return Path(local_app_data) / "CowellCLI" / "config.toml"


def load_config(path: Path | None = None) -> AppConfig:
    config_path = path or default_config_path()
    if not config_path.is_file():
        raise ConfigurationError(
            "Cowell CLI configuration file was not found",
            {"path": str(config_path)},
        )
    try:
        with config_path.open("rb") as handle:
            raw = tomllib.load(handle)
    except tomllib.TOMLDecodeError as error:
        raise ConfigurationError(
            "Cowell CLI configuration is invalid TOML",
            {"path": str(config_path), "reason": str(error)},
        ) from error
    return parse_config(raw)


def parse_config(raw: Mapping[str, Any]) -> AppConfig:
    try:
        cowell = raw["cowell"]
        storage = raw["storage"]
        base_url = str(cowell["base_url"]).strip()
        browser_profile = _expand_path(str(cowell["browser_profile"]))
        database_path = _expand_path(str(storage["database"]))
    except (KeyError, TypeError, ValueError) as error:
        raise ConfigurationError(
            "Cowell CLI configuration is missing required fields"
        ) from error

    parsed_url = urlparse(base_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise ConfigurationError("cowell.base_url must be an HTTPS URL")

    return AppConfig(
        cowell_base_url=base_url.rstrip("/") + "/",
        browser_profile=browser_profile,
        database_path=database_path,
    )


def _expand_path(value: str) -> Path:
    return Path(os.path.expandvars(value)).expanduser()
