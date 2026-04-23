import typer

from fil.application.services.runtime import audio_storage_root, listen_service, meeting_service
from fil.application.services.meeting_service import MeetingConfig, SummaryMode
from fil.domain.models.audio import AudioInputMode
from fil.shared.console import console
from fil.shared.meter import render_ascii_meter
from fil.shared.terminal import is_quit_key, read_key, terminal_keys


def register(app: typer.Typer) -> None:
    listen_app = typer.Typer(help="Record meeting audio from Linux audio devices.")

    @listen_app.command("start")
    def start() -> None:
        """Starts a listening session."""
        service = listen_service()
        try:
            result = service.start(audio_storage_root())
        except RuntimeError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(code=1) from exc

        console.print(f"[bold green]Listening started[/bold green] ({result.session.id})")
        console.print(f"Audio file: [cyan]{result.audio_path}[/cyan]")
        console.print("Source: default PipeWire input via [bold]pw-record[/bold]")

    @listen_app.command("stop")
    def stop() -> None:
        """Stops the active listening session."""
        service = listen_service()
        try:
            session = service.stop()
        except RuntimeError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(code=1) from exc

        console.print(f"[bold green]Listening stopped[/bold green] ({session.id})")
        if session.audio_path:
            console.print(f"Audio file: [cyan]{session.audio_path}[/cyan]")

    @listen_app.command("live")
    def live(
        input_mode: str = typer.Option(AudioInputMode.MIXED.value, help="Audio input mode: mic, system or mixed."),
        chunk_seconds: float = typer.Option(30.0, min=1.0, max=60.0, help="Chunk size in seconds for live transcript."),
        summary_every_seconds: float = typer.Option(45.0, min=15.0, max=300.0, help="How often to ask OpenCode for insights."),
        summary_mode: str = typer.Option(SummaryMode.AUTO.value, help="Insight mode: auto, manual or off."),
        summary_model: str = typer.Option("openai/gpt-5.4-mini-fast", help="OpenCode model for live insights."),
        transcription_model: str = typer.Option("tiny", help="Whisper model name."),
        transcription_language: str = typer.Option("es", help="Language hint for Whisper, or auto."),
        persist_transcript: bool = typer.Option(True, help="Persist the transcript to disk."),
        persist_insights: bool = typer.Option(True, help="Persist periodic insights to disk."),
    ) -> None:
        """Runs a live meeting session with transcript and periodic insights."""
        try:
            selected_mode = AudioInputMode(input_mode)
        except ValueError as exc:
            console.print(f"[red]Error:[/red] invalid input mode: {input_mode}")
            raise typer.Exit(code=1) from exc

        try:
            selected_summary_mode = SummaryMode(summary_mode)
        except ValueError as exc:
            console.print(f"[red]Error:[/red] invalid summary mode: {summary_mode}")
            raise typer.Exit(code=1) from exc

        service = meeting_service()
        try:
            session = service.start(
                config=MeetingConfig(
                    input_mode=selected_mode,
                    transcript_chunk_seconds=chunk_seconds,
                    summary_every_seconds=summary_every_seconds,
                    summary_mode=selected_summary_mode,
                    summary_model=summary_model,
                    transcription_model=transcription_model,
                    transcription_language=None if transcription_language == "auto" else transcription_language,
                    persist_transcript=persist_transcript,
                    persist_insights=persist_insights,
                )
            )
        except RuntimeError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(code=1) from exc

        console.print(f"[bold green]Meeting live[/bold green] ({session.id})")
        console.print(f"Input mode: [cyan]{selected_mode.value}[/cyan]")
        console.print(f"Transcript chunks: [cyan]{chunk_seconds}s[/cyan]")
        console.print(f"Summary mode: [cyan]{selected_summary_mode.value}[/cyan]")
        if selected_summary_mode == SummaryMode.AUTO:
            console.print(f"Insights every: [cyan]{summary_every_seconds}s[/cyan]")
        if selected_summary_mode != SummaryMode.OFF:
            console.print(f"Insight model: [cyan]{summary_model}[/cyan]")
        console.print(f"Model: [cyan]{transcription_model}[/cyan]")
        console.print(f"Language: [cyan]{transcription_language}[/cyan]")
        console.print(f"Persist transcript: [cyan]{persist_transcript}[/cyan]")
        console.print(f"Persist insights: [cyan]{persist_insights}[/cyan]")
        if selected_summary_mode == SummaryMode.MANUAL:
            console.print("Press [bold]i[/bold] to generate an insight. Press [bold]q[/bold] or [bold]Ctrl+C[/bold] to stop.")
        else:
            console.print("Press [bold]q[/bold] or [bold]Ctrl+C[/bold] to stop.")

        try:
            from rich.live import Live
            from rich.layout import Layout
            from rich.markdown import Markdown
            from rich.panel import Panel

            stop_requested = False

            def build_layout() -> Layout:
                layout = Layout()
                layout.split_column(
                    Layout(name="header", size=10),
                    Layout(name="body"),
                )
                layout["body"].split_column(
                    Layout(name="insights"),
                    Layout(name="transcript", size=6),
                )
                return layout

            def split_insight_columns(insight: str) -> tuple[str, str]:
                left_titles = {"ideas principales", "observaciones"}
                right_titles = {"decisiones", "compromisos", "pendientes"}
                preamble: list[str] = []
                sections: list[tuple[str, str]] = []
                current_title: str | None = None
                current_lines: list[str] = []

                for line in insight.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("## "):
                        if current_title is not None:
                            sections.append((current_title, "\n".join(current_lines).strip()))
                        current_title = stripped[3:].strip().lower()
                        current_lines = [stripped]
                        continue

                    if current_title is None:
                        preamble.append(line)
                    else:
                        current_lines.append(line)

                if current_title is not None:
                    sections.append((current_title, "\n".join(current_lines).strip()))

                if not sections:
                    return insight.strip(), ""

                left_blocks: list[str] = []
                right_blocks: list[str] = []
                extras: list[str] = []
                preamble_text = "\n".join(preamble).strip()
                if preamble_text:
                    left_blocks.append(preamble_text)

                for title, block in sections:
                    if title in left_titles:
                        left_blocks.append(block)
                    elif title in right_titles:
                        right_blocks.append(block)
                    else:
                        extras.append(block)

                for block in extras:
                    if len("\n\n".join(left_blocks)) <= len("\n\n".join(right_blocks)):
                        left_blocks.append(block)
                    else:
                        right_blocks.append(block)

                return "\n\n".join(left_blocks).strip(), "\n\n".join(right_blocks).strip()

            def render_insights(insight: str):
                if not insight:
                    return Panel("waiting for insights...", title="Session Insight", border_style="magenta")

                left_text, right_text = split_insight_columns(insight)
                if console.size.width < 120 or not right_text:
                    return Panel(Markdown(insight), title="Session Insight", border_style="magenta")

                insight_layout = Layout()
                insight_layout.split_row(
                    Layout(Panel(Markdown(left_text), title="Summary", border_style="magenta"), name="left"),
                    Layout(Panel(Markdown(right_text), title="Actions", border_style="magenta"), name="right"),
                )
                return insight_layout

            def update_screen(layout: Layout, snapshot) -> None:
                header_lines = [
                    f"Mode: {snapshot.mode}",
                    f"Status: {snapshot.status_message}",
                ]
                if selected_mode in {AudioInputMode.MIC, AudioInputMode.MIXED}:
                    header_lines.append(f"Mic: {render_ascii_meter(snapshot.mic_meter)}")
                    header_lines.append(f"Mic voice: {'detected' if snapshot.mic_meter.voice_detected else 'silence'}")
                if selected_mode in {AudioInputMode.SYSTEM, AudioInputMode.MIXED}:
                    header_lines.append(f"System: {render_ascii_meter(snapshot.system_meter)}")
                    header_lines.append(f"System audio: {'active' if snapshot.system_meter.voice_detected else 'idle'}")
                header_lines.append(f"Summary mode: {snapshot.summary_mode}")
                if snapshot.next_summary_in is not None:
                    header_lines.append(f"Next insight in: {snapshot.next_summary_in:.0f}s")
                header_lines.append(f"Summary status: {snapshot.summary_status}")
                if snapshot.summary_mode == SummaryMode.MANUAL.value:
                    header_lines.append("Controls: i insight, q quit")
                else:
                    header_lines.append("Controls: q quit")
                if snapshot.last_summary_at:
                    header_lines.append(f"Last summary at: {snapshot.last_summary_at}")
                if snapshot.summary_error:
                    header_lines.append(f"Summary error: {snapshot.summary_error}")

                transcript_lines = [line.strip() for line in snapshot.live_transcript.splitlines() if line.strip()]
                transcript_text = "\n".join(transcript_lines[-3:]) if transcript_lines else "waiting for transcript..."
                insight_renderable = render_insights(snapshot.latest_insight)

                layout["header"].update(Panel("\n".join(header_lines), title=f"FIL Listen Live ({session.id})", border_style="cyan"))
                layout["transcript"].update(Panel(transcript_text, title="Transcript", border_style="green"))
                layout["insights"].update(insight_renderable)

            layout = build_layout()
            update_screen(layout, service.snapshot())
            with terminal_keys(), Live(layout, console=console, auto_refresh=False) as live:
                while True:
                    snapshot = service.snapshot()
                    update_screen(layout, snapshot)
                    live.refresh()
                    key = read_key(0.5)
                    if key in {"i", "I"} and snapshot.summary_mode == SummaryMode.MANUAL.value:
                        service.request_summary()
                        continue
                    if is_quit_key(key):
                        stop_requested = True
                        break
            if stop_requested:
                stopped = service.stop()
                console.print(f"[bold green]Meeting stopped[/bold green] ({stopped.id})")
        except KeyboardInterrupt:
            stopped = service.stop()
            console.print(f"[bold green]Meeting stopped[/bold green] ({stopped.id})")
        except RuntimeError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(code=1) from exc

    app.add_typer(listen_app, name="listen")
