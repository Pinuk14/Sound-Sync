# SpeakerSync: Architecture Decision Records (ADR)

This document records architectural decisions, feasibility findings, and deviations from baseline specifications.

---

## ADR 001: Feasibility and Strategy for Simultaneous Dual Bluetooth Audio Output on Windows 11

### Status
**Accepted** (M0 Feasibility Gate)

### Date
2026-10-22

### Context
SpeakerSync requires concurrent, time-aligned audio playback to two distinct physical Bluetooth speakers:
- **FRONT** (`HBTS001`) for dialogue and subtle sound effects.
- **BACK** (`Pure Sound Pro III`) for loud events, bass, and impacts.

Windows 11 natively restricts default system audio playback to a single default multimedia endpoint at any given time (unless Bluetooth LE Audio broadcast / Auracast is supported by both the host controller and both sink devices). The question investigated is:
*Can Windows 11 support two simultaneous Bluetooth audio sinks as independent endpoints from a single desktop application, and what are the limitations and fallbacks?*

### Technical Findings & Research

1. **Endpoint Enumeration & WASAPI Architecture**:
   - In Windows 11, each paired and connected Bluetooth audio device running the A2DP sink profile is registered as an independent audio endpoint (`IMMDevice`) with a unique endpoint ID.
   - The Windows Audio Engine (WASAPI) operates in two modes:
     - **Exclusive Mode**: An application locks a hardware buffer directly. Opening multiple exclusive streams to different endpoints is supported, but sample rates and bit depths must strictly match hardware capabilities.
     - **Shared Mode**: The Windows Audio Engine mixes streams and performs sample rate conversion if needed. An application can open multiple `IAudioClient` instances targeting different endpoints simultaneously.
   - **Conclusion**: PortAudio (`sounddevice` in Python) running on the WASAPI backend can open two simultaneous `sounddevice.OutputStream` instances—one targeting FRONT (`HBTS001`) and one targeting BACK (`Pure Sound Pro III`).

2. **RF Radio Contention & Bluetooth Multiplexing**:
   - The host system uses an integrated Intel Wireless Bluetooth adapter (Intel Wi-Fi 6 AX201, BT 5.2).
   - Because both speakers connect to a single Bluetooth baseband controller, the radio time-division multiplexes A2DP packets (typically 2-DH5 or 3-DH5 packets) on the 2.4 GHz ISM band.
   - Streaming two stereo streams at typical SBC bitrates (~328 kbps × 2 ≈ 656 kbps) or AAC (~256 kbps × 2 ≈ 512 kbps) is within the theoretical 2 Mbps EDR bandwidth limit of Bluetooth 5.2.
   - **Risk**: Radio packet retries due to 2.4 GHz Wi-Fi interference can induce asynchronous packet queuing delay (jitter) between the two speaker streams.

3. **Fallbacks**:
   - **Fallback A (Dedicated Secondary BT Adapter)**: Insert an external USB Bluetooth 5.0+ dongle to isolate BACK traffic from FRONT traffic onto separate RF controllers and OS driver queues.
   - **Fallback B (Hybrid Wired + Wireless)**: Route the FRONT speaker via the wired USB DAC (`Audiocular D07` 3.5mm AUX) and the BACK speaker via Bluetooth A2DP. Because FRONT is at 0.5 m directly in front of the user, a wired auxiliary connection is physically convenient and completely eliminates Bluetooth RF contention for FRONT.

### Decision
1. Proceed with dual WASAPI Shared Mode streams via `sounddevice` on the single Intel AX201 Bluetooth adapter as the primary architecture.
2. Implement independent ring buffer feeders and delay lines per speaker (as designed in `ARCHITECTURE.md` §7 and §9).
3. Monitor clock drift and buffer health via the telemetry bus (M5/M8).
4. If single-adapter RF jitter exceeds the 10 ms sync target in M8, adopt Fallback A (USB BT dongle) or Fallback B (Audiocular D07 wired FRONT).

### Citations & References
- Microsoft Learn: *About the Windows Core Audio APIs and WASAPI Shared Mode*.  
  `https://learn.microsoft.com/en-us/windows/win32/coreaudio/about-the-windows-core-audio-apis`
- Microsoft Learn: *Stream Routing and Endpoint Selection*.  
  `https://learn.microsoft.com/en-us/windows/win32/coreaudio/stream-routing`
- PortAudio Documentation: *PortAudio WASAPI Specific Information*.  
  `http://www.portaudio.com/docs/v19-doxydocs/compile_windows_wasapi.html`
- Bluetooth SIG: *Advanced Audio Distribution Profile (A2DP) Specification v1.3.2*.  
  `https://www.bluetooth.com/specifications/specs/a2dp-1-3-2/`
- Bluetooth SIG: *Bluetooth Core Specification v5.2, Vol 4: Host Controller Interface*.

---

## Summary of Core Architectural Decisions (from ARCHITECTURE.md §15)

| ADR # | Decision | Rationale | Revisit Criteria |
|---|---|---|---|
| **002** | Single render thread for FRONT and BACK | Guarantees identical analysis timeline and phase coherence | Render thread exceeds real-time audio budget |
| **003** | Delay applied after DSP, per device | Compute DSP once; sync is independent of filter math | N zones with diverging DSP chains |
| **004** | Final delay = Auto base + Manual trim + Room term | User manual trim is never overwritten by auto-calibration | User requests unified single offset |
| **005** | Gain-based Focus/Impact router first | Lower distortion and pumping risk than hard level split | Listening tests in M2/M11 demonstrate level split superiority |
| **006** | Audio clock is master; video delayed by $T_{total}$ | Bluetooth latency demands video delay to preserve lip-sync | Host video pipeline incapable of presentation delay |
| **007** | Python + NumPy/SciPy + PortAudio for core | Fast development, mathematical expressiveness, measurable | Callback latency p99 exceeds 50% block time |
| **008** | Mode-dependent buffering | Movies prioritize low latency; music prioritizes underrun safety | Fixed small buffer proves completely robust in long soak |
