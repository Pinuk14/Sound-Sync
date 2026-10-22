# SpeakerSync: Agent Build Workflow v2

**Use cases this version is built for**
1. Two Bluetooth speakers: **FRONT** = dialogue and small/quiet sounds, **BACK** = loud sounds.
2. **Manual latency control per speaker** (slider) *and* **automatic latency adjustment** that is deliberately fine-tuned during development.
3. An **immersive experience for movies and songs**.

**How to use:** Give the agent this whole file plus `ARCHITECTURE.md` once. Then feed ONE milestone at a time (Part F template). Do not advance until the gate is passed and you have reviewed the evidence. `ARCHITECTURE.md` is authoritative; if the build needs to deviate, the agent records an ADR in `docs/DECISIONS.md` and updates `ARCHITECTURE.md` in the same commit.

### What changed from v1

| Area | v1 | v2 |
|---|---|---|
| Routing | Generic "bass/ambience rear, dialogue front" | **Focus/Impact router**: loudness-relative events and low end to BACK; dialogue + quiet detail to FRONT, with dialogue guard |
| Latency | Automatic only | **Auto base + manual trim + global A/V offset**; live, click-free sliders; manual never overwritten |
| Auto latency | One calibration milestone | Calibration **plus a dedicated Auto-Latency Tuning Lab (M9)** with ground truth, parameter sweeps, confidence scores and policy |
| Content | Movies | **Movies and music** (Movie, Night, Music, Immersive Music modes), mode-dependent buffering |
| Video | Not handled | **Video delayed by total latency** so lip-sync holds with Bluetooth delay |
| Architecture | Sketch | Full `ARCHITECTURE.md` |

---

## PART A: Product requirements (acceptance summary)

| ID | Requirement | Acceptance |
|---|---|---|
| R1 | FRONT = dialogue + small sounds; BACK = loud sounds | Measured on synthetic scenes and real clips (M2, M11, M14) |
| R2 | Manual latency per speaker + global A/V offset, live | Click-free at any slider speed, <100 ms UI-to-audio, persisted (M8, M13) |
| R3 | Auto latency, tuned during development | Meets accuracy/repeatability targets in M9; auto and manual coexist |
| R4 | Immersive movies and songs | Modes + Immersion control; A/B listening tables; no pumping/clipping (M10-M14) |

---

## PART B: Agent working rules (non-negotiable)

1. **Proof over claims.** Never say "done/works/fixed" without a passing test, plot, measured number or log. Each milestone ends with `evidence/Mx/` containing `REPORT.md`, `GATE.md` (PASS/FAIL per item with links), plots, raw data (CSV/JSON) and the exact commands used.
2. **Gate discipline.** If any gate item fails, stay in the milestone, diagnose, fix, re-run.
3. **Layer separation.** `player/`, `engine/` (pure DSP), `timing/` and `devices/` (no DSP), `control/` (parameters/telemetry), `calib/`, `ui/`. UI talks only to the control plane. Follow `ARCHITECTURE.md`.
4. **Offline first, then real-time, then hardware.** Block-wise real-time processing must equal offline processing.
5. **Synthetic first.** Every algorithm is tested on generated signals with mathematically known answers before real media.
6. **Real-time safety.** No allocation, locks, disk I/O or logging inside audio callbacks.
7. **Click-free live control.** Every live parameter (gain, EQ, mode, delay) changes via smoothing or crossfade, never a step. Prove it with the click/discontinuity detector.
8. **Manual wins, auto never overwrites.** Final delay = auto base + manual trim + room term, stored separately. Re-calibration updates only the auto base.
9. **No magic numbers.** Tunables live in config/param registry with unit, range and comment.
10. **Determinism.** Seed randomness; tests pass on repeat.
11. **Ask, don't assume,** about hardware (OS, speaker models, mic) and perception. Never invent measurements.
12. **Honest reporting.** If a target isn't met, report the number, cause and options. Never weaken a test silently.
13. **Small commits:** `Mx: <what> (<evidence file>)`.

