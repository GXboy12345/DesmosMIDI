# `song.report.json` schema

`schema_version: 1`. Emit on every `inspect` and `export`.

## Top-level

```json
{
  "schema_version": 1,
  "tool": {
    "name": "DesmosMIDI",
    "version": "0.1.0",
    "command": "desmosmidi export input.mid --out dist/song",
    "generated_at": "ISO-8601"
  },
  "source": {
    "path": "input.mid",
    "sha256": "hex",
    "bytes": 0,
    "midi_type": 1,
    "ticks_per_beat": 480,
    "track_count": 0,
    "length_beats": 0.0,
    "length_seconds_from_tempo_map": 0.0
  },
  "parse": {
    "merge_strategy": "merge_type_0_1_tracks",
    "selected_tracks": [],
    "selected_channels": [],
    "skipped_tracks": [],
    "skipped_channels": [],
    "events_scanned": 0,
    "meta_events_scanned": 0
  },
  "piano_gate": {
    "mode": "strict-acoustic-piano",
    "accepted_programs": [0, 1],
    "assume_missing_program_is_piano": true,
    "channels": [],
    "drum_channel": { "channel": 9, "note_count": 0, "policy": "fail-if-present" },
    "non_piano_channels": []
  },
  "tempo": {
    "unit": "quarter_note_beats",
    "default_tempo_us_per_quarter": 500000,
    "segments": [{ "start_tick": 0, "start_beat": 0.0, "tempo_us_per_quarter": 500000, "bpm": 120.0 }],
    "time_signatures": []
  },
  "pedal": {
    "cc64_threshold": 64,
    "events": [],
    "notes_extended_by_sustain": 0,
    "max_sustain_extension_beats": 0.0
  },
  "notes": {
    "input_note_on_count": 0,
    "input_note_off_count": 0,
    "velocity_zero_note_off_count": 0,
    "exported_note_segments": 0,
    "reattacks_cut": 0,
    "dangling_note_ons": [],
    "dangling_note_offs": [],
    "min_midi_note": 0,
    "max_midi_note": 127
  },
  "render": {
    "frequency_formula": "440*2^((m-69)/12)",
    "tone_model": "sine",
    "time_axis": "T in quarter-note beats",
    "clock": "api-requestAnimationFrame",
    "release_beats": 0.08,
    "decay_model": "exponential",
    "decay_per_beat": 0.65,
    "live_decay_slider_D_default": 3.65,
    "live_bass_slider_B_default": 1.6,
    "velocity_curve": "linear",
    "global_gain": 0.08
  },
  "voices": {
    "allocation": "unbounded-audible-interval-lanes",
    "lane_count": 0,
    "peak_physical_polyphony": 0,
    "peak_audible_polyphony": 0,
    "per_lane": []
  },
  "desmos": {
    "api_version": "1.13",
    "expressions": 0,
    "tone_expressions": 0,
    "definition_expressions": 0,
    "uses_setExpressions": true,
    "estimated_total_latex_chars": 0,
    "chunk_beats": null
  },
  "warnings": [],
  "errors": []
}
```

## Warning codes

| Code | When |
| --- | --- |
| `MISSING_PROGRAM_ASSUMED_PIANO` | Notes on channel with no `program_change` |
| `PEAK_POLYPHONY_HIGH` | `peak_audible_polyphony` over soft threshold |
| `EXPRESSION_COUNT_HIGH` | Many `tone()` rows |
| `LANE_BRANCH_COUNT_HIGH` | Piecewise branches per lane |
| `SHORT_NOTE_FRAME_QUANTIZATION` | Notes shorter than ~0.03s local tempo |
| `TYPE2_UNSUPPORTED` | SMF type 2 without `--track` |

## Soft limits (warn only)

Never steal voices; warn in `song.report.json` only.

| Metric | warn | strong | pathological |
| --- | ---: | ---: | ---: |
| `peak_audible_polyphony` | 32 | 64 | 128 |
| `tone_expression_count` | 64 | 128 | 256 |
| branches per expression | 250 | 500 | 1000 |
| LaTeX chars per expression | 12k | 30k | 75k |
| total LaTeX chars | 250k | 1M | — |
