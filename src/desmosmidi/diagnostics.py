from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from desmosmidi import __version__
from desmosmidi.desmos_latex import DesmosExpression
from desmosmidi.envelopes import audit_gains
from desmosmidi.models import (
    DEFAULT_LIVE_BASS_MULT,
    DEFAULT_LIVE_DECAY_MULT,
    BuildResult,
    ExportConfig,
    ParsedMidi,
)

THRESHOLDS = {
    "peak_audible_polyphony": (32, 64, 128),
    "tone_expression_count": (64, 128, 256),
}


def _tier(val: int, bounds: tuple[int, int, int]) -> str | None:
    w, s, p = bounds
    if val >= p:
        return "pathological"
    if val >= s:
        return "strong_warn"
    if val >= w:
        return "warn"
    return None


def build_report(
    path: str | Path,
    parsed: ParsedMidi,
    br: BuildResult,
    cfg: ExportConfig,
    meta: dict[str, Any],
    *,
    exprs: list[DesmosExpression],
) -> dict:
    stats = meta.get("stats", {})
    tone_n = stats.get("tone_count", 0)
    latex_total = stats.get("latex_chars", 0)
    warnings = list(br.warnings)

    tier = _tier(br.peak_audible, THRESHOLDS["peak_audible_polyphony"])
    if tier:
        warnings.append(
            {
                "code": "PEAK_POLYPHONY_HIGH",
                "severity": tier,
                "message": f"Peak audible polyphony {br.peak_audible}",
            }
        )
    tier = _tier(tone_n, THRESHOLDS["tone_expression_count"])
    if tier:
        warnings.append(
            {
                "code": "TONE_EXPRESSION_COUNT_HIGH",
                "severity": tier,
                "message": f"{tone_n} tone expressions",
            }
        )

    ch_info = meta.get("ch_info", [])
    return {
        "schema_version": 1,
        "tool": {
            "name": "DesmosMIDI",
            "version": __version__,
            "command": meta.get("command", ""),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "source": {
            "path": str(Path(path).resolve()),
            "sha256": parsed.sha256,
            "bytes": parsed.file_bytes,
            "midi_type": parsed.midi_type,
            "ticks_per_beat": parsed.ticks_per_beat,
            "track_count": parsed.track_count,
            "length_beats": br.duration_beats,
            "length_seconds_from_tempo_map": br.duration_seconds,
        },
        "parse": {
            "merge_strategy": "merge_type_0_1_tracks",
            "selected_tracks": parsed.selected_tracks,
            "selected_channels": sorted({c["channel"] for c in ch_info}),
            "skipped_tracks": [],
            "skipped_channels": [],
            "events_scanned": parsed.events_scanned,
            "meta_events_scanned": parsed.meta_scanned,
        },
        "piano_gate": {
            "mode": "strict-acoustic-piano",
            "accepted_programs": [0, 1],
            "assume_missing_program_is_piano": cfg.assume_piano_default,
            "channels": ch_info,
            "drum_channel": {
                "channel": 9,
                "note_count": parsed.drum_note_count,
                "policy": "fail-if-present" if not cfg.strip_drums else "strip",
            },
            "non_piano_channels": [],
        },
        "tempo": {
            "unit": "quarter_note_beats",
            "default_tempo_us_per_quarter": parsed.tempo_segments[0].tempo_us_per_quarter,
            "segments": [
                {
                    "start_tick": s.start_tick,
                    "start_beat": s.start_beat,
                    "tempo_us_per_quarter": s.tempo_us_per_quarter,
                    "bpm": s.bpm,
                }
                for s in parsed.tempo_segments
            ],
            "time_signatures": [
                {
                    "tick": t.tick,
                    "beat": t.beat,
                    "numerator": t.numerator,
                    "denominator": t.denominator,
                }
                for t in parsed.time_signatures
            ],
        },
        "pedal": {
            "cc64_threshold": 64,
            "events": [
                {
                    "channel": p.channel,
                    "beat": p.beat,
                    "value": p.value,
                    "state": p.state,
                }
                for p in br.pedal_events
            ],
            "notes_extended_by_sustain": br.sustain_extensions,
            "max_sustain_extension_beats": br.max_sustain_extension,
        },
        "notes": {
            "input_note_on_count": sum(
                1
                for _, m in parsed.events
                if getattr(m, "type", None) == "note_on" and m.velocity > 0
            ),
            "input_note_off_count": sum(
                1
                for _, m in parsed.events
                if getattr(m, "type", None) == "note_off"
            ),
            "velocity_zero_note_off_count": sum(
                1
                for _, m in parsed.events
                if getattr(m, "type", None) == "note_on" and m.velocity == 0
            ),
            "exported_note_segments": len(br.segments),
            "reattacks_cut": br.reattacks_cut,
            "dangling_note_ons": [],
            "dangling_note_offs": [],
            "min_midi_note": min((s.pitch for s in br.segments), default=0),
            "max_midi_note": max((s.pitch for s in br.segments), default=0),
        },
        "render": {
            "frequency_formula": "440*2^((m-69)/12)",
            "tone_model": "sine",
            "time_axis": "T in quarter-note beats",
            "clock": "api-requestAnimationFrame",
            "release_beats": cfg.release_beats,
            "decay_model": "exponential",
            "decay_per_beat": cfg.decay_per_beat,
            "live_decay_slider_D_default": DEFAULT_LIVE_DECAY_MULT,
            "live_bass_slider_B_default": DEFAULT_LIVE_BASS_MULT,
            "velocity_curve": "power_1.5",
            "global_gain": cfg.global_gain,
        },
        "voices": {
            "allocation": "unbounded-audible-interval-lanes",
            "lane_count": len(br.lanes),
            "peak_physical_polyphony": br.peak_physical,
            "peak_audible_polyphony": br.peak_audible,
            "per_lane": stats.get("per_lane", []),
        },
        "desmos": {
            "api_version": "1.13",
            "expressions": len(exprs),
            "tone_expressions": tone_n,
            "definition_expressions": len(exprs) - tone_n,
            "uses_setState": True,
            "estimated_total_latex_chars": latex_total,
            "chunk_beats": cfg.chunk_beats,
            "gain_audit": audit_gains(br.audible, cfg, br.peak_audible),
        },
        "warnings": warnings,
        "errors": br.errors,
    }