## PART C: Stack and layout

Python 3.11+, `numpy`, `scipy`, `soundfile`, `librosa`, `matplotlib`, `sounddevice`, `pyyaml`, `pytest`, `typer`; FFmpeg CLI; UI framework chosen in M13 (ask me). Target OS: **ask me**. Repo layout is the module tree in `ARCHITECTURE.md` §5, plus `tests/`, `evidence/`, `docs/`, `profiles/`, `config/`.

## PART D: Targets (report measured results against these)

| Metric | Target |
|---|---|
| Inter-speaker sync error after calibration | ≤ 10 ms (stretch ≤ 5 ms) |
| Drift over 60 min (with correction) | ≤ 10 ms accumulated |
| **Auto-latency accuracy vs. ground truth** | median ≤ 3 ms, p95 ≤ 8 ms |
| **Auto-latency repeatability (std over 20 trials)** | ≤ 2 ms |
| Auto full calibration / quick re-check duration | ≤ 15 s / ≤ 5 s |
| **Manual slider range / step** | ±300 ms per speaker, 1 ms (0.1 ms fine); global A/V ±500 ms |
| **Slider UI-to-audio response** | < 100 ms |
| **Click-free live change** | 0 discontinuities above -60 dBFS during slider sweeps and mode switches |
| **Impact → BACK** | Events above threshold: BACK ≥ FRONT by ≥ 3 dB (scaled by Immersion) |
| **Small sounds → FRONT** | Sub-threshold content: FRONT ≥ BACK by ≥ 6 dB |
| **Dialogue protection** | Speech-band level at the listening position reduced ≤ 1 dB when BACK boosts for simultaneous effects |
| BACK onset | BACK gain reaches ≥ 80% of target within 30 ms of an event onset (look-ahead) |
| Clipping after limiter | 0 samples ≥ 0 dBFS; true-peak ≤ -1 dBFS |
| Buffer underruns | 0 in 30 min (stretch 2 h) |
| Reconnect recovery | < 10 s to resume or fall back |
| Lip-sync (movies) | audio leading ≤ ~45 ms, lagging ≤ ~125 ms (approximate ITU-R BT.1359 detectability; verify and cite) |

---

## PART E: Milestones

### M0: Setup, feasibility, hardware [COMPLETED - PASS: evidence/M0/GATE.md]

**Tasks**
1. Repo skeleton, venv, `pyproject.toml`, ruff + pytest, `config/default.yaml` stub, copy `ARCHITECTURE.md` to `docs/`. [DONE]
2. **Ask me:** OS, PC model, both speaker models, BT adapter version, available codecs, wired inputs, **microphone availability** (type and position options). [DONE]
3. `docs/HARDWARE.md` with real answers. [DONE]
4. `tools/list_devices.py` listing all output/input devices (index, name, host API, channels, sample rate, default latencies). [DONE]
5. **Feasibility research (cited) in `docs/DECISIONS.md`:** can this OS keep two BT speakers connected as separate output devices simultaneously? Fallbacks (USB BT adapter, one wired speaker). [DONE]
6. Write the initial **latency budget** table (expected BT latency per codec, buffers, algorithmic look-ahead). [DONE]

**GATE M0:** tests run in a fresh venv; both speakers (or the documented fallback) appear as separate outputs; `HARDWARE.md` complete; feasibility finding saved with sources. [PASSED - 2026-10-22]

---

### M1: Audio laboratory (movies and music) [COMPLETED - PASS: evidence/M1/GATE.md]

**Tasks:** FFmpeg decode to float32 PCM with metadata and channel layout (no silent downmix); `speakersync inspect` (sample rate, channels, layout labels, duration, per-channel peak/RMS/crest/DC, **LUFS integrated/short-term**); signal generators (sine, log sweep, click train, pink/white noise, silence, speech-like AM noise, **synthetic scene builder**); plots (waveform, spectrum, spectrogram). [DONE]

