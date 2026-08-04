from pathlib import Path

import pytest

from cowell_cli.config import parse_config
from cowell_cli.errors import ConfigurationError


def valid_config():
    return {
        "cowell": {
            "base_url": "https://cowell.example/",
            "browser_profile": r"C:\profiles\cowell",
        },
        "storage": {"database": r"C:\data\cowell.db"},
    }


def test_parse_config_normalizes_values():
    config = parse_config(valid_config())

    assert config.cowell_base_url == "https://cowell.example/"
    assert config.browser_profile == Path(r"C:\profiles\cowell")
    assert config.database_path == Path(r"C:\data\cowell.db")


def test_parse_config_rejects_non_https_url():
    raw = valid_config()
    raw["cowell"]["base_url"] = "http://cowell.example/"

    with pytest.raises(ConfigurationError) as error:
        parse_config(raw)

    assert "HTTPS" in error.value.message


def test_parse_config_requires_storage():
    raw = valid_config()
    del raw["storage"]

    with pytest.raises(ConfigurationError):
        parse_config(raw)
