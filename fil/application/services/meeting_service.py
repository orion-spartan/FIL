from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fil.application.services.audio_meter_runtime import AudioMeterRuntime
from fil.domain.models.audio import AudioInputMode
from fil.domain.models.session import Session, SessionStatus, SessionType
from fil.infrastructure.agents.opencode_runner import OpenCodeRunner
from fil.infrastructure.audio.meeting_recorder import FfmpegMeetingRecorder, MeetingRecordingHandle
from fil.infrastructure.storage.session_store import SessionStore
from fil.infrastructure.transcription.faster_whisper import FasterWhisperTranscriber
from fil.shared.meter import AudioMeterState


@dataclass(slots=True)
class MeetingConfig:
    input_mode: AudioInputMode = AudioInputMode.MIXED
    transcript_chunk_seconds: float = 30.0
    summary_every_seconds: float = 45.0
    transcription_model: str = "tiny"
    transcription_language: str | None = "es"
    persist_transcript: bool = True
    persist_insights: bool = True


@dataclass(slots=True)
class MeetingSnapshot:
    mode: str = "idle"
    status_message: str = "ready"
    mic_meter: AudioMeterState = field(default_factory=AudioMeterState)
    system_meter: AudioMeterState = field(default_factory=AudioMeterState)
    live_transcript: str = ""
    latest_insight: str = ""
    summary_status: str = "idle"
    summary_error: str | None = None
    last_summary_at: str | None = None
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
        meter_runtime: AudioMeterRuntime,
        output_root: Path,
        temp_root: Path,
    ) -> None:
        self.session_store = session_store
        self.recorder = recorder
        self.transcriber = transcriber
        self.open_code = open_code
        self.meter_runtime = meter_runtime
        self.output_root = output_root
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
        self._insights_file: Path | None = None
        self._transcript_parts: list[str] = []
        self._processed_chunk_names: set[str] = set()

    def snapshot(self) -> MeetingSnapshot:
        meter_snapshot = self.meter_runtime.snapshot()
        with self._lock:
            return MeetingSnapshot(
                mode=self._snapshot.mode,
                status_message=self._snapshot.status_message,
                mic_meter=meter_snapshot.mic,
                system_meter=meter_snapshot.system,
                live_transcript=self._snapshot.live_transcript,
                latest_insight=self._snapshot.latest_insight,
                summary_status=self._snapshot.summary_status,
                summary_error=self._snapshot.summary_error,
                last_summary_at=self._snapshot.last_summary_at,
                session_id=self._snapshot.session_id,
                next_summary_in=self._snapshot.next_summary_in,
                error_message=self._snapshot.error_message,
            )

    def start(self, *, config: MeetingConfig) -> Session:
        with self._lock:
            if self._snapshot.mode == "running":
                raise RuntimeError("meeting mode is already running")
            self._snapshot = MeetingSnapshot(
                mode="running",
                status_message="starting meeting capture",
                summary_status="waiting for transcript",
            )

        session_id = uuid4().hex[:12]
        now = datetime.utcnow()
        session_dir = self.temp_root / f"meeting-{session_id}"
        session_dir.mkdir(parents=True, exist_ok=True)
        output_dir = self.output_root / session_id
        output_dir.mkdir(parents=True, exist_ok=True)

        with self._lock:
            self._snapshot.status_message = "loading live transcription model"

        self.transcriber.configure(model_name=config.transcription_model, beam_size=1, vad_filter=False)
        self.transcriber.configure(language=config.transcription_language)
        self.transcriber.ensure_loaded()

        transcript_file = output_dir / "transcript.md" if config.persist_transcript else None
        insights_file = output_dir / "insights.md" if config.persist_insights else None

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
                "transcription_language": config.transcription_language,
                "persist_transcript": config.persist_transcript,
                "persist_insights": config.persist_insights,
                "output_dir": str(output_dir),
                "insights_path": str(insights_file) if insights_file is not None else None,
            },
        )
        self.session_store.create_session(session)
        if transcript_file is not None:
            self._write_transcript_markdown(session, transcript_file, "")
        if insights_file is not None:
            self._write_insights_header(session, insights_file)

        recording_dir = session_dir / "audio"
        recording: MeetingRecordingHandle | None = None
        try:
            self.recorder.segment_time = config.transcript_chunk_seconds
            recording = self.recorder.start(recording_dir, config.input_mode)
            self.meter_runtime.start(config.input_mode)
        except Exception as exc:
            if recording is not None:
                try:
                    self.recorder.stop(recording.pid)
                except Exception:
                    self.recorder.force_stop(recording.pid)
            session.status = SessionStatus.FAILED
            session.error_message = str(exc)
            self.session_store.update_session(session)
            raise RuntimeError(f"failed to start meeting runtime: {exc}") from exc

        self._stop_event = threading.Event()
        self._recording = recording
        self._session_dir = session_dir
        self._session = session
        self._transcript_file = transcript_file
        self._insights_file = insights_file
        self._transcript_parts = []
        self._processed_chunk_names = set()

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
            self._snapshot.status_message = "capturing the first transcript window"
            self._snapshot.next_summary_in = None
            self._snapshot.summary_status = "waiting for transcript"

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

        if recording is not None:
            try:
                self.recorder.stop(recording.pid)
            except Exception:
                self.recorder.force_stop(recording.pid)

        self.meter_runtime.stop()

        if transcript_thread is not None:
            transcript_thread.join(timeout=3)
        if summary_thread is not None:
            summary_thread.join(timeout=3)

        if session_dir is not None:
            self._process_transcript_chunks(session_dir / "audio", include_open_tail=True)

        if session_dir is not None:
            session.updated_at = datetime.utcnow()
            session.status = SessionStatus.STOPPED
            if self._transcript_file is not None:
                session.transcript_path = str(self._transcript_file)
            self.session_store.update_session(session)

        with self._lock:
            self._recording = None
            self._transcriber_thread = None
            self._summary_thread = None
            self._session_dir = None
            self._session = None
            self._transcript_file = None
            self._insights_file = None
            self._snapshot = MeetingSnapshot(mode="stopped", status_message="meeting capture stopped")

        return session

    def _transcribe_loop(self, config: MeetingConfig, audio_dir: Path) -> None:
        while not self._stop_event.wait(0.5):
            try:
                with self._lock:
                    self._snapshot.status_message = "transcribing live meeting"

                self._process_transcript_chunks(audio_dir, include_open_tail=False)
            except Exception as exc:
                with self._lock:
                    self._snapshot.error_message = str(exc)
                continue

    def _process_transcript_chunks(self, audio_dir: Path, *, include_open_tail: bool) -> None:
        chunk_files = sorted(audio_dir.glob("chunk-*.wav"))
        if not chunk_files:
            with self._lock:
                if not self._transcript_parts:
                    self._snapshot.status_message = "waiting for the first audio window"
            return

        ready_chunks = chunk_files if include_open_tail else chunk_files[:-1]
        if not ready_chunks:
            with self._lock:
                if not self._transcript_parts:
                    self._snapshot.status_message = "building the first transcript window"
            return

        chunk_file = self._latest_unprocessed_chunk(ready_chunks)
        if chunk_file is None:
            return

        text = self.transcriber.transcribe(chunk_file).strip()
        self._processed_chunk_names.add(chunk_file.name)
        if not text:
            return

        self._transcript_parts.append(text)

        live_transcript = "\n".join(self._transcript_parts).strip()
        if self._session is not None and self._transcript_file is not None:
            self._write_transcript_markdown(self._session, self._transcript_file, live_transcript)

        with self._lock:
            self._snapshot.live_transcript = live_transcript

    def _write_transcript_markdown(self, session: Session, transcript_file: Path, transcript: str) -> None:
        lines = [
            "# Session Transcript",
            "",
            f"- Session: `{session.id}`",
            f"- Type: `{session.type.value}`",
            f"- Created: `{session.created_at.isoformat(timespec='seconds')}`",
        ]
        if input_mode := session.metadata.get("input_mode"):
            lines.append(f"- Input mode: `{input_mode}`")
        lines.extend(["", "## Transcript", ""])
        if transcript.strip():
            lines.extend(["```text", transcript.strip(), "```", ""])
        else:
            lines.extend(["_Waiting for transcript..._", ""])
        transcript_file.write_text("\n".join(lines), encoding="utf-8")

    def _write_insights_header(self, session: Session, insights_file: Path) -> None:
        lines = [
            "# Session Insights",
            "",
            f"- Session: `{session.id}`",
            f"- Type: `{session.type.value}`",
            f"- Created: `{session.created_at.isoformat(timespec='seconds')}`",
        ]
        if input_mode := session.metadata.get("input_mode"):
            lines.append(f"- Input mode: `{input_mode}`")
        lines.extend([
            "",
            "_Waiting for insights..._",
            "",
        ])
        insights_file.write_text("\n".join(lines), encoding="utf-8")

    def _append_insight_markdown(self, insights_file: Path, insight: str, created_at: datetime) -> None:
        existing = insights_file.read_text(encoding="utf-8") if insights_file.exists() else ""
        if "_Waiting for insights..._" in existing:
            existing = existing.replace("_Waiting for insights..._\n", "")

        section = [
            "",
            f"## {created_at.isoformat(timespec='seconds')}",
            "",
            insight.strip() or "_No insight generated._",
            "",
        ]
        insights_file.write_text(existing.rstrip() + "\n" + "\n".join(section), encoding="utf-8")

    def _latest_unprocessed_chunk(self, ready_chunks: list[Path]) -> Path | None:
        for chunk_file in reversed(ready_chunks):
            if chunk_file.name not in self._processed_chunk_names:
                return chunk_file
        return None

    def _summary_loop(self, config: MeetingConfig) -> None:
        last_summary_at = time.monotonic()
        last_len = 0
        while not self._stop_event.wait(1.0):
            elapsed = time.monotonic() - last_summary_at
            with self._lock:
                live_text = self._snapshot.live_transcript
                live_len = len(live_text)
                if live_len == 0:
                    self._snapshot.next_summary_in = None
                else:
                    self._snapshot.next_summary_in = max(config.summary_every_seconds - elapsed, 0.0)

            if elapsed < config.summary_every_seconds or live_len <= last_len:
                with self._lock:
                    if live_len == 0:
                        self._snapshot.summary_status = "waiting for transcript"
                        self._snapshot.status_message = "waiting for the first transcript window"
                    elif live_len <= last_len:
                        self._snapshot.summary_status = "waiting for new transcript"
                continue

            delta_text = live_text[last_len:].strip()
            if not delta_text:
                with self._lock:
                    self._snapshot.summary_status = "waiting for transcript"
                continue

            prompt = (
                "Resume esta sesion en espanol usando Markdown simple y exactamente estas secciones: "
                "## Ideas principales, ## Observaciones, ## Decisiones, ## Compromisos y ## Pendientes. "
                "En cada seccion usa bullets cortos y concretos. "
                "No agregues introduccion ni conclusion. "
                "Texto nuevo de la sesion:\n\n"
                f"{delta_text}"
            )

            with self._lock:
                self._snapshot.summary_status = "running"
                self._snapshot.summary_error = None

            try:
                insight_created_at = datetime.utcnow()
                insight = self.open_code.run(
                    prompt,
                    system_prompt=(
                        "Eres un asistente de reuniones que resume de forma concreta. "
                        "Devuelve Markdown limpio, con headings y bullets solamente."
                    ),
                )
                summary_status = "done"
                summary_error = None
            except Exception as exc:
                insight = f"summary failed: {exc}"
                summary_status = "failed"
                summary_error = str(exc)

            if config.persist_insights and self._insights_file is not None:
                self._append_insight_markdown(self._insights_file, insight, insight_created_at)

            with self._lock:
                self._snapshot.latest_insight = insight
                self._snapshot.status_message = "summarizing meeting progress"
                self._snapshot.summary_status = summary_status
                self._snapshot.summary_error = summary_error
                self._snapshot.last_summary_at = insight_created_at.isoformat(timespec="seconds")

            last_summary_at = time.monotonic()
            last_len = live_len
