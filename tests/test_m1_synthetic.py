"""Tests for the 6-segment synthetic scene builder."""

import numpy as np

from speakersync.lab.inspect import inspect_audio
from speakersync.lab.synthetic import build_synthetic_scene


def test_synthetic_scene_segments():
    """Verify that each segment of the synthetic scene satisfies its specified ground truth."""
    sr = 48000
    scene, metadata = build_synthetic_scene(segment_duration_s=2.0, sample_rate=sr)

    assert scene.ndim == 2
    assert scene.shape[1] == 2  # Stereo

    segments = metadata["segments"]
    assert len(segments) == 6
    names = [s["name"] for s in segments]
    assert names == [
        "S1_dialogue",
        "S2_small_sounds",
        "S3_explosion",
        "S4_dialogue_explosion",
        "S5_music",
        "S6_room_tone",
    ]

    # 1. S1 Dialogue: speech-like noise 200-4000 Hz, target -23 LUFS
    s1_meta = segments[0]
    s1_audio = scene[s1_meta["start_sample"]:s1_meta["end_sample"], :]
    s1_metrics = inspect_audio(s1_audio, sample_rate=sr)
    assert np.isclose(s1_metrics.integrated_lufs, -23.0, atol=1.5), (
        f"S1 Dialogue LUFS should be -23 +- 1.5, got {s1_metrics.integrated_lufs:.2f}"
    )

    # 2. S2 Small sounds: soft clicks/bursts, target -40 LUFS
    s2_meta = segments[1]
    s2_audio = scene[s2_meta["start_sample"]:s2_meta["end_sample"], :]
    s2_metrics = inspect_audio(s2_audio, sample_rate=sr)
    assert np.isclose(s2_metrics.integrated_lufs, -40.0, atol=2.5), (
        f"S2 Small sounds LUFS should be -40 +- 2.5, got {s2_metrics.integrated_lufs:.2f}"
    )

    # 3. S3 Explosion: broadband + <100 Hz burst, peak -8 dBFS
    s3_meta = segments[2]
    s3_audio = scene[s3_meta["start_sample"]:s3_meta["end_sample"], :]
    s3_metrics = inspect_audio(s3_audio, sample_rate=sr)
    max_peak = max(s3_metrics.peak_dbfs)
    assert np.isclose(max_peak, -8.0, atol=1.0), (
        f"S3 Explosion peak should be -8.0 +- 1.0 dBFS, got {max_peak:.2f}"
    )

    # 4. S4 Dialogue + Explosion simultaneously: both dialogue band and low end active
    s4_meta = segments[3]
    s4_audio = scene[s4_meta["start_sample"]:s4_meta["end_sample"], :]
    s4_metrics = inspect_audio(s4_audio, sample_rate=sr)
    assert max(s4_metrics.peak_dbfs) >= -9.0

    # 5. S5 Music: layered instruments, balanced stereo
    s5_meta = segments[4]
    s5_audio = scene[s5_meta["start_sample"]:s5_meta["end_sample"], :]
    s5_metrics = inspect_audio(s5_audio, sample_rate=sr)
    assert -25.0 < s5_metrics.integrated_lufs < -10.0

    # 6. S6 Quiet room tone: low energy
    s6_meta = segments[5]
    s6_audio = scene[s6_meta["start_sample"]:s6_meta["end_sample"], :]
    s6_metrics = inspect_audio(s6_audio, sample_rate=sr)
    assert s6_metrics.integrated_lufs < -45.0
