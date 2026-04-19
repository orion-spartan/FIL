from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from pathlib import Path
import shutil
import tempfile
import threading
import time

from fil.application.services.clipboard_service import ClipboardService
from fil.infrastructure.audio.ffmpeg_segments import FfmpegSegmentRecorder, SegmentedRecordingHandle
from fil.infrastructure.transcription.faster_whisper import FasterWhisperTranscriber
from fil.shared.audio import concatenate_wav_files


class TalkMode(StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
    FINALIZING = "finalizing"
    TRANSCRIBING = "transcribing"
    COPYING = "copying"
    DONE = "done"
    ERROR = "error"


@dataclass(slots=True)
class TalkSnapshot:
    mode: TalkMode = TalkMode.IDLE
    status_message: str = "ready for the next command"
    partial_transcript: str = ""
    final_transcript: str = ""
    copied_to_clipboard: bool = False
    clipboard_error: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None


@dataclass(slots=True)
class TalkResult:
    transcript: str
    copied_to_clipboard: bool
    clipboard_error: str | None = None


class TalkService:
    def __init__(
        self,
        recorder: FfmpegSegmentRecorder,
        preview_transcriber: FasterWhisperTranscriber,
        final_transcriber: FasterWhisperTranscriber,
        clipboard: ClipboardService,
        temp_root: Path,
    ) -> None:
        self.recorder = recorder
        self.preview_transcriber = preview_transcriber
        self.final_transcriber = final_transcriber
        self.clipboard = clipboard
        self.temp_root = temp_root

        self._lock = threading.Lock()
        self._snapshot = TalkSnapshot()
        self._recording: SegmentedRecordingHandle | None = None
        self._session_dir: Path | None = None
        self._preview_thread: threading.Thread | None = None
        self._preview_stop = threading.Event()

    def snapshot(self) -> TalkSnapshot:
        with self._lock:
            return replace(self._snapshot)

    def start(self) -> None:
        with self._lock:
            if self._snapshot.mode == TalkMode.LISTENING:
                raise RuntimeError("talk mode is already listening")
            self._snapshot = TalkSnapshot(
                mode=TalkMode.LISTENING,
                status_message="capturing microphone input",
                started_at=datetime.utcnow(),
            )

        self.temp_root.mkdir(parents=True, exist_ok=True)
        session_dir = Path(tempfile.mkdtemp(prefix="talk-", dir=self.temp_root))
        self._session_dir = session_dir
        self._recording = self.recorder.start(session_dir)

        self._preview_stop = threading.Event()
        self._preview_thread = threading.Thread(target=self._preview_loop, name="fil-talk-preview", daemon=True)
        self._preview_thread.start()

    def stop(self) -> TalkResult:
        with self._lock:
            if self._snapshot.mode != TalkMode.LISTENING:
                raise RuntimeError("talk mode is not currently listening")
            self._snapshot.mode = TalkMode.FINALIZING
            self._snapshot.status_message = "closing the current utterance"

        self._stop_recording()
        chunk_files = self._chunk_files(include_open_tail=True)
        if not chunk_files:
            self._cleanup_session_dir()
            result = TalkResult(transcript="", copied_to_clipboard=False)
            with self._lock:
                self._snapshot = TalkSnapshot(
                    mode=TalkMode.DONE,
                    status_message="no speech detected; nothing was saved",
                    final_transcript="",
                )
            return result

        final_audio = self._session_dir / "final.wav"
        try:
            with self._lock:
                self._snapshot.status_message = "building a final audio pass"
            concatenate_wav_files(chunk_files, final_audio)
            with self._lock:
                self._snapshot.mode = TalkMode.TRANSCRIBING
                self._snapshot.status_message = "transcribing the final utterance"
            transcript = self.final_transcriber.transcribe(final_audio)
        except Exception as exc:
            self._cleanup_session_dir()
            with self._lock:
                self._snapshot.mode = TalkMode.ERROR
                self._snapshot.status_message = "transcription failed"
                self._snapshot.error_message = f"transcription failed: {exc}"
            raise RuntimeError("talk transcription failed") from exc

        copied = False
        clipboard_error = None
        try:
            with self._lock:
                self._snapshot.mode = TalkMode.COPYING
                self._snapshot.status_message = "copying the transcript to the clipboard"
                self._snapshot.final_transcript = transcript
            self.clipboard.copy(transcript)
            copied = bool(transcript)
        except RuntimeError as exc:
            clipboard_error = str(exc)

        self._cleanup_session_dir()
        with self._lock:
            self._snapshot = TalkSnapshot(
                mode=TalkMode.DONE,
                status_message="ready for the next command",
                partial_transcript="",
                final_transcript=transcript,
                copied_to_clipboard=copied,
                clipboard_error=clipboard_error,
            )

        return TalkResult(transcript=transcript, copied_to_clipboard=copied, clipboard_error=clipboard_error)

    def cancel(self) -> None:
        self._stop_recording()
        self._cleanup_session_dir()
        with self._lock:
            self._snapshot = TalkSnapshot(
                mode=TalkMode.IDLE,
                status_message="cancelled; nothing was saved",
            )

    def _stop_recording(self) -> None:
        self._preview_stop.set()
        if self._preview_thread is not None:
            self._preview_thread.join(timeout=2)
            self._preview_thread = None

        recording = self._recording
        self._recording = None
        if recording is None:
            return

        try:
            self.recorder.stop(recording.pid)
        except Exception:
            self.recorder.force_stop(recording.pid)

    def _cleanup_session_dir(self) -> None:
        if self._session_dir is not None:
            shutil.rmtree(self._session_dir, ignore_errors=True)
            self._session_dir = None

    def _preview_loop(self) -> None:
        last_signature: tuple[str, ...] = ()
        while not self._preview_stop.wait(0.2):
            try:
                chunk_files = self._chunk_files(include_open_tail=False)
                signature = tuple(path.name for path in chunk_files)
                if not chunk_files or signature == last_signature:
                    continue

                preview_audio = self._session_dir / "preview.wav"
                concatenate_wav_files(chunk_files, preview_audio)
                transcript = self.preview_transcriber.transcribe(preview_audio)
                last_signature = signature
                with self._lock:
                    if self._snapshot.mode == TalkMode.LISTENING:
                        self._snapshot.partial_transcript = transcript
            except Exception:
                continue

    def _chunk_files(self, *, include_open_tail: bool) -> list[Path]:
        session_dir = self._session_dir
        if session_dir is None:
            return []

        chunk_files = sorted(session_dir.glob("chunk-*.wav"))
        if not include_open_tail and len(chunk_files) > 1:
            return chunk_files[:-1]
        if not include_open_tail and len(chunk_files) <= 1:
            return []
        return chunk_files
