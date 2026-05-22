from __future__ import annotations

import subprocess
import sys
import webbrowser
from pathlib import Path

from textual import events, on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Label, RichLog, Static

from desmosmidi import __version__
from desmosmidi.env import has_api_key, save_api_key
from desmosmidi.paths_util import resolve_midi, select_midi_dialog, strip_quotes
from desmosmidi.runner import RunOptions, run_build, run_check, run_play
from desmosmidi.tui_layout import MIN_COLS, MIN_ROWS


class TooSmallScreen(Screen):
    """Full-screen notice when the terminal is below MIN_COLS × MIN_ROWS."""

    BINDINGS = [Binding("q", "quit", "Quit")]

    CSS = """
    TooSmallScreen {
        align: center middle;
    }
    #too-small-box {
        width: auto;
        max-width: 90%;
        height: auto;
        border: round $error;
        padding: 1 2;
        background: $surface;
    }
    #too-small-title {
        text-style: bold;
        color: $error;
        padding: 0 0 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="too-small-box"):
            yield Label("Terminal too small", id="too-small-title")
            yield Static(id="too-small-body")

    def on_mount(self) -> None:
        self._refresh_body()

    def on_resize(self, event: events.Resize) -> None:
        self._refresh_body()

    def _refresh_body(self) -> None:
        w, h = self.app.size.width, self.app.size.height
        body = self.query_one("#too-small-body", Static)
        body.update(
            f"DesmosMIDI needs at least {MIN_COLS} columns × {MIN_ROWS} rows.\n"
            f"Current size: {w} × {h}\n\n"
            "Resize the terminal window or use a smaller font, then continue."
        )


class ModeChoiceScreen(ModalScreen[bool | None]):
    """Optional: enable visualization (off by default). Dismiss bool = viz on."""

    CSS = """
    ModeChoiceScreen {
        align: center middle;
    }
    #mode-box {
        width: 72;
        height: auto;
        border: round $primary;
        padding: 1 2;
        background: $surface;
    }
    .mode-title {
        text-style: bold;
        padding: 0 0 1 0;
    }
    .mode-fast {
        color: $success;
    }
    .mode-standard {
        color: $warning;
    }
    .mode-body {
        padding: 0 0 1 0;
    }
    #mode-actions {
        height: auto;
        padding: 1 0 0 0;
    }
    #mode-actions Button {
        margin: 0 1 0 0;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="mode-box"):
            yield Label("Visualization?", classes="mode-title")
            yield Label("[bold]Audio only[/bold] — default", classes="mode-fast")
            yield Label(
                "Stable playback. No keyroll or waveform.",
                classes="mode-body",
            )
            yield Label("[bold]With visualization[/bold]", classes="mode-standard")
            yield Label(
                "Keyroll + amplitude. Can stutter or drop notes on long pieces.",
                classes="mode-body",
            )
            with Horizontal(id="mode-actions"):
                yield Button("Audio only", variant="success", id="pick-audio")
                yield Button("With visualization", variant="warning", id="pick-viz")
                yield Button("Cancel", id="pick-cancel")

    @on(Button.Pressed, "#pick-audio")
    def pick_audio(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#pick-viz")
    def pick_viz(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#pick-cancel")
    def pick_cancel(self) -> None:
        self.dismiss(None)


class SetupScreen(ModalScreen[bool]):
    """Paste Desmos API key."""

    CSS = """
    SetupScreen {
        align: center middle;
    }
    #setup-box {
        width: 60;
        height: auto;
        border: round $primary;
        padding: 1 2;
        background: $surface;
    }
    #key-input {
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="setup-box"):
            yield Label("Desmos API key — desmos.com/my-api")
            yield Input(placeholder="paste key here", password=True, id="key-input")
            with Horizontal():
                yield Button("Save", variant="primary", id="save-key")
                yield Button("Cancel", id="cancel-key")

    @on(Button.Pressed, "#save-key")
    def save(self) -> None:
        key = self.query_one("#key-input", Input).value.strip()
        if not key:
            return
        save_api_key(key)
        self.dismiss(True)

    @on(Button.Pressed, "#cancel-key")
    def cancel(self) -> None:
        self.dismiss(False)


class DesmosMidiApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "DesmosMIDI"
    SUB_TITLE = f"v{__version__}"

    def __init__(self) -> None:
        super().__init__()
        self._server: subprocess.Popen | None = None
        self._playback_mode_chosen = True
        self._viz_enabled = False
        self._pending_play: bool | None = None

    BINDINGS = [
        Binding("o", "pick_midi", "Open MIDI"),
        Binding("c", "do_check", "Check"),
        Binding("b", "do_build", "Build"),
        Binding("p", "do_play", "Play"),
        Binding("m", "change_mode", "Mode"),
        Binding("s", "do_setup", "Setup"),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="main-container"):
            with Horizontal(id="path-row"):
                yield Input(placeholder="path to .mid file", id="midi-path")
                yield Button("Open…", id="btn-pick")
            with Horizontal(classes="action-bar"):
                yield Button("Check", id="btn-check")
                yield Button("Build", id="btn-build", variant="primary")
                yield Button("Play", id="btn-play", variant="success")
                yield Button("Setup", id="btn-setup")
                yield Checkbox("Visualization (unstable)", id="viz-mode", value=False)
            yield Static("Audio only (default)", id="mode-label")
            yield RichLog(id="log-panel", highlight=True, markup=True)
            yield Static(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_status()
        log = self.query_one("#log-panel", RichLog)
        log.write(f"[bold cyan]DesmosMIDI[/bold cyan] [dim]v{__version__}[/dim]")
        log.write("[dim]Piano MIDI → Desmos tone() player in your browser[/dim]")
        log.write("")
        log.write(
            "[dim]o[/dim] open  [dim]c[/dim] check  [dim]b[/dim] build  [dim]p[/dim] play  "
            "[dim]m[/dim] mode  [dim]s[/dim] setup"
        )
        self._gate_terminal_size()

    @on(events.Resize)
    def on_resize(self, event: events.Resize) -> None:
        self._gate_terminal_size()

    def _terminal_size_ok(self) -> bool:
        if MIN_COLS <= 0 or MIN_ROWS <= 0:
            return True
        return self.size.width >= MIN_COLS and self.size.height >= MIN_ROWS

    def _gate_terminal_size(self) -> None:
        if MIN_COLS <= 0 or MIN_ROWS <= 0:
            if isinstance(self.screen, TooSmallScreen):
                self.pop_screen()
            return
        ok = self._terminal_size_ok()
        on_gate = isinstance(self.screen, TooSmallScreen)
        if ok:
            if on_gate:
                self.pop_screen()
            return
        if not on_gate:
            self.push_screen(TooSmallScreen())

    def _refresh_status(self) -> None:
        bar = self.query_one("#status-bar", Static)
        if has_api_key():
            bar.update("[green]API key set[/green] · output in dist/")
        else:
            bar.update("[yellow]No API key[/yellow] — press Setup or [dim]s[/dim]")

    def _log(self, msg: str) -> None:
        self.query_one("#log-panel", RichLog).write(msg)

    def _midi_path(self) -> Path | None:
        raw = self.query_one("#midi-path", Input).value
        if not raw.strip():
            self._log("[yellow]Enter a MIDI path or press Open…[/yellow]")
            return None
        try:
            return resolve_midi(raw)
        except FileNotFoundError:
            self._log(f"[red]Not found:[/red] {strip_quotes(raw)}")
            return None

    def _update_mode_label(self) -> None:
        label = self.query_one("#mode-label", Static)
        if self._viz_enabled:
            label.update("[yellow]Visualization on[/yellow] [dim]· may be unstable[/dim]")
        else:
            label.update("[green]Audio only[/green] [dim]· default[/dim]")

    def _apply_viz(self, viz: bool, *, log: bool = True) -> None:
        self._viz_enabled = viz
        self._playback_mode_chosen = True
        self.query_one("#viz-mode", Checkbox).value = viz
        self._update_mode_label()
        if log:
            self._log(
                "[yellow]Visualization enabled[/yellow]"
                if viz
                else "[green]Audio only[/green]"
            )

    @on(Checkbox.Changed, "#viz-mode")
    def on_viz_toggled(self, event: Checkbox.Changed) -> None:
        self._apply_viz(bool(event.value), log=False)

    def _options(self) -> RunOptions:
        return RunOptions(viz=self._viz_enabled)

    def action_change_mode(self) -> None:
        self.push_screen(ModeChoiceScreen(), self._on_mode_chosen)

    def _on_mode_chosen(self, viz: bool | None) -> None:
        if viz is None:
            self._pending_play = None
            return
        self._apply_viz(viz)
        pending = self._pending_play
        self._pending_play = None
        if pending is not None:
            midi = self._midi_path()
            if midi:
                self._run_build_worker(midi, play=pending)

    def _start_build_or_play(self, *, play: bool) -> None:
        if not self._playback_mode_chosen:
            self._pending_play = play
            self.push_screen(ModeChoiceScreen(), self._on_mode_chosen)
            return
        midi = self._midi_path()
        if not midi:
            return
        self._run_build_worker(midi, play=play)

    def action_pick_midi(self) -> None:
        picked = select_midi_dialog()
        if picked:
            self.query_one("#midi-path", Input).value = str(picked)
            self._log(f"[cyan]Selected[/cyan] {picked.name}")
        else:
            self._log("[dim]No file selected.[/dim]")

    def action_do_setup(self) -> None:
        self.push_screen(SetupScreen(), self._on_setup_done)

    def _on_setup_done(self, ok: bool | None) -> None:
        if ok:
            self._refresh_status()
            self._log("[green]API key saved to .env[/green]")

    @on(Button.Pressed, "#btn-pick")
    def on_pick(self) -> None:
        self.action_pick_midi()

    @on(Button.Pressed, "#btn-setup")
    def on_setup(self) -> None:
        self.action_do_setup()

    @on(Button.Pressed, "#btn-check")
    def on_check(self) -> None:
        self.action_do_check()

    @on(Button.Pressed, "#btn-build")
    def on_build(self) -> None:
        self.action_do_build()

    @on(Button.Pressed, "#btn-play")
    def on_play(self) -> None:
        self.action_do_play()

    def action_do_check(self) -> None:
        midi = self._midi_path()
        if not midi:
            return
        self._run_check_worker(midi)

    def action_do_build(self) -> None:
        self._start_build_or_play(play=False)

    def action_do_play(self) -> None:
        self._start_build_or_play(play=True)

    def _stop_server(self) -> None:
        if self._server:
            self._server.terminate()
            try:
                self._server.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._server.kill()
            self._server = None

    def on_unmount(self) -> None:
        self._stop_server()

    @work(thread=True)
    def _run_check_worker(self, midi: Path) -> None:
        self.call_from_thread(self._log, f"\n[bold]Checking {midi.name}…[/bold]")
        rc, report = run_check(midi, self._options(), emit=False)
        src = report.get("source", {})
        voices = report.get("voices", {})
        notes = report.get("notes", {})
        self.call_from_thread(
            self._log,
            f"  {src.get('length_beats', 0):.1f} beats · "
            f"{notes.get('exported_note_segments', 0)} notes · "
            f"poly {voices.get('peak_audible_polyphony', 0)}",
        )
        if rc == 0:
            self.call_from_thread(self._log, "[green]Piano check OK — ready to build.[/green]")
        else:
            self.call_from_thread(self._log, "[red]Check failed — see messages above.[/red]")
            for e in report.get("errors") or []:
                self.call_from_thread(self._log, f"  [red]{e.get('message', '')}[/red]")

    @work(thread=True)
    def _run_build_worker(self, midi: Path, *, play: bool) -> None:
        opt = self._options()
        label = "Play" if play else "Build"
        mode = "viz" if opt.viz else "audio only"
        self.call_from_thread(
            self._log, f"\n[bold]{label}[/bold] {midi.name} [dim]({mode} mode)[/dim]"
        )
        rc, out = run_build(midi, opt, quiet=True)
        if rc == 1:
            self.call_from_thread(self._log, "[red]Need API key — press Setup[/red]")
            return
        if rc != 0 or not out:
            self.call_from_thread(self._log, "[red]Build failed.[/red]")
            return
        url = f"http://127.0.0.1:{opt.port}/player.html"
        self.call_from_thread(self._log, f"[green]Built[/green] {out}")
        if not play:
            self.call_from_thread(self._log, f"[cyan]{url}[/cyan]")
            return
        self.call_from_thread(self._stop_server)
        self._server = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(opt.port), "--bind", "127.0.0.1"],
            cwd=out.resolve(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        webbrowser.open(url)
        self.call_from_thread(
            self._log,
            f"[green]Serving[/green] [cyan]{url}[/cyan]\n[dim]Quit app or press q to stop server.[/dim]",
        )


def run_app() -> None:
    DesmosMidiApp().run()
