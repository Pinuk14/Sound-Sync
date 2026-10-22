# SpeakerSync: Architecture

**Status:** v2 (authoritative design document; the build agent must keep it in sync with the code and record every deviation as an ADR in `docs/DECISIONS.md`)

---

## 1. Purpose and product definition

SpeakerSync is a desktop application that plays movie and music audio through **two independent Bluetooth speakers** placed **in front of** and **behind** the listener to create a more immersive experience than either speaker alone.

| ID | Requirement |
|---|---|
| R1 | **Zone split.** FRONT speaker = dialogue and small/quiet sounds (detail, foley, soft music elements). BACK speaker = loud sounds (impacts, explosions, bass, drum hits, music peaks). |
| R2 | **Manual latency control.** The user can adjust the latency of each speaker from the app (slider + numeric + fine nudge), live during playback, without clicks, persisted per profile. A global audio/video offset exists for lip-sync. |
| R3 | **Automatic latency adjustment.** The app can measure and keep both speakers time-aligned. The auto algorithm is deliberately tuned and evaluated during development (see the Auto-Latency Tuning Lab, workflow M9). Auto and manual coexist: auto provides the base value, the manual trim is added on top and is never silently overwritten. |
| R4 | **Immersion for movies AND songs.** Content-aware modes (Movie, Night, Music, Immersive Music) with an "Immersion" intensity control. |

### Non-goals

- True 5.1 localization (two speakers cannot reproduce it; this is a front/back enhancement).
- Room correction beyond level, delay and polarity (no full-range room EQ in v1).
- Supporting more than two output zones in v1 (the design leaves room for N zones).

---

## 2. System context

```
                    ┌────────────────────────────────────────────┐
  Movie / Music ──► │                SPEAKERSYNC                 │
  (file, stream)    │                                            │
                    │  Player → Engine → Timing/Sync → Devices   │
  User ◄──────────► │  UI  ◄── Control Plane ──► Calibration     │
                    └───────┬─────────────────────────┬──────────┘
                            │ BT audio                │ BT audio
                            ▼                         ▼
                      🔊 FRONT                    🔊 BACK
                            ▲                         ▲
                            └──────── 🎤 mic ─────────┘   (calibration only)
                                     listener
```

External dependencies: FFmpeg (decode), PortAudio via `sounddevice` (output/input), OS Bluetooth stack (outside our control), optional microphone (phone/laptop/USB) for auto-calibration.

---

## 3. Architectural principles

1. **Three strict layers:** `player/` (media), `engine/` (DSP; pure functions on arrays; no device code), `devices/` (timing, buffering, output; no DSP). A fourth, orthogonal **control plane** carries parameters and telemetry. A fifth subsystem, **calibration**, uses the others through public interfaces only.
2. **Compute once, delay per speaker.** The engine renders FRONT and BACK blocks on a single master timeline. Per-speaker delay is applied *after* DSP, in the timing layer.
3. **Real-time safety.** Audio callbacks never allocate, lock, log to disk, or wait. All cross-thread communication is lock-free (SPSC ring buffers, atomics, double-buffered parameter snapshots).
4. **Click-free by construction.** Every live parameter (gain, EQ, delay, mode) changes through smoothing or crossfade, never a step.
5. **Auto never fights the user.** Final delay = auto base + manual trim + room term. The manual trim is stored separately and survives re-calibration.
6. **Measure, don't assume.** Every timing and DSP claim has a test or measurement (see `evidence/`).
7. **Offline ⇒ real-time ⇒ hardware.** Every algorithm must exist and be verified offline first; real-time wrappers must be proven equivalent.

---

## 4. Layered view

