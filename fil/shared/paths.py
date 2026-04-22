from __future__ import annotations

import os
from pathlib import Path


def data_root() -> Path:
    state_home = os.environ.get("XDG_STATE_HOME")
    if state_home:
        root = Path(state_home) / "fil"
    else:
        root = Path.home() / ".local" / "state" / "fil"
    root.mkdir(parents=True, exist_ok=True)
    return root


def audio_root() -> Path:
    root = data_root() / "audio"
    root.mkdir(parents=True, exist_ok=True)
    return root


def temp_root() -> Path:
    root = data_root() / "tmp"
    root.mkdir(parents=True, exist_ok=True)
    return root


def sessions_root() -> Path:
    root = data_root() / "sessions"
    root.mkdir(parents=True, exist_ok=True)
    return root


def db_path() -> Path:
    return data_root() / "fil.db"
