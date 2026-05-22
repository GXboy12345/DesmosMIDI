from __future__ import annotations

import json
from pathlib import Path

from desmosmidi.models import AudibleSegment


def audible_to_viz_notes(audible: list[AudibleSegment]) -> list[dict]:
    out: list[dict] = []
    for a in audible:
        if a.is_release_tail:
            continue
        out.append(
            {
                "p": a.pitch,
                "s": round(a.start_beat, 6),
                "e": round(a.end_beat, 6),
                "v": a.velocity,
            }
        )
    out.sort(key=lambda n: (n["s"], n["p"]))
    return out


def write_viz_notes(out_dir: Path, audible: list[AudibleSegment]) -> dict:
    from desmosmidi.viz_desmos import write_viz_sidecar

    notes = audible_to_viz_notes(audible)
    pitch_lo = min((n["p"] for n in notes), default=21)
    pitch_hi = max((n["p"] for n in notes), default=108)
    write_viz_sidecar(out_dir, audible)
    payload = {
        "notes": notes,
        "pitch_min": pitch_lo,
        "pitch_max": pitch_hi,
        "viz_data": "expr/viz-data.json",
        "pcm_y_max": 0.08,
        "pcm_gain": 12.0,
    }
    viz_dir = out_dir / "viz"
    viz_dir.mkdir(parents=True, exist_ok=True)
    (viz_dir / "notes.json").write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    return payload