```
┌──────────────────────────────────────────────────────────────────┐
│ UI  (desktop app)                                                │
│  Transport · Mode · Immersion · Latency sliders · Calibration    │
└───────────────┬───────────────────────────────▲──────────────────┘
                │ commands (set_param, calibrate)│ state/telemetry
┌───────────────▼───────────────────────────────┴──────────────────┐
│ CONTROL PLANE  (parameter bus, profile store, telemetry bus)     │
└───┬───────────────┬───────────────────┬─────────────────┬────────┘
    │               │                   │                 │
┌───▼─────┐   ┌─────▼──────┐   ┌────────▼───────┐  ┌──────▼───────┐
│ PLAYER  │──►│  ENGINE    │──►│ TIMING & SYNC  │─►│  DEVICES     │
│ decode  │   │ analyze    │   │ delay lines    │  │ front stream │
│ transport│  │ route      │   │ drift control  │  │ back stream  │
│ A/V clock│  │ shape/limit│   │ latency model  │  │ supervisor   │
└─────────┘   └────────────┘   └────────────────┘  └──────────────┘
                                         ▲
                              ┌──────────┴───────────┐
                              │ CALIBRATION          │
                              │ measure · estimate · │
                              │ tune · apply         │
                              └──────────────────────┘
```

---

## 5. Module breakdown

```
src/speakersync/
├── player/
│   ├── decode.py          # FFmpeg → float32 PCM blocks + metadata + channel layout
│   ├── transport.py       # play / pause / seek / stop, fades
│   └── avsync.py          # audio-master clock; video presentation offset
├── engine/
│   ├── features.py        # loudness (K-weighted), flux, band energy, MFCC
│   ├── speech.py          # speech probability (DSP first; ML optional)
│   ├── router.py          # ★ Focus/Impact router (see §6)
│   ├── modes.py           # Movie / Night / Music / Immersive Music presets
│   ├── filters.py         # crossovers, shelves, peaking EQ (SOS, causal)
│   ├── ambience.py        # side extraction, decorrelation (music/immersive)
│   ├── dynamics.py        # look-ahead limiter, soft-knee compressor
│   └── upmix.py           # stereo / 5.1 / 7.1 handling, downmix rules
├── timing/
│   ├── latency_model.py   # ★ computes per-speaker delay (see §7)
│   ├── delay_line.py      # fractional delay, live-adjustable, click-free
│   ├── drift.py           # clock-drift estimation + micro-resampling
│   └── clock.py           # master timeline in samples
├── devices/
│   ├── stream.py          # PortAudio OutputStream wrapper + ring buffer pull
│   ├── manager.py         # enumerate/select/identify devices (by name/ID)
│   └── supervisor.py      # state machine, reconnect, fallback (see §10)
├── calib/
│   ├── signals.py         # chirp / MLS / click generators
│   ├── measure.py         # play + record + align
│   ├── estimators.py      # xcorr, GCC-PHAT, matched filter, sub-sample interp
│   ├── auto.py            # policy: when/how auto adjusts (see §8)
│   ├── tuning_lab.py      # ★ experiment harness for auto-latency fine-tuning
│   └── wizard.py          # guided steps used by UI
├── control/
│   ├── params.py          # typed parameter registry, ranges, units
│   ├── bus.py             # lock-free snapshot bus (UI thread → audio threads)
│   ├── profiles.py        # per-room / per-speaker-pair profiles (YAML)
│   └── telemetry.py       # metrics ring + CSV/JSON export
├── lab/                   # diagnostics, plots, reports, signal generators
├── ui/
└── cli.py
```

---

## 6. The Focus/Impact router (core of R1 and R4)

### 6.1 Concept

Every audio frame is split into three *paths* and then recombined into two outputs:

| Path | Content | Primary destination |
|---|---|---|
| **Dialogue** | Speech (5.1: center channel; stereo: mid, ~200 Hz-4 kHz, weighted by speech probability). In music: lead vocal (center-panned mid). | FRONT |
| **Detail** | Quiet and small sounds: foley, room tone, soft music elements, anything below the "event" threshold | FRONT |
| **Impact** | Loud events and low end: explosions, hits, drum transients, bass/LFE, music peaks | BACK |

### 6.2 Event amount E(t) ∈ [0, 1]

Computed on a 10 ms hop from:

- **Relative level** `Rel = momentary loudness − running programme loudness`. This is "how loud compared with the usual level of this film/song", so quiet films still get impact moments and loud songs aren't permanently "impact".
- **Onset/flux** (spectral flux or transient detector).
- **Low-band ratio** (energy < ~120 Hz / total).

