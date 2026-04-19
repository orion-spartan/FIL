from __future__ import annotations

import subprocess


class ClipboardService:
    def copy(self, text: str) -> None:
        if not text:
            return

        commands = (
            ["wl-copy"],
            ["xsel", "--clipboard", "--input"],
        )

        for command in commands:
            try:
                subprocess.run(command, input=text, text=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except FileNotFoundError:
                continue
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(f"clipboard command failed: {' '.join(command)}") from exc

        raise RuntimeError("no supported clipboard command found")
