"""Synthetic scene builder for offline router and immersion evaluation.

Builds a standardized 6-segment scene with mathematically known truth for each segment:
- S1: Dialogue (speech-like noise 200-4000 Hz, -23 LUFS)
- S2: Small sounds (soft clicks/noise bursts, -40 LUFS)
- S3: Explosion (broadband + <100 Hz bass burst, peak -8 dBFS)
- S4: Dialogue + explosion simultaneously
- S5: Music-like (kick, bass, chord pad, center-panned lead, hi-hats)
- S6: Quiet room tone
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

import numpy as np
from scipy import signal

from speakersync.lab.generators import (
    dbfs_to_linear,
    generate_noise,
    generate_speech_am_noise,
)
from speakersync.lab.inspect import calculate_lufs


def _generate_s2_small_sounds(
    duration_s: float,
    sample_rate: int,
    target_lufs: float = -40.0,
    seed: int = 42,
) -> np.ndarray:
    """Generate quiet foley details, soft clicks, and room whispers."""
    rng = np.random.default_rng(seed)
    num_samples = int(duration_s * sample_rate)
    out = np.zeros(num_samples, dtype=np.float32)

    # Insert sporadic tiny clicks (5 per second)
    num_clicks = int(duration_s * 5)
    click_indices = rng.integers(0, num_samples, size=num_clicks)
    click_amplitudes = rng.uniform(0.005, 0.02, size=num_clicks)
    for idx, amp in zip(click_indices, click_amplitudes):
        out[idx] += float(amp)

    # Add soft filtered noise puffs (highpassed foley whispers)
    raw_noise = rng.standard_normal(num_samples)
    sos = signal.butter(2, 1500.0, btype="highpass", fs=sample_rate, output="sos")
    whispers = signal.sosfilt(sos, raw_noise) * 0.003
    out += whispers.astype(np.float32)

    # Calibrate to target LUFS
    curr_lufs, _ = calculate_lufs(out[:, np.newaxis], sample_rate)
    if curr_lufs > -100.0:
        gain_db = target_lufs - curr_lufs
        scale = 10.0 ** (gain_db / 20.0)
        out *= scale

    return out[:, np.newaxis]


def _generate_s3_explosion(
    duration_s: float,
    sample_rate: int,
    target_peak_dbfs: float = -8.0,
    seed: int = 88,
) -> np.ndarray:
    """Generate an explosion transient: sub-100 Hz sinusoidal thump + decaying broadband burst."""
    rng = np.random.default_rng(seed)
    num_samples = int(duration_s * sample_rate)
    t = np.arange(num_samples, dtype=np.float64) / sample_rate

    # Event starts at t = 0.2 s
    t_event = np.maximum(0.0, t - 0.2)

    # 1. Low-end boom: 80 Hz dropping to 35 Hz with exponential decay
    freq_sweep = 80.0 * np.exp(-3.0 * t_event) + 35.0
    phase = 2.0 * np.pi * np.cumsum(freq_sweep) / sample_rate
    sub_decay = np.exp(-2.5 * t_event) * (t >= 0.2)
    sub_boom = np.sin(phase) * sub_decay

    # 2. Broadband noise burst with fast attack and 0.4s decay
    noise_raw = rng.standard_normal(num_samples)
    sos = signal.butter(3, 1200.0, btype="lowpass", fs=sample_rate, output="sos")
    shaped_noise = signal.sosfilt(sos, noise_raw)
    noise_decay = np.exp(-4.5 * t_event) * (t >= 0.2)
    burst = shaped_noise * noise_decay

    combined = sub_boom * 0.7 + burst * 0.5
    # Normalize to exact target peak dBFS
    max_amp = np.max(np.abs(combined))
    if max_amp > 1e-9:
        target_linear = dbfs_to_linear(target_peak_dbfs)
        combined = (combined / max_amp) * target_linear

    return combined.astype(np.float32)[:, np.newaxis]


def _generate_s5_music(
    duration_s: float,
    sample_rate: int,
    target_lufs: float = -18.0,
) -> np.ndarray:
    """Generate layered music segment (kick, bass synth, chord pad, lead, hi-hats)."""
    num_samples = int(duration_s * sample_rate)
    t = np.arange(num_samples, dtype=np.float64) / sample_rate
    bpm = 120.0
    beat_period = 60.0 / bpm  # 0.5 s per beat

    left = np.zeros(num_samples, dtype=np.float64)
    right = np.zeros(num_samples, dtype=np.float64)

    # 1. Four-on-the-floor kick drum (every 0.5s)
    kick_samples = int(0.25 * sample_rate)
    t_kick = np.arange(kick_samples, dtype=np.float64) / sample_rate
    kick_pitch = 120.0 * np.exp(-25.0 * t_kick) + 48.0
    kick_phase = 2.0 * np.pi * np.cumsum(kick_pitch) / sample_rate
    kick_env = np.exp(-12.0 * t_kick)
    single_kick = np.sin(kick_phase) * kick_env * 0.4

    for beat_t in np.arange(0.0, duration_s, beat_period):
        b_idx = int(beat_t * sample_rate)
        end_idx = min(num_samples, b_idx + kick_samples)
        k_len = end_idx - b_idx
        left[b_idx:end_idx] += single_kick[:k_len]
        right[b_idx:end_idx] += single_kick[:k_len]

    # 2. Bass synth line: 55 Hz (A1) and 73.4 Hz (D2)
    bass = 0.25 * np.sin(2.0 * np.pi * 55.0 * t) + 0.1 * np.sin(2.0 * np.pi * 110.0 * t)
    left += bass
    right += bass

    # 3. Stereo chord pad: A minor (A3: 220Hz, C4: 261.6Hz, E4: 329.6Hz)
    chord_l = 0.08 * np.sin(2.0 * np.pi * 220.0 * t) + 0.06 * np.sin(2.0 * np.pi * 329.6 * t)
    chord_r = 0.08 * np.sin(2.0 * np.pi * 261.63 * t) + 0.06 * np.sin(2.0 * np.pi * 329.6 * t)
    left += chord_l
    right += chord_r

    # 4. Vocal lead (center-panned mid): 440 Hz (A4)
    vocal = 0.15 * np.sin(2.0 * np.pi * 440.0 * t) * (0.8 + 0.2 * np.sin(2.0 * np.pi * 3.0 * t))
    left += vocal
    right += vocal

    # 5. Hi-hats: sixteenth-note ticks (highpassed noise bursts)
    rng = np.random.default_rng(999)
    hat_noise = rng.standard_normal(num_samples)
    sos_hat = signal.butter(3, 7000.0, btype="highpass", fs=sample_rate, output="sos")
    hat_filtered = signal.sosfilt(sos_hat, hat_noise) * 0.08

    hat_period = beat_period / 2.0  # Eighth notes
    hat_env = np.zeros(num_samples, dtype=np.float64)
    hat_len = int(0.04 * sample_rate)
    t_hat = np.arange(hat_len, dtype=np.float64) / sample_rate
    hat_pulse = np.exp(-60.0 * t_hat)

    for h_t in np.arange(0.125, duration_s, hat_period):
        h_idx = int(h_t * sample_rate)
        end_idx = min(num_samples, h_idx + hat_len)
        h_l = end_idx - h_idx
        hat_env[h_idx:end_idx] += hat_pulse[:h_l]

    left += hat_filtered * hat_env
    right += hat_filtered * hat_env

    stereo = np.column_stack((left, right))
    curr_lufs, _ = calculate_lufs(stereo, sample_rate)
    if curr_lufs > -100.0:
        scale = 10.0 ** ((target_lufs - curr_lufs) / 20.0)
        stereo *= scale

    return stereo.astype(np.float32)


def build_synthetic_scene(
    segment_duration_s: float = 2.0,
    sample_rate: int = 48000,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Build the canonical 6-segment synthetic test suite.

    Returns:
        (scene_stereo, metadata)
    """
    # S1: Dialogue (calibrated to -23.0 LUFS stereo)
    s1_mono = generate_speech_am_noise(
        duration_s=segment_duration_s,
        sample_rate=sample_rate,
        target_lufs=-23.0,
        seed=101,
    )
    s1 = np.repeat(s1_mono, 2, axis=1)
    s1_lufs, _ = calculate_lufs(s1, sample_rate)
    if s1_lufs > -100.0:
        s1 *= 10.0 ** ((-23.0 - s1_lufs) / 20.0)

    # S2: Small sounds (calibrated to -40.0 LUFS stereo)
    s2_mono = _generate_s2_small_sounds(
        duration_s=segment_duration_s,
        sample_rate=sample_rate,
        target_lufs=-40.0,
        seed=202,
    )
    s2 = np.repeat(s2_mono, 2, axis=1)
    s2_lufs, _ = calculate_lufs(s2, sample_rate)
    if s2_lufs > -100.0:
        s2 *= 10.0 ** ((-40.0 - s2_lufs) / 20.0)

    # S3: Explosion
    s3_mono = _generate_s3_explosion(
        duration_s=segment_duration_s,
        sample_rate=sample_rate,
        target_peak_dbfs=-8.0,
        seed=303,
    )
    s3 = np.repeat(s3_mono, 2, axis=1)

    # S4: Dialogue + Explosion simultaneously
    s4_mono = s1_mono + s3_mono
    s4 = np.repeat(s4_mono, 2, axis=1)

    # S5: Music-like
    s5 = _generate_s5_music(
        duration_s=segment_duration_s,
        sample_rate=sample_rate,
        target_lufs=-18.0,
    )

    # S6: Room tone (-60 dBFS quiet noise)
    s6_mono = generate_noise(
        noise_type="pink",
        duration_s=segment_duration_s,
        sample_rate=sample_rate,
        amplitude_dbfs=-60.0,
        seed=606,
    )
    s6 = np.repeat(s6_mono, 2, axis=1)

    segments_data = [s1, s2, s3, s4, s5, s6]
    scene_stereo = np.vstack(segments_data)

    num_samples_seg = int(segment_duration_s * sample_rate)
    metadata = {
        "sample_rate": sample_rate,
        "segment_duration_s": segment_duration_s,
        "total_duration_s": segment_duration_s * 6,
        "segments": [
            {
                "id": 1,
                "name": "S1_dialogue",
                "start_sample": 0,
                "end_sample": num_samples_seg,
                "start_time_s": 0.0,
                "end_time_s": segment_duration_s,
                "target": "Dialogue: 200-4000 Hz, -23 LUFS",
                "router_expectation": "FRONT >= BACK + 10 dB",
            },
            {
                "id": 2,
                "name": "S2_small_sounds",
                "start_sample": num_samples_seg,
                "end_sample": 2 * num_samples_seg,
                "start_time_s": segment_duration_s,
                "end_time_s": 2 * segment_duration_s,
                "target": "Small sounds: soft clicks, -40 LUFS",
                "router_expectation": "FRONT >= BACK + 6 dB",
            },
            {
                "id": 3,
                "name": "S3_explosion",
                "start_sample": 2 * num_samples_seg,
                "end_sample": 3 * num_samples_seg,
                "start_time_s": 2 * segment_duration_s,
                "end_time_s": 3 * segment_duration_s,
                "target": "Explosion: broadband + <100 Hz, peak -8 dBFS",
                "router_expectation": "BACK >= FRONT + 3 dB",
            },
            {
                "id": 4,
                "name": "S4_dialogue_explosion",
                "start_sample": 3 * num_samples_seg,
                "end_sample": 4 * num_samples_seg,
                "start_time_s": 3 * segment_duration_s,
                "end_time_s": 4 * segment_duration_s,
                "target": "Dialogue + Explosion simultaneous",
                "router_expectation": "BACK elevated, FRONT dialogue loss <= 1 dB",
            },
            {
                "id": 5,
                "name": "S5_music",
                "start_sample": 4 * num_samples_seg,
                "end_sample": 5 * num_samples_seg,
                "start_time_s": 4 * segment_duration_s,
                "end_time_s": 5 * segment_duration_s,
                "target": "Music: kick, bass, pad, center lead",
                "router_expectation": "Kick/bass to BACK, lead vocals to FRONT",
            },
            {
                "id": 6,
                "name": "S6_room_tone",
                "start_sample": 5 * num_samples_seg,
                "end_sample": 6 * num_samples_seg,
                "start_time_s": 5 * segment_duration_s,
                "end_time_s": 6 * segment_duration_s,
                "target": "Room tone: quiet noise floor",
                "router_expectation": "No BACK pumping (gain variation < 1 dB)",
            },
        ],
    }

    return scene_stereo, metadata
