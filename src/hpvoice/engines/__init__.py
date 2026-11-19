"""HP Voice Studio — src/hpvoice/engines."""

from .base import AudioResult, EngineBase, SynthesisOptions, VoiceInfo
from .cpu_detect import CpuInfo, default_precision, detect_cpu, weak_machine_advice
from .v3_engine import V3Engine

__all__ = [
    "AudioResult",
    "EngineBase",
    "SynthesisOptions",
    "VoiceInfo",
    "V3Engine",
    "CpuInfo",
    "detect_cpu",
    "default_precision",
    "weak_machine_advice",
]
