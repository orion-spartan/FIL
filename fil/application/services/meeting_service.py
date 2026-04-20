from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fil.domain.models.audio import AudioInputMode
from fil.domain.models.session import Session, SessionStatus, SessionType
from fil.infrastructure.agents.opencode_runner import OpenCodeRunner
from fil.infrastructure.audio.meeting_recorder import FfmpegMeetingRecorder, MeetingRecordingHandle
from fil.infrastructure.storage.session_store import SessionStore
from fil.infrastructure.transcription.faster_whisper import FasterWhisperTranscriber
from fil.shared.audio import wav_rms_level
from fil.shared.meter import AudioMeterState


@dataclass(slots=True)
class MeetingConfig:
    input_mode: AudioInputMode = AudioInputMode.MIXED
    transcript_chunk_seconds: float = 3.0
    summary_every_seconds: float = 45.0
    transcription_model: str = "base"
    persist_transcript: bool = True
    persist_insights: bool = True


@dataclass(slots=True)
class MeetingSnapshot:
    mode: str = "idle"
    status_message: str = "ready"
    meter: AudioMeterState = field(default_factory=AudioMeterState)
    live_transcript: str = ""
    latest_insight: str = ""
    session_id: str | None = None
    next_summary_in: float | None = None
    error_message: str | None = None


