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


if __name__ == "__main__":
    app()

