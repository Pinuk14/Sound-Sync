# SpeakerSync Initial Latency Budget Breakdown (Milestone 0)

**Document Status:** Complete (M0 Baseline)  
**Date:** 2026-10-22  
**Reference Architecture:** `ARCHITECTURE.md` §7.4  

---

## 1. Overview and Timing Formula

According to `ARCHITECTURE.md` §7.4, the total system latency before sound leaves the speakers and reaches the listener's ears is:

$$T_{\text{total}} = T^* + D_{\text{algo}} + D_{\text{buffer}} + G$$

Where:
- $T^* = \max_j (L_j + P_j - M_j)$ is the reference synchronization arrival time.
- $L_j$ is the device output latency (Bluetooth stack + RF transmission + speaker DSP/FIFO).
- $P_j = d_j / 343\text{ m/s}$ is the acoustic propagation delay from speaker to listener.
- $M_j$ is the user manual trim for speaker $j$.
- $D_{\text{algo}}$ is the algorithmic look-ahead (transient detector look-ahead and filter group delay).
- $D_{\text{buffer}}$ is the audio engine and WASAPI driver ring buffer margin.
- $G$ is the user global A/V offset slider ($\pm 500\text{ ms}$).

---

## 2. Component Latency Breakdown

| Subsystem Component | Typical Value (ms) | Range / Constraints | Rationale & Source |
|---|---|---|---|
| **OS Audio Engine (WASAPI Shared Mode)** | **10.0 ms** | 10 – 20 ms | Windows audio engine quantum period (~10 ms per buffer frame) |
| **Ring Buffer & Inter-thread Margin** | **15.0 ms** | 10 – 25 ms | Lock-free SPSC buffer between render thread and feeder callbacks |
| **SpeakerSync Algorithmic Look-Ahead** | **30.0 ms** | 20 – 40 ms | Look-ahead for Focus/Impact router ($E(t)$ onset rise ahead of transient) |
| **Crossover & Limiter Group Delay** | **3.0 ms** | 2 – 5 ms | Second-order SOS Linkwitz-Riley filter and look-ahead limiter |
| **Bluetooth Host Stack Queue (Windows)** | **35.0 ms** | 20 – 50 ms | Windows A2DP packetizer and driver buffer queue |
| **Bluetooth RF Transmission & Scheduling** | **15.0 ms** | 10 – 30 ms | 2.4 GHz packet transmission, slot alignment, retry margin |
| **Speaker Hardware Onboard Buffer & DSP** | **70.0 ms** | 40 – 120 ms | On-speaker DAC, internal ring buffer, hardware SBC/AAC decoder |
| **Acoustic Delay - FRONT ($d=0.5\text{ m}$)** | **1.5 ms** | 1.0 – 2.0 ms | $0.5\text{ m} / 343\text{ m/s} = 1.46\text{ ms}$ |
| **Acoustic Delay - BACK ($d=1.5\text{ m}$)** | **4.4 ms** | 4.0 – 5.0 ms | $1.5\text{ m} / 343\text{ m/s} = 4.37\text{ ms}$ |

---

## 3. Bluetooth Codec Latency Comparison

| Codec | Windows 11 Native Support | Bitrate (kbps) | Typical Hardware Latency | Jitter Profile |
|---|---|---|---|---|
| **SBC (Standard)** | Yes (Universal) | 328 kbps (Joint Stereo) | **150 – 220 ms** | Moderate (frame-based) |
| **AAC** | Yes (Windows 11 native) | 256 kbps | **120 – 180 ms** | Low to moderate |
| **aptX / aptX HD** | Optional (Vendor driver dependent) | 352 – 576 kbps | **80 – 130 ms** | Low |
| **aptX Low Latency** | No (Requires dedicated hardware) | 352 kbps | **30 – 45 ms** | Very low |
| **LDAC** | No (Requires third-party driver) | Up to 990 kbps | **160 – 250 ms** | High on crowded 2.4 GHz |

*Note for Dell Inspiron 14 with Intel AX201 on Windows 11*: The primary active codecs will be **AAC** (if supported by `HBTS001` and `Pure Sound Pro III`) or **SBC** (standard mandatory fallback).

---

## 4. End-to-End Latency Scenarios & Video Lip-Sync

### Scenario A: Movie Mode (Low-latency buffering)
- Target Audio Engine buffer: 10 ms
- Router look-ahead: 30 ms
- Estimated Bluetooth delay ($L_i$): ~140 ms (AAC) / ~180 ms (SBC)
- Acoustic delay ($P_i$): ~1.5 to 4.4 ms
- **Total Expected Audio Delay ($T_{\text{total}}$)**: **~185 ms (AAC) to ~225 ms (SBC)**

### Scenario B: Music Mode (Robust buffering)
- Target Audio Engine buffer: 25 ms
- Router look-ahead: 30 ms
- Estimated Bluetooth delay ($L_i$): ~150 to 200 ms
- **Total Expected Audio Delay ($T_{\text{total}}$)**: **~210 ms to ~260 ms**
*(Lip-sync is not applicable for audio-only music playback)*

---

## 5. Video Delay Specification for Lip-Sync

In video playback, Bluetooth audio delay of ~200 ms makes audio severely lag behind video without compensation.

**ITU-R BT.1359 Lip-Sync Thresholds:**
- Undetectable range: Audio leading picture by $\le 25\text{ ms}$, lagging by $\le 95\text{ ms}$.
- Detectability limit: Audio leading picture by $\le 45\text{ ms}$, lagging by $\le 125\text{ ms}$.

**SpeakerSync Solution (`player/avsync.py`):**
The player delays video picture presentation by:

$$T_{\text{video\_delay}} = T_{\text{total}} + G$$

Where $G$ is the user manual global A/V offset slider ($\pm 500\text{ ms}$). This ensures that when the audio wave physically reaches the listener's ears at $t_{\text{render}} + T_{\text{total}}$, the video display frame appears at the exact same instant, holding lip-sync within $\pm 5\text{ ms}$.
