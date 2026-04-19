from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fil.domain.models.session import Session, SessionStatus, SessionType
from fil.infrastructure.audio.pw_record import PwRecordRecorder, RecordingHandle
from fil.infrastructure.storage.session_store import SessionStore
from fil.shared.process import is_process_running


@dataclass(slots=True)
class ListenStartResult:
    session: Session
    audio_path: Path


class ListenService:
    def __init__(self, session_store: SessionStore, recorder: PwRecordRecorder) -> None:
        self.session_store = session_store
        self.recorder = recorder

    def start(self, audio_root: Path) -> ListenStartResult:
        active_session = self._reconcile_active_session()
        if active_session is not None:
            raise RuntimeError(f"an active session already exists: {active_session.id}")

        session_id = uuid4().hex[:12]
        now = datetime.utcnow()
        output_path = audio_root / f"{session_id}.wav"
        recording = self.recorder.start(output_path)

        session = Session(
            id=session_id,
            type=SessionType.MEETING,
            status=SessionStatus.RUNNING,
            created_at=now,
            updated_at=now,
            audio_path=str(recording.audio_path),
            recorder_pid=recording.pid,
        )
        self.session_store.create_session(session)
        return ListenStartResult(session=session, audio_path=recording.audio_path)

    def stop(self) -> Session:
        active_session = self._reconcile_active_session()
        if active_session is None:
            raise RuntimeError("no active listening session")

        pid = active_session.recorder_pid
        if pid is not None and is_process_running(pid):
            try:
                self.recorder.stop(pid)
            except Exception:
                self.recorder.force_stop(pid)

        active_session.recorder_pid = None
        active_session.status = SessionStatus.STOPPED
        self.session_store.update_session(active_session)
        return active_session

    def get_active_session(self) -> Session | None:
        return self._reconcile_active_session()

    def _reconcile_active_session(self) -> Session | None:
        active_session = self.session_store.get_active_session()
        if active_session is None:
            return None
        if is_process_running(active_session.recorder_pid):
            return active_session

        active_session.status = SessionStatus.FAILED
        active_session.error_message = "recording process is no longer running"
        active_session.recorder_pid = None
        self.session_store.update_session(active_session)
        return None
