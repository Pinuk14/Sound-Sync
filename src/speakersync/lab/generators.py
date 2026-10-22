"""Calibrated reference audio signal generators.

Provides mathematically deterministic test signals including sine waves, log sweeps,
click trains, white/pink noise, silence, speech-like AM noise, and 6-channel identification tests.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np
from scipy import signal

from speakersync.lab.inspect import calculate_lufs


def dbfs_to_linear(dbfs: float) -> float:
    """Convert dBFS to peak linear amplitude."""
    return float(10.0 ** (dbfs / 20.0))


def generate_sine(
    freq_hz: float = 1000.0,
    duration_s: float = 1.0,
    sample_rate: int = 48000,
    amplitude_dbfs: float = -6.0,
) -> np.ndarray:
    """Generate a pure sinusoidal waveform.

    Returns:
        np.ndarray of shape (num_samples, 1), float32.
    """
    num_samples = int(duration_s * sample_rate)
    t = np.arange(num_samples, dtype=np.float64) / sample_rate
    amplitude = dbfs_to_linear(amplitude_dbfs)
    data = amplitude * np.sin(2.0 * np.pi * freq_hz * t)
    return data.astype(np.float32)[:, np.newaxis]


def generate_log_sweep(
    f_start: float = 20.0,
    f_end: float = 20000.0,
    duration_s: float = 2.0,
    sample_rate: int = 48000,
    amplitude_dbfs: float = -6.0,
) -> np.ndarray:
    """Generate an exponential (logarithmic) frequency sweep.

    Returns:
        np.ndarray of shape (num_samples, 1), float32.
    """
    num_samples = int(duration_s * sample_rate)
    t = np.arange(num_samples, dtype=np.float64) / sample_rate
    amplitude = dbfs_to_linear(amplitude_dbfs)

    # Instantaneous frequency: f(t) = f_start * (f_end / f_start) ** (t / duration)
    # Phase integral:
    # phi(t) = 2*pi*f_start * ((f_end/f_start)**(t/T) - 1) / (ln(f_end/f_start)/T)
    rate = np.log(f_end / f_start) / duration_s
    phi = 2.0 * np.pi * f_start * (np.exp(rate * t) - 1.0) / rate
    data = amplitude * np.sin(phi)
    return data.astype(np.float32)[:, np.newaxis]


def generate_click_train(
    interval_s: float = 0.1,
    duration_s: float = 1.0,
    sample_rate: int = 48000,
    amplitude_dbfs: float = 0.0,
) -> np.ndarray:
    """Generate discrete single-sample impulses separated by interval_s.

    Returns:
        np.ndarray of shape (num_samples, 1), float32.
    """
    num_samples = int(duration_s * sample_rate)
    data = np.zeros(num_samples, dtype=np.float32)
    step_samples = int(interval_s * sample_rate)
    amplitude = dbfs_to_linear(amplitude_dbfs)

    for i in range(0, num_samples, step_samples):
        data[i] = amplitude

    return data[:, np.newaxis]


def generate_silence(
    duration_s: float = 1.0,
    sample_rate: int = 48000,
    channels: int = 2,
) -> np.ndarray:
    """Generate perfect digital silence.

    Returns:
        np.ndarray of shape (num_samples, channels), float32.
    """
    num_samples = int(duration_s * sample_rate)
    return np.zeros((num_samples, channels), dtype=np.float32)


def generate_noise(
    noise_type: str = "white",
    duration_s: float = 1.0,
    sample_rate: int = 48000,
    amplitude_dbfs: float = -12.0,
    seed: int = 42,
) -> np.ndarray:
    """Generate pseudo-random white or pink noise with calibrated RMS amplitude.

    Returns:
        np.ndarray of shape (num_samples, 1), float32.
    """
    rng = np.random.default_rng(seed)
    num_samples = int(duration_s * sample_rate)

    if noise_type.lower() == "white":
        raw = rng.standard_normal(num_samples)
    elif noise_type.lower() == "pink":
        # Generate pink noise using Voss-McCartney algorithm or 1/f spectral filtering
        white = rng.standard_normal(num_samples)
        # Apply pinking filter: 3-pole, 3-zero IIR filter (Paul Kellet's method)
        b = np.array([0.049922035, -0.095993537, 0.050612699, -0.004408786])
        a = np.array([1.0, -2.494956002, 2.017265875, -0.522189400])
        raw = signal.lfilter(b, a, white)
    else:
        raise ValueError(f"Unsupported noise type: {noise_type}. Choose 'white' or 'pink'.")

    # Normalize to target RMS
    current_rms = np.sqrt(np.mean(raw**2))
    target_rms = dbfs_to_linear(amplitude_dbfs)
    scaled = (raw / max(current_rms, 1e-9)) * target_rms

    # Prevent digital clipping: if extreme peak exceeds -0.5 dBFS, gentle soft-clip
    peak_val = np.max(np.abs(scaled))
    if peak_val > dbfs_to_linear(-0.5):
        # Soft-clip extreme tails beyond 0.95
        scaled = np.tanh(scaled / 0.95) * 0.95

    return scaled.astype(np.float32)[:, np.newaxis]


def generate_speech_am_noise(
    duration_s: float = 2.0,
    sample_rate: int = 48000,
    target_lufs: float = -23.0,
    seed: int = 1234,
) -> np.ndarray:
    """Generate speech-like AM noise bandpassed between 200 Hz and 4000 Hz with syllabic AM.

    Returns:
        np.ndarray of shape (num_samples, 1), float32, calibrated to target_lufs.
    """
    rng = np.random.default_rng(seed)
    num_samples = int(duration_s * sample_rate)
    raw = rng.standard_normal(num_samples)

    # 1. Bandpass filter: 200 Hz to 4000 Hz (4th-order Butterworth)
    sos = signal.butter(4, [200.0, 4000.0], btype="bandpass", fs=sample_rate, output="sos")
    bandpassed = signal.sosfilt(sos, raw)

    # 2. Syllabic amplitude modulation (approx 4 Hz with some 6 Hz variation)
    t = np.arange(num_samples, dtype=np.float64) / sample_rate
    am_envelope = 0.5 + 0.4 * np.sin(2.0 * np.pi * 4.0 * t) + 0.1 * np.cos(2.0 * np.pi * 6.5 * t)
    am_envelope = np.clip(am_envelope, 0.0, 1.0)
    modulated = bandpassed * am_envelope

    # 3. Calibrate to exact target LUFS
    signal_2d = modulated[:, np.newaxis]
    current_lufs, _ = calculate_lufs(signal_2d, sample_rate)
    if current_lufs > -100.0:
        gain_db = target_lufs - current_lufs
        scale = 10.0 ** (gain_db / 20.0)
        calibrated = modulated * scale
    else:
        calibrated = modulated

    return calibrated.astype(np.float32)[:, np.newaxis]


def generate_channel_identification_6ch(
    tone_duration_s: float = 0.5,
    sample_rate: int = 48000,
) -> Tuple[np.ndarray, List[str]]:
    """Generate 6-channel 5.1 layout test audio with sequential identification tones.

    Channels:
        0: FL (440 Hz - A4)
        1: FR (554.37 Hz - C#5)
        2: C  (659.25 Hz - E5)
        3: LFE (80 Hz - Sub bass)
        4: Ls (880 Hz - A5)
        5: Rs (1108.73 Hz - C#6)

    Returns:
        (audio_data, channel_labels)
    """
    layout_labels = ["FL", "FR", "C", "LFE", "Ls", "Rs"]
    frequencies = [440.0, 554.37, 659.25, 80.0, 880.0, 1108.73]
    amplitudes_dbfs = [-6.0, -6.0, -6.0, -3.0, -6.0, -6.0]

    num_samples_per_tone = int(tone_duration_s * sample_rate)
    total_samples = num_samples_per_tone * 6
    audio_6ch = np.zeros((total_samples, 6), dtype=np.float32)

    for ch_idx, freq in enumerate(frequencies):
        tone = generate_sine(
            freq_hz=freq,
            duration_s=tone_duration_s,
            sample_rate=sample_rate,
            amplitude_dbfs=amplitudes_dbfs[ch_idx],
        )[:, 0]

        # Apply 5ms fade-in and fade-out to prevent clicks
        fade_len = int(0.005 * sample_rate)
        fade = np.linspace(0.0, 1.0, fade_len, dtype=np.float32)
        tone[:fade_len] *= fade
        tone[-fade_len:] *= fade[::-1]

        start_samp = ch_idx * num_samples_per_tone
        end_samp = start_samp + num_samples_per_tone
        audio_6ch[start_samp:end_samp, ch_idx] = tone

    return audio_6ch, layout_labels
