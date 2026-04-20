from __future__ import annotations

import subprocess


class OpenCodeRunner:
    def run(self, prompt: str, *, system_prompt: str | None = None, timeout: int = 120) -> str:
        command = ["opencode", "run"]
        if system_prompt:
            command.extend(["--prompt", system_prompt])
        command.append(prompt)

        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