**Synthetic scene builder** (used by M2/M10/M14), each segment has known truth:
- S1 dialogue: speech-like noise 200-4000 Hz, -23 LUFS [DONE]
- S2 small sounds: soft clicks/noise bursts, -40 LUFS [DONE]
- S3 explosion: broadband + <100 Hz burst, peak -8 dBFS [DONE]
- S4 dialogue + explosion simultaneously [DONE]
- S5 music-like: kick, bass, chord pad, "vocal" lead panned center, hi-hats [DONE]
- S6 quiet room tone [DONE]

**GATE M1:** inspect works on stereo, 5.1 (synthetic OK), video container, and a music file (FLAC/MP3); numeric tests pass (1 kHz at -6 dBFS → peak ≈ -6.0 ± 0.1 dB, RMS ≈ -9.0 ± 0.1 dB); 6-channel tone-per-channel test identified correctly; plots generated and explained. [PASSED - 2026-10-22]

---

### M2: Focus/Impact router v1 (offline)

**Objective:** Implement `ARCHITECTURE.md` §6 offline and prove R1 on synthetic scenes.

**Tasks**
1. `features.py` (K-weighted loudness, running programme loudness, spectral flux, low-band ratio), `filters.py` (crossovers, shelves), `dynamics.py` (look-ahead limiter).
2. `router.py`: dialogue/detail/impact paths, event amount E(t) with attack/release and look-ahead, dialogue guard, BACK leak, Immersion scaling.
3. `speakersync route <in> --mode movie --immersion 0.7` writes `front.wav`, `rear.wav`, plus a JSON of parameters and E(t) CSV.
4. Parameters registered in `control/params.py` with ranges.

**Proof (per-segment energy table, FRONT vs BACK in dB):**

| Scene | Expectation |
|---|---|
| S1 dialogue | FRONT ≥ BACK + 10 dB |
| S2 small sounds | FRONT ≥ BACK + 6 dB |
| S3 explosion | BACK ≥ FRONT + 3 dB (Immersion 0.7) |
| S4 dialogue + explosion | BACK elevated, speech-band level in FRONT within 1 dB of S1-only |
| S5 music (Movie mode vs Music mode) | Music mode: kick/bass → BACK, lead → FRONT; Movie mode differs measurably |
| S6 room tone | No BACK pumping (gain variation < 1 dB) |

Also: FRONT+BACK sum reconstructs within ±1.5 dB over 100 Hz-8 kHz at neutral settings; E(t) onset reaches 80% within 30 ms.

**GATE M2:** all rows pass with plots (E(t), gains, per-segment bars); front/rear files for 2 real movie clips and 2 songs generated; I fill the first listening table (provided empty).

---

### M3: Diagnostics ("audio debugger")

**Tasks:** clipping, true-peak (4× oversampled), DC offset, silence, sudden gain jumps, click/discontinuity detector, phase/correlation meter (front/back and L/R), band-energy table, LUFS, spectrum/spectrogram; `speakersync diagnose` → `diagnostics.json` + `.md`.

**Tests:** inject known faults (hard-clipped sine, DC shift, inverted channel, click, 20 dB step) into synthetic signals; each is detected, clean controls are not flagged (TP/FP table).

**GATE M3:** all injected faults detected, controls clean; diagnose run on M2 outputs and issues fixed or documented.

---

### M4: Offline simulation, latency perception, by-ear alignment prototype

**Tasks**
1. `timing/delay_line.py`: sample-accurate fractional delay (windowed-sinc/Farrow), **live-adjustable**: slew-limited small changes, two-tap equal-power crossfade for large ones (see `ARCHITECTURE.md` §7.3).
2. `speakersync simulate` renders a monitor file with per-speaker delays; delay ladder: 0, 10, 20, 40, 60, 80, 100, 150, 200 ms on a click train, a movie clip and a music clip (with strong bass hits).
3. **Flam test prototype:** alternating clicks FRONT/BACK; a tool to apply `M_i` trims by ear (offline simulation of sliders).
4. Listening sheet for me: single event / echo / smeared bass / lip-sync off / "feels immersive vs. disjointed".
5. Cross-correlation tool recovers offsets.

