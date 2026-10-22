"""Parameter registry for SpeakerSync.

Every tunable parameter is registered here with its type, unit, valid range,
default value, and smoothing/transition time to ensure click-free live adjustments.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ParamSpec:
    """Specification of a controllable system parameter."""

    name: str
    param_type: type
    default: Any
    unit: str = ""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    smooth_ms: float = 20.0
    description: str = ""


# Master parameter registry
PARAMETER_REGISTRY: Dict[str, ParamSpec] = {
    # Latency parameters (R2, R3)
    "latency.front.trim_ms": ParamSpec(
        name="latency.front.trim_ms",
        param_type=float,
        default=0.0,
        unit="ms",
        min_value=-300.0,
        max_value=300.0,
        step=1.0,
        smooth_ms=20.0,
        description="Manual latency trim for FRONT speaker (positive delays speaker)",
    ),
    "latency.back.trim_ms": ParamSpec(
        name="latency.back.trim_ms",
        param_type=float,
        default=0.0,
        unit="ms",
        min_value=-300.0,
        max_value=300.0,
        step=1.0,
        smooth_ms=20.0,
        description="Manual latency trim for BACK speaker (positive delays speaker)",
    ),
    "latency.global_av_offset_ms": ParamSpec(
        name="latency.global_av_offset_ms",
        param_type=float,
        default=0.0,
        unit="ms",
        min_value=-500.0,
        max_value=500.0,
        step=1.0,
        smooth_ms=50.0,
        description="Global audio/video offset for lip-sync alignment",
    ),
    # Content & Immersion parameters (R1, R4)
    "router.immersion": ParamSpec(
        name="router.immersion",
        param_type=float,
        default=0.7,
        unit="",
        min_value=0.0,
        max_value=1.0,
        step=0.05,
        smooth_ms=30.0,
        description="Immersion intensity scaling impact send to BACK and ducking in FRONT",
    ),
    "router.dialogue_guard": ParamSpec(
        name="router.dialogue_guard",
        param_type=float,
        default=0.8,
        unit="",
        min_value=0.0,
        max_value=1.0,
        step=0.05,
        smooth_ms=30.0,
        description="Preserves front speech-band clarity during loud events",
    ),
    "levels.front_trim_db": ParamSpec(
        name="levels.front_trim_db",
        param_type=float,
        default=0.0,
        unit="dB",
        min_value=-24.0,
        max_value=12.0,
        step=0.5,
        smooth_ms=20.0,
        description="Level trim for FRONT speaker",
    ),
    "levels.back_trim_db": ParamSpec(
        name="levels.back_trim_db",
        param_type=float,
        default=0.0,
        unit="dB",
        min_value=-24.0,
        max_value=12.0,
        step=0.5,
        smooth_ms=20.0,
        description="Level trim for BACK speaker",
    ),
    "levels.back_cap_dbfs": ParamSpec(
        name="levels.back_cap_dbfs",
        param_type=float,
        default=-6.0,
        unit="dBFS",
        min_value=-24.0,
        max_value=0.0,
        step=0.5,
        smooth_ms=10.0,
        description="Safety ceiling to protect rear speaker driver",
    ),
}
