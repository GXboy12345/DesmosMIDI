from __future__ import annotations

import math
from dataclasses import dataclass

from desmosmidi.envelopes import (
    decay_for_freq,
    f_branch_latex,
    g_branch_latex,
    global_gain_default,
    midi_to_hz,
    peak_gain,
)
from desmosmidi.models import (
    DEFAULT_LIVE_BASS_MULT,
    DEFAULT_LIVE_DECAY_MULT,
    AudibleSegment,
    ExportConfig,
    Lane,
)


@dataclass
class DesmosExpression:
    id: str
    latex: str
    role: str = "helper"
    table_columns: list[dict] | None = None


def _sym(lane: int, chunk: int) -> tuple[str, str]:
    """API id suffix and LaTeX subscript (braced). F_0_1 in Desmos means F_0*1; f_{l0c1} is one symbol."""
    tag = f"l{lane}c{chunk}"
    return tag, tag


def _piecewise(branches: list[str], fallback: str) -> str:
    body = ",".join(branches)
    return f"\\left\\{{{body},{fallback}\\right\\}}"


def _bass_low_indicator(f_sym: str, cutoff_hz: int) -> str:
    """Numeric 0/1 from sign; Desmos rejects inequalities inside tone()."""
    return (
        f"\\frac{{\\operatorname{{sign}}\\left({cutoff_hz}-{f_sym}\\left(T\\right)\\right)+1}}{{2}}"
    )


def lane_to_expressions(
    lane: Lane,
    chunk_idx: int,
    segments: list[AudibleSegment],
    cfg: ExportConfig,
    g: float,
) -> list[DesmosExpression]:
    lid = lane.index
    sid, sub = _sym(lid, chunk_idx)
    f_id = f"f_{sid}"
    g_id = f"g_{sid}"
    tone_id = f"tone_{sid}"
    f_sym = f"f_{{{sub}}}"
    g_sym = f"g_{{{sub}}}"
    f_br: list[str] = []
    g_br: list[str] = []
    for seg in segments:
        freq = midi_to_hz(seg.pitch)
        pk = peak_gain(seg.velocity, freq, g)
        d = decay_for_freq(freq, cfg.decay_per_beat)
        s, e = seg.start_beat, seg.end_beat
        f_br.append(f_branch_latex(s, e, freq))
        if seg.is_release_tail:
            rel_pk = pk * math.exp(-d * max(0.0, e - s))
            span = max(e - s, 1e-6)
            g_br.append(
                f"{s:.4g}\\le T<{e:.4g}:"
                f"{rel_pk:.4g}\\left(1-\\frac{{T-{s:.4g}}}{{{span:.4g}}}\\right)"
            )
        else:
            e_hold = max(s, e - cfg.release_beats)
            g_br.append(g_branch_latex(s, e_hold, cfg.release_beats, pk, d))

    f_latex = f"{f_sym}\\left(T\\right)={_piecewise(f_br, '20')}"
    g_latex = f"{g_sym}\\left(T\\right)={_piecewise(g_br, '0')}"
    cut = int(cfg.bass_cutoff_hz)
    low = _bass_low_indicator(f_sym, cut)
    tone_latex = (
        f"\\operatorname{{tone}}\\left({f_sym}\\left(T\\right),"
        f"{g_sym}\\left(T\\right)\\cdot\\left(1+\\left(B-1\\right)\\cdot{low}\\right)\\right)"
    )
    return [
        DesmosExpression(f_id, f_latex, "helper"),
        DesmosExpression(g_id, g_latex, "helper"),
        DesmosExpression(tone_id, tone_latex, "tone"),
    ]


def chunk_lane_segments(
    lane: Lane,
    cfg: ExportConfig,
) -> list[list[AudibleSegment]]:
    segs = lane.segments
    if not segs:
        return []
    chunks: list[list[AudibleSegment]] = []
    cur: list[AudibleSegment] = []
    cur_start = segs[0].start_beat
    for seg in segs:
        trial = cur + [seg]
        branches = len(trial) * 2
        span = seg.end_beat - cur_start
        split = branches > cfg.max_branches
        if cur:
            est = sum(
                len(f_branch_latex(x.start_beat, x.end_beat, midi_to_hz(x.pitch)))
                for x in trial
            )
            est += len(trial) * 40
            if est > 12000:
                split = True
        if cfg.chunk_beats and span > cfg.chunk_beats and len(cur) > 20:
            split = True
        if split and cur:
            chunks.append(cur)
            cur = [seg]
            cur_start = seg.start_beat
        else:
            cur.append(seg)
    if cur:
        chunks.append(cur)
    return chunks if chunks else [segs]


def build_expressions(
    lanes: list[Lane],
    cfg: ExportConfig,
    peak_audible: int,
) -> tuple[list[DesmosExpression], dict]:
    g = global_gain_default(peak_audible, cfg.global_gain)
    exprs = [
        DesmosExpression("T", "T=0", "clock"),
        DesmosExpression("B", f"B={DEFAULT_LIVE_BASS_MULT}", "bass_ctrl"),
        DesmosExpression("D", f"D={DEFAULT_LIVE_DECAY_MULT}", "decay_ctrl"),
    ]
    if not cfg.audio_only:
        exprs.append(DesmosExpression("V", "V=1", "view_ctrl"))
    stats = {"tone_count": 0, "latex_chars": 0, "per_lane": []}

    for lane in lanes:
        chunks = chunk_lane_segments(lane, cfg)
        lane_chars = 0
        for ci, chunk in enumerate(chunks):
            part = lane_to_expressions(lane, ci, chunk, cfg, g)
            exprs.extend(part)
            stats["tone_count"] += 1
            for p in part:
                lane_chars += len(p.latex)
        stats["per_lane"].append(
            {
                "lane": lane.index,
                "segments": len(lane.segments),
                "chunks": len(chunks),
                "latex_chars": lane_chars,
            }
        )
        stats["latex_chars"] += lane_chars

    return exprs, stats


def expressions_to_api(exprs: list[DesmosExpression]) -> list[dict]:
    from desmosmidi.expr_bundle import expressions_to_api as _api

    return _api(exprs)


def expressions_to_md(exprs: list[DesmosExpression]) -> str:
    lines = ["# DesmosMIDI expressions", "", "Set `T=0`, unmute tones, open `player.html` or use API.", ""]
    for e in exprs:
        lines.append(f"- `{e.latex}`")
    return "\n".join(lines) + "\n"
