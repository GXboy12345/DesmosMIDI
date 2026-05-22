from __future__ import annotations

import sys
from pathlib import Path

import click

from desmosmidi import __version__
from desmosmidi.console import print_error, print_info, print_welcome
from desmosmidi.env import has_api_key, load_env
from desmosmidi.paths_util import looks_like_midi, resolve_midi
from desmosmidi.runner import RunOptions, run_build, run_check, run_play, run_setup_interactive


class DefaultGroup(click.Group):
    """No args → Textual TUI; song.mid → build; lone flags → TUI."""

    def parse_args(self, ctx, args):
        if not args:
            return super().parse_args(ctx, ["tui"])
        if args[0] in ("-h", "--help", "--version"):
            return super().parse_args(ctx, args)
        if args[0] not in self.commands and looks_like_midi(args[0]):
            return super().parse_args(ctx, ["build", *args])
        if args[0].startswith("-") and args[0] not in ("--help", "-h", "--version"):
            return super().parse_args(ctx, ["tui", *args])
        return super().parse_args(ctx, args)


def _options_from_ctx(**kw) -> RunOptions:
    out = kw.get("out")
    return RunOptions(
        out=Path(out) if out else None,
        viz=bool(kw.get("viz")),
        port=int(kw.get("port") or 8765),
        transpose=int(kw.get("transpose") or 0),
        release_beats=float(kw.get("release_beats") or 0.08),
        decay_per_beat=float(kw.get("decay_per_beat") or 0.65),
        global_gain=kw.get("global_gain"),
        strip_drums=bool(kw.get("strip_drums")),
        strip_non_piano=bool(kw.get("strip_non_piano")),
        allow_any_program=bool(kw.get("allow_any_program")),
        no_assume_piano_default=bool(kw.get("no_assume_piano_default")),
        channel=kw.get("channel"),
        salvage_mido=bool(kw.get("salvage_mido")),
        inline_expressions=bool(kw.get("inline_expressions")),
        show_helper_graphs=bool(kw.get("show_helper_graphs")),
        expr_per_chunk=int(kw.get("expr_per_chunk") or 12),
        chunk_beats=kw.get("chunk_beats"),
    )


def _apply_api_key_override(api_key: str | None) -> None:
    if api_key:
        import os

        os.environ["DESMOS_API_KEY"] = api_key


def _shared_options(fn):
    fn = click.option("--transpose", type=int, default=0, hidden=True)(fn)
    fn = click.option("--release-beats", type=float, default=0.08, hidden=True)(fn)
    fn = click.option("--decay-per-beat", type=float, default=0.65, hidden=True)(fn)
    fn = click.option("--global-gain", type=float, default=None, hidden=True)(fn)
    fn = click.option("--strip-drums", is_flag=True, hidden=True)(fn)
    fn = click.option("--strip-non-piano", is_flag=True, hidden=True)(fn)
    fn = click.option("--allow-any-program", is_flag=True, hidden=True)(fn)
    fn = click.option("--no-assume-piano-default", is_flag=True, hidden=True)(fn)
    fn = click.option("--channel", type=int, default=None, hidden=True)(fn)
    fn = click.option("--salvage-mido", is_flag=True, hidden=True)(fn)
    return fn


def _build_options(fn):
    fn = click.option(
        "--viz",
        is_flag=True,
        help="keyroll + amplitude (heavier; may be unstable on long scores)",
    )(fn)
    fn = click.option("--fast", is_flag=True, hidden=True, help="deprecated; audio-only is default")(fn)
    fn = click.option("--audio-only", is_flag=True, hidden=True, help="deprecated alias for default export")(fn)
    fn = click.option("-o", "--out", type=click.Path(), default=None, help="output folder")(fn)
    fn = click.option("--port", default=8765, hidden=True)(fn)
    fn = click.option("--inline-expressions", is_flag=True, hidden=True)(fn)
    fn = click.option("--show-helper-graphs", is_flag=True, hidden=True)(fn)
    fn = click.option("--expr-per-chunk", default=12, hidden=True)(fn)
    fn = click.option("--chunk-beats", type=float, default=None, hidden=True)(fn)
    fn = click.option("--api-key", default=None, hidden=True)(fn)
    return fn


@click.group(cls=DefaultGroup, invoke_without_command=True)
@click.version_option(__version__, prog_name="desmosmidi")
def cli():
    """Piano MIDI → Desmos player in your browser."""
    load_env()


@cli.command()
def tui():
    """Interactive terminal UI (default)."""
    from desmosmidi.app import run_app

    run_app()


@cli.command()
@click.argument("midi", type=click.Path(exists=True, dir_okay=False))
@_shared_options
@_build_options
def build(midi, **kw):
    """Build dist/…/player.html from a MIDI file."""
    path = resolve_midi(midi)
    _apply_api_key_override(kw.get("api_key"))
    rc, _ = run_build(path, _options_from_ctx(**kw))
    raise SystemExit(rc)


@cli.command()
@click.argument("midi", type=click.Path(exists=True, dir_okay=False))
@_shared_options
@_build_options
def play(midi, **kw):
    """Build, serve locally, and open the player in your browser."""
    path = resolve_midi(midi)
    _apply_api_key_override(kw.get("api_key"))
    raise SystemExit(run_play(path, _options_from_ctx(**kw)))


@cli.command()
@click.argument("midi", type=click.Path(exists=True, dir_okay=False))
@click.option("--json", is_flag=True, help="machine-readable report")
@_shared_options
def check(midi, json, **kw):
    """Preview length, notes, and piano check (no build)."""
    path = resolve_midi(midi)
    rc, _ = run_check(path, _options_from_ctx(**kw), json_out=json)
    raise SystemExit(rc)


@cli.command()
def setup():
    """Save Desmos API key to .env (first-time)."""
    raise SystemExit(run_setup_interactive())


@cli.command("export", hidden=True)
@click.argument("midi", type=click.Path(exists=True, dir_okay=False))
@_shared_options
@_build_options
def export_cmd(midi, **kw):
    """Alias for build."""
    ctx = click.get_current_context()
    ctx.invoke(build, midi=midi, **kw)


@cli.command("inspect", hidden=True)
@click.argument("midi", type=click.Path(exists=True, dir_okay=False))
@click.option("--json", is_flag=True, hidden=True)
@_shared_options
def inspect_cmd(midi, json, **kw):
    ctx = click.get_current_context()
    ctx.invoke(check, midi=midi, json=json, **kw)


@cli.command(hidden=True)
def make_fixtures():
    from desmosmidi.fixtures_gen import main as mk

    mk()
    print_info("Test MIDI → tests/fixtures/generated/")
    print_info("Try: desmosmidi play tests/fixtures/generated/c_major_chord.mid")


@cli.command(hidden=True)
def help_cmd():
    """Short command reference."""
    print_welcome(__version__, has_key=has_api_key())


def main(argv: list[str] | None = None) -> int:
    try:
        cli.main(args=argv, standalone_mode=False)
        return 0
    except SystemExit as e:
        code = e.code
        if code is None:
            return 0
        return int(code) if isinstance(code, int) else 1
    except click.exceptions.Exit as e:
        return int(e.exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
