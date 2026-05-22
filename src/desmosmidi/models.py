from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DEFAULT_LIVE_BASS_MULT: float = 1.6
DEFAULT_LIVE_DECAY_MULT: float = 3.65


@dataclass
class TempoSegment:
    start_tick: int
    start_beat: float
    tempo_us_per_quarter: int

    @property
    def bpm(self) -> float:
        return 60_000_000 / self.tempo_us_per_quarter


@dataclass
class TimeSignature:
    tick: int
    beat: float
    numerator: int
    denominator: int


@dataclass
class PedalEvent:
    channel: int
    beat: float
    value: int
    state: str


@dataclass
class NoteSegment:
    channel: int
    pitch: int
    velocity: int
    start_beat: float
    effective_end_beat: float
    physical_off_beat: float
    is_release_tail: bool = False
    parent_pitch: int | None = None


@dataclass
class AudibleSegment:
    channel: int
    pitch: int
    velocity: int
    start_beat: float
    end_beat: float
    is_release_tail: bool = False


@dataclass
class Lane:
    index: int
    segments: list[AudibleSegment] = field(default_factory=list)

    @property
    def last_audible_end(self) -> float:
        if not self.segments:
            return 0.0
        return max(s.end_beat for s in self.segments)


@dataclass
class ExportConfig:
    transpose: int = 0
    release_beats: float = 0.08
    decay_per_beat: float = 0.65
    global_gain: float | None = None
    chunk_beats: float | None = None
    max_branches: int = 80
    expr_chunk_size: int = 12
    inline_expressions: bool = False
    assume_piano_default: bool = True
    piano_only: bool = True
    strip_drums: bool = False
    strip_non_piano: bool = False
    allow_any_program: bool = False
    channel: int | None = None
    strict_mido: bool = True
    epsilon: float = 1e-9
    expr_per_chunk: int = 12
    hide_helper_graphs: bool = True
    split_expr_folder: bool = True
    bass_cutoff_hz: float = 280.0
    audio_only: bool = True


@dataclass
class ParsedMidi:
    path: str
    sha256: str
    file_bytes: int
    midi_type: int
    ticks_per_beat: int
    track_count: int
    tempo_segments: list[TempoSegment]
    time_signatures: list[TimeSignature]
    events: list[tuple[int, Any]]
    programs: dict[int, int | None]
    channel_note_counts: dict[int, int]
    drum_note_count: int
    selected_tracks: list[int]
    events_scanned: int
    meta_scanned: int


@dataclass
class BuildResult:
    segments: list[NoteSegment]
    audible: list[AudibleSegment]
    lanes: list[Lane]
    pedal_events: list[PedalEvent]
    reattacks_cut: int
    sustain_extensions: int
    max_sustain_extension: float
    peak_physical: int
    peak_audible: int
    warnings: list[dict[str, str]]
    errors: list[dict[str, str]]
    duration_beats: float
    duration_seconds: float
