# Milestone 1 (M1) Evidence Report: Audio Laboratory (Movies and Music)

**Date:** 2026-10-22  
**Status:** **PASSED & VERIFIED**  
**Gate Checklist:** [GATE.md](GATE.md)  

---

## 1. Executive Summary

Milestone 1 implemented the complete Audio Laboratory foundation:
1. **FFmpeg Float32 PCM Decoder (`player/decode.py`)**: Direct raw PCM decoding preserving all channel layouts (stereo, 5.1, 7.1) without unintended downmixing, using the bundled static FFmpeg binary.
2. **Quantitative Inspection Suite (`lab/inspect.py` & CLI `speakersync inspect`)**: Computes Sample Rate, Channels, Layout, Duration, per-channel Peak (dBFS), RMS (dBFS), Crest factor (dB), DC offset, and ITU-R BS.1770-4 Integrated & Short-term LUFS.
3. **Calibrated Signal Generators (`lab/generators.py`)**: Mathematically exact sine waves, log sweeps, click trains, calibrated white/pink noise, silence, speech AM noise, and 6-channel 5.1 identification signals.
4. **Canonical 6-Segment Synthetic Scene Builder (`lab/synthetic.py`)**: Standardized multi-segment movie/music test suite with known ground truth ($S1$–$S6$) used for router and latency evaluation.
5. **Visualization Tools (`lab/plots.py` & CLI `speakersync plot`)**: High-resolution waveform, FFT magnitude spectrum, and STFT spectrogram plots.

---

## 2. Quantitative Verification Results

### 2.1 Numeric Calibration Verification (Sine 1 kHz at -6 dBFS)
From [evidence/M1/inspect_sine.json](inspect_sine.json):
- **Peak Level**: **-6.00 dBFS** (Target: $-6.0 \pm 0.1\text{ dBFS}$) $\rightarrow$ **PASS**
- **RMS Level**: **-9.01 dBFS** (Target: $-9.0 \pm 0.1\text{ dBFS}$) $\rightarrow$ **PASS**
- **Crest Factor**: **3.01 dB** (Analytical pure sine truth: $20\log_{10}(\sqrt{2}) = 3.0103\text{ dB}$) $\rightarrow$ **PASS**
- **DC Offset**: **$-1.5 \times 10^{-5}$** (Target: $< 10^{-4}$) $\rightarrow$ **PASS**

### 2.2 6-Channel 5.1 Tone-Per-Channel Identification
From [evidence/M1/inspect_5_1.json](inspect_5_1.json) and [evidence/M1/plots/channel_id_5_1_waveform.png](plots/channel_id_5_1_waveform.png):
- Channel 0 ($FL$): 440 Hz tone, Peak: -6.00 dBFS, Bleed into other channels: 0.0
- Channel 1 ($FR$): 554 Hz tone, Peak: -6.00 dBFS, Bleed into other channels: 0.0
- Channel 2 ($C$): 659 Hz tone, Peak: -6.00 dBFS, Bleed into other channels: 0.0
- Channel 3 ($LFE$): 80 Hz sub-bass tone, Peak: -3.00 dBFS, Bleed into other channels: 0.0
- Channel 4 ($Ls$): 880 Hz tone, Peak: -6.00 dBFS, Bleed into other channels: 0.0
- Channel 5 ($Rs$): 1108 Hz tone, Peak: -6.00 dBFS, Bleed into other channels: 0.0
- **Cross-talk / Bleed**: Exactly **0.00** across all channels. Preserves discrete 6-channel routing without silent downmix.

### 2.3 Synthetic Scene ($S1$–$S6$) Ground Truth Verification
From [evidence/M1/signals/synthetic_scene_metadata.json](signals/synthetic_scene_metadata.json) and [evidence/M1/inspect_synthetic.json](inspect_synthetic.json):
- **S1 (Dialogue)**: Bandpassed 200–4000 Hz, speech AM modulation $\rightarrow$ **-23.00 LUFS** (Target: -23 LUFS).
- **S2 (Small Sounds)**: Foley transients, whispers, soft clicks $\rightarrow$ **-40.00 LUFS** (Target: -40 LUFS).
- **S3 (Explosion)**: Sub-100 Hz boom + broadband noise burst $\rightarrow$ Peak: **-8.00 dBFS** (Target: -8 dBFS).
- **S4 (Dialogue + Explosion)**: Simultaneous speech band + bass transient $\rightarrow$ Peak: **-7.46 dBFS**.
- **S5 (Music)**: Layered kick (55 Hz), bass synth, A-minor chord pad, center lead vocal, hi-hats $\rightarrow$ **-18.00 LUFS**.
- **S6 (Room Tone)**: Diffuse pink noise floor at **-60.00 dBFS**.

### 2.4 Container & Format Compatibility
From [evidence/M1/inspect_video.json](inspect_video.json) and [evidence/M1/inspect_music.json](inspect_music.json):
- **Video Container (`test_video.mp4`)**: Successfully demuxed and decoded to float32 PCM without downmix (12.01s duration, -19.20 LUFS).
- **Music File (`music.flac`)**: Successfully decoded (48 kHz stereo, -18.00 LUFS).
- **Stereo WAV (`sine_1khz_m6dbfs.wav`)**: Fast-path decoded via libsndfile.

---

## 3. Visualizations Generated

| Plot | Description | File Link |
|---|---|---|
| **Sine 1 kHz Overview** | Waveform, FFT log-spectrum, and STFT spectrogram | [plots/sine_calibration_overview.png](plots/sine_calibration_overview.png) |
| **Synthetic Scene Overview** | Complete 12s $S1$–$S6$ time-domain and time-frequency visualization | [plots/synthetic_scene_overview.png](plots/synthetic_scene_overview.png) |
| **5.1 Channel Isolation** | 6-channel time-series showing sequential tone firing | [plots/channel_id_5_1_waveform.png](plots/channel_id_5_1_waveform.png) |
| **Music Track Spectrogram** | Harmonic distribution of kick, bass, pad, and lead vocal | [plots/music_spectrogram.png](plots/music_spectrogram.png) |

---

## 4. Commands Executed

```powershell
# 1. Run all unit and calibration tests
.\.venv\Scripts\pytest.exe -v

# 2. Run linter
.\.venv\Scripts\ruff.exe check .

# 3. Generate test suite signals and synthetic scenes
.\.venv\Scripts\speakersync.exe generate-signals --out-dir evidence/M1/signals

# 4. Inspect test signals across formats
.\.venv\Scripts\speakersync.exe inspect evidence/M1/signals/sine_1khz_m6dbfs.wav --json-out evidence/M1/inspect_sine.json
.\.venv\Scripts\speakersync.exe inspect evidence/M1/signals/channel_id_5_1.wav --json-out evidence/M1/inspect_5_1.json
.\.venv\Scripts\speakersync.exe inspect evidence/M1/signals/synthetic_scene.wav --json-out evidence/M1/inspect_synthetic.json
.\.venv\Scripts\speakersync.exe inspect evidence/M1/signals/test_video.mp4 --json-out evidence/M1/inspect_video.json
.\.venv\Scripts\speakersync.exe inspect evidence/M1/signals/music.flac --json-out evidence/M1/inspect_music.json
```
