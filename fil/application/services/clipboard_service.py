from __future__ import annotations

import subprocess
import threading


class ClipboardService:
    def _reap_process(self, process: subprocess.Popen[str]) -> None:
        try:
            process.wait()
        except Exception:
            pass

    def copy(self, text: str) -> None:
        if not text:
            return

        commands = (
            ["wl-copy"],
            ["xsel", "--clipboard", "--input"],
        )

        for command in commands:
            try:
                process = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    start_new_session=True,
                )

                try:
                    process.communicate(input=text, timeout=0.05)
                except subprocess.TimeoutExpired:
                    # Clipboard tools often stay alive to own the selection.
                    threading.Thread(target=self._reap_process, args=(process,), daemon=True).start()
                else:
                    if process.returncode not in (0, None):
                        raise RuntimeError(f"clipboard command failed: {' '.join(command)}")
                return
            except FileNotFoundError:
                continue
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(f"clipboard command failed: {' '.join(command)}") from exc

        raise RuntimeError("no supported clipboard command found")