class MeetingService:
    def __init__(
        self,
        *,
        session_store: SessionStore,
        recorder: FfmpegMeetingRecorder,
        transcriber: FasterWhisperTranscriber,
        open_code: OpenCodeRunner,
        temp_root: Path,
    ) -> None:
        self.session_store = session_store
        self.recorder = recorder
        self.transcriber = transcriber
        self.open_code = open_code
        self.temp_root = temp_root

        self._lock = threading.Lock()
        self._snapshot = MeetingSnapshot()
        self._stop_event = threading.Event()
        self._recording: MeetingRecordingHandle | None = None
        self._session_dir: Path | None = None
        self._session: Session | None = None
        self._transcriber_thread: threading.Thread | None = None
        self._summary_thread: threading.Thread | None = None
        self._transcript_file: Path | None = None
        self._summary_file: Path | None = None

    def snapshot(self) -> MeetingSnapshot:
        with self._lock:
            return MeetingSnapshot(
                mode=self._snapshot.mode,
                status_message=self._snapshot.status_message,
                meter=AudioMeterState(level=self._snapshot.meter.level, voice_detected=self._snapshot.meter.voice_detected),
                live_transcript=self._snapshot.live_transcript,
                latest_insight=self._snapshot.latest_insight,
                session_id=self._snapshot.session_id,
                next_summary_in=self._snapshot.next_summary_in,
                error_message=self._snapshot.error_message,
            )

    def start(self, *, config: MeetingConfig) -> Session:
        with self._lock:
            if self._snapshot.mode == "running":
                raise RuntimeError("meeting mode is already running")
            self._snapshot = MeetingSnapshot(mode="running", status_message="starting meeting capture")

        session_id = uuid4().hex[:12]
        now = datetime.utcnow()
        session_dir = self.temp_root / f"meeting-{session_id}"
        session_dir.mkdir(parents=True, exist_ok=True)

        self.transcriber.configure(model_name=config.transcription_model)

        transcript_file = session_dir / "transcript.txt" if config.persist_transcript else None
        summary_file = session_dir / "insights.jsonl"

        session = Session(
            id=session_id,
            type=SessionType.MEETING,
            status=SessionStatus.RUNNING,
            created_at=now,
            updated_at=now,
            audio_path=str(session_dir / "audio"),
            transcript_path=str(transcript_file) if transcript_file is not None else None,
            metadata={
                "input_mode": config.input_mode.value,
                "transcript_chunk_seconds": config.transcript_chunk_seconds,
                "summary_every_seconds": config.summary_every_seconds,
                "transcription_model": config.transcription_model,
                "persist_transcript": config.persist_transcript,
                "persist_insights": config.persist_insights,
            },
        )
        self.session_store.create_session(session)

        recording_dir = session_dir / "audio"
        self.recorder.segment_time = config.transcript_chunk_seconds
        recording = self.recorder.start(recording_dir, config.input_mode)

        self._stop_event = threading.Event()
        self._recording = recording
        self._session_dir = session_dir
        self._session = session
        self._transcript_file = transcript_file
        self._summary_file = summary_file

        self._transcriber_thread = threading.Thread(
            target=self._transcribe_loop,
            args=(config, recording_dir),
            name=f"fil-meeting-transcribe-{session_id}",
            daemon=True,
        )
        self._summary_thread = threading.Thread(
            target=self._summary_loop,
            args=(config,),
            name=f"fil-meeting-summary-{session_id}",
            daemon=True,
        )
        self._transcriber_thread.start()
        self._summary_thread.start()

        with self._lock:
            self._snapshot.session_id = session_id
            self._snapshot.status_message = "meeting capture running"
            self._snapshot.next_summary_in = config.summary_every_seconds

        return session

    def stop(self) -> Session:
        with self._lock:
            if self._snapshot.mode != "running" or self._session is None:
                raise RuntimeError("meeting mode is not currently running")
            session = self._session
            recording = self._recording
            transcript_thread = self._transcriber_thread
            summary_thread = self._summary_thread
            session_dir = self._session_dir

            self._stop_event.set()
            self._recording = None
            self._transcriber_thread = None
            self._summary_thread = None
            self._session_dir = None
            self._session = None

        if recording is not None:
            try:
                self.recorder.stop(recording.pid)
            except Exception:
                self.recorder.force_stop(recording.pid)

        if transcript_thread is not None:
            transcript_thread.join(timeout=3)
        if summary_thread is not None:
            summary_thread.join(timeout=3)

        if session_dir is not None:
            session.updated_at = datetime.utcnow()
            session.status = SessionStatus.STOPPED
            if self._transcript_file is not None:
                session.transcript_path = str(self._transcript_file)
            self.session_store.update_session(session)

        with self._lock:
            self._snapshot = MeetingSnapshot(mode="stopped", status_message="meeting capture stopped")

        return session

    def _transcribe_loop(self, config: MeetingConfig, audio_dir: Path) -> None:
        last_signature: tuple[str, ...] = ()
        transcript_parts: list[str] = []
        while not self._stop_event.wait(0.5):
            try:
                chunk_files = sorted(audio_dir.glob("chunk-*.wav"))
                signature = tuple(path.name for path in chunk_files)
                if not chunk_files or signature == last_signature:
                    continue

                text = self.transcriber.transcribe(chunk_files[-1])
                level = wav_rms_level(chunk_files[-1])
                last_signature = signature

                with self._lock:
                    self._snapshot.meter = AudioMeterState(
                        level=level,
                        voice_detected=level > 0.015,
                    )
                    self._snapshot.status_message = "transcribing live meeting"
                    self._snapshot.next_summary_in = config.summary_every_seconds

                if not text:
                    continue

                transcript_parts.append(text)
                live_transcript = "\n".join(transcript_parts).strip()
                if self._transcript_file is not None:
                    self._transcript_file.write_text(live_transcript, encoding="utf-8")

                with self._lock:
                    self._snapshot.live_transcript = live_transcript
            except Exception as exc:
                with self._lock:
                    self._snapshot.error_message = str(exc)
                continue

    def _summary_loop(self, config: MeetingConfig) -> None:
        last_summary_at = time.monotonic()
        last_len = 0
        while not self._stop_event.wait(1.0):
            elapsed = time.monotonic() - last_summary_at
            with self._lock:
                live_text = self._snapshot.live_transcript
                live_len = len(live_text)
                self._snapshot.next_summary_in = max(config.summary_every_seconds - elapsed, 0.0)

            if elapsed < config.summary_every_seconds or live_len <= last_len:
                continue

            delta_text = live_text[last_len:].strip()
            if not delta_text:
                last_summary_at = time.monotonic()
                continue

            prompt = (
                "Resume esta sesion de reuniones en espanol con estas secciones: "
                "ideas principales, observaciones, decisiones, compromisos y pendientes. "
                "Texto nuevo de la sesion:\n\n"
                f"{delta_text}"
            )

            try:
                insight = self.open_code.run(prompt, system_prompt="Eres un asistente de reuniones que resume de forma concreta.")
            except Exception as exc:
                insight = f"summary failed: {exc}"

            if config.persist_insights and self._summary_file is not None:
                payload = {
                    "ts": datetime.utcnow().isoformat(),
                    "insight": insight,
                }
                with self._summary_file.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

            with self._lock:
                self._snapshot.latest_insight = insight
                self._snapshot.status_message = "summarizing meeting progress"

            last_summary_at = time.monotonic()
            last_len = live_len
