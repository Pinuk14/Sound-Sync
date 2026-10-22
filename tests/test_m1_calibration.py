"""Tests for M1 Numeric Calibration and Signal Generators."""

import numpy as np

from speakersync.lab.generators import (
    generate_click_train,
    generate_log_sweep,
    generate_noise,
    generate_silence,
    generate_sine,
)
from speakersync.lab.inspect import inspect_audio


def test_sine_numeric_calibration():
    """Verify that a 1 kHz sine at -6 dBFS measures peak = -6.0 +- 0.1 dB
    and RMS = -9.0 +- 0.1 dB."""
    sr = 48000
    duration_s = 2.0
    amplitude_dbfs = -6.0
    sine = generate_sine(
        freq_hz=1000.0,
        duration_s=duration_s,
        sample_rate=sr,
        amplitude_dbfs=amplitude_dbfs,
    )

    metrics = inspect_audio(sine, sample_rate=sr)

    # 1. Peak level must be -6.0 +- 0.1 dBFS
    assert np.isclose(metrics.peak_dbfs[0], -6.0, atol=0.1), (
        f"Expected peak -6.0 dBFS, got {metrics.peak_dbfs[0]:.2f}"
    )

    # 2. RMS level for pure sine is Peak - 3.01 dB = -9.01 +- 0.1 dBFS
    assert np.isclose(metrics.rms_dbfs[0], -9.01, atol=0.1), (
        f"Expected RMS -9.01 dBFS, got {metrics.rms_dbfs[0]:.2f}"
    )

    # 3. DC offset for pure sine should be practically zero (< 1e-6)
    assert abs(metrics.dc_offset[0]) < 1e-6, (
        f"Expected DC offset < 1e-6, got {metrics.dc_offset[0]}"
    )

    # 4. Crest factor should be approx 3.01 dB
    assert np.isclose(metrics.crest_factor_db[0], 3.01, atol=0.1)


def test_silence_generator():
    """Verify silence generator produces zero samples and true -inf / floor RMS."""
    sr = 44100
    silence = generate_silence(duration_s=1.0, sample_rate=sr, channels=2)
    assert silence.shape == (44100, 2)
    assert np.all(silence == 0.0)

    metrics = inspect_audio(silence, sample_rate=sr)
    assert metrics.peak_dbfs[0] < -120.0
    assert metrics.rms_dbfs[0] < -120.0
    assert metrics.dc_offset[0] == 0.0


def test_log_sweep_generator():
    """Verify log sweep covers expected duration and amplitude bounds."""
    sr = 48000
    sweep = generate_log_sweep(
        f_start=20.0,
        f_end=20000.0,
        duration_s=1.5,
        sample_rate=sr,
        amplitude_dbfs=-3.0,
    )
    assert sweep.shape == (int(1.5 * sr), 1)
    metrics = inspect_audio(sweep, sample_rate=sr)
    assert np.isclose(metrics.peak_dbfs[0], -3.0, atol=0.1)


def test_click_train_generator():
    """Verify click train produces discrete impulses with exact interval."""
    sr = 48000
    interval_s = 0.1  # 100 ms = 4800 samples
    clicks = generate_click_train(
        interval_s=interval_s,
        duration_s=1.0,
        sample_rate=sr,
        amplitude_dbfs=-1.0,
    )
    # Find sample indices of non-zero elements
    non_zeros = np.where(np.abs(clicks[:, 0]) > 0.01)[0]
    assert len(non_zeros) == 10
    diffs = np.diff(non_zeros)
    assert np.all(diffs == 4800)


def test_noise_generators():
    """Verify white and pink noise generators produce valid samples within target range."""
    sr = 48000
    white = generate_noise(noise_type="white", duration_s=1.0, sample_rate=sr, amplitude_dbfs=-12.0)
    pink = generate_noise(noise_type="pink", duration_s=1.0, sample_rate=sr, amplitude_dbfs=-12.0)

    metrics_white = inspect_audio(white, sample_rate=sr)
    metrics_pink = inspect_audio(pink, sample_rate=sr)

    assert metrics_white.peak_dbfs[0] < 0.0
    assert metrics_pink.peak_dbfs[0] < 0.0
    assert np.isclose(metrics_white.rms_dbfs[0], -12.0, atol=1.5)
    assert np.isclose(metrics_pink.rms_dbfs[0], -12.0, atol=1.5)
