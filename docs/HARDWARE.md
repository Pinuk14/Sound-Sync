# SpeakerSync Hardware Specification & Environment Profile

**Document Status:** Complete (M0 Verified)  
**Date:** 2026-10-22  
**Target Environment:** Windows 11 Desktop / Laptop  

---

## 1. Host System

| Component | Specification | Source / Detection Method |
|---|---|---|
| **Manufacturer** | Dell Inc. | `Win32_ComputerSystem` |
| **Model** | Inspiron 14 5418 | `Win32_ComputerSystem` |
| **Operating System** | Microsoft Windows 11 Home Single Language | `Win32_OperatingSystem` |
| **OS Build** | 10.0.26300 (Build 26300, 64-bit) | `Win32_OperatingSystem` |
| **Installed Memory** | 8.00 GB (8,316,030,976 bytes) | `Win32_ComputerSystem` |
| **Python Runtime** | Python 3.12.10 (64-bit) | `python --version` |

---

## 2. Bluetooth Controller & Radio

| Parameter | Specification | Details |
|---|---|---|
| **Controller Name** | Intel(R) Wireless Bluetooth(R) | Device Manager / PnP Entity |
| **Hardware ID** | `USB\VID_8087&PID_0026` | Integrated Intel Wi-Fi 6 AX201 combo module |
| **Bluetooth Core Version** | Bluetooth 5.2 (HCI 11 / LMP 11) | Hardware Spec |
| **Supported Codecs** | SBC (mandatory), AAC | Windows 11 native A2DP stack |
| **Radio Concurrency** | Single 2.4 GHz transceiver | Both speakers share the radio channel; jitter monitored in M8 |

---

## 3. Speaker Configuration & Roles

### 3.1 FRONT Speaker (Dialogue & Small Sounds)
- **Model / Identifier**: `HBTS001`
- **Role**: Dialogue clarity, foley, detail, quiet music elements
- **Connection Type**: Bluetooth A2DP Sink
- **Distance to Listener ($d_{front}$)**: 0.50 meters (< 0.5 m)
- **Acoustic Propagation Delay ($P_{front}$)**: $0.50\text{ m} / 343\text{ m/s} \approx 1.46\text{ ms}$
- **Initial Polarity**: Normal
- **Target Routing**: Dialogue band (200 Hz – 4 kHz), sub-threshold detail ($1 - a \cdot E(t)$)

### 3.2 BACK Speaker (Impact & Loud Sounds)
- **Model / Identifier**: `Pure Sound Pro III` (Portronics Pure Sound Pro III)
- **Role**: Impacts, explosions, bass transients, drum kicks, music peaks
- **Connection Type**: Bluetooth A2DP Sink
- **Distance to Listener ($d_{back}$)**: 1.50 meters ($\pm$ 0.10 m)
- **Acoustic Propagation Delay ($P_{back}$)**: $1.50\text{ m} / 343\text{ m/s} \approx 4.37\text{ ms}$
- **Initial Polarity**: Normal
- **Target Routing**: Low-frequency content ($< 120\text{ Hz}$), impact bursts ($E(t) \cdot c$), ambience side signal, safety capped at -6 dBFS

### 3.3 Acoustic Differential
$$\Delta P = P_{back} - P_{front} = 4.37\text{ ms} - 1.46\text{ ms} = +2.91\text{ ms}$$
Sound from the BACK speaker takes approximately 2.91 ms longer to physically reach the listener's ears.

---

## 4. Audio Interfaces & Microphones

| Role | Device Name | Interface | Purpose |
|---|---|---|---|
| **Primary Calibration Mic** | `Microphone (Audiocular D07)` | USB Audio (External DAC/ADC) | High-fidelity chirp/MLS impulse capture (M7, M9) |
| **Backup Calibration Mic** | `Microphone Array (Intel Smart Sound Technology)` | Integrated Digital Mic Array | Fallback acoustic measurement |
| **Manual Tuning Path** | Human Hearing / Ear Alignment | N/A | Flam test prototype (alternating clicks) in M4/M9 |
| **Auxiliary Output** | `Speakers (Audiocular D07)` | USB Audio (Headphone DAC) | Reference monitor / latency baseline |
| **Integrated Audio** | `Speakers (Realtek(R) Audio)` | Onboard 3.5mm / Laptop Speakers | System audio fallback |

---

## 5. Environment & Constraints

1. **Dual Bluetooth Streaming**: Windows 11 handles multiple endpoints via PortAudio WASAPI Shared Mode. Since both speakers stream through the same Intel AX201 Bluetooth adapter, throughput and packet timing will be profiled for jitter in M8.
2. **Microphone Linearity**: Laptop digital array incorporates OS-level beamforming/noise suppression. For clean impulse response, `Audiocular D07` external mic input is prioritized with software processing disabled.
