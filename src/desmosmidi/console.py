from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


def print_welcome(version: str, *, has_key: bool) -> None:
    grid = Table.grid(padding=(0, 2))
    grid.add_column()
    grid.add_column()
    grid.add_row("API key", "[green]set[/green]" if has_key else "[yellow]run setup[/yellow]")
    grid.add_row("Default", "desmosmidi  (opens this UI)")
    grid.add_row("Quick", "desmosmidi play song.mid")
    console.print(
        Panel(
            grid,
            title=f"[bold cyan]DesmosMIDI[/bold cyan] [dim]{version}[/dim]",
            border_style="cyan",
        )
    )


def print_check_report(report: dict) -> None:
    src = report.get("source", {})
    notes = report.get("notes", {})
    voices = report.get("voices", {})
    name = Path(src.get("path", "midi")).name

    table = Table(title=f"Check · {name}", show_header=False, box=None, padding=(0, 1))
    table.add_column("label", style="dim")
    table.add_column("value")
    table.add_row("Length", f"{src.get('length_beats', 0):.1f} beats · {src.get('length_seconds_from_tempo_map', 0):.0f}s")
    table.add_row("Notes", str(notes.get("exported_note_segments", 0)))
    table.add_row("Polyphony", str(voices.get("peak_audible_polyphony", 0)))
    tones = report.get("desmos", {}).get("tone_expressions")
    if tones is not None:
        table.add_row("Tone layers", str(tones))
    ok = not report.get("errors")
    table.add_row("Piano", "[green]OK[/green]" if ok else "[red]failed[/red]")
    console.print(table)

    for w in (report.get("warnings") or [])[:6]:
        console.print(f"  [yellow]![/yellow] {w.get('message', w.get('code', ''))}")
    for e in report.get("errors") or []:
        console.print(f"  [red]×[/red] {e.get('message', e.get('code', 'error'))}")

    console.print()
    if ok:
        console.print("[dim]Build:[/dim] desmosmidi build " + repr(name))
        console.print("[dim]Play:[/dim]  desmosmidi play " + repr(name))
    else:
        print_error("This file cannot export until piano check passes.")


def print_build_done(out: Path, port: int, *, audio_only: bool, open_url: str | None = None) -> None:
    url = open_url or f"http://127.0.0.1:{port}/player.html"
    lines = [
        f"[green]Built[/green] {out.resolve()}/",
        f"[cyan]Player[/cyan]  {url}",
        "[dim]Click Play once in the page to hear the piece.[/dim]",
    ]
    if audio_only:
        lines.append("[dim]Audio only — add --viz for keyroll and waveform.[/dim]")
    else:
        lines.append("[yellow]Visualization enabled — may be unstable on long scores.[/yellow]")
    console.print(Panel("\n".join(lines), title="Ready", border_style="green"))


def print_play_steps(out: Path, port: int) -> None:
    url = f"http://127.0.0.1:{port}/player.html"
    console.print(f"[blue]Serving[/blue] {out.name} → [link={url}]{url}[/link]")
    console.print("[dim]Press Ctrl+C to stop the server.[/dim]")


def print_success(msg: str) -> None:
    console.print(f"[green]{msg}[/green]")


def print_error(msg: str) -> None:
    console.print(f"[red]{msg}[/red]")


def print_info(msg: str) -> None:
    console.print(f"[blue]{msg}[/blue]")


def print_warn(msg: str) -> None:
    console.print(f"[yellow]{msg}[/yellow]")


@contextmanager
def task_progress(description: str):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=32),
        console=console,
        transient=True,
    ) as prog:
        tid = prog.add_task(description, total=None)
        yield lambda msg: prog.update(tid, description=msg)
