from __future__ import annotations

from fil.application.services.listen_service import ListenService
from fil.infrastructure.audio.pw_record import PwRecordRecorder
from fil.infrastructure.storage.session_store import SessionStore
from fil.shared.paths import audio_root, db_path


def session_store() -> SessionStore:
    return SessionStore(db_path())


def listen_service() -> ListenService:
    return ListenService(session_store=session_store(), recorder=PwRecordRecorder())


def audio_storage_root():
    return audio_root()
