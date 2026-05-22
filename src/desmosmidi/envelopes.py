from __future__ import annotations

import math

from desmosmidi.models import AudibleSegment, ExportConfig


def midi_to_hz(pitch: int) -> float:
    hz = 440.0 * (2.0 ** ((pitch - 69) / 12.0))
    return max(20.0, min(20000.0, hz))


def max_gain(freq: float) -> float:
    return min(10.0, 660.0 / freq)


def freq_gain_mult(freq: float) -> float:
    """Perceptual lift below ~280 Hz; stays within Desmos max_gain after peak_gain clamps."""
    knee = 280.0
    if freq >= knee:
        return 1.0
    return min(2.8, math.sqrt(knee / max(40.0, freq)))


def decay_for_freq(freq: float, decay_per_beat: float) -> float:
    """Slower envelope decay on low partials so bass does not die early under dense polyphony."""
    ref = 440.0
    return decay_per_beat * min(1.0, max(0.22, freq / ref))


def global_gain_default(peak_audible: int, override: float | None) -> float:
    if override is not None:
        return override
    return min(0.15, 0.6 / math.sqrt(max(1, peak_audible)))


def peak_gain(
    velocity: int,
    freq: float,
    g: float,
) -> float:
    a = g * ((velocity / 127.0) ** 1.5) * freq_gain_mult(freq)
    return min(a, max_gain(freq))


def audit_gains(
    segments: list[AudibleSegment],
    cfg: ExportConfig,
    peak_audible: int,
) -> dict:
    """Check exported peaks against Desmos per-frequency gain cap (0..10, not 0..100)."""
    g = global_gain_default(peak_audible, cfg.global_gain)
    peaks: list[float] = []
    at_cap = 0
    for seg in segments:
        freq = midi_to_hz(seg.pitch)
        cap = max_gain(freq)
        pk = peak_gain(seg.velocity, freq, g)
        peaks.append(pk)
        if pk >= cap - 1e-9:
            at_cap += 1
    n = len(peaks)
    return {
        "desmos_gain_range": "0_to_10",
        "desmos_cap_formula": "min(10, 660/f_hz)",
        "peak_gain_min": min(peaks) if peaks else 0.0,
        "peak_gain_max": max(peaks) if peaks else 0.0,
        "segments_at_desmos_cap": at_cap,
        "segments_total": n,
        "at_cap_fraction": (at_cap / n) if n else 0.0,
        "export_over_cap_count": 0,
    }


def _coef(x: float) -> str:
    return f"{x:.4g}"


def g_branch_latex(
    s: float,
    e: float,
    r: float,
    peak: float,
    decay: float,
) -> str:
    """Desmos needs explicit \\cdot before e^{...}; avoid 0.150000e^{ which reads as broken sci notation."""
    env = f"{_coef(peak)}\\cdot e^{{-D\\cdot{decay:.4g}\\left(T-{s:.4g}\\right)}}"
    if r <= 0:
        return f"{s:.4g}\\le T<{e:.4g}:{env}"
    hold = f"{s:.4g}\\le T<{e:.4g}:{env}"
    rel_peak = peak * math.exp(-decay * (e - s))
    rel = (
        f"{e:.4g}\\le T<{e + r:.4g}:"
        f"{_coef(rel_peak)}\\left(1-\\frac{{T-{e:.4g}}}{{{r:.4g}}}\\right)"
    )
    return f"{hold},{rel}"


def f_branch_latex(s: float, e: float, freq: float) -> str:
    return f"{s:.4g}\\le T<{e:.4g}:{freq:.4g}"
