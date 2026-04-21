from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass


@dataclass(slots=True)
class LiveMeterHandle:
    process: subprocess.Popen[bytes]
    source_name: str


class FfmpegLiveMeterSource:
    def __init__(self, *, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate

    def start(self, source_name: str) -> LiveMeterHandle:
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
                source_name,
                "-ac",
                "1",
                "-ar",
                str(self.sample_rate),
                "-f",
                "s16le",
                "-",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            bufsize=0,
        )
        if process.stdout is None:
            raise RuntimeError("could not open ffmpeg meter stdout")
        return LiveMeterHandle(process=process, source_name=source_name)

    def stop(self, handle: LiveMeterHandle) -> None:
        try:
            os.killpg(handle.process.pid, signal.SIGINT)
        except ProcessLookupError:
            return
        self._wait_for_exit(handle.process.pid)

    def force_stop(self, handle: LiveMeterHandle) -> None:
        try:
            os.killpg(handle.process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        self._wait_for_exit(handle.process.pid)

    @staticmethod
    def _wait_for_exit(pid: int, timeout: float = 2.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.05)
