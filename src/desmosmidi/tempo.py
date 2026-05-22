from __future__ import annotations

import mido

from desmosmidi.models import TempoSegment, TimeSignature

DEFAULT_TEMPO = 500_000


def tick_to_beat(tick: int, tpb: int) -> float:
    return tick / tpb


def build_tempo_segments(events: list[tuple[int, object]], tpb: int) -> list[TempoSegment]:
    segs: list[TempoSegment] = []
    tempo = DEFAULT_TEMPO
    for tick, msg in events:
        if getattr(msg, "type", None) == "set_tempo":
            tempo = msg.tempo
            segs.append(
                TempoSegment(
                    start_tick=tick,
                    start_beat=tick_to_beat(tick, tpb),
                    tempo_us_per_quarter=tempo,
                )
            )
    if not segs:
        segs.append(TempoSegment(0, 0.0, DEFAULT_TEMPO))
    return segs


def tempo_at_tick(tick: int, segs: list[TempoSegment]) -> int:
    tempo = segs[0].tempo_us_per_quarter
    for s in segs:
        if s.start_tick <= tick:
            tempo = s.tempo_us_per_quarter
        else:
            break
    return tempo


def tick_to_second(tick: int, tpb: int, segs: list[TempoSegment]) -> float:
    if tick <= 0:
        return 0.0
    total = 0.0
    bounds = segs + [TempoSegment(tick, tick_to_beat(tick, tpb), segs[-1].tempo_us_per_quarter)]
    for i in range(len(segs)):
        t0 = segs[i].start_tick
        t1 = bounds[i + 1].start_tick if i + 1 < len(bounds) else tick
        t1 = min(t1, tick)
        if t1 <= t0:
            continue
        tempo = segs[i].tempo_us_per_quarter
        total += mido.tick2second(t1 - t0, tpb, tempo)
        if t1 >= tick:
            break
    return total


def beat_to_second(beat: float, tpb: int, segs: list[TempoSegment]) -> float:
    return tick_to_second(int(round(beat * tpb)), tpb, segs)


def bpm_at_beat(beat: float, segs: list[TempoSegment]) -> float:
    bpm = segs[0].bpm
    for s in segs:
        if beat >= s.start_beat - 1e-12:
            bpm = s.bpm
        else:
            break
    return bpm


def parse_time_signatures(events: list[tuple[int, object]], tpb: int) -> list[TimeSignature]:
    out: list[TimeSignature] = []
    for tick, msg in events:
        if getattr(msg, "type", None) == "time_signature":
            out.append(
                TimeSignature(
                    tick=tick,
                    beat=tick_to_beat(tick, tpb),
                    numerator=msg.numerator,
                    denominator=msg.denominator,
                )
            )
    return out
