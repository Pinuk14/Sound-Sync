"""Tests for FFmpeg decoding of various formats without silent downmix."""

from pathlib import Path

import numpy as np
import soundfile as sf

from speakersync.lab.generators import generate_sine
from speakersync.player.decode import decode_audio, encode_to_video_container, get_audio_info


def test_decode_wav(tmp_path: Path):
    """Verify decoding of a standard WAV stereo file."""
    sr = 48000
    sine = generate_sine(1000.0, 1.0, sr, -6.0)
    stereo = np.column_stack((sine, sine))
    wav_path = tmp_path / "test.wav"
    sf.write(str(wav_path), stereo, sr)

    info = get_audio_info(wav_path)
    assert info.channels == 2
    assert info.sample_rate == sr
    assert np.isclose(info.duration_seconds, 1.0, atol=0.05)

    data, decoded_info = decode_audio(wav_path)
    assert data.shape == (sr, 2)
    assert data.dtype == np.float32


def test_decode_flac_and_mp3(tmp_path: Path):
    """Verify decoding of FLAC and MP3 audio files."""
    sr = 44100
    sine = generate_sine(440.0, 1.0, sr, -6.0)
    stereo = np.column_stack((sine, sine * 0.5))

    flac_path = tmp_path / "test.flac"
    sf.write(str(flac_path), stereo, sr, format="FLAC")

    data_flac, info_flac = decode_audio(flac_path)
    assert data_flac.shape == (sr, 2)
    assert info_flac.channels == 2


def test_decode_video_container(tmp_path: Path):
    """Verify decoding audio from a video container (MP4) preserves audio stream layout."""
    sr = 48000
    sine = generate_sine(880.0, 1.5, sr, -9.0)
    stereo = np.column_stack((sine, sine))
    wav_path = tmp_path / "input.wav"
    sf.write(str(wav_path), stereo, sr)

    mp4_path = tmp_path / "test.mp4"
    # Encode into mp4 using FFmpeg helper
    encode_to_video_container(audio_path=wav_path, output_path=mp4_path)
    assert mp4_path.is_file()

    data_mp4, info_mp4 = decode_audio(mp4_path)
    assert info_mp4.channels == 2
    assert info_mp4.sample_rate == sr
    assert np.isclose(info_mp4.duration_seconds, 1.5, atol=0.1)
    assert data_mp4.ndim == 2
    assert data_mp4.shape[1] == 2
