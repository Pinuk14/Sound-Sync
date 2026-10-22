"""Tests for M0 Setup, Architecture, and Device Enumeration."""

from pathlib import Path


def test_package_and_submodules_importable():
    """Verify that the package and all layered submodules can be imported cleanly."""
    import speakersync
    import speakersync.calib
    import speakersync.control
    import speakersync.control.params
    import speakersync.devices
    import speakersync.engine
    import speakersync.lab
    import speakersync.player
    import speakersync.timing
    import speakersync.ui

    assert speakersync.__version__ == "0.1.0"


def test_default_config_schema(default_config: dict):
    """Verify that config/default.yaml contains all required architecture keys."""
    required_keys = [
        "profile",
        "devices",
        "latency",
        "mode",
        "immersion",
        "levels",
        "router",
    ]
    for key in required_keys:
        assert key in default_config, f"Missing key: {key} in config/default.yaml"

    # Validate devices block
    assert "front" in default_config["devices"]
    assert "back" in default_config["devices"]
    assert "match" in default_config["devices"]["front"]
    assert "distance_m" in default_config["devices"]["front"]
    assert "match" in default_config["devices"]["back"]
    assert "distance_m" in default_config["devices"]["back"]

    # Validate latency block
    latency = default_config["latency"]
    assert "auto" in latency and "manual" in latency
    assert "trim_ms" in latency["manual"]
    assert "global_av_offset_ms" in latency["manual"]

    # Validate router block
    router = default_config["router"]
    assert "hop_ms" in router
    assert "lookahead_ms" in router
    assert "event" in router
    assert "dialogue_guard" in router


def test_param_registry():
    """Verify master parameter registry definitions and constraints."""
    from speakersync.control.params import PARAMETER_REGISTRY

    expected_params = [
        "latency.front.trim_ms",
        "latency.back.trim_ms",
        "latency.global_av_offset_ms",
        "router.immersion",
        "router.dialogue_guard",
        "levels.front_trim_db",
        "levels.back_trim_db",
        "levels.back_cap_dbfs",
    ]
    for param in expected_params:
        assert param in PARAMETER_REGISTRY, f"Missing parameter {param} in registry"
        spec = PARAMETER_REGISTRY[param]
        assert spec.name == param
        if spec.min_value is not None and spec.max_value is not None:
            assert spec.min_value <= spec.default <= spec.max_value


def test_device_enumeration_function(repo_root: Path):
    """Verify tools/list_devices.py can enumerate devices and returns a valid data structure."""
    import sys

    # Add tools to sys.path
    tools_dir = str(repo_root / "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)

    import list_devices

    data = list_devices.get_devices_data()
    assert "devices" in data
    assert "host_apis" in data
    assert len(data["host_apis"]) > 0
    assert len(data["devices"]) > 0


def test_docs_exist(repo_root: Path):
    """Verify required M0 documentation files are present in docs/."""
    docs_dir = repo_root / "docs"
    assert (docs_dir / "ARCHITECTURE.md").is_file()
    assert (docs_dir / "HARDWARE.md").is_file()
    assert (docs_dir / "DECISIONS.md").is_file()
