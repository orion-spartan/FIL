from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AudioMeterState:
    level: float = 0.0
    voice_detected: bool = False

    @property
    def percentage(self) -> int:
        clamped = max(0.0, min(self.level, 1.0))
        return int(clamped * 100)


def render_ascii_meter(state: AudioMeterState, *, width: int = 16) -> str:
    clamped = max(0.0, min(state.level, 1.0))
    filled = min(int(round(clamped * width)), width)
    return f"[{'#' * filled}{'-' * (width - filled)}] {state.percentage:02d}%"
