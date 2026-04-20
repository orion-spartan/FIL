from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from fil.domain.models.session import Session, SessionStatus, SessionType


def _utcnow() -> datetime:
    return datetime.utcnow()


class SessionStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    title TEXT,
                    audio_path TEXT,
                    transcript_path TEXT,
                    recorder_pid INTEGER,
                    error_message TEXT,
                    metadata_json TEXT
                )
                """
            )
            self._ensure_column(connection, "metadata_json", "TEXT")

    def _ensure_column(self, connection: sqlite3.Connection, name: str, sql_type: str) -> None:
        rows = connection.execute("PRAGMA table_info(sessions)").fetchall()
        if any(row["name"] == name for row in rows):
            return
        connection.execute(f"ALTER TABLE sessions ADD COLUMN {name} {sql_type}")

    def create_session(self, session: Session) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions (
                    id, type, status, created_at, updated_at, title,
                    audio_path, transcript_path, recorder_pid, error_message, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.type.value,
                    session.status.value,
                    session.created_at.isoformat(),
                    session.updated_at.isoformat(),
                    session.title,
                    session.audio_path,
                    session.transcript_path,
                    session.recorder_pid,
                    session.error_message,
                    json.dumps(session.metadata, ensure_ascii=False),
                ),
            )

    def update_session(self, session: Session) -> None:
        session.updated_at = _utcnow()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE sessions
                SET type = ?, status = ?, updated_at = ?, title = ?,
                    audio_path = ?, transcript_path = ?, recorder_pid = ?, error_message = ?, metadata_json = ?
                WHERE id = ?
                """,
                (
                    session.type.value,
                    session.status.value,
                    session.updated_at.isoformat(),
                    session.title,
                    session.audio_path,
                    session.transcript_path,
                    session.recorder_pid,
                    session.error_message,
                    json.dumps(session.metadata, ensure_ascii=False),
                    session.id,
                ),
            )

    def list_sessions(self, limit: int = 20) -> list[Session]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM sessions
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_session(row) for row in rows]

    def get_session(self, session_id: str) -> Session | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        return self._row_to_session(row) if row else None

    def get_active_session(self) -> Session | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM sessions
                WHERE status = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (SessionStatus.RUNNING.value,),
            ).fetchone()
        return self._row_to_session(row) if row else None

    @staticmethod
    def _row_to_session(row: sqlite3.Row) -> Session:
        return Session(
            id=row["id"],
            type=SessionType(row["type"]),
            status=SessionStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            title=row["title"],
            audio_path=row["audio_path"],
            transcript_path=row["transcript_path"],
            recorder_pid=row["recorder_pid"],
            error_message=row["error_message"],
            metadata=json.loads(row["metadata_json"] or "{}"),
        )
