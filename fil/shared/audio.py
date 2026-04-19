from __future__ import annotations

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
