"""Pytest configuration and shared fixtures for SpeakerSync."""

from pathlib import Path

import pytest
import yaml


@pytest.fixture
def repo_root() -> Path:
    """Return the absolute path to the repository root."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def default_config(repo_root: Path) -> dict:
    """Load and return the parsed config/default.yaml dictionary."""
    config_path = repo_root / "config" / "default.yaml"
    assert config_path.is_file(), f"Config file not found at {config_path}"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
