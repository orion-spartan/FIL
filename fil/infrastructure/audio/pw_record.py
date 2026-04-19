from __future__ import annotations

import os
import signal
import time
from dataclasses import dataclass
from pathlib import Path
import subprocess


@dataclass(slots=True)
class RecordingHandle:
    pid: int
    audio_path: Path


class PwRecordRecorder:
    def start(self, output_path: Path) -> RecordingHandle:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        process = subprocess.Popen(
            ["pw-record", str(output_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return RecordingHandle(pid=process.pid, audio_path=output_path)

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
