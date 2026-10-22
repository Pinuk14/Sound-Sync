"""Audio visualization and plotting utilities.

Generates high-resolution waveform, FFT magnitude spectrum, and spectrogram plots.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib

# Set non-interactive backend for headless / script execution
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal


def plot_waveform(
    data: np.ndarray,
    sample_rate: int,
    title: str = "Audio Waveform",
    out_path: Optional[Path | str] = None,
) -> plt.Figure:
    """Plot multi-channel time-series waveform."""
    if data.ndim == 1:
        data = data[:, np.newaxis]

    num_samples, channels = data.shape
    t = np.arange(num_samples) / sample_rate

    fig, axes = plt.subplots(channels, 1, figsize=(10, 2.5 * channels), sharex=True, squeeze=False)
    fig.suptitle(title, fontsize=12, fontweight="bold")

    for ch in range(channels):
        ax = axes[ch, 0]
        ax.plot(t, data[:, ch], color="#1f77b4", linewidth=0.8)
        ax.set_ylabel(f"Ch {ch+1} Amp")
        ax.set_ylim([-1.05, 1.05])
        ax.grid(True, linestyle="--", alpha=0.6)

    axes[-1, 0].set_xlabel("Time (seconds)")
    plt.tight_layout()

    if out_path:
        p = Path(out_path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p, dpi=150)
        plt.close(fig)

    return fig


def plot_spectrum(
    data: np.ndarray,
    sample_rate: int,
    title: str = "Frequency Spectrum (FFT)",
    out_path: Optional[Path | str] = None,
) -> plt.Figure:
    """Plot FFT power spectrum (magnitude in dBFS vs logarithmic frequency)."""
    if data.ndim == 1:
        data = data[:, np.newaxis]

    num_samples, channels = data.shape
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_title(title, fontsize=12, fontweight="bold")

    # Apply Hanning window
    window = np.hanning(num_samples)

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
    freqs = np.fft.rfftfreq(num_samples, 1.0 / sample_rate)

    for ch in range(channels):
        fft_vals = np.fft.rfft(data[:, ch] * window)
        mag = np.abs(fft_vals) / (num_samples / 2.0)
        mag_db = 20.0 * np.log10(np.maximum(mag, 1e-7))
        color = colors[ch % len(colors)]
        ax.semilogx(freqs, mag_db, label=f"Ch {ch+1}", color=color, alpha=0.85, linewidth=1.0)

    ax.set_xlim([20.0, sample_rate / 2.0])
    ax.set_ylim([-100.0, 5.0])
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Magnitude (dBFS)")
    ax.grid(True, which="both", linestyle="--", alpha=0.5)
    ax.legend(loc="upper right")
    plt.tight_layout()

    if out_path:
        p = Path(out_path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p, dpi=150)
        plt.close(fig)

    return fig


def plot_spectrogram(
    data: np.ndarray,
    sample_rate: int,
    title: str = "Spectrogram (STFT)",
    out_path: Optional[Path | str] = None,
) -> plt.Figure:
    """Plot STFT spectrogram in dB color scale."""
    if data.ndim > 1:
        # Use first channel or mono sum
        mono = np.mean(data, axis=1)
    else:
        mono = data

    nperseg = 1024
    noverlap = 512
    freqs, times, Sxx = signal.spectrogram(
        mono,
        fs=sample_rate,
        window="hann",
        nperseg=nperseg,
        noverlap=noverlap,
        scaling="spectrum",
    )

    Sxx_db = 10.0 * np.log10(np.maximum(Sxx, 1e-12))

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_title(title, fontsize=12, fontweight="bold")
    im = ax.pcolormesh(
        times, freqs, Sxx_db, shading="gouraud", cmap="inferno", vmin=-90.0, vmax=0.0
    )
    ax.set_ylabel("Frequency (Hz)")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylim([0, min(sample_rate / 2.0, 16000.0)])
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Power (dBFS)")
    plt.tight_layout()

    if out_path:
        p = Path(out_path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p, dpi=150)
        plt.close(fig)

    return fig


def plot_audio_overview(
    data: np.ndarray,
    sample_rate: int,
    title: str = "Audio Laboratory Overview",
    out_path: Optional[Path | str] = None,
) -> plt.Figure:
    """Generate a combined 3-panel figure: Waveform, Power Spectrum, and Spectrogram."""
    fig = plt.figure(figsize=(12, 10))
    fig.suptitle(title, fontsize=14, fontweight="bold")

    if data.ndim == 1:
        data = data[:, np.newaxis]
    num_samples, channels = data.shape
    t = np.arange(num_samples) / sample_rate

    # Panel 1: Waveform
    ax1 = fig.add_subplot(3, 1, 1)
    ax1.plot(t, data[:, 0], color="#1f77b4", linewidth=0.7, label="Ch 1 (L)")
    if channels > 1:
        ax1.plot(t, data[:, 1], color="#ff7f0e", linewidth=0.7, alpha=0.7, label="Ch 2 (R)")
    ax1.set_title("Time-Domain Waveform")
    ax1.set_ylabel("Amplitude")
    ax1.set_xlabel("Time (s)")
    ax1.set_ylim([-1.05, 1.05])
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper right")

    # Panel 2: FFT Spectrum
    ax2 = fig.add_subplot(3, 1, 2)
    window = np.hanning(num_samples)
    freqs = np.fft.rfftfreq(num_samples, 1.0 / sample_rate)
    fft_vals = np.fft.rfft(data[:, 0] * window)
    mag_db = 20.0 * np.log10(np.maximum(np.abs(fft_vals) / (num_samples / 2.0), 1e-7))
    ax2.semilogx(freqs, mag_db, color="#2ca02c", linewidth=1.0)
    ax2.set_title("Power Spectrum (Ch 1)")
    ax2.set_xlim([20.0, sample_rate / 2.0])
    ax2.set_ylim([-90.0, 5.0])
    ax2.set_xlabel("Frequency (Hz)")
    ax2.set_ylabel("Magnitude (dBFS)")
    ax2.grid(True, which="both", linestyle="--", alpha=0.5)

    # Panel 3: Spectrogram
    ax3 = fig.add_subplot(3, 1, 3)
    mono = np.mean(data, axis=1)
    f, times, Sxx = signal.spectrogram(mono, fs=sample_rate, nperseg=1024, noverlap=512)
    Sxx_db = 10.0 * np.log10(np.maximum(Sxx, 1e-12))
    im = ax3.pcolormesh(times, f, Sxx_db, shading="gouraud", cmap="inferno", vmin=-80.0, vmax=0.0)
    ax3.set_title("Time-Frequency Spectrogram")
    ax3.set_xlabel("Time (s)")
    ax3.set_ylabel("Frequency (Hz)")
    ax3.set_ylim([0, min(sample_rate / 2.0, 16000.0)])
    cbar = fig.colorbar(im, ax=ax3, orientation="vertical")
    cbar.set_label("dBFS")

    plt.tight_layout()

    if out_path:
        p = Path(out_path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p, dpi=150)
        plt.close(fig)

    return fig
