# Milestone 1 (M1) Gate Checklist

**Target:** Audio laboratory (movies and music)  
**Date:** 2026-10-22  
**Result:** **PASS**  

---

## Gate Checklist

| Item | Requirement | Status | Evidence Link |
|---|---|:---:|---|
| **1. Numeric Calibration Tests** | 1 kHz at -6 dBFS measures peak $\approx -6.0 \pm 0.1\text{ dB}$, RMS $\approx -9.0 \pm 0.1\text{ dB}$ | **PASS** | Peak: -6.00 dBFS, RMS: -9.01 dBFS. [inspect_sine.json](inspect_sine.json), [tests/test_m1_calibration.py](../../tests/test_m1_calibration.py) |
| **2. Multichannel 5.1 Identification** | 6-channel tone-per-channel test correctly identified with 0 bleed | **PASS** | [inspect_5_1.json](inspect_5_1.json), [plots/channel_id_5_1_waveform.png](plots/channel_id_5_1_waveform.png), [tests/test_m1_multichannel.py](../../tests/test_m1_multichannel.py) |
| **3. Format Compatibility** | `inspect` works on stereo, 5.1, video container (MP4), and music (FLAC/MP3) | **PASS** | [inspect_video.json](inspect_video.json), [inspect_music.json](inspect_music.json), [tests/test_m1_decode.py](../../tests/test_m1_decode.py) |
| **4. Synthetic Scene Builder** | S1 dialogue (-23 LUFS), S2 small sounds (-40 LUFS), S3 explosion (-8 dBFS peak), S4 mixed, S5 music, S6 room tone | **PASS** | [synthetic_scene_metadata.json](signals/synthetic_scene_metadata.json), [inspect_synthetic.json](inspect_synthetic.json), [tests/test_m1_synthetic.py](../../tests/test_m1_synthetic.py) |
| **5. Visualizations & Plots** | Waveform, spectrum, and spectrogram generated and documented | **PASS** | [plots/synthetic_scene_overview.png](plots/synthetic_scene_overview.png), [plots/sine_calibration_overview.png](plots/sine_calibration_overview.png), [plots/music_spectrogram.png](plots/music_spectrogram.png) |
| **6. Automated Test Suite** | 15 of 15 automated unit and regression tests pass | **PASS** | [REPORT.md §4](REPORT.md#4-commands-executed) |
| **7. Code Quality & Linting** | `ruff check .` passes with zero errors | **PASS** | [REPORT.md §4](REPORT.md#4-commands-executed) |

---

## Gate Decision
**Status: ALL ITEMS PASS**  
Milestone 1 is complete. The quantitative audio measurement suite and reference synthetic scenes are verified and ready for Milestone 2: Focus/Impact router v1 (offline).
