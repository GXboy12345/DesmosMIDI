from __future__ import annotations

import json
import subprocess
import sys
import webbrowser
from dataclasses import dataclass
from pathlib import Path

from desmosmidi.console import print_build_done, print_check_report, print_error, print_play_steps, task_progress
from desmosmidi.env import api_key, load_env
from desmosmidi.models import ExportConfig
from desmosmidi.paths_util import default_out_dir, resolve_midi
from desmosmidi.pipeline import build_from_file, export_bundle


@dataclass
class RunOptions:
    out: Path | None = None
    viz: bool = False
    port: int = 8765
    transpose: int = 0
    release_beats: float = 0.08
    decay_per_beat: float = 0.65
    global_gain: float | None = None
    strip_drums: bool = False
    strip_non_piano: bool = False
    allow_any_program: bool = False
    no_assume_piano_default: bool = False
    channel: int | None = None
    salvage_mido: bool = False
    inline_expressions: bool = False
    show_helper_graphs: bool = False
    expr_per_chunk: int = 12
    chunk_beats: float | None = None


def options_to_config(opt: RunOptions) -> ExportConfig:
    return ExportConfig(
        transpose=opt.transpose,
        release_beats=opt.release_beats,
        decay_per_beat=opt.decay_per_beat,
        global_gain=opt.global_gain,
        chunk_beats=opt.chunk_beats,
        assume_piano_default=not opt.no_assume_piano_default,
        piano_only=not opt.allow_any_program,
        strip_drums=opt.strip_drums,
        strip_non_piano=opt.strip_non_piano,
        allow_any_program=opt.allow_any_program,
        channel=opt.channel,
        strict_mido=not opt.salvage_mido,
        split_expr_folder=not opt.inline_expressions,
        hide_helper_graphs=not opt.show_helper_graphs,
        expr_per_chunk=opt.expr_per_chunk,
        audio_only=not opt.viz,
    )


def run_check(
    midi: Path,
    opt: RunOptions,
    *,
    json_out: bool = False,
    emit: bool = True,
) -> tuple[int, dict]:
    load_env()
    cfg = options_to_config(opt)
    cmd = f"desmosmidi check {midi.name}"
    br, parsed, exprs, meta = build_from_file(midi, cfg, command=cmd)
    from desmosmidi.diagnostics import build_report

    report = build_report(midi, parsed, br, cfg, meta, exprs=exprs)
    if json_out:
        if emit:
            print(json.dumps(report, indent=2))
    elif emit:
        print_check_report(report)
    if report.get("errors"):
        return 2, report
    if not br.segments:
        return 3, report
    return 0, report


def run_build(midi: Path, opt: RunOptions, *, quiet: bool = False) -> tuple[int, Path | None]:
    load_env()
    key = api_key()
    if not key:
        if not quiet:
            print_error("No Desmos API key.")
            print_error("Run: desmosmidi setup")
        return 1, None
    out = opt.out or default_out_dir(midi)
    cfg = options_to_config(opt)
    cmd = f"desmosmidi build {midi.name}"

    def _do():
        export_bundle(midi, out, cfg, api_key=key, command=cmd)

    try:
        if quiet:
            _do()
        else:
            with task_progress(f"Building {midi.name}") as tick:
                tick(f"Exporting → {out}")
                _do()
    except RuntimeError as e:
        if not quiet:
            print_error(str(e))
        return 2, None

    if not quiet:
        print_build_done(out, opt.port, audio_only=cfg.audio_only)
    return 0, out


def run_play(midi: Path, opt: RunOptions) -> int:
    rc, out = run_build(midi, opt, quiet=False)
    if rc != 0 or out is None:
        return rc
    url = f"http://127.0.0.1:{opt.port}/player.html"
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(opt.port), "--bind", "127.0.0.1"],
        cwd=out.resolve(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print_play_steps(out, opt.port)
    webbrowser.open(url)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        proc.wait(timeout=5)
    return 0


def run_setup_interactive() -> int:
    from desmosmidi.env import has_api_key, save_api_key

    load_env()
    if has_api_key():
        from desmosmidi.console import print_info

        print_info("API key already in .env")
        return 0
    from desmosmidi.console import print_info, print_success

    print_info("Free key: https://www.desmos.com/my-api")
    try:
        key = input("Paste API key: ").strip()
    except (EOFError, KeyboardInterrupt):
        return 1
    if not key:
        print_error("No key entered.")
        return 1
    path = save_api_key(key)
    print_success(f"Saved to {path}")
    return 0