```
E_raw = clip( w_rel · norm(Rel) + w_flux · norm(Flux) + w_low · norm(LowRatio) )
E     = smooth(E_raw, attack = 10-30 ms, release = 200-500 ms)
```

A **look-ahead of 20-40 ms** lets the BACK gain begin rising *before* the transient is heard. This look-ahead is a fixed algorithmic latency (§7.4).

### 6.3 Output mix

```
FRONT = g_f · [ Dialogue + Detail · (1 − a·E) ]
BACK  = g_b · [ Bass · b  +  Body · E · c  +  Ambience · m  +  Dialogue · leak ]
```

- `a` (front ducking of loud content) and `c` (impact send to back) scale with the **Immersion** control.
- **Dialogue guard:** when speech probability `P_s` is high, `c` is reduced and front gain on the dialogue band is held, so loud effects never mask speech at the listener.
- `leak` is small (default ≈ -18 dB) to avoid a "hole" when BACK is the only speaker heard from a given seat.
- `Ambience` (music/immersive) = side signal (L−R), high-passed, decorrelated (all-pass/short delay), checked for mono-compatibility.
- A final **look-ahead limiter per output** (ceiling ≈ -1 dBFS) and a **rear safety cap** protect hearing and the small speaker.

### 6.4 Modes

| Mode | Speech guard | Impact weights | Ambience to BACK | Notes |
|---|---|---|---|---|
| Movie | High | Rel + flux + low | Low | Dialogue first |
| Night | High | Compressed range; BACK capped | Low | Reduced dynamic range |
| Music | Off (vocal-protect only) | Flux + low (drum/bass emphasis) | Medium | Vocals FRONT, rhythm section BACK |
| Immersive Music | Off | Flux + low | High (decorrelated) | Envelopment; phase-safety enforced |
| Custom | User | User | User | Sliders map to the parameters |

Modes are **config files** (YAML), not code.

### 6.5 Experimental variant (to be evaluated, not assumed)

*Level-split*: FRONT receives a soft-limited version at threshold T; BACK receives the residual. Compare against the gain-based design in the M2/M11 evaluation; adopt only if measured and listened results are better (distortion risk).

---

## 7. Latency model (core of R2 and R3)

### 7.1 Definitions

| Symbol | Meaning | Source |
|---|---|---|
| `L_i` | End-to-end output latency of speaker *i* (app write → sound leaves the speaker); mostly Bluetooth buffering + codec + speaker DSP | **Auto** measurement |
| `P_i` | Acoustic propagation delay = `d_i / 343 m/s` | Room distances (config / wizard) |
| `M_i` | **Manual trim** for speaker *i* (positive = delay this speaker more) | **User slider** |
| `D_i` | Delay the app applies to speaker *i*'s signal | Computed |
| `G` | **Global A/V offset** (user lip-sync trim) | **User slider** |

### 7.2 Computation

We want every event to reach the listener's ears together:

```
arrival_i = t_render + D_i + L_i + P_i

D_i = T* − (L_i + P_i) + M_i          with   T* = max_j ( L_j + P_j − M_j )   (so every D_i ≥ 0)
```

- Moving the slider `M_back` by +10 ms makes `D_back` 10 ms larger (BACK arrives 10 ms later).
- Auto-calibration updates `L_i` only. `M_i` is untouched.
- Slider ranges: `M_i ∈ [−300, +300] ms`, step 1 ms, fine nudge 0.1 ms. `G ∈ [−500, +500] ms`.
- The UI always shows three numbers per speaker: **Auto base**, **Manual trim**, **Applied delay**.

### 7.3 Live adjustment without artifacts

| Change size | Technique | Property |
|---|---|---|
| Small (< ~5 ms) or continuous slider drag | Slew-limited fractional delay (≤ ~1 ms of delay change per second, pitch deviation ≈ 0.1%) | No audible pitch shift |
| Large jump | Two-tap **equal-power crossfade** (~50 ms) between old and new delay | No click, no pitch glitch |
| Drift correction | Micro-resampling ±50-200 ppm | Inaudible |

### 7.4 Latency budget and video

```
T_total = T* + algorithmic latency (look-ahead, filters) + buffering + G
```

