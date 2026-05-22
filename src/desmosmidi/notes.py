from __future__ import annotations

from dataclasses import dataclass, field

from desmosmidi.models import (
    AudibleSegment,
    ExportConfig,
    NoteSegment,
    ParsedMidi,
    PedalEvent,
)
from desmosmidi.tempo import tick_to_beat


@dataclass
class ActiveNote:
    start_beat: float
    velocity: int
    physical_off_beat: float | None = None


@dataclass
class NoteBuilderState:
    active: dict[tuple[int, int], ActiveNote] = field(default_factory=dict)
    sustained: dict[tuple[int, int], ActiveNote] = field(default_factory=dict)
    pedal: dict[int, bool] = field(default_factory=dict)
    segments: list[NoteSegment] = field(default_factory=list)
    pedal_events: list[PedalEvent] = field(default_factory=list)
    reattacks: int = 0
    sustain_ext: int = 0
    max_sustain_ext: float = 0.0
    peak_physical: int = 0


def _beat(tick: int, tpb: int) -> float:
    return tick_to_beat(tick, tpb)


def _emit(
    st: NoteBuilderState,
    ch: int,
    pitch: int,
    vel: int,
    start: float,
    phys_off: float,
    eff_end: float,
    *,
    release_tail: bool = False,
) -> None:
    st.segments.append(
        NoteSegment(
            channel=ch,
            pitch=pitch,
            velocity=vel,
            start_beat=start,
            effective_end_beat=eff_end,
            physical_off_beat=phys_off,
            is_release_tail=release_tail,
        )
    )


def _finish_note(
    st: NoteBuilderState,
    ch: int,
    pitch: int,
    note: ActiveNote,
    eff_end: float,
) -> None:
    phys = note.physical_off_beat if note.physical_off_beat is not None else eff_end
    if not note.is_release_tail if hasattr(note, "is_release_tail") else True:
        if eff_end > phys and st.pedal.get(ch, False) is False:
            ext = eff_end - phys
            if ext > 0.01:
                st.sustain_ext += 1
                if ext > st.max_sustain_ext:
                    st.max_sustain_ext = ext
    _emit(st, ch, pitch, note.velocity, note.start_beat, phys, eff_end)


def _release_tail(st: NoteBuilderState, ch: int, pitch: int, vel: int, at: float, r: float) -> None:
    _emit(st, ch, pitch, vel, at, at, at + r, release_tail=True)


def _pedal_up(st: NoteBuilderState, ch: int, up_beat: float) -> None:
    for key in [k for k in st.sustained if k[0] == ch]:
        note = st.sustained.pop(key)
        _, pitch = key
        phys = note.physical_off_beat or note.start_beat
        ext = up_beat - phys
        if ext > st.max_sustain_ext:
            st.max_sustain_ext = ext
        st.sustain_ext += 1
        _emit(st, ch, pitch, note.velocity, note.start_beat, phys, up_beat)


def extract_notes(parsed: ParsedMidi, cfg: ExportConfig) -> NoteBuilderState:
    tpb = parsed.ticks_per_beat
    st = NoteBuilderState()
    r = cfg.release_beats

    for tick, msg in parsed.events:
        if msg.is_meta or not hasattr(msg, "channel"):
            continue
        ch = msg.channel
        b = _beat(tick, tpb)

        if msg.type == "control_change" and msg.control == 64:
            down = msg.value >= 64
            was = st.pedal.get(ch, False)
            if down != was:
                st.pedal[ch] = down
                st.pedal_events.append(
                    PedalEvent(ch, b, msg.value, "down" if down else "up")
                )
            if was and not down:
                _pedal_up(st, ch, b)
            continue

        if msg.type not in ("note_on", "note_off"):
            continue

        vel = msg.velocity
        pitch = msg.note + cfg.transpose
        key = (ch, pitch)
        is_on = msg.type == "note_on" and vel > 0
        is_off = msg.type == "note_off" or (msg.type == "note_on" and vel == 0)

        if is_on:
            if key in st.sustained:
                note = st.sustained.pop(key)
                phys = note.physical_off_beat or b
                _emit(st, ch, pitch, note.velocity, note.start_beat, phys, b)
            if key in st.active:
                prev = st.active.pop(key)
                st.reattacks += 1
                _emit(st, ch, pitch, prev.velocity, prev.start_beat, b, b)
                _release_tail(st, ch, pitch, prev.velocity, b, r)
            st.active[key] = ActiveNote(b, vel)
            st.peak_physical = max(st.peak_physical, len(st.active))

        elif is_off:
            note = st.active.pop(key, None)
            if note is None:
                continue
            note.physical_off_beat = b
            if st.pedal.get(ch, False):
                st.sustained[key] = note
            else:
                _emit(st, ch, pitch, note.velocity, note.start_beat, b, b)

    for key, note in list(st.active.items()):
        ch, pitch = key
        off = note.start_beat + 1.0
        note.physical_off_beat = off
        _emit(st, ch, pitch, note.velocity, note.start_beat, off, off)
    for key, note in list(st.sustained.items()):
        ch, pitch = key
        phys = note.physical_off_beat or note.start_beat
        up = phys + 1.0
        _emit(st, ch, pitch, note.velocity, note.start_beat, phys, up)

    return st


def to_audible(segments: list[NoteSegment], release_beats: float) -> list[AudibleSegment]:
    out: list[AudibleSegment] = []
    for s in segments:
        end = s.effective_end_beat if s.is_release_tail else s.effective_end_beat + release_beats
        out.append(
            AudibleSegment(
                channel=s.channel,
                pitch=s.pitch,
                velocity=s.velocity,
                start_beat=s.start_beat,
                end_beat=end,
                is_release_tail=s.is_release_tail,
            )
        )
    return out


def peak_audible_polyphony(audible: list[AudibleSegment]) -> int:
    pts: list[tuple[float, int]] = []
    for a in audible:
        pts.append((a.start_beat, 1))
        pts.append((a.end_beat, -1))
    pts.sort()
    cur = peak = 0
    for _, d in pts:
        cur += d
        peak = max(peak, cur)
    return peak
