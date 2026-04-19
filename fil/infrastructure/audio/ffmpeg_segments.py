from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class SegmentedRecordingHandle:
    pid: int
    output_dir: Path
    pattern: str


class FfmpegSegmentRecorder:
    def __init__(self, *, segment_time: float = 0.35) -> None:
        self.segment_time = segment_time

    def start(self, output_dir: Path) -> SegmentedRecordingHandle:
        output_dir.mkdir(parents=True, exist_ok=True)
        pattern = str(output_dir / "chunk-%05d.wav")
        process = subprocess.Popen(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-f",
                "pulse",
                "-i",
                "default",
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
                pattern,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return SegmentedRecordingHandle(pid=process.pid, output_dir=output_dir, pattern=pattern)

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