For **movies**, the video renderer delays picture presentation by `T_total` so picture and sound agree (the audio clock is master). For **music**, only inter-speaker sync matters and larger buffers are allowed for robustness. Buffering is therefore **mode-dependent** (Movie: smallest safe; Music: larger).

### 7.5 Clock drift

Front and back are separate devices with separate clocks. The drift controller measures relative buffer-fill trend, estimates ppm error, and applies micro-resampling to keep accumulated misalignment within target.

---

## 8. Auto-latency subsystem (R3)

### 8.1 Methods (layered)

| Method | When | Needs mic | Notes |
|---|---|---|---|
| **A. Full calibration** | First setup, new room, new speaker, after codec change | Yes | Chirp/MLS to each speaker, cross-correlate; 20+ trials; outlier rejection; sub-sample interpolation |
| **B. Quick re-check** | On connect/reconnect; optionally periodic | Yes | 2-3 short bursts; compare with stored `L_i` |
| **C. Continuous tracking** | During playback | No | Relative drift from buffer telemetry (cannot see absolute latency change) |
| **D. Passive tracking (research)** | During playback | Yes | Correlate mic signal against the known playback stream (system-ID style); developed only if the Tuning Lab shows it is reliable |
| **E. Manual by ear** | Fallback when no mic, or user preference | No | Alternating-click ("flam") test + sliders |

### 8.2 Policy (`calib/auto.py`)

- Modes: `Off`, `Manual only`, `Auto on connect`, `Auto + periodic recheck`.
- Change < `apply_threshold` (default ≈ 3 ms): apply silently via slew.
- Change ≥ `apply_threshold`: apply with crossfade and notify, or ask (configurable).
- Hysteresis and maximum step per update to avoid hunting.
- Each estimate carries a **confidence score** (peak sharpness, trial variance, SNR). Low confidence ⇒ no automatic change, UI suggests re-measuring.
- **Learned trim:** manual adjustments made after an auto-calibration are logged. If a consistent residual emerges (≥ 3 sessions, std < ~3 ms), the app *offers* to fold it into the auto base as a per-profile bias. Never automatic.

### 8.3 Auto-Latency Tuning Lab (`calib/tuning_lab.py`)

A development-time harness (also usable by advanced users) that treats the estimator as something to be **designed experimentally**:

- **Ground-truth sources:** (1) simulator with injected delay/noise/reverb; (2) wired or electrical loopback reference; (3) **human truth**: best offset found by ear (repeated, with its own variance reported).
- **Factors swept:** estimator (xcorr, GCC-PHAT, matched filter, envelope), signal (chirp length, band, level, MLS), repetitions, filtering band per speaker, outlier method (median/MAD), sub-sample interpolation, SNR (0/10/20 dB), reverberation, mic position, with and without background music (for method D).
- **Outputs:** error distributions (ECDF), repeatability, convergence time, failure modes, recommended defaults, confidence-score calibration (does low confidence actually predict large error?).
- Results are stored as CSV/JSON in `evidence/M9/` and the chosen defaults are written to `config/default.yaml` with a link to the evidence.

---

## 9. Runtime threading and data flow

```
 ┌───────────┐  blocks   ┌────────────┐  front/back  ┌──────────────┐
 │ Decode    │──────────►│ Render     │─────────────►│ Timing       │
 │ thread    │ ring buf  │ thread     │ block pairs  │ (per device  │
 └───────────┘           │ analyze →  │              │ delay lines, │
                         │ route →    │              │ resamplers)  │
                         │ shape      │              └───┬──────┬───┘
                         └─────▲──────┘     ring buf ▼        ▼ ring buf
                               │ params          ┌────────┐ ┌────────┐
                 ┌─────────────┴──────┐          │ FRONT  │ │ BACK   │
                 │ Control plane      │          │callback│ │callback│
                 │ (UI/main thread)   │          └───┬────┘ └───┬────┘
                 └────────────────────┘              ▼          ▼
                                                   🔊          🔊
```

