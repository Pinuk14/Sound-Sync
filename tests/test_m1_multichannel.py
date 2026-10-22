"""Tests for 5.1 multichannel layouts and channel identification."""

import numpy as np

from speakersync.lab.generators import generate_channel_identification_6ch
from speakersync.lab.inspect import inspect_audio


def test_channel_identification_6ch():
    """Verify that a 6-channel 5.1 tone-per-channel signal isolates channels accurately."""
    sr = 48000
    tone_duration_s = 0.5
    audio_6ch, layout_labels = generate_channel_identification_6ch(
        tone_duration_s=tone_duration_s,
        sample_rate=sr,
    )

    assert audio_6ch.shape[1] == 6
    assert layout_labels == ["FL", "FR", "C", "LFE", "Ls", "Rs"]

    # Each channel should have energy during its respective slice, and silence during others
    num_samples_per_tone = int(tone_duration_s * sr)

    for ch_idx in range(6):
        start_samp = ch_idx * num_samples_per_tone
        end_samp = (ch_idx + 1) * num_samples_per_tone

        # Active window in channel ch_idx
        active_segment = audio_6ch[start_samp:end_samp, ch_idx]
        active_rms = np.sqrt(np.mean(active_segment**2))
        assert active_rms > 0.1, f"Channel {layout_labels[ch_idx]} was inactive in its slot!"

        # Inactive channels in this window must be completely silent
        for other_ch in range(6):
            if other_ch != ch_idx:
                bleed = audio_6ch[start_samp:end_samp, other_ch]
                assert np.all(bleed == 0.0), (
                    f"Bleed on {layout_labels[other_ch]} during "
                    f"{layout_labels[ch_idx]} active slot!"
                )

    metrics = inspect_audio(audio_6ch, sample_rate=sr, channel_layout="5.1")
    assert metrics.num_channels == 6
    assert len(metrics.peak_dbfs) == 6
    for ch_idx in range(6):
        assert metrics.peak_dbfs[ch_idx] > -12.0
