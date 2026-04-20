from __future__ import annotations

from pathlib import Path

from faster_whisper import WhisperModel


class FasterWhisperTranscriber:
    def __init__(self, model_name: str = "base", *, beam_size: int = 1, vad_filter: bool = True) -> None:
        self.model_name = model_name
        self.beam_size = beam_size
        self.vad_filter = vad_filter
        self._model: WhisperModel | None = None

    def transcribe(self, audio_path: Path) -> str:
        model = self._get_model()
        segments, _info = model.transcribe(
            str(audio_path),
            vad_filter=self.vad_filter,
            beam_size=self.beam_size,
            condition_on_previous_text=False,
        )
        transcript = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
        return transcript.strip()

    def configure(self, *, model_name: str | None = None, beam_size: int | None = None, vad_filter: bool | None = None) -> None:
        if model_name is not None and model_name != self.model_name:
            self.model_name = model_name
            self._model = None
        if beam_size is not None:
            self.beam_size = beam_size
        if vad_filter is not None:
            self.vad_filter = vad_filter

    def _get_model(self) -> WhisperModel:
        if self._model is None:
            self._model = WhisperModel(self.model_name, device="auto", compute_type="auto")
        return self._model