- **Decode thread:** FFmpeg → PCM → ring buffer (look-ahead of a few seconds).
- **Render thread:** one thread produces both outputs for the same timeline position (guarantees front/back are derived from identical input and analysis).
- **Device callbacks:** real-time, only copy from ring buffers (and apply delay-line read + micro-resampling if done in the callback path; otherwise done in a feeder thread just ahead of the callback).
- **Control plane:** UI changes are written to a **parameter snapshot** (versioned, double-buffered); audio threads read the latest snapshot at each block boundary and smooth transitions.

### Sequence: live slider change

```
UI slider (M_back +10 ms)
   │ set_param("latency.back.trim_ms", +10)
   ▼
Control plane ── snapshot v+1 ──► Timing layer
                                    │ latency_model recompute → D_back'
                                    │ delta small? slew : crossfade
                                    ▼
                               back delay line updated (click-free)
                                    │
                                    ▼
UI ◄── telemetry: applied delay, T_total, A/V offset
```

### Sequence: full calibration

```
Wizard → Supervisor: pause content, set known levels
  for speaker in (front, back):
      measure.play(speaker, chirp) ; record mic ; estimate (xcorr/PHAT) × N
      reject outliers ; compute L_i, jitter, confidence
  compute relative offset, update latency_model (L_i)
  verify: play click on both → measure residual sync error
  store calibration.json in profile ; show Auto base / Manual trim / Applied
```

---

## 10. Device supervision and failure handling

```
                 ┌──────────┐  back lost   ┌──────────────┐
      ┌─────────►│ BOTH_OK  │─────────────►│ BACK_LOST    │ (front-only, remix)
      │          └────▲─────┘              └──────┬───────┘
      │               │                           │ device returns
      │         resync OK                         ▼
      │          ┌────┴─────┐  reconnect ok ┌──────────────┐
      │          │ RESYNC   │◄──────────────│ RECONNECTING │ (backoff)
      │          └──────────┘               └──────────────┘
      │ front lost → FRONT_LOST (back-only, remix) → same path
      │ both lost → FALLBACK (system default device)
```

- On reconnect, **quick re-check (method B)** runs because Bluetooth latency can change after reconnection.
- In single-speaker modes, the remaining speaker receives a folded mix with level compensation so content is not lost.
- Underrun ⇒ increase buffering and log. High fill ⇒ gentle resampling correction.
- A **fault-injection harness** (drop device, stall callback, clock jump, delayed device) is part of the test suite.

---

## 11. Configuration and profiles

`config/default.yaml` (defaults) plus per-profile overrides in `profiles/<name>.yaml`:

```yaml
profile: living_room
devices:
  front: { match: "JBL Flip 6", distance_m: 2.0, polarity: normal }
  back:  { match: "Sony SRS-XB13", distance_m: 3.5, polarity: normal }
latency:
  auto:
    enabled: true
    mode: auto_on_connect         # off | manual_only | auto_on_connect | auto_periodic
    apply_threshold_ms: 3.0
    base_ms: { front: 87.2, back: 132.4 }   # written by calibration
    confidence: { front: 0.94, back: 0.91 }
  manual:
    trim_ms: { front: 0.0, back: 6.5 }      # user sliders
    global_av_offset_ms: -20.0
mode: movie
immersion: 0.7
levels: { front_trim_db: 0.0, back_trim_db: -2.0, back_cap_dbfs: -6.0 }
router:
  hop_ms: 10
  lookahead_ms: 30
  event: { w_rel: 0.5, w_flux: 0.3, w_low: 0.2, attack_ms: 15, release_ms: 350 }
  dialogue_guard: 0.8
  dialogue_leak_db: -18
```

Every parameter in code is declared once in `control/params.py` with type, unit, range, default and smoothing time. The UI is generated from, and validated against, this registry.

---

## 12. UI architecture

- UI talks **only** to the control plane (`set_param`, `get_state`, `run_calibration`, transport commands). It never imports `engine/` or `devices/`.
- **Screens:** Player (transport, mode, immersion) · Speakers (status, test tones, levels, polarity) · **Latency** · Calibration wizard · Diagnostics (live meters, sync status).
- **Latency screen (R2):** per speaker, a slider and numeric field for manual trim, ±0.1 ms nudge buttons, `Reset trim`, `Re-measure`, and an Auto base readout with a confidence indicator; a global A/V offset slider; a *Flam test* (alternating clicks front/back) and an *A/V test* (flash + beep) to align by eye/ear; live indicators for estimated sync error and drift.
- Slider-to-audio response time target < 100 ms; no clicks at any slider speed.

