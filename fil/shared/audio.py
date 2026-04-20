from __future__ import annotations

from array import array
from math import sqrt
from pathlib import Path
import wave


def concatenate_wav_files(input_files: list[Path], output_file: Path) -> None:
    if not input_files:
        raise ValueError("no wav files to concatenate")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(input_files[0]), "rb") as first_input:
        params = first_input.getparams()
        format_signature = (params.nchannels, params.sampwidth, params.framerate, params.comptype, params.compname)
        with wave.open(str(output_file), "wb") as output:
            output.setparams(params)
            output.writeframes(first_input.readframes(first_input.getnframes()))

            for input_file in input_files[1:]:
                with wave.open(str(input_file), "rb") as current_input:
                    current_params = current_input.getparams()
                    current_signature = (
                        current_params.nchannels,
                        current_params.sampwidth,
                        current_params.framerate,
                        current_params.comptype,
                        current_params.compname,
                    )
                    if current_signature != format_signature:
                        raise ValueError("wav files do not share the same audio format")
                    output.writeframes(current_input.readframes(current_input.getnframes()))


def wav_rms_level(input_file: Path) -> float:
    with wave.open(str(input_file), "rb") as audio_file:
        if audio_file.getsampwidth() != 2:
            raise ValueError("only 16-bit wav files are supported for level metering")

        frame_count = audio_file.getnframes()
        if frame_count == 0:
            return 0.0

        samples = array("h")
        samples.frombytes(audio_file.readframes(frame_count))
        if not samples:
            return 0.0

        squared_sum = sum(sample * sample for sample in samples)
        rms = sqrt(squared_sum / len(samples))
        return min(rms / 32768.0, 1.0)
