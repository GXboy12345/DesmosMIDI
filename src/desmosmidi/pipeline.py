from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from desmosmidi import __version__
from desmosmidi.desmos_latex import build_expressions, expressions_to_md
from desmosmidi.diagnostics import build_report
from desmosmidi.expr_bundle import write_expr_bundle, write_meta
from desmosmidi.midi_parse import load_midi
from desmosmidi.models import BuildResult, ExportConfig, ParsedMidi
from desmosmidi.notes import extract_notes, peak_audible_polyphony, to_audible
from desmosmidi.piano_gate import filter_events, gate_channels
from desmosmidi.render_html import render_player
from desmosmidi.tempo import beat_to_second
from desmosmidi.voices import allocate_lanes
from desmosmidi.viz_desmos import build_viz_controls
from desmosmidi.viz_export import write_viz_notes
import json


def build_from_file(path: str | Path, cfg: ExportConfig, *, command: str = "") -> tuple[BuildResult, ParsedMidi, list, dict]:
    parsed = load_midi(path, clip=not cfg.strict_mido)
    allowed, w_gate, e_gate, ch_info = gate_channels(parsed, cfg)
    if e_gate and cfg.piano_only:
        br = BuildResult(
            segments=[],
            audible=[],
            lanes=[],
            pedal_events=[],
            reattacks_cut=0,
            sustain_extensions=0,
            max_sustain_extension=0.0,
            peak_physical=0,
            peak_audible=0,
            warnings=w_gate,
            errors=e_gate,
            duration_beats=0.0,
            duration_seconds=0.0,
        )
        return br, parsed, [], {"ch_info": ch_info, "errors": e_gate}

    ev = filter_events(parsed.events, allowed, cfg)
    parsed = replace(parsed, events=ev)

    nb = extract_notes(parsed, cfg)
    audible = to_audible(nb.segments, cfg.release_beats)
    peak_phys = nb.peak_physical
    peak_aud = peak_audible_polyphony(audible)
    lanes = allocate_lanes(audible, cfg)

    dur_b = max((a.end_beat for a in audible), default=0.0)
    dur_s = beat_to_second(dur_b, parsed.ticks_per_beat, parsed.tempo_segments)

    warnings = list(w_gate)
    br = BuildResult(
        segments=nb.segments,
        audible=audible,
        lanes=lanes,
        pedal_events=nb.pedal_events,
        reattacks_cut=nb.reattacks,
        sustain_extensions=nb.sustain_ext,
        max_sustain_extension=nb.max_sustain_ext,
        peak_physical=peak_phys,
        peak_audible=peak_aud,
        warnings=warnings,
        errors=[],
        duration_beats=dur_b,
        duration_seconds=dur_s,
    )
    exprs, stats = build_expressions(lanes, cfg, peak_aud)
    if not cfg.audio_only:
        exprs.extend(build_viz_controls(exprs))
    meta = {"ch_info": ch_info, "stats": stats, "command": command, "version": __version__}
    return br, parsed, exprs, meta


def export_bundle(
    path: str | Path,
    out_dir: str | Path,
    cfg: ExportConfig,
    *,
    api_key: str,
    command: str,
) -> dict:
    br, parsed, exprs, meta = build_from_file(path, cfg, command=command)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    if meta.get("errors"):
        report = build_report(path, parsed, br, cfg, meta, exprs=[])
        (out / "song.report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        raise RuntimeError("Piano gate failed: " + "; ".join(e["message"] for e in meta["errors"]))

    tempo_map = [{"beat": s.start_beat, "bpm": s.bpm} for s in parsed.tempo_segments]
    write_meta(
        out,
        duration_beats=br.duration_beats,
        tempo_map=tempo_map,
        bass_cutoff_hz=cfg.bass_cutoff_hz,
        decay_per_beat=cfg.decay_per_beat,
    )
    from desmosmidi.envelopes import audit_gains

    meta_json = json.loads((out / "song.meta.json").read_text(encoding="utf-8"))
    meta_json["gain_audit"] = audit_gains(br.audible, cfg, br.peak_audible)

    if cfg.split_expr_folder:
        manifest = write_expr_bundle(
            out,
            exprs,
            chunk_size=cfg.expr_per_chunk,
            hide_graph=cfg.hide_helper_graphs,
            audio_only=cfg.audio_only,
        )
        meta_json["expression_count"] = manifest["expression_count"]
        meta_json["chunk_count"] = len(manifest["chunks"])
        meta_json["expressions_load"] = "expressions.json"
    else:
        from desmosmidi.expr_bundle import expressions_to_api

        api_exprs = expressions_to_api(exprs, hide_graph=cfg.hide_helper_graphs)
        (out / "expressions.json").write_text(json.dumps(api_exprs, indent=2), encoding="utf-8")
        meta_json["expressions_inline"] = True

    meta_json["audio_only"] = cfg.audio_only
    if cfg.audio_only:
        meta_json["viz"] = None
    else:
        viz = write_viz_notes(out, br.audible)
        meta_json["viz"] = {
            "notes": "viz/notes.json",
            "note_count": len(viz["notes"]),
            "viz_data": viz.get("viz_data", "expr/viz-data.json"),
        }

    (out / "song.meta.json").write_text(json.dumps(meta_json, indent=2), encoding="utf-8")

    (out / "expressions.md").write_text(expressions_to_md(exprs), encoding="utf-8")

    report = build_report(path, parsed, br, cfg, meta, exprs=exprs)
    (out / "song.report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out / "song.report.md").write_text(_report_md(report), encoding="utf-8")

    html = render_player(api_key, json.loads((out / "song.meta.json").read_text(encoding="utf-8")))
    (out / "player.html").write_text(html, encoding="utf-8")
    return report


def _report_md(report: dict) -> str:
    lines = [
        "# DesmosMIDI report",
        "",
        f"- Notes exported: {report['notes']['exported_note_segments']}",
        f"- Lanes: {report['voices']['lane_count']}",
        f"- Peak audible polyphony: {report['voices']['peak_audible_polyphony']}",
        f"- Duration (beats): {report['source']['length_beats']:.3f}",
        "",
    ]
    for w in report.get("warnings", []):
        lines.append(f"- **{w['code']}**: {w['message']}")
    for e in report.get("errors", []):
        lines.append(f"- **ERROR {e['code']}**: {e['message']}")
    return "\n".join(lines) + "\n"