---

## 13. Observability

- **Telemetry (always on, cheap):** buffer fill per device, underruns, callback time p50/p99, measured drift ppm, resampling ratio, applied delays, scene state, E(t), speech probability, front/back gains.
- **Recording:** `--trace` mode writes CSV/JSON consumed by the plotting tools in `lab/`.
- **Diagnostics tooling:** clipping, true peak, DC, silence, gain jumps, clicks, phase correlation, spectrum/spectrogram, LUFS.

---

## 14. Testing architecture

| Level | What | Examples |
|---|---|---|
| Unit | Pure DSP and math | Filter responses by sweep+FFT, latency formula, event detector on synthetic scenes |
| Equivalence | Offline vs. chunked real-time | Max abs diff < 1e-5 over random block sizes |
| Simulation | Virtual devices with injected latency/drift | 60-min accelerated drift; slider storm test |
| Fault injection | Supervisor | Drop/reconnect/stall |
| Hardware-in-loop | Real speakers + mic | Sync error before/after, 30-120 min soak |
| Human | Listening and by-ear alignment tables filled by the user | Mode A/B, flam test |

Every milestone produces `evidence/Mx/` (report, plots, raw data, gate checklist).

---

## 15. Key decisions (ADR summary)

| # | Decision | Rationale | Revisit if |
|---|---|---|---|
| 1 | Single render thread produces both outputs | Identical analysis/timeline for both speakers | CPU-bound |
| 2 | Delay applied after DSP, per device | Compute once; sync independent of DSP | N zones with different DSP latencies |
| 3 | Final delay = auto base + manual trim + room term, stored separately | Manual never lost on re-calibration | Users want a single combined value |
| 4 | Gain-based router first, level-split as experiment | Lower distortion risk, easier to tune | Experiments show level-split wins |
| 5 | Audio clock is master; video delayed by `T_total` | Only way to keep lip-sync with BT latency | A video pipeline that cannot delay |
| 6 | Python + NumPy/SciPy + PortAudio first | Fast iteration, measurable | Callback p99 too high ⇒ move hot path to native extension (Rust/C++) |
| 7 | Mode-dependent buffering | Music tolerates latency, movies don't | Always-low-latency proves stable |
| 8 | Microphone-based calibration with by-ear fallback | Mic absent or poor ⇒ still usable | Better OS APIs for reporting device latency |

---

## 16. Risks and open questions

- **OS support for two simultaneous Bluetooth audio outputs** must be proven in M0; fallbacks: USB Bluetooth adapter, one wired speaker.
- **Bluetooth latency can vary** (reconnect, codec renegotiation, interference); hence quick re-check, confidence scores, and the Tuning Lab.
- **Two speakers share radio resources** on one adapter; jitter must be measured.
- **Uncalibrated microphones**: use for timing and relative checks, not absolute SPL/frequency claims.
- **Impact routing can fight dialogue clarity**; the dialogue guard thresholds must be validated with measurements and listening.
- **Open:** exact OS, mic availability, speaker models (answers go in `docs/HARDWARE.md`).

---

## 17. Future extensions

Support for more than two zones, LE Audio/Auracast broadcast (if speakers support it, potentially tighter sync), head-tracking-free "sweet spot" widening, learned scene classifier, per-room profile auto-detect, streaming-service capture (loopback) input.

---

## 18. Glossary

**Auto base (`L_i`)**: measured device latency. **Manual trim (`M_i`)**: user's per-speaker offset. **Applied delay (`D_i`)**: what the timing layer actually inserts. **T\***: reference arrival time. **Event amount E(t)**: continuous "impact-ness" of the current audio. **Flam test**: alternating clicks on two speakers used to align by ear. **GCC-PHAT**: phase-transform generalized cross-correlation, a robust delay estimator.
