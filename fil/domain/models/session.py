from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class SessionType(StrEnum):
    MEETING = "meeting"
    DICTATION = "dictation"
    AGENT_TASK = "agent-task"


class SessionStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class Session:
    id: str
    type: SessionType
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    title: str | None = None
    audio_path: str | None = None
    transcript_path: str | None = None
    recorder_pid: int | None = None
    error_message: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