**Tests:** delay line exact for integer and fractional delays (error < 0.01 sample at test frequencies); delay sweep produces no discontinuities > -60 dBFS (click detector) and pitch deviation within spec; xcorr recovers all ladder offsets within 1 sample.

**GATE M4:** tests pass; my completed sheet is summarized into **my measured tolerances**, stored in `DECISIONS.md` and used as defaults for targets (movies vs. music, since tolerance may differ).

---

### M5: Real-time engine (single device) with live control

**Tasks**
1. `devices/stream.py` (PortAudio stream, ring buffer pull) and render thread (see `ARCHITECTURE.md` §9).
2. **Control plane:** parameter registry, lock-free double-buffered snapshots, smoothing for every parameter, telemetry bus.
3. Transport: play/pause/seek/stop with fades.
4. Block-wise causal processing with filter state across blocks (router included, with look-ahead handled correctly).
5. **Mode-dependent buffering:** Movie (small) vs Music (larger).
6. Telemetry CSV: buffer fill, underruns, callback time, CPU.

**Tests:** chunked vs. whole-file equivalence (max diff < 1e-5 over random block sizes); **parameter-storm test** (random parameter changes at high rate) yields no discontinuities > -60 dBFS and no underruns; 30-min soak: 0 underruns, callback p99 < 50% of block duration.

**GATE M5:** all pass with plots; chosen block sizes justified.

---

### M6: Real speakers, one at a time

**Tasks:** select devices by name via config; per speaker play sine, sweep, click train, pink noise; record with mic; analyze frequency response (approximate), THD at 1 kHz, noise floor, clipping; record codec/sample rate if exposed; characterize **bass capability** and **max clean loudness** of each speaker (important for the BACK role).

**GATE M6:** recordings and plots per speaker; measured bass limits and safe level caps written to config defaults; **recommendation** of which speaker suits BACK/FRONT based on measurements (final choice is mine).

---

### M7: Auto-latency measurement engine v1

**Tasks** (`calib/signals.py`, `measure.py`, `estimators.py`)
1. Test signals: log chirp and MLS with pre-roll silence; per-speaker band limiting.
2. Play → record → align via cross-correlation (FFT) with parabolic **sub-sample** interpolation; subtract acoustic delay `d/343`; handle mic-latency as a common offset that cancels in the *relative* offset (document how; verify with wired loopback if available).
3. N = 20 trials per speaker; median/MAD outlier rejection; output mean, std, jitter, histogram, **confidence score**.
4. `calibration.json` written into the profile (auto base only; manual trim untouched).

**Tests:** simulated devices with known delays (e.g. 83 ms, 137 ms) + noise + reverb: recovered within ±1 ms; real devices: repeatability std reported.

**GATE M7:** simulated self-test passes; real results with histograms for both speakers; statement whether latency is stable enough for static compensation.

---

### M8: Dual-device sync, latency model, and manual controls backend

**Tasks**
1. Single render thread produces FRONT and BACK blocks on one master timeline; per-device feeder applies delay lines and drift micro-resampling.
2. `timing/latency_model.py` implementing the formula in `ARCHITECTURE.md` §7.2 with: auto base `L_i`, manual trim `M_i`, room term `P_i`, global A/V offset `G`, and `T_total`.
3. **Manual control backend:** `set_param("latency.<speaker>.trim_ms")`, `latency.global_av_offset_ms`; live, click-free (slew vs. crossfade).
4. **Video presentation offset:** `player/avsync.py` delays video by `T_total` + `G` (audio is master clock). Provide a flash+beep A/V test clip.
5. Drift controller: buffer-fill trend → ppm estimate → micro-resampling (±50-200 ppm).
6. Persist auto base and manual trims separately in profiles.

