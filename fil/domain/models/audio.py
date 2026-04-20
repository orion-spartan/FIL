from __future__ import annotations

from enum import StrEnum


class AudioInputMode(StrEnum):
    MIC = "mic"
    SYSTEM = "system"
    MIXED = "mixed"
