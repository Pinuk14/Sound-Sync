"""Audio decoding pipeline via FFmpeg and soundfile.

Decodes audio files and video containers directly to float32 PCM blocks while
preserving channel layouts without silent downmixing.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import soundfile as sf


def get_ffmpeg_binary() -> str:
    """Return the path to the FFmpeg executable."""
    # 1. Check system PATH
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg

    # 2. Check imageio_ffmpeg bundled binary
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass

    raise RuntimeError(
        "FFmpeg executable not found. Please install FFmpeg on system PATH "
        "or install imageio-ffmpeg."
    )


@dataclass
class AudioInfo:
    """Metadata describing an audio stream."""

    path: Path
    sample_rate: int
    channels: int
    channel_layout: str
    duration_seconds: float
    num_frames: int
    codec: str


def _map_channel_layout(channels: int, raw_layout: Optional[str] = None) -> str:
    """Map channel count to canonical channel layout name."""
    if raw_layout:
        clean = raw_layout.strip().lower()
        if "5.1" in clean:
            return "5.1"
        if "7.1" in clean:
            return "7.1"
        if "stereo" in clean:
            return "stereo"
        if "mono" in clean:
            return "mono"

    if channels == 1:
        return "mono"
    elif channels == 2:
        return "stereo"
    elif channels == 6:
        return "5.1"
    elif channels == 8:
        return "7.1"
    else:
        return f"{channels}ch"


def get_audio_info(path: Path | str) -> AudioInfo:
    """Extract metadata for an audio file or video container without full decoding."""
    p = Path(path).resolve()
    if not p.is_file():
        raise FileNotFoundError(f"Audio file not found: {p}")

    ext = p.suffix.lower()
    # Fast path for native formats supported by libsndfile
    if ext in [".wav", ".flac", ".ogg"]:
        try:
            info = sf.info(str(p))
            layout = _map_channel_layout(info.channels)
            return AudioInfo(
                path=p,
                sample_rate=info.samplerate,
                channels=info.channels,
                channel_layout=layout,
                duration_seconds=info.duration,
                num_frames=info.frames,
                codec=info.format,
            )
        except Exception:
            pass

    # Use FFmpeg to probe metadata for containers / other codecs
    ffmpeg_exe = get_ffmpeg_binary()
    cmd = [
        ffmpeg_exe,
        "-hide_banner",
        "-i",
        str(p),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stderr = proc.stderr

    # Parse duration: "Duration: 00:00:05.12, ..."
    duration = 0.0
    dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", stderr)
    if dur_match:
        h, m, s = float(dur_match.group(1)), float(dur_match.group(2)), float(dur_match.group(3))
        duration = h * 3600 + m * 60 + s

    # Parse audio stream: "Stream #0:0...: Audio: aac, 48000 Hz, stereo, fltp, 128 kb/s"
    stream_match = re.search(r"Stream.*Audio:\s*([^,\n]+),\s*(\d+)\s*Hz,\s*([^,\n]+)", stderr)
    codec = "unknown"
    sample_rate = 44100
    channels = 2
    channel_layout = "stereo"

    if stream_match:
        codec = stream_match.group(1).strip()
        sample_rate = int(stream_match.group(2))
        layout_str = stream_match.group(3).strip()

        if "mono" in layout_str:
            channels = 1
            channel_layout = "mono"
        elif "stereo" in layout_str:
            channels = 2
            channel_layout = "stereo"
        elif "5.1" in layout_str:
            channels = 6
            channel_layout = "5.1"
        elif "7.1" in layout_str:
            channels = 8
            channel_layout = "7.1"
        else:
            # Try to parse channel count if format like "2 channels"
            ch_match = re.search(r"(\d+)\s*channels", layout_str)
            if ch_match:
                channels = int(ch_match.group(1))
                channel_layout = _map_channel_layout(channels)

    num_frames = int(duration * sample_rate)

    return AudioInfo(
        path=p,
        sample_rate=sample_rate,
        channels=channels,
        channel_layout=channel_layout,
        duration_seconds=duration,
        num_frames=num_frames,
        codec=codec,
    )


def decode_audio(
    path: Path | str,
    target_sr: Optional[int] = None,
) -> Tuple[np.ndarray, AudioInfo]:
    """Decode any audio file or video container into float32 PCM arrays.

    Returns:
        (data, info) where data is a 2D np.ndarray of shape (num_samples, channels)
        with values in range [-1.0, 1.0].
    """
    p = Path(path).resolve()
    info = get_audio_info(p)
    ext = p.suffix.lower()

    # Fast path for soundfile supported native formats without resampling needed
    if ext in [".wav", ".flac", ".ogg"] and (target_sr is None or target_sr == info.sample_rate):
        data, sr = sf.read(str(p), dtype="float32", always_2d=True)
        return data, info

    # FFmpeg pipe decode to raw float32 LE PCM
    ffmpeg_exe = get_ffmpeg_binary()
    out_sr = target_sr if target_sr is not None else info.sample_rate

    cmd = [
        ffmpeg_exe,
        "-v",
        "error",
        "-i",
        str(p),
        "-vn",  # Disable video
        "-f",
        "f32le",
        "-acodec",
        "pcm_f32le",
    ]
    if target_sr is not None:
        cmd.extend(["-ar", str(out_sr)])

    cmd.append("-")

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        err_msg = proc.stderr.decode("utf-8", errors="ignore")
        raise RuntimeError(f"FFmpeg decoding failed: {err_msg}")

    raw_bytes = proc.stdout
    data = np.frombuffer(raw_bytes, dtype=np.float32)

    channels = info.channels if info.channels > 0 else 2
    if len(data) % channels != 0:
        # Trim incomplete tail frame if any
        data = data[: len(data) - (len(data) % channels)]

    data = data.reshape(-1, channels)

    # Update info duration and frames if resampled
    actual_frames = data.shape[0]
    actual_duration = actual_frames / out_sr
    updated_info = AudioInfo(
        path=p,
        sample_rate=out_sr,
        channels=channels,
        channel_layout=info.channel_layout,
        duration_seconds=actual_duration,
        num_frames=actual_frames,
        codec=info.codec,
    )
    return data, updated_info


def encode_to_video_container(audio_path: Path | str, output_path: Path | str) -> None:
    """Create a synthetic MP4 video container combining a test video stream with the given audio."""
    ffmpeg_exe = get_ffmpeg_binary()
    a_path = Path(audio_path).resolve()
    out_p = Path(output_path).resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)

    # Generate test video frame with audio
    cmd = [
        ffmpeg_exe,
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=320x240:r=24",
        "-i",
        str(a_path),
        "-c:v",
        "mpeg4",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(out_p),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg video encoding failed: {proc.stderr}")