**Tests / proof**
- Formula unit tests (property-based: for random `L`, `P`, `M`, all `D_i ≥ 0` and arrival times equal when `M = 0`; shifting `M_i` by x shifts only that speaker by x).
- **Slider-storm test:** continuous sweeps ±300 ms at various speeds: no discontinuities > -60 dBFS, no underruns, UI-to-audio < 100 ms.
- Simulated drift: clocks at 0 and +100 ppm over 60 min (accelerated): ≤ 10 ms with correction; linear growth without it (both plotted).
- Real: click train on both speakers recorded at the listening position at t = 0, 10, 30, 60 min; sync error before vs. after calibration.
- Re-calibration preserves manual trims (test).

**GATE M8:** before/after sync table (target ≤ 10 ms), drift plots, slider-storm results, manual-vs-auto coexistence test passing, A/V test clip lip-sync check by me.

---

### M9: Auto-Latency Tuning Lab (the fine-tuning phase)

**Objective:** Treat the auto algorithm as an experimentally tuned component; choose defaults from data, not guesses (`ARCHITECTURE.md` §8.3).

**Tasks**
1. `calib/tuning_lab.py`: experiment runner that sweeps factors and writes CSV/JSON + plots.
2. **Ground truths:** (a) simulator with injected delay/noise/reverb; (b) wired/electrical loopback reference if available; (c) **human truth:** I align by ear with the flam test, 5 repeats per condition (report my own variance).
3. **Factors:** estimator (xcorr, GCC-PHAT, matched filter, envelope), signal (chirp length 0.25-2 s, band, level -30 to -10 dBFS, MLS), number of repetitions, per-speaker band filtering, outlier method, sub-sample interpolation, SNR (0/10/20 dB), reverberation, mic position (3 positions), room-noise conditions.
4. **Passive tracking experiment (method D):** estimate latency from mic while music plays by correlating against the known stream; adopt only if error and failure rate meet targets.
5. **Confidence calibration:** does low confidence predict large error? Choose thresholds for "apply / ask / don't apply".
6. **Policy (`calib/auto.py`):** modes (Off, Manual only, Auto on connect, Auto + periodic); apply threshold (default ≈ 3 ms), hysteresis, max step, notification rules; quick re-check on reconnect.
7. **Learned trim:** log manual adjustments after auto-calibration; when a consistent residual appears (≥ 3 sessions, std < ~3 ms), *offer* to fold it into a per-profile bias (never automatic).
8. Write chosen defaults to `config/default.yaml` with links to evidence.

**Proof:** ECDFs of absolute error per method/condition; repeatability table; convergence time; failure-mode catalogue; comparison of auto vs. human truth; confidence-vs-error scatter.

**GATE M9:** targets met (median ≤ 3 ms, p95 ≤ 8 ms vs. ground truth; std ≤ 2 ms; full ≤ 15 s, quick ≤ 5 s), or explicit report of what was achieved with the limiting cause and my decision; policy tests pass (hysteresis, no hunting, low-confidence → no auto-change); `DECISIONS.md` records chosen estimator and parameters with evidence.

---

### M10: Immersion tuning on the real speakers (movies and songs)

**Tasks**
1. Use M6 measurements to set crossover, EQ, trims, rear cap.
2. **Polarity/phase:** bass sweep in-phase vs. inverted at the listening position; measure and choose; report comb-filter notches 100 Hz-2 kHz.
3. **Level match** of both speakers at the listener (pink noise, mic): ±1 dB.
4. Mode presets as YAML: **Movie, Night, Music, Immersive Music**, plus Custom; **Immersion** control scaling `a`, `c`, ambience send.
5. Ambience path for music: side extraction, decorrelation, mono-compatibility check (sum-to-mono loss reported, no deep notches).
6. Tune the router on real clips: 5 movie scenes (dialogue, action, quiet, mixed, music-in-film) and 5 songs (different genres).

