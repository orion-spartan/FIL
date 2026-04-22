import time

import typer

from fil.application.services.runtime import audio_storage_root, listen_service, meeting_service
from fil.application.services.meeting_service import MeetingConfig
from fil.domain.models.audio import AudioInputMode
from fil.shared.console import console
from fil.shared.meter import render_ascii_meter


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

        service = meeting_service()
        try:
            session = service.start(
                config=MeetingConfig(
                    input_mode=selected_mode,
                    transcript_chunk_seconds=chunk_seconds,
                    summary_every_seconds=summary_every_seconds,
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
        console.print(f"Insights every: [cyan]{summary_every_seconds}s[/cyan]")
        console.print(f"Model: [cyan]{transcription_model}[/cyan]")
        console.print(f"Language: [cyan]{transcription_language}[/cyan]")
        console.print(f"Persist transcript: [cyan]{persist_transcript}[/cyan]")
        console.print(f"Persist insights: [cyan]{persist_insights}[/cyan]")
        console.print("Press [bold]Ctrl+C[/bold] to stop.")

        try:
            from rich.live import Live
            from rich.layout import Layout
            from rich.markdown import Markdown
            from rich.panel import Panel

            def build_layout() -> Layout:
                layout = Layout()
                layout.split_column(
                    Layout(name="header", size=12),
                    Layout(name="body"),
                )
                layout["body"].split_row(
                    Layout(name="transcript", ratio=3),
                    Layout(name="insights", ratio=2),
                )
                return layout

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
                if snapshot.next_summary_in is not None:
                    header_lines.append(f"Next insight in: {snapshot.next_summary_in:.0f}s")
                header_lines.append(f"Summary status: {snapshot.summary_status}")
                if snapshot.last_summary_at:
                    header_lines.append(f"Last summary at: {snapshot.last_summary_at}")
                if snapshot.summary_error:
                    header_lines.append(f"Summary error: {snapshot.summary_error}")

                transcript_text = snapshot.live_transcript[-3000:] if snapshot.live_transcript else "waiting for transcript..."
                insight_renderable = Markdown(snapshot.latest_insight) if snapshot.latest_insight else "waiting for insights..."

                layout["header"].update(Panel("\n".join(header_lines), title=f"FIL Listen Live ({session.id})", border_style="cyan"))
                layout["transcript"].update(Panel(transcript_text, title="Transcript", border_style="green"))
                layout["insights"].update(Panel(insight_renderable, title="Session Insight", border_style="magenta"))

            layout = build_layout()
            update_screen(layout, service.snapshot())
            console.show_cursor(False)
            try:
                with Live(layout, console=console, auto_refresh=False) as live:
                    while True:
                        snapshot = service.snapshot()
                        update_screen(layout, snapshot)
                        live.refresh()
                        time.sleep(0.5)
            finally:
                console.show_cursor(True)
        except KeyboardInterrupt:
            stopped = service.stop()
            console.print(f"[bold green]Meeting stopped[/bold green] ({stopped.id})")
        except RuntimeError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(code=1) from exc

    app.add_typer(listen_app, name="listen")
