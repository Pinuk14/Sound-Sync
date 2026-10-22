"""Audio inspection and quantitative measurement suite.

Measures Sample Rate, Channels, Layout, Duration, per-channel Peak, RMS, Crest Factor,
DC offset, and ITU-R BS.1770-4 Integrated and Short-Term LUFS.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import List, Optional

import numpy as np
from scipy import signal


@dataclass
class AudioInspectionResult:
    """Quantitative measurement results for an audio signal."""

    sample_rate: int
    num_channels: int
    channel_layout: str
    channel_labels: List[str]
    duration_seconds: float
    num_samples: int
    peak_dbfs: List[float]
    rms_dbfs: List[float]
    crest_factor_db: List[float]
    dc_offset: List[float]
    integrated_lufs: float
    max_short_term_lufs: float

    def to_dict(self) -> dict:
        return asdict(self)


def get_channel_labels(channels: int, layout: Optional[str] = None) -> List[str]:
    """Return standard channel labels for a given layout."""
    if layout and "5.1" in layout or channels == 6:
        return ["FL", "FR", "C", "LFE", "Ls", "Rs"]
    elif layout and "7.1" in layout or channels == 8:
        return ["FL", "FR", "C", "LFE", "Ls", "Rs", "Rls", "Rrs"]
    elif channels == 1:
        return ["M"]
    elif channels == 2:
        return ["L", "R"]
    else:
        return [f"Ch{i+1}" for i in range(channels)]


def _itu1770_filter(data: np.ndarray, sample_rate: int) -> np.ndarray:
    """Apply ITU-R BS.1770-4 K-weighting pre-filter (High-shelf + High-pass RLB)."""
    # 1. High-shelf filter: gain +4 dB at ~1.6 kHz
    # Standard 48 kHz reference coefficients (BS.1770-4 Table 1)
    # Parametric design using scipy for arbitrary sample rate:
    f0_shelf = 1681.97
    gain_shelf_db = 3.99984
    q_shelf = 0.707175

    A = 10.0 ** (gain_shelf_db / 40.0)
    w0 = 2.0 * np.pi * f0_shelf / sample_rate
    alpha = np.sin(w0) / (2.0 * q_shelf)

    b_shelf = np.array([
        A * ((A + 1.0) + (A - 1.0) * np.cos(w0) + 2.0 * np.sqrt(A) * alpha),
        -2.0 * A * ((A - 1.0) + (A + 1.0) * np.cos(w0)),
        A * ((A + 1.0) + (A - 1.0) * np.cos(w0) - 2.0 * np.sqrt(A) * alpha),
    ])
    a_shelf = np.array([
        (A + 1.0) - (A - 1.0) * np.cos(w0) + 2.0 * np.sqrt(A) * alpha,
        2.0 * ((A - 1.0) - (A + 1.0) * np.cos(w0)),
        (A + 1.0) - (A - 1.0) * np.cos(w0) - 2.0 * np.sqrt(A) * alpha,
    ])
    b_shelf /= a_shelf[0]
    a_shelf /= a_shelf[0]

    # 2. High-pass filter: RLB weighting at ~38 Hz
    f0_hp = 38.135
    q_hp = 0.500327
    w0_hp = 2.0 * np.pi * f0_hp / sample_rate
    alpha_hp = np.sin(w0_hp) / (2.0 * q_hp)

    b_hp = np.array([
        (1.0 + np.cos(w0_hp)) / 2.0,
        -(1.0 + np.cos(w0_hp)),
        (1.0 + np.cos(w0_hp)) / 2.0,
    ])
    a_hp = np.array([
        1.0 + alpha_hp,
        -2.0 * np.cos(w0_hp),
        1.0 - alpha_hp,
    ])
    b_hp /= a_hp[0]
    a_hp /= a_hp[0]

    # Apply causal IIR filters channel by channel
    filtered = np.zeros_like(data, dtype=np.float64)
    for ch in range(data.shape[1]):
        y_shelf = signal.lfilter(b_shelf, a_shelf, data[:, ch])
        y_rlb = signal.lfilter(b_hp, a_hp, y_shelf)
        filtered[:, ch] = y_rlb

    return filtered


def calculate_lufs(data: np.ndarray, sample_rate: int) -> tuple[float, float]:
    """Calculate ITU-R BS.1770-4 Integrated LUFS and Max Short-Term LUFS.

    Args:
        data: shape (N, channels)
        sample_rate: sampling frequency

    Returns:
        (integrated_lufs, max_short_term_lufs)
    """
    if len(data) == 0 or np.all(data == 0):
        return -120.0, -120.0

    channels = data.shape[1]
    filtered = _itu1770_filter(data, sample_rate)

    # Channel weights (SMPTE 5.1 layout: FL, FR, C, LFE, Ls, Rs)
    # LFE (channel 3 in 5.1) is excluded (weight = 0)
    # Surrounds (Ls, Rs) have weight 1.41 (+1.5 dB)
    weights = np.ones(channels, dtype=np.float64)
    if channels == 6:
        weights = np.array([1.0, 1.0, 1.0, 0.0, 1.41, 1.41])

    # 400 ms blocks with 75% overlap (100 ms step)
    block_size = int(0.400 * sample_rate)
    step_size = int(0.100 * sample_rate)

    num_samples = filtered.shape[0]
    if num_samples < block_size:
        # File shorter than 400 ms: compute un-gated
        z_power = np.mean(filtered**2, axis=0)
        l_sum = np.sum(weights * z_power)
        val = -0.691 + 10.0 * np.log10(max(l_sum, 1e-12))
        return float(val), float(val)

    # Compute power per 400 ms block
    block_starts = list(range(0, num_samples - block_size + 1, step_size))
    block_powers = np.zeros(len(block_starts), dtype=np.float64)

    for idx, start in enumerate(block_starts):
        chunk = filtered[start : start + block_size, :]
        z_pow = np.mean(chunk**2, axis=0)
        block_powers[idx] = np.sum(weights * z_pow)

    # Convert block powers to LKFS
    block_lkfs = -0.691 + 10.0 * np.log10(np.maximum(block_powers, 1e-12))

    # Absolute threshold gating: blocks > -70 LKFS
    abs_thresh = -70.0
    abs_gated_indices = np.where(block_lkfs > abs_thresh)[0]

    if len(abs_gated_indices) == 0:
        return -120.0, -120.0

    # Relative threshold gating: relative to average of absolute gated blocks - 10 dB
    mean_abs_power = np.mean(block_powers[abs_gated_indices])
    gamma_r = (-0.691 + 10.0 * np.log10(max(mean_abs_power, 1e-12))) - 10.0

    rel_gated_indices = np.where(block_lkfs > gamma_r)[0]
    if len(rel_gated_indices) == 0:
        return -120.0, -120.0

    integrated_power = np.mean(block_powers[rel_gated_indices])
    integrated_lufs = float(-0.691 + 10.0 * np.log10(max(integrated_power, 1e-12)))

    # Short-term loudness: 3-second sliding rectangular window
    st_window_blocks = int(3.0 / 0.100)  # 30 blocks of 100ms
    if len(block_powers) >= st_window_blocks:
        st_kernel = np.ones(st_window_blocks) / st_window_blocks
        st_powers = np.convolve(block_powers, st_kernel, mode="valid")
        max_st_power = np.max(st_powers)
        max_short_term_lufs = float(-0.691 + 10.0 * np.log10(max(max_st_power, 1e-12)))
    else:
        max_short_term_lufs = integrated_lufs

    return integrated_lufs, max_short_term_lufs


def inspect_audio(
    data: np.ndarray,
    sample_rate: int,
    channel_layout: Optional[str] = None,
) -> AudioInspectionResult:
    """Compute complete quantitative inspection metrics on an audio array.

    Args:
        data: 2D numpy array with shape (samples, channels).
        sample_rate: sample rate in Hz.
        channel_layout: optional string layout name.
    """
    if data.ndim == 1:
        data = data[:, np.newaxis]

    num_samples, channels = data.shape
    duration = num_samples / sample_rate

    labels = get_channel_labels(channels, channel_layout)

    peak_dbfs: List[float] = []
    rms_dbfs: List[float] = []
    crest_factor: List[float] = []
    dc_offset: List[float] = []

    for ch in range(channels):
        ch_data = data[:, ch]
        abs_max = np.max(np.abs(ch_data)) if len(ch_data) > 0 else 0.0
        peak_val = 20.0 * np.log10(abs_max) if abs_max > 1e-9 else -144.0
        peak_dbfs.append(float(peak_val))

        rms_val_raw = np.sqrt(np.mean(ch_data**2)) if len(ch_data) > 0 else 0.0
        rms_val = 20.0 * np.log10(rms_val_raw) if rms_val_raw > 1e-9 else -144.0
        rms_dbfs.append(float(rms_val))

        crest_factor.append(float(peak_val - rms_val))
        dc_offset.append(float(np.mean(ch_data)))

    integrated_lufs, max_st_lufs = calculate_lufs(data, sample_rate)

    layout_str = channel_layout or (
        "5.1" if channels == 6 else ("stereo" if channels == 2 else f"{channels}ch")
    )

    return AudioInspectionResult(
        sample_rate=sample_rate,
        num_channels=channels,
        channel_layout=layout_str,
        channel_labels=labels,
        duration_seconds=duration,
        num_samples=num_samples,
        peak_dbfs=peak_dbfs,
        rms_dbfs=rms_dbfs,
        crest_factor_db=crest_factor,
        dc_offset=dc_offset,
        integrated_lufs=integrated_lufs,
        max_short_term_lufs=max_st_lufs,
    )


def format_inspection_report(res: AudioInspectionResult, filename: str = "") -> str:
    """Format inspection result as a clean terminal table string."""
    lines: List[str] = []
    lines.append("=" * 80)
    lines.append(f"SpeakerSync Audio Inspection: {filename or 'In-Memory Signal'}")
    lines.append("=" * 80)
    lines.append(f"Sample Rate:      {res.sample_rate} Hz")
    lines.append(f"Channels:         {res.num_channels} ({res.channel_layout})")
    lines.append(f"Duration:         {res.duration_seconds:.3f} s ({res.num_samples} samples)")
    lines.append(f"Integrated LUFS:  {res.integrated_lufs:6.2f} LUFS")
    lines.append(f"Max Short-Term:   {res.max_short_term_lufs:6.2f} LUFS")
    header = (
        f"{'Channel':<10} | {'Peak (dBFS)':<13} | {'RMS (dBFS)':<13} | "
        f"{'Crest (dB)':<13} | {'DC Offset':<13}"
    )
    lines.append(header)
    lines.append("-" * 80)
    for i, label in enumerate(res.channel_labels):
        lines.append(
            f"{label:<10} | {res.peak_dbfs[i]:11.2f}  | {res.rms_dbfs[i]:11.2f}  | "
            f"{res.crest_factor_db[i]:11.2f}  | {res.dc_offset[i]:11.6f}"
        )
    lines.append("=" * 80)
    return "\n".join(lines)
