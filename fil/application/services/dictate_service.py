from __future__ import annotations

import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
import os

from fil.application.services.clipboard_service import ClipboardService
from fil.infrastructure.audio.pw_record import PwRecordRecorder
from fil.infrastructure.transcription.faster_whisper import FasterWhisperTranscriber


@dataclass(slots=True)
class DictationResult:
    transcript: str
    copied_to_clipboard: bool
    audio_path: Path | None = None


class DictateService:
    def __init__(
        self,
        recorder: PwRecordRecorder,
        transcriber: FasterWhisperTranscriber,
        clipboard: ClipboardService,
    ) -> None:
        self.recorder = recorder
        self.transcriber = transcriber
        self.clipboard = clipboard

    def run(self, temp_root: Path) -> DictationResult:
        temp_root.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix="dictate-", suffix=".wav", dir=temp_root)
        os.close(fd)
        audio_path = Path(temp_name)
        recording = self.recorder.start(audio_path)

        try:
            while True:
                time.sleep(0.2)
        except KeyboardInterrupt:
            self._stop_recording(recording.pid)

        try:
            transcript = self.transcriber.transcribe(audio_path)
        except Exception:
            raise RuntimeError(f"transcription failed; audio kept at {audio_path}")

        copied = False
        try:
            self.clipboard.copy(transcript)
            copied = True
        finally:
            audio_path.unlink(missing_ok=True)

        return DictationResult(transcript=transcript, copied_to_clipboard=copied)

    def _stop_recording(self, pid: int) -> None:
        try:
            self.recorder.stop(pid)
        except Exception:
            self.recorder.force_stop(pid)
