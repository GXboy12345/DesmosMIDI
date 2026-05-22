# DesmosMIDI

Convert Standard MIDI Files into a **prefilled Desmos graph** that plays **piano** music via **`tone()`** synthesis—unbounded polyphony, sustain pedal, decay on gain, beat-proportional timeline, optional keyroll/amplitude viz.

V1 is **not** [MIDI2Desmos](https://github.com/AlexApps99/MIDI2Desmos)-style Audio Trace; it uses documented `tone(frequency, gain)` with a global beat variable `T`.

## Quickstart

See **[Quickstart.md](Quickstart.md)** for the full walkthrough.

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
desmosmidi setup
desmosmidi                          # terminal UI
desmosmidi play path/to/song.mid    # build + open browser
```

Or build only: `desmosmidi path/to/song.mid` (writes `dist/<song-name>/`).

Keyroll + waveform (optional): `desmosmidi path/to/song.mid --viz`

## Requirements

- Python 3.11+
- [Desmos API key](https://www.desmos.com/my-api) for embedded HTML player
- Modern browser with Web Audio (user gesture required for sound)
- Static HTTP server for exports that load `expr/` chunks (not `file://`)

## Commands

| Command | Purpose |
| --- | --- |
| `desmosmidi setup` | Save API key to `.env` |
| `desmosmidi FILE.mid` | Build player under `dist/` |
| `desmosmidi play FILE.mid` | Build + open in browser |
| `desmosmidi check FILE.mid` | Preview file info |

See `docs/cli.md` for flags (`--viz`, chunking, piano gate).

## Output layout

```text
dist/prelude/
  player.html              # Jinja player; inlined song.meta.json
  song.meta.json           # tempo map, duration, audio_only, viz pointers
  expr/
    manifest.json          # chunk list + folder specs
    chunk-0000.json        # batched expressions
    viz-data.json          # keyroll table (only with --viz)
  expressions.json         # folder-ordered list (setState / primary load)
  viz/notes.json           # pitch range, pcm viewport (only with --viz)
  expressions.md           # paste fallback for desmos.com
  song.report.json
  song.report.md
```

**Folders** (collapsed by default in Desmos): `clock` (`T`, `B`, `D`, optional `V`), `MIDI helpers` (`F_*`, `G_*`), `audio` (`tone_*`), optional `viz`.

**Player:** Play/Stop, Bass (default 1.6×), Decay (default 3.65×), Output master gain. With `--viz`: Keyroll / Amplitude and **No render**. Details: `docs/viz.md`, `docs/desmos-playback.md`.

## Documentation

| Doc | Contents |
| --- | --- |
| [docs/README.md](docs/README.md) | Topic index |
| [docs/viz.md](docs/viz.md) | Keyroll, amplitude, player UX |
| [docs/desmos-playback.md](docs/desmos-playback.md) | `tone()`, clocks, API player |
| [docs/tempo-map.md](docs/tempo-map.md) | Beats, BPM, ticker recipe |
| [Quickstart.md](Quickstart.md) | Setup and first export |

## Status

**V1** — CLI, MIDI parse, piano gate, sustain/reattack, unlimited voice lanes, chunked `tone()` export, HTML player, default audio-only export. `pytest`: 20 tests.

## License

Apache License 2.0. See [LICENSE](LICENSE).
