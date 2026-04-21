from __future__ import annotations

import threading
from dataclasses import dataclass

from fil.domain.models.audio import AudioInputMode
from fil.infrastructure.audio.live_meter import FfmpegLiveMeterSource, LiveMeterHandle
from fil.infrastructure.audio.pulse_sources import PulseSourceResolver
from fil.shared.audio import pcm16le_rms_level
from fil.shared.meter import AudioMeterState


@dataclass(slots=True)
class AudioMeterSnapshot:
    mic: AudioMeterState
    system: AudioMeterState


class AudioMeterRuntime:
    VOICE_THRESHOLD = 0.015

    def __init__(
        self,
        *,
        source_factory: FfmpegLiveMeterSource,
        source_resolver: PulseSourceResolver,
        frame_window_seconds: float = 0.05,
    ) -> None:
        self.source_factory = source_factory
        self.source_resolver = source_resolver
        self.frame_window_seconds = frame_window_seconds

        self._lock = threading.Lock()
        self._snapshot = AudioMeterSnapshot(mic=AudioMeterState(), system=AudioMeterState())
        self._stop_event = threading.Event()
        self._workers: list[threading.Thread] = []
        self._handles: dict[str, LiveMeterHandle] = {}

    def start(self, input_mode: AudioInputMode) -> None:
        self.stop()

        self._stop_event = threading.Event()
        source_map = self._resolve_sources(input_mode)
        with self._lock:
            self._snapshot = AudioMeterSnapshot(mic=AudioMeterState(), system=AudioMeterState())

        try:
            for channel, source_name in source_map.items():
                handle = self.source_factory.start(source_name)
                self._handles[channel] = handle
                worker = threading.Thread(
                    target=self._read_loop,
                    args=(channel, handle),
                    name=f"fil-meter-{channel}",
                    daemon=True,
                )
                self._workers.append(worker)
                worker.start()
        except Exception:
            self.stop()
            raise

    def stop(self) -> None:
        self._stop_event.set()

        handles = list(self._handles.values())
        for handle in handles:
            try:
                self.source_factory.stop(handle)
            except Exception:
                self.source_factory.force_stop(handle)

        for worker in self._workers:
            worker.join(timeout=1)

        self._handles.clear()
        self._workers.clear()
        with self._lock:
            self._snapshot = AudioMeterSnapshot(mic=AudioMeterState(), system=AudioMeterState())

    def snapshot(self) -> AudioMeterSnapshot:
        with self._lock:
            return AudioMeterSnapshot(
                mic=AudioMeterState(level=self._snapshot.mic.level, voice_detected=self._snapshot.mic.voice_detected),
                system=AudioMeterState(level=self._snapshot.system.level, voice_detected=self._snapshot.system.voice_detected),
            )

    def _resolve_sources(self, input_mode: AudioInputMode) -> dict[str, str]:
        if input_mode == AudioInputMode.MIC:
            return {"mic": self.source_resolver.default_source()}
        if input_mode == AudioInputMode.SYSTEM:
            return {"system": self.source_resolver.system_monitor_source()}
        return {
            "mic": self.source_resolver.default_source(),
            "system": self.source_resolver.system_monitor_source(),
        }

    def _read_loop(self, channel: str, handle: LiveMeterHandle) -> None:
        bytes_per_second = self.source_factory.sample_rate * 2
        frame_bytes = max(int(bytes_per_second * self.frame_window_seconds), 320)
        if frame_bytes % 2 != 0:
            frame_bytes += 1

        stdout = handle.process.stdout
        if stdout is None:
            return

        while not self._stop_event.is_set():
            try:
                data = stdout.read(frame_bytes)
            except Exception:
                break
            if not data:
                break

            level = pcm16le_rms_level(data)
            state = AudioMeterState(level=level, voice_detected=level >= self.VOICE_THRESHOLD)
            with self._lock:
                if channel == "mic":
                    self._snapshot.mic = state
                elif channel == "system":
                    self._snapshot.system = state
