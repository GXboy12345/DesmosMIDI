from __future__ import annotations

import json
from pathlib import Path

from desmosmidi.desmos_latex import DesmosExpression
from desmosmidi.viz_export import audible_to_viz_notes
from desmosmidi.models import AudibleSegment


def _broken_xy(notes: list[dict]) -> tuple[list[str], list[str]]:
    """List plot with undefined between rows so Desmos does not connect note to note."""
    xs: list[str] = []
    ys: list[str] = []
    for n in notes:
        xs.extend([str(n["s"]), str(n["e"]), "undefined"])
        ys.extend([str(n["p"]), str(n["p"]), "undefined"])
    return xs, ys


def build_viz_controls(exprs: list[DesmosExpression]) -> list[DesmosExpression]:
    return [
        DesmosExpression("viz_playhead", "x=T", "viz_playhead"),
        build_pcm_expression(exprs),
    ]


def build_pcm_expression(exprs: list[DesmosExpression], *, pcm_gain: float = 12.0) -> DesmosExpression:
    terms: list[str] = []
    for e in exprs:
        if e.role != "helper" or not e.id.startswith("f_"):
            continue
        tag = e.id[2:]
        f_sym = f"f_{{{tag}}}"
        g_sym = f"g_{{{tag}}}"
        terms.append(
            f"{g_sym}\\left(T\\right)\\cdot\\sin\\left(2\\pi {f_sym}\\left(T\\right)x\\right)"
        )
    if not terms:
        body = "0"
    else:
        k = len(terms)
        g = f"{pcm_gain:g}"
        body = f"{g}\\cdot\\frac{{1}}{{{k}}}\\left({'+'.join(terms)}\\right)"
    return DesmosExpression("pcm_sum", f"\\operatorname{{pcm}}\\left(x\\right)={body}", "viz_pcm")


def write_viz_sidecar(out_dir: Path, audible: list[AudibleSegment]) -> None:
    notes = audible_to_viz_notes(audible)
    x_vals, y_vals = _broken_xy(notes)
    rows = [
        {
            "id": "keyroll",
            "type": "table",
            "folderId": "dmidi_viz",
            "columns": [
                {
                    "latex": "x_k",
                    "values": x_vals,
                    "points": False,
                    "lines": True,
                },
                {
                    "latex": "y_k",
                    "values": y_vals,
                    "points": False,
                    "lines": True,
                },
            ],
            "color": "#64b4ff",
            "lineWidth": 5,
        },
    ]
    path = out_dir / "expr" / "viz-data.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, separators=(",", ":")), encoding="utf-8")
