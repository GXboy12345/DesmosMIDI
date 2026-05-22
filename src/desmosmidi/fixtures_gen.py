"""Generate test MIDI fixtures into tests/fixtures/generated/."""

from __future__ import annotations

from pathlib import Path

from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

TPB = 480
OUT = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "generated"


def _track(name: str, events: list[tuple[int, object]]) -> MidiTrack:
    tr = MidiTrack()
    tr.append(MetaMessage("track_name", name=name, time=0))
    last = 0
    for tick, msg in sorted(events, key=lambda x: x[0]):
        tr.append(msg.copy(time=tick - last))
        last = tick
    tr.append(MetaMessage("end_of_track", time=0))
    return tr


def _tempo_tr(tempos: list[tuple[int, float]]) -> MidiTrack:
    ev = [(t, MetaMessage("set_tempo", tempo=bpm2tempo(b))) for t, b in tempos]
    return _track("tempo", ev)


def save_sustain(out: Path) -> None:
    mid = MidiFile(type=1, ticks_per_beat=TPB)
    mid.tracks.append(_tempo_tr([(0, 120)]))
    mid.tracks.append(
        _track(
            "piano",
            [
                (0, Message("program_change", channel=0, program=0, time=0)),
                (0, Message("note_on", channel=0, note=60, velocity=96, time=0)),
                (int(0.5 * TPB), Message("control_change", channel=0, control=64, value=127, time=0)),
                (2 * TPB, Message("note_off", channel=0, note=60, velocity=64, time=0)),
                (int(2.5 * TPB), Message("control_change", channel=0, control=64, value=0, time=0)),
            ],
        )
    )
    mid.save(out)


def save_reattack(out: Path) -> None:
    mid = MidiFile(type=1, ticks_per_beat=TPB)
    mid.tracks.append(_tempo_tr([(0, 120)]))
    mid.tracks.append(
        _track(
            "piano",
            [
                (0, Message("program_change", channel=0, program=0, time=0)),
                (0, Message("note_on", channel=0, note=60, velocity=96, time=0)),
                (TPB, Message("note_on", channel=0, note=60, velocity=100, time=0)),
                (2 * TPB, Message("note_off", channel=0, note=60, velocity=64, time=0)),
            ],
        )
    )
    mid.save(out)


def save_tempo_change(out: Path) -> None:
    mid = MidiFile(type=1, ticks_per_beat=TPB)
    mid.tracks.append(_tempo_tr([(0, 120), (4 * TPB, 60), (8 * TPB, 180)]))
    mid.tracks.append(
        _track(
            "piano",
            [
                (0, Message("program_change", channel=0, program=0, time=0)),
                (0, Message("note_on", channel=0, note=60, velocity=96, time=0)),
                (TPB, Message("note_off", channel=0, note=60, velocity=64, time=0)),
                (4 * TPB, Message("note_on", channel=0, note=64, velocity=96, time=0)),
                (5 * TPB, Message("note_off", channel=0, note=64, velocity=64, time=0)),
                (8 * TPB, Message("note_on", channel=0, note=67, velocity=96, time=0)),
                (9 * TPB, Message("note_off", channel=0, note=67, velocity=64, time=0)),
            ],
        )
    )
    mid.save(out)


def save_chord(out: Path) -> None:
    mid = MidiFile(type=1, ticks_per_beat=TPB)
    mid.tracks.append(_tempo_tr([(0, 120)]))
    mid.tracks.append(
        _track(
            "piano",
            [
                (0, Message("program_change", channel=0, program=0, time=0)),
                (0, Message("note_on", channel=0, note=60, velocity=96, time=0)),
                (0, Message("note_on", channel=0, note=64, velocity=90, time=0)),
                (0, Message("note_on", channel=0, note=67, velocity=88, time=0)),
                (2 * TPB, Message("note_on", channel=0, note=60, velocity=0, time=0)),
                (2 * TPB, Message("note_on", channel=0, note=64, velocity=0, time=0)),
                (2 * TPB, Message("note_on", channel=0, note=67, velocity=0, time=0)),
            ],
        )
    )
    mid.save(out)


def save_two_hand(out: Path) -> None:
    mid = MidiFile(type=1, ticks_per_beat=TPB)
    mid.tracks.append(_tempo_tr([(0, 120)]))
    mid.tracks.append(
        _track(
            "lh",
            [
                (0, Message("program_change", channel=0, program=0, time=0)),
                (0, Message("note_on", channel=0, note=48, velocity=90, time=0)),
                (4 * TPB, Message("note_off", channel=0, note=48, velocity=64, time=0)),
            ],
        )
    )
    mid.tracks.append(
        _track(
            "rh",
            [
                (0, Message("program_change", channel=1, program=0, time=0)),
                (0, Message("note_on", channel=1, note=72, velocity=90, time=0)),
                (4 * TPB, Message("note_off", channel=1, note=72, velocity=64, time=0)),
            ],
        )
    )
    mid.save(out)


def save_non_piano(out: Path) -> None:
    mid = MidiFile(type=1, ticks_per_beat=TPB)
    mid.tracks.append(_tempo_tr([(0, 120)]))
    mid.tracks.append(
        _track(
            "strings",
            [
                (0, Message("program_change", channel=0, program=48, time=0)),
                (0, Message("note_on", channel=0, note=60, velocity=96, time=0)),
                (TPB, Message("note_off", channel=0, note=60, velocity=64, time=0)),
            ],
        )
    )
    mid.save(out)


def save_drum(out: Path) -> None:
    mid = MidiFile(type=1, ticks_per_beat=TPB)
    mid.tracks.append(_tempo_tr([(0, 120)]))
    mid.tracks.append(
        _track(
            "drums",
            [
                (0, Message("note_on", channel=9, note=36, velocity=100, time=0)),
                (TPB // 2, Message("note_off", channel=9, note=36, velocity=64, time=0)),
            ],
        )
    )
    mid.save(out)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    save_sustain(OUT / "sustain_cc64.mid")
    save_reattack(OUT / "reattack_same_pitch.mid")
    save_tempo_change(OUT / "tempo_changes.mid")
    save_chord(OUT / "c_major_chord.mid")
    save_two_hand(OUT / "two_hand_two_channel.mid")
    save_non_piano(OUT / "non_piano_strings_fail.mid")
    save_drum(OUT / "drum_channel_fail.mid")
