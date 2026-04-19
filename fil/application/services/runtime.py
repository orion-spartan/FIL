from __future__ import annotations

from fil.application.services.clipboard_service import ClipboardService
from fil.application.services.dictate_service import DictateService
from fil.application.services.listen_service import ListenService
from fil.application.services.talk_service import TalkService
from fil.infrastructure.audio.ffmpeg_segments import FfmpegSegmentRecorder
from fil.infrastructure.audio.pw_record import PwRecordRecorder
from fil.infrastructure.storage.session_store import SessionStore
from fil.infrastructure.transcription.faster_whisper import FasterWhisperTranscriber
from fil.shared.paths import audio_root, db_path, temp_root


def session_store() -> SessionStore:
    return SessionStore(db_path())


def listen_service() -> ListenService:
    return ListenService(session_store=session_store(), recorder=PwRecordRecorder())


def dictate_service() -> DictateService:
    return DictateService(
        recorder=PwRecordRecorder(),
        transcriber=FasterWhisperTranscriber(model_name="base", beam_size=3),
        clipboard=ClipboardService(),
    )


def talk_service() -> TalkService:
    return TalkService(
        recorder=FfmpegSegmentRecorder(segment_time=0.35),
        preview_transcriber=FasterWhisperTranscriber(model_name="tiny", beam_size=1, vad_filter=False),
        clipboard=ClipboardService(),
        temp_root=temp_root(),
    )


def audio_storage_root():
    return audio_root()


def temp_storage_root():
    return temp_root()
