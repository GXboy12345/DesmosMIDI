# MIDI input policy — piano V1

## SMF types

| Type | Behavior |
| --- | --- |
| 0 | Parse single track |
| 1 | Merge tracks to one timeline (stable tick order) |
| 2 | **Reject** V1 |

## Channels

Mido `msg.channel` is 0-based. GM channel 10 drums → `channel == 9`.

| GM channel | V1 default |
| --- | --- |
| 1–9, 11–16 melodic | Piano gate applies |
| 10 drums | **Hard fail** if any note events (`--strip-drums` to drop) |

## Piano-only gate

Mode: **`strict-acoustic-piano`**.

| mido `program` | GM name | Default |
| ---: | --- | --- |
| 0 | Acoustic Grand Piano | accept |
| 1 | Bright Acoustic Piano | accept |
| 2–7 | Other keyboard family | reject (`--allow-piano-family` later) |
| 8–15 | Chromatic percussion | reject |
| 16+ | Organ, strings, etc. | reject |

**Missing `program_change`** on a channel with notes: assume program 0, emit `MISSING_PROGRAM_ASSUMED_PIANO` warning. Disable with `--no-assume-piano-default`.

**Two-hand exports:** LH/RH on channels 0 and 1, both program 0 → merge and accept.

## Default export behavior

```text
desmosmidi export input.mid
  Accept type 0/1
  Merge accepted piano channels
  Hard fail: drums on ch 9, non-piano programs
  Assume missing program = 0 (warn)
```

Destructive overrides (explicit only):

| Flag | Effect |
| --- | --- |
| `--strip-drums` | Drop channel 9 notes, warn |
| `--strip-non-piano` | Drop failing melodic channels, warn |
| `--allow-any-program` | Bypass program gate (still sine tone) |
| `--channel N` | Single channel 1–16 |

## Note events

| Event | Handling |
| --- | --- |
| `note_on` vel > 0 | Start; rearticulate same `(ch, pitch)` |
| `note_on` vel = 0 | `note_off` |
| `note_off` | End unless sustained |
| CC64 ≥ 64 | Pedal down |
| CC64 < 64 | Pedal up, flush sustained |

## Polyphony

All exported segments participate in allocation. **No voice cap.**

## inspect / report

See `docs/report-schema.md` — `piano_gate.channels[]`, `non_piano_channels`, `drum_channel.note_count`.

## V2

Per-program timbre routes; SoundFont simulation; type 2 pattern select.
