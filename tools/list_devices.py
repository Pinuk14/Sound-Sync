#!/usr/bin/env python3
"""List all audio output and input devices via PortAudio.

Reports index, name, host API, channels, default sample rate, and default latencies.
Outputs formatted table to console and saves raw device details to evidence/M0/devices.json.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import sounddevice as sd


def get_devices_data() -> Dict[str, Any]:
    """Query sounddevice for all devices and host APIs."""
    raw_devices = sd.query_devices()
    host_apis = sd.query_hostapis()
    default_input, default_output = sd.default.device

    devices_list: List[Dict[str, Any]] = []
    for idx, dev in enumerate(raw_devices):
        host_api_idx = dev.get("hostapi", -1)
        host_api_name = (
            host_apis[host_api_idx]["name"]
            if 0 <= host_api_idx < len(host_apis)
            else "Unknown"
        )

        dev_dict = {
            "index": idx,
            "name": dev["name"],
            "host_api": host_api_name,
            "host_api_index": host_api_idx,
            "max_input_channels": dev["max_input_channels"],
            "max_output_channels": dev["max_output_channels"],
            "default_samplerate": dev["default_samplerate"],
            "default_low_input_latency": dev.get("default_low_input_latency", 0.0),
            "default_low_output_latency": dev.get("default_low_output_latency", 0.0),
            "default_high_input_latency": dev.get("default_high_input_latency", 0.0),
            "default_high_output_latency": dev.get("default_high_output_latency", 0.0),
            "is_default_input": (idx == default_input),
            "is_default_output": (idx == default_output),
        }
        devices_list.append(dev_dict)

    return {
        "default_input_index": default_input,
        "default_output_index": default_output,
        "devices": devices_list,
        "host_apis": [api["name"] for api in host_apis],
    }


def print_devices_table(data: Dict[str, Any]) -> None:
    """Print devices in a clean tabular view."""
    print("=" * 110)
    print("SpeakerSync Audio Device Enumeration (PortAudio / sounddevice)")
    print("=" * 110)
    print(
        f"{'Idx':<4} | {'Name':<40} | {'Host API':<12} | {'In/Out':<7} | "
        f"{'Rate (Hz)':<10} | {'Low Lat (ms)':<13} | {'High Lat (ms)':<13}"
    )
    print("-" * 110)

    for dev in data["devices"]:
        in_out = f"{dev['max_input_channels']} / {dev['max_output_channels']}"
        low_lat = (
            f"{dev['default_low_output_latency'] * 1000:6.1f} (out)"
            if dev["max_output_channels"] > 0
            else f"{dev['default_low_input_latency'] * 1000:6.1f} (in)"
        )
        high_lat = (
            f"{dev['default_high_output_latency'] * 1000:6.1f} (out)"
            if dev["max_output_channels"] > 0
            else f"{dev['default_high_input_latency'] * 1000:6.1f} (in)"
        )
        tag = ""
        if dev["is_default_output"]:
            tag = " [DEFAULT OUT]"
        elif dev["is_default_input"]:
            tag = " [DEFAULT IN]"

        name_display = (dev["name"][:37] + "...") if len(dev["name"]) > 40 else dev["name"]
        print(
            f"{dev['index']:<4} | {name_display:<40} | {dev['host_api']:<12} | {in_out:<7} | "
            f"{int(dev['default_samplerate']):<10} | {low_lat:<13} | {high_lat:<13}{tag}"
        )

    print("=" * 110)


def main() -> None:
    parser = argparse.ArgumentParser(description="Enumerate PortAudio audio devices.")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("evidence/M0/devices.json"),
        help="Path to save raw devices JSON",
    )
    args = parser.parse_args()

    data = get_devices_data()
    print_devices_table(data)

    # Save output to evidence
    out_path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"\n[INFO] Device details successfully saved to {out_path.resolve()}")


if __name__ == "__main__":
    main()
