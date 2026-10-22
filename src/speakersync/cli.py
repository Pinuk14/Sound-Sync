"""SpeakerSync command line interface."""

from pathlib import Path

import typer

app = typer.Typer(
    name="speakersync",
    help="SpeakerSync: Dual Bluetooth Speaker Synchronization and Audio Routing.",
    no_args_is_help=True,
)


@app.command()
def version() -> None:
    """Print the SpeakerSync version."""
    import speakersync

    typer.echo(f"SpeakerSync v{speakersync.__version__}")


@app.command()
def devices(
    output_json: Path = typer.Option(
        Path("evidence/M0/devices.json"),
        "--out",
        help="Path to save raw device JSON data.",
    ),
) -> None:
    """List all audio output and input devices via PortAudio."""
    import sys

    # Add project tools directory to sys.path if not present
    tools_dir = Path(__file__).resolve().parent.parent.parent / "tools"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))

    import list_devices

    data = list_devices.get_devices_data()
    list_devices.print_devices_table(data)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    import json

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    typer.echo(f"\n[INFO] Device details saved to {output_json.resolve()}")


@app.command()
def inspect(
    file_path: Path = typer.Argument(..., help="Path to audio file or video container to inspect."),
    json_out: Path = typer.Option(
        None,
        "--json-out",
        help="Optional path to export inspection metrics as JSON.",
    ),
) -> None:
    """Inspect an audio file or video container (LUFS, Peak, RMS, Crest, DC, Layout)."""
    import json

    from speakersync.lab.inspect import format_inspection_report, inspect_audio
    from speakersync.player.decode import decode_audio

    data, info = decode_audio(file_path)
    res = inspect_audio(data, info.sample_rate, info.channel_layout)

    typer.echo(format_inspection_report(res, str(file_path.name)))

    if json_out:
        json_out = Path(json_out).resolve()
        json_out.parent.mkdir(parents=True, exist_ok=True)
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(res.to_dict(), f, indent=2)
        typer.echo(f"[INFO] Exported inspection metrics to {json_out}")


@app.command()
def generate_signals(
    out_dir: Path = typer.Option(
        Path("evidence/M1/signals"),
        "--out-dir",
        help="Directory to save generated test signals and synthetic scenes.",
    ),
) -> None:
    """Generate reference calibration signals and the canonical 6-segment synthetic scene."""
    import json

    import soundfile as sf

    from speakersync.lab.generators import (
        generate_channel_identification_6ch,
        generate_click_train,
        generate_log_sweep,
        generate_noise,
        generate_sine,
    )
    from speakersync.lab.synthetic import build_synthetic_scene

    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    sr = 48000
    # 1. Sine 1 kHz at -6 dBFS
    sine_1k = generate_sine(1000.0, 2.0, sr, -6.0)
    sf.write(str(out_dir / "sine_1khz_m6dbfs.wav"), sine_1k, sr)

    # 2. Log sweep
    sweep = generate_log_sweep(20.0, 20000.0, 3.0, sr, -6.0)
    sf.write(str(out_dir / "log_sweep_20_20k.wav"), sweep, sr)

    # 3. Click train
    clicks = generate_click_train(0.1, 2.0, sr, 0.0)
    sf.write(str(out_dir / "click_train_100ms.wav"), clicks, sr)

    # 4. Pink noise
    pink = generate_noise("pink", 2.0, sr, -12.0)
    sf.write(str(out_dir / "pink_noise_m12dbfs.wav"), pink, sr)

    # 5. 6-channel 5.1 identification tone
    ident_6ch, _ = generate_channel_identification_6ch(0.5, sr)
    sf.write(str(out_dir / "channel_id_5_1.wav"), ident_6ch, sr)

    # 6. Canonical 6-segment synthetic scene
    scene, metadata = build_synthetic_scene(2.0, sr)
    sf.write(str(out_dir / "synthetic_scene.wav"), scene, sr)

    with open(out_dir / "synthetic_scene_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    typer.echo(f"[SUCCESS] Calibrated signals and synthetic scene saved to {out_dir}")


@app.command()
def plot(
    file_path: Path = typer.Argument(..., help="Path to audio file to plot."),
    out_path: Path = typer.Option(
        None,
        "--out",
        help="Path to save output figure PNG.",
    ),
) -> None:
    """Generate waveform, spectrum, and spectrogram plots for an audio file."""
    from speakersync.lab.plots import plot_audio_overview
    from speakersync.player.decode import decode_audio

    data, info = decode_audio(file_path)
    output = out_path or file_path.with_suffix(".png")
    plot_audio_overview(data, info.sample_rate, f"Analysis: {file_path.name}", output)
    typer.echo(f"[SUCCESS] Generated overview plot at {output.resolve()}")


if __name__ == "__main__":
    app()