**GATE M10:** polarity decision and level match documented with measurements; diagnostics clean (no clipping at high volume on bass-heavy material); my A/B listening tables (single speaker vs. SpeakerSync, per mode) completed; the router parameters tuned and recorded.

---

### M11: Analysis upgrades and multi-channel support

**Tasks**
1. Speech probability (`engine/speech.py`): DSP first (voice-band energy ratio, 3-8 Hz modulation, VAD); use the center channel as a prior for 5.1. ML only if it beats the DSP baseline on a labelled set.
2. Music analysis: onset/beat strength, vocal-presence estimate (center-panned mid), used by Music modes.
3. Scene/state with hysteresis (dialogue, action, ambient, music) for UI display; **not** used to hard-switch audio (the continuous E(t) remains the driver).
4. 5.1/7.1 handling: FRONT = FL + FR + C, BACK = surrounds + LFE (level-managed, +10 dB LFE convention documented); stereo → pseudo-surround path.
5. Explicit limitation note: not true 5.1 localization.

**Proof:** speech detection precision/recall on ~10 labelled 30 s clips (labels approved by me); confusion matrix on synthetic scenes; gain-curve plots (smoothness, gain-reversal rate per minute); synthetic 6-channel tone test lands in correct outputs.

**GATE M11:** reported numbers vs. baseline; no pumping (limits in `DECISIONS.md`); 5.1 synthetic and real clip diagnostics clean.

---

### M12: Robustness and failure handling

**Tasks:** supervisor state machine (`ARCHITECTURE.md` §10): BOTH_OK, BACK_LOST, FRONT_LOST, RECONNECTING, RESYNC, FALLBACK; reconnect with backoff; **quick latency re-check after reconnect**; underrun/overflow responses; single-speaker remix with level compensation; fault-injection harness (drop device, stall callback, clock jump, delayed device).

**GATE M12:** fault-injection tests pass with logged transitions; manual test: power off BACK mid-playback → front-only within X s and auto-resync on return (times recorded); manual trims preserved across reconnect; 2-hour soak: 0 crashes, sync in target.

---

### M13: UI and calibration wizard

**Required controls**
- **Per speaker:** Manual latency **slider** (±300 ms), numeric field, ±1 ms and ±0.1 ms nudge, `Reset trim`, `Re-measure`, readouts for **Auto base**, **Manual trim**, **Applied delay**, auto confidence indicator.
- **Global:** A/V offset slider (±500 ms), auto mode selector (Off / Manual only / On connect / Periodic), "Apply to both" link toggle.
- **Aids:** Flam test (alternating clicks), A/V test (flash + beep), live sync-error/drift indicators.
- **Sound:** mode (Movie, Night, Music, Immersive Music, Custom), **Immersion** slider, front/back level trims, polarity toggle, master volume, rear safety cap.
- **Wizard:** select devices → test tones → distances → mic placement → auto calibration → polarity → level match → verify → save profile. A by-ear path when no mic.
- **Status:** connection, buffer health, scene state, live front/back meters.

**GATE M13:** I complete the wizard unaided; slider-storm re-run via the UI path (no clicks); screenshots of every screen; UI imports only the control plane (import check in CI); profile save/load round-trips with auto base and manual trim separate.

---

### M14: Evaluation and final report

**Tasks:** run the full matrix below; plots: sync error before/after, drift with/without correction, auto-latency error distributions (from M9), router behavior per mode, loudness and clipping stats, CPU/callback; **ablations:** static vs. adaptive routing, with vs. without drift correction, auto only vs. auto + manual trim, Movie vs. Music modes; write `FINAL_REPORT.md` (problem, architecture, methods, results, limitations, future work); a `reproduce` script regenerates every plot from saved raw data.

