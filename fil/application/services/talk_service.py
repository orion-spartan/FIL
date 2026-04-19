from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from pathlib import Path
import shutil
import tempfile
import threading

from fil.application.services.clipboard_service import ClipboardService
from fil.infrastructure.audio.ffmpeg_segments import FfmpegSegmentRecorder, SegmentedRecordingHandle
from fil.infrastructure.transcription.faster_whisper import FasterWhisperTranscriber
from fil.shared.audio import concatenate_wav_files


class TalkMode(StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
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
        clipboard: ClipboardService,
        temp_root: Path,
    ) -> None:
        self.recorder = recorder
        self.preview_transcriber = preview_transcriber
        self.clipboard = clipboard
        self.temp_root = temp_root

        self._lock = threading.Lock()
        self._snapshot = TalkSnapshot()
        self._recording: SegmentedRecordingHandle | None = None
        self._session_dir: Path | None = None
        self._preview_thread: threading.Thread | None = None
        self._preview_stop: threading.Event | None = None

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
        self._preview_thread = threading.Thread(
            target=self._preview_loop,
            args=(self._preview_stop, session_dir),
            name="fil-talk-preview",
            daemon=True,
        )
        self._preview_thread.start()

    def stop(self) -> TalkResult:
        with self._lock:
            if self._snapshot.mode != TalkMode.LISTENING:
                raise RuntimeError("talk mode is not currently listening")
            visible_transcript = self._snapshot.partial_transcript.strip()
            self._snapshot.mode = TalkMode.COPYING
            self._snapshot.status_message = "copying the visible transcript"
            self._snapshot.final_transcript = visible_transcript

            recording = self._recording
            session_dir = self._session_dir
            preview_thread = self._preview_thread
            preview_stop = self._preview_stop

            self._recording = None
            self._session_dir = None
            self._preview_thread = None
            self._preview_stop = None

        if preview_stop is not None:
            preview_stop.set()

        self._finalize_session_async(
            recording=recording,
            preview_thread=preview_thread,
            session_dir=session_dir,
        )

        copied = False
        clipboard_error = None

        if visible_transcript:
            try:
                self.clipboard.copy(visible_transcript)
                copied = True
            except RuntimeError as exc:
                clipboard_error = str(exc)

        with self._lock:
            self._snapshot = TalkSnapshot(
                mode=TalkMode.DONE,
                status_message=(
                    "ready for the next command"
                    if visible_transcript
                    else "no visible transcript to copy; nothing was saved"
                ),
                partial_transcript="",
                final_transcript=visible_transcript,
                copied_to_clipboard=copied,
                clipboard_error=clipboard_error,
            )

        return TalkResult(
            transcript=visible_transcript,
            copied_to_clipboard=copied,
            clipboard_error=clipboard_error,
        )

    def cancel(self) -> None:
        with self._lock:
            recording = self._recording
            session_dir = self._session_dir
            preview_thread = self._preview_thread
            preview_stop = self._preview_stop

            self._recording = None
            self._session_dir = None
            self._preview_thread = None
            self._preview_stop = None

        if preview_stop is not None:
            preview_stop.set()
        self._finalize_session_async(
            recording=recording,
            preview_thread=preview_thread,
            session_dir=session_dir,
        )

        with self._lock:
            self._snapshot = TalkSnapshot(
                mode=TalkMode.IDLE,
                status_message="cancelled; nothing was saved",
            )

    def _finalize_session_async(
        self,
        *,
        recording: SegmentedRecordingHandle | None,
        preview_thread: threading.Thread | None,
        session_dir: Path | None,
    ) -> None:
        thread = threading.Thread(
            target=self._finalize_session,
            kwargs={
                "recording": recording,
                "preview_thread": preview_thread,
                "session_dir": session_dir,
            },
            name="fil-talk-finalize",
            daemon=True,
        )
        thread.start()

    def _finalize_session(
        self,
        *,
        recording: SegmentedRecordingHandle | None,
        preview_thread: threading.Thread | None,
        session_dir: Path | None,
    ) -> None:
        if recording is not None:
            try:
                self.recorder.stop(recording.pid)
            except Exception:
                self.recorder.force_stop(recording.pid)

        if preview_thread is not None:
            preview_thread.join(timeout=2)

        if session_dir is not None:
            shutil.rmtree(session_dir, ignore_errors=True)

    def _preview_loop(self, stop_event: threading.Event, session_dir: Path) -> None:
        last_signature: tuple[str, ...] = ()
        while not stop_event.wait(0.2):
            try:
                chunk_files = self._chunk_files(session_dir, include_open_tail=False)
                signature = tuple(path.name for path in chunk_files)
                if not chunk_files or signature == last_signature:
                    continue

                preview_audio = session_dir / "preview.wav"
                concatenate_wav_files(chunk_files, preview_audio)
                transcript = self.preview_transcriber.transcribe(preview_audio)
                last_signature = signature
                with self._lock:
                    if self._snapshot.mode == TalkMode.LISTENING:
                        self._snapshot.partial_transcript = transcript
            except Exception:
                continue

    @staticmethod
    def _chunk_files(session_dir: Path, *, include_open_tail: bool) -> list[Path]:
        chunk_files = sorted(session_dir.glob("chunk-*.wav"))
        if not include_open_tail and len(chunk_files) > 1:
            return chunk_files[:-1]
        if not include_open_tail and len(chunk_files) <= 1:
            return []
        return chunk_files
