# Milestone 0 (M0) Evidence Report: Setup, Feasibility, and Hardware

**Date:** 2026-10-22  
**Status:** COMPLETE & PASSED  
**Milestone Gate:** [GATE.md](GATE.md)  

---

## 1. Executive Summary

Milestone 0 established the complete foundation for SpeakerSync:
1. Created the clean layered architecture skeleton conforming to `ARCHITECTURE.md` §5.
2. Built a fresh Python 3.12 virtual environment (`.venv`) with all core and test dependencies.
3. Successfully installed `speakersync` in editable mode and verified the Typer CLI (`speakersync --help`, `speakersync version`, `speakersync devices`).
4. Surveyed and documented real hardware environment in [docs/HARDWARE.md](../../docs/HARDWARE.md).
5. Documented Windows 11 dual Bluetooth output feasibility research and citations in [docs/DECISIONS.md](../../docs/DECISIONS.md) (ADR 001).
6. Executed audio endpoint enumeration via PortAudio (`tools/list_devices.py`), confirming that both speakers (`HBTS001` and `Pure Sound Pro III`) appear as separate stereo output endpoints under Windows WASAPI.
7. Formulated the initial end-to-end latency budget in [latency_budget.md](latency_budget.md).
8. Passed all automated tests with 100% pass rate and clean `ruff` linting.

---

## 2. Real Hardware & Device Enumeration Evidence

### 2.1 Hardware Configuration
- **Host PC**: Dell Inc. Inspiron 14 5418, 8 GB RAM, Windows 11 Home Single Language (Build 26300, 64-bit).
- **Bluetooth Radio**: Intel(R) Wireless Bluetooth(R) (Intel AX201 combo module, Bluetooth 5.2).
- **FRONT Speaker**: `HBTS001` at ~0.5 m from listening position ($P_{front} \approx 1.46\text{ ms}$).
- **BACK Speaker**: `Pure Sound Pro III` at 1.5 m from listening position ($P_{back} \approx 4.37\text{ ms}$).
- **Acoustic Differential**: $\Delta P = P_{back} - P_{front} = +2.91\text{ ms}$.
- **Primary Calibration Microphone**: `Audiocular D07` USB Interface / ADC.
- **Backup Microphone**: `Intel(R) Smart Sound Technology for Digital Microphones` (integrated laptop array).

### 2.2 PortAudio WASAPI Endpoint Detection (from `devices.json`)
From [evidence/M0/devices.json](devices.json):
- **Index 18**: `Sound Bar (Pure Sound Pro III)` | Host API: `Windows WASAPI` | Channels: `0 in / 2 out` | Native Rate: `44100 Hz` | Low Latency: `3.0 ms` | High Latency: `10.0 ms`
- **Index 19**: `speaker (HBTS001)` | Host API: `Windows WASAPI` | Channels: `0 in / 2 out` | Native Rate: `44100 Hz` | Low Latency: `3.0 ms` | High Latency: `10.0 ms`
- **Index 24**: `Microphone (Audiocular D07)` | Host API: `Windows WASAPI` | Channels: `2 in / 0 out` | Native Rate: `48000 Hz` | Low Latency: `3.0 ms` | High Latency: `10.0 ms`
- **Index 22**: `Microphone Array (Intel Smart Sound)` | Host API: `Windows WASAPI` | Channels: `2 in / 0 out` | Native Rate: `48000 Hz` | Low Latency: `2.0 ms` | High Latency: `10.0 ms`

---

## 3. Feasibility Finding Summary

Windows 11 restricts system-level default playback to a single endpoint, but custom applications using PortAudio WASAPI Shared Mode can open two independent `sounddevice.OutputStream` streams simultaneously without driver conflict.

Because both speakers share the Intel AX201 2.4 GHz radio:
- Combined bandwidth (approx. 500–650 kbps) is well within Bluetooth 5.2 2 Mbps EDR limits.
- Packet retry delays (RF jitter) will be monitored via telemetry in M5/M8.
- Two documented fallbacks are established in ADR 001:
  - **Fallback A**: Secondary USB Bluetooth adapter to isolate BACK traffic.
  - **Fallback B**: Hybrid setup with FRONT connected via wired 3.5mm AUX (`Audiocular D07`) and BACK via Bluetooth.

---

## 4. Commands Executed and Verification Logs

### Virtual Environment Setup & Installation
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```
*Result*: Successfully installed 44 packages, including `numpy-2.5.4`, `scipy-1.18.1`, `sounddevice-0.5.6`, `soundfile-0.14.0`, `librosa-1.0.0`, `matplotlib-3.11.2`, `typer-0.27.3`, `pytest-9.1.1`, and `ruff-0.17.1`.

### Linting
```powershell
.\.venv\Scripts\ruff.exe check .
```
*Result*: `All checks passed!`

### Test Suite Execution
```powershell
.\.venv\Scripts\pytest.exe -v
```
*Result*:
```
tests/test_m0_skeleton.py::test_package_and_submodules_importable PASSED [ 20%]
tests/test_m0_skeleton.py::test_default_config_schema PASSED             [ 40%]
tests/test_m0_skeleton.py::test_param_registry PASSED                    [ 60%]
tests/test_m0_skeleton.py::test_device_enumeration_function PASSED       [ 80%]
tests/test_m0_skeleton.py::test_docs_exist PASSED                        [100%]
============================== 5 passed in 0.36s ==============================
```

### Device Listing Tool
```powershell
.\.venv\Scripts\python.exe tools/list_devices.py
```
*Result*: Enumerated 47 PortAudio devices, correctly detecting both `speaker (HBTS001)` and `Sound Bar (Pure Sound Pro III)` under WASAPI, and saved [devices.json](devices.json).

### CLI Verification
```powershell
.\.venv\Scripts\speakersync.exe --help
.\.venv\Scripts\speakersync.exe version
```
*Result*: CLI runs correctly with help text and reports `SpeakerSync v0.1.0`.
