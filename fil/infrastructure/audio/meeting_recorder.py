from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from fil.domain.models.audio import AudioInputMode
from fil.infrastructure.audio.pulse_sources import PulseSourceResolver


@dataclass(slots=True)
class MeetingRecordingHandle:
    pid: int
    output_dir: Path
    input_mode: AudioInputMode


class FfmpegMeetingRecorder:
    def __init__(self, *, segment_time: float = 3.0, resolver: PulseSourceResolver | None = None) -> None:
        self.segment_time = segment_time
        self.resolver = resolver or PulseSourceResolver()

    def start(self, output_dir: Path, input_mode: AudioInputMode) -> MeetingRecordingHandle:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_pattern = str(output_dir / "chunk-%05d.wav")

        if input_mode == AudioInputMode.MIXED:
            mic_source, monitor_source = self.resolver.resolve(AudioInputMode.MIXED)
            command = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-f",
                "pulse",
                "-i",
                mic_source,
                "-f",
                "pulse",
                "-i",
                monitor_source,
                "-filter_complex",
                "[0:a][1:a]amix=inputs=2:duration=longest:dropout_transition=0[a]",
                "-map",
                "[a]",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                "-f",
                "segment",
                "-segment_time",
                str(self.segment_time),
                "-reset_timestamps",
                "1",
                output_pattern,
            ]
        else:
            source = self.resolver.resolve(input_mode)[0]
            command = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-f",
                "pulse",
                "-i",
                source,
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                "-f",
                "segment",
                "-segment_time",
                str(self.segment_time),
                "-reset_timestamps",
                "1",
                output_pattern,
            ]

        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return MeetingRecordingHandle(pid=process.pid, output_dir=output_dir, input_mode=input_mode)

    def stop(self, pid: int) -> None:
        os.killpg(pid, signal.SIGINT)
        self._wait_for_exit(pid)

    def force_stop(self, pid: int) -> None:
        os.killpg(pid, signal.SIGTERM)
        self._wait_for_exit(pid)

    @staticmethod
    def _wait_for_exit(pid: int, timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.1)
