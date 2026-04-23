from __future__ import annotations

import subprocess


class OpenCodeRunner:
    def run(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        timeout: int = 120,
        model: str | None = None,
    ) -> str:
        final_prompt = prompt
        if system_prompt:
            final_prompt = f"{system_prompt}\n\n{prompt}"

        command = ["opencode", "run"]
        if model:
            command.extend(["-m", model])
        command.append(final_prompt)

        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"opencode timed out after {timeout}s") from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            stdout = (exc.stdout or "").strip()
            detail = stderr or stdout or "unknown opencode failure"
            raise RuntimeError(f"opencode failed: {detail}") from exc

        output = result.stdout.strip()
        if not output:
            raise RuntimeError("opencode returned an empty response")
        return output
