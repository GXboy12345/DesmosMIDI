from __future__ import annotations

from desmosmidi.models import AudibleSegment, ExportConfig, Lane


def allocate_lanes(audible: list[AudibleSegment], cfg: ExportConfig) -> list[Lane]:
    ordered = sorted(audible, key=lambda a: (a.start_beat, a.end_beat, a.pitch))
    lanes: list[Lane] = []
    eps = cfg.epsilon

    for seg in ordered:
        placed = False
        for lane in lanes:
            if lane.last_audible_end <= seg.start_beat + eps:
                lane.segments.append(seg)
                placed = True
                break
        if not placed:
            lanes.append(Lane(index=len(lanes), segments=[seg]))

    return lanes
