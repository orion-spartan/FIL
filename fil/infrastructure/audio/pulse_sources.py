from __future__ import annotations

import subprocess

from fil.domain.models.audio import AudioInputMode


class PulseSourceResolver:
    def default_source(self) -> str:
        return self._pactl_value("Default Source")

    def default_sink(self) -> str:
        return self._pactl_value("Default Sink")

    def system_monitor_source(self) -> str:
        sink = self.default_sink()
        return f"{sink}.monitor"

    def resolve(self, mode: AudioInputMode) -> list[str]:
        if mode == AudioInputMode.MIC:
            return [self.default_source()]
        if mode == AudioInputMode.SYSTEM:
            return [self.system_monitor_source()]
        return [self.default_source(), self.system_monitor_source()]

    @staticmethod
    def _pactl_value(label: str) -> str:
        result = subprocess.run(["pactl", "info"], check=True, capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if line.startswith(f"{label}:"):
                return line.split(":", 1)[1].strip()
        raise RuntimeError(f"could not resolve {label.lower()}")
