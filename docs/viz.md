# Visualization (keyroll, amplitude, playback UI)

Optional graph layers sit in the **`dmidi_viz`** folder. They do not affect audio synthesis; tones live in **`dmidi_audio`**. **Exports omit viz unless you pass `--viz`** (see `docs/cli.md`).

**Tradeoff:**

| Export | Playback | Visualization |
| --- | --- | --- |
| **Default** (no flag) | Stable | None |
| **`--viz`** | Can stutter or drop notes on long pieces | Keyroll + amplitude |

Toggle **Visualization** in the TUI, or press **`m`** for the tradeoff dialog.

## Export artifacts

| Path | Role |
| --- | --- |
| `expr/viz-data.json` | `keyroll` table (`x_k`, `y_k` with `undefined` breaks between notes) |
| `viz/notes.json` | Note list + `pitch_min` / `pitch_max` / `pcm_y_max` / `pcm_gain` for the player |
| `song.meta.json` → `viz` | Pointers: `viz_data`, `notes`, `note_count` |

`build_viz_controls()` adds `viz_playhead` (`x=T`) and `pcm_sum` (`pcm(x)=…`) to the expression bundle. `V` view slider (`1` = keyroll, `2` = amplitude) is omitted when `audio_only` is true.

## Keyroll

- One list plot table **`keyroll`**: each note is a horizontal segment from start beat to end beat at MIDI pitch.
- **`undefined`** between rows prevents Desmos from connecting segments (discrete piano-key bars, not one polyline).
- `lineWidth: 5` on the table.
- Viewport: X `[0, duration_beats]`, Y `[pitch_min - 2, pitch_max + 2]` (from `viz/notes.json`).
- Playhead: red vertical line `viz_playhead` at `x=T`. Bounds are fixed for the full piece—no per-frame `setMathBounds` during playback (avoids drift and dropped audio).

## Amplitude (`pcm_sum`)

Sum of active partials at wall time `x` (not beat `T`):

```latex
\operatorname{pcm}(x) = \frac{12}{k}\sum_i g_i(T)\cdot\sin(2\pi f_i(T)\,x)
```

`k` is the count of `f_*` helpers; **12** is `pcm_gain` (export default). Player Y bounds: `[-pcm_y_max, pcm_y_max]` with default **`pcm_y_max = 0.08`**. Expression starts **`hidden: true`**; the Amplitude view unhides it and hides keyroll + playhead.

## Live controls (HTML player)

| Control | Desmos id | Default | Effect |
| --- | --- | --- | --- |
| Bass | `B` | **1.6×** | Low partials below `bass_cutoff_hz` (280 Hz): `tone(..., G·(1+(B-1)·lowIndicator))` |
| Decay | `D` | **3.65×** (slider 1–5) | Scales exponential decay in every `G` branch: `e^{-D·d(T-s)}` where `d` comes from `--decay-per-beat` at export |
| Output | — | 100% | Web Audio master gain via `__dmidiBus` (wraps `AudioContext.destination`) |
| Graph view | `V` | Keyroll | `1` keyroll, `2` amplitude |
| No render | — | off | Sets `hidden: true` on `keyroll`, `viz_playhead`, `pcm_sum` during playback (calculator UI stays; audio unchanged) |

**No render** is not “hide Desmos.” It suppresses viz expression updates and visibility for performance while `T` and tones still run.

## Expression load order

1. Fetch `expressions.json` (folder-ordered flat list) or chunk via `expr/manifest.json`.
2. Merge `expr/viz-data.json` into `dmidi_viz` if not already present.
3. `setExpressions` flat rows (`slider` → `sliderBounds`).
4. `setState` with `rebuildFolderState()` so folder membership matches export; collapse all folders.
5. Fallback: flat list only if `setState` fails.

Serve the export directory over HTTP (`python3 -m http.server`); chunk and viz fetches need a origin, not raw `file://`.

## Audio-only mode (default)

Build and play without `--viz`:

- Folders: `clock`, `MIDI helpers`, `audio` only (no `dmidi_viz`).
- No `V`, `viz_playhead`, `pcm_sum`, `keyroll`, `viz/`, `expr/viz-data.json`.
- `song.meta.json`: `"audio_only": true`, `"viz": null`.
- Player hides graph view and No render; status shows `audio only`.

Pass **`--viz`** when you want keyroll and amplitude despite the stability cost on long scores.