| Test | Expected | Evidence |
|---|---|---|
| Dialogue scene (movie) | FRONT dominant; BACK low | per-segment table + listening |
| Small sounds/foley | FRONT ≥ BACK + 6 dB | band/energy table |
| Explosion/action | BACK elevated with look-ahead, smooth | E(t) + gain curve |
| Dialogue + explosion | Speech intact (≤ 1 dB loss) | measurement |
| Quiet scene | No BACK pumping/noise amplification | noise-floor + gain curve |
| Song: vocals + drums/bass | Vocals FRONT, rhythm BACK | band tables + listening |
| Immersive Music | Envelopment without phase issues | mono-compat + listening |
| Night mode | Reduced range, BACK capped | loudness stats |
| Manual slider sweeps | No clicks, <100 ms response | slider-storm |
| Auto then manual trim | Both coexist; re-calibration keeps trim | test log |
| Auto accuracy | median ≤ 3 ms, p95 ≤ 8 ms | M9 plots |
| Lip-sync (movie) | Within thresholds after `T_total` video delay | A/V test + my sign-off |
| 30 min / 2 h playback | Sync within target | drift plots |
| Speaker disconnect/reconnect | Fallback + recovery + re-check | state logs |
| Stereo / 5.1 / different movies | Works without retuning | diagnostics |
| High volume + bass-heavy | No clipping | diagnostics |

**GATE M14:** every row PASS or justified FAIL; every number traceable to raw data; reproduce script works from a clean checkout.

---

## PART F: Per-milestone prompt template

```
Execute Milestone M{N} from SPEAKERSYNC_AGENT_WORKFLOW_v2.md.

Context: M0 to M{N-1} are complete and gated. Follow ARCHITECTURE.md and Part B rules.
Hardware facts: docs/HARDWARE.md. My measured tolerances: docs/DECISIONS.md.

Do in order:
1. Restate the objective and plan (max 10 lines); list anything you must ask me.
2. Write the tests first where the milestone specifies tests.
3. Implement.
4. Run tests; produce all evidence into evidence/M{N}/.
5. Fill GATE.md with PASS/FAIL and links.
6. Summarize: what passed, measured numbers, failures/uncertainty, what you need from me
   (listening tables, physical actions, mic placement, hardware info).
7. Update ARCHITECTURE.md / DECISIONS.md if anything deviated.

Do NOT start M{N+1}.
```

## PART G: Debugging protocol (when a gate fails)

1. Reproduce on the smallest synthetic input.
2. Isolate by layer: file → decode → router → delay/sync → device → speaker → room/mic. Run the engine offline first; then pipe through virtual devices with injected latency; only then suspect Bluetooth, the speaker or the room.
3. One variable at a time; log each trial in `evidence/Mx/debug_log.md` with **hypothesis, prediction, measurement**.
4. After 3 structured attempts without progress, stop and ask me with the data.

## PART H: What I (the human) must do

| Milestone | My action |
|---|---|
| M0 | Provide OS, speaker models, mic info |
| M2, M4, M9, M10, M11 | Fill listening tables; do by-ear alignment (flam test) for human truth |
| M6-M9 | Place speakers/mic; confirm distances in meters |
| M9 | Provide repeated by-ear alignments; decide on any unmet accuracy target |
| M10 | Choose which speaker plays BACK; approve mode presets |
| M11 | Approve labelled dialogue/action ground truth |
| M12 | Power-cycle speakers on request |
| M13 | Act as first-time user of the wizard |

## PART I: Known risks the agent must address

- Two simultaneous BT outputs may not be supported on every OS or adapter; M0 decides the fallback.
- BT latency changes after reconnects/codec renegotiation; hence quick re-check, confidence scores and the Tuning Lab.
- Two speakers on one radio may add jitter; measure it.
- Phone/laptop mics are uncalibrated: use for timing and relative checks, not absolute SPL.
- BACK speaker must survive loud peaks: respect measured limits (rear cap + limiter).
- Impact routing can hurt dialogue clarity; the dialogue guard must be proven by measurement and listening.
- Total latency makes video late unless the player delays video by `T_total`; verify with the A/V test.
- Two speakers cannot create true 5.1 localization; report it as an enhancement.
