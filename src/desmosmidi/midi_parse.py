from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import mido

from desmosmidi.models import ParsedMidi
from desmosmidi.tempo import build_tempo_segments, parse_time_signatures


def _abs_events(mid: mido.MidiFile) -> list[tuple[int, Any]]:
    if mid.type == 2:
        raise ValueError("SMF type 2 not supported in V1")
    merged = mido.merge_tracks(mid.tracks) if mid.type == 1 else mid.tracks[0]
    out: list[tuple[int, Any]] = []
    t = 0
    meta = 0
    ev = 0
    for msg in merged:
        t += msg.time
        if msg.is_meta:
            meta += 1
        else:
            ev += 1
        out.append((t, msg))
    return out, meta, ev


def load_midi(path: str | Path, *, clip: bool = False) -> ParsedMidi:
    p = Path(path)
    raw = p.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    mid = mido.MidiFile(str(p), clip=clip)
    events, meta_n, ev_n = _abs_events(mid)
    tpb = mid.ticks_per_beat
    tempo_segments = build_tempo_segments(events, tpb)
    time_sigs = parse_time_signatures(events, tpb)

    programs: dict[int, int | None] = {}
    channel_note_counts: dict[int, int] = {}
    drum_notes = 0
    selected = list(range(len(mid.tracks))) if mid.type == 1 else [0]

    for tick, msg in events:
        if not hasattr(msg, "channel"):
            continue
        ch = msg.channel
        if msg.type == "program_change":
            programs[ch] = msg.program
        if msg.type in ("note_on", "note_off"):
            vel = getattr(msg, "velocity", 0)
            is_on = msg.type == "note_on" and vel > 0
            is_off = msg.type == "note_off" or (msg.type == "note_on" and vel == 0)
            if is_on or is_off:
                channel_note_counts[ch] = channel_note_counts.get(ch, 0) + 1
                if ch == 9:
                    drum_notes += 1

    return ParsedMidi(
        path=str(p.resolve()),
        sha256=sha,
        file_bytes=len(raw),
        midi_type=mid.type,
        ticks_per_beat=tpb,
        track_count=len(mid.tracks),
        tempo_segments=tempo_segments,
        time_signatures=time_sigs,
        events=events,
        programs=programs,
        channel_note_counts=channel_note_counts,
        drum_note_count=drum_notes,
        selected_tracks=selected,
        events_scanned=ev_n,
        meta_scanned=meta_n,
    )
