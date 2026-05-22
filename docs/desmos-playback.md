# Desmos playback model

## Why `tone()`, not Audio Trace

Audio Trace sonifies **one selected trace** at a time. Public docs do not describe simultaneous multi-expression trace playback. Chords need **multiple independent oscillators**.

`tone(frequency, gain)` accepts Hz directly (20–20000 documented range). Multiple `tone(...)` expressions can sound together when unmuted.

Sources:

- [Tone help](https://help.desmos.com/hc/en-us/articles/21373904717197-Tone)
- [API — Tones, audio settings](https://www.desmos.com/api/v1.13/docs/index.html)
- [Audio Trace help](https://help.desmos.com/hc/en-us/articles/37064105800333-Audio-Trace)

## Expression pattern

Global beat variable (slider or API-driven):

```latex
T=0
B=1.6
D=3.65
V=1
```

Per voice (chunked lanes use ids like `f_l0c0`, `g_l0c0`, `tone_l0c0`):

```latex
F_{1}(T)=\left\{0\le T<2:261.625565,20\right\}
G_{1}(T)=\left\{0\le T<2:0.12\cdot e^{-D\cdot 0.65\left(T-0\right)},0\right\}
\operatorname{tone}\left(F_{1}(T),G_{1}(T)\cdot\left(1+\left(B-1\right)\cdot low\right)\right)
```

During silence segments, **`G=0`**; keep `F` at harmless frequency.

`low` is a numeric 0/1 indicator for frequencies below `bass_cutoff_hz` (280 Hz) so inequalities do not appear inside `tone()`.

## Gain clamp (Desmos)

Desmos `tone(frequency, gain)` uses **gain as amplitude multiplier**, not a 0–100 percent slider. Typical range is **0–1**; low frequencies allow up to **10** via:

```text
max_gain(f) = min(10, 660 / f)
```

Apply after velocity and polyphony scaling. Export clamps every segment peak with `min(a, max_gain(f))`.

Dense chords still **sum** in the browser mixer. The HTML player **Output** slider scales Web Audio **after** Desmos (`__dmidiBus` master `GainNode` on `AudioContext.destination`), not the `tone()` gain argument.

## Polyphony headroom

```python
base = min(0.15, 0.6 / sqrt(max(1, peak_polyphony)))
gain_segment = base * (velocity / 127) ** 1.5 * freq_gain_mult(frequency)
gain_segment = min(gain_segment, max_gain(frequency))
```

No voice stealing in V1.

## Share

V1: `dist/<song>/player.html` + static hosting. Serve the export directory so `fetch("expressions.json")`, `expr/chunk-*.json`, and `expr/viz-data.json` succeed. No programmatic `desmos.com/calculator/<id>` creation. See `share.md`.

## HTML player (V1 primary UX)

```js
const calculator = Desmos.GraphingCalculator(elt, {
  audio: true,
  tone: true,
  muted: true,
  expressions: true,
  actions: true,
});
```

Load path (see `docs/viz.md` for viz):

1. Parse inlined `song.meta.json`.
2. `fetch` `expressions.json` or manifest chunks; merge viz sidecar.
3. `setExpressions` (flat, `sliderBounds` on controls).
4. `setState` with rebuilt folder list; collapse folders.

On **Play** (single user gesture):

1. `calculator.updateSettings({ muted: false })`
2. `__dmidiBus.resume()` if needed
3. Beat clock from `tempo_map` via `requestAnimationFrame`
4. `setExpression({ id: "T", latex: "T=" + beat })` only when the latex string changes (4 decimal places)

**Controls:** Output (master gain), Bass `B`, Decay `D`, Keyroll / Amplitude (`V`), **No render** (hide `keyroll`, `viz_playhead`, `pcm_sum` only).

**Audio-only exports:** graph view controls hidden; generic math bounds; no viz fetch.

## Ticker-compatible export (Milestone 10 — next)

For graphs pasted into **desmos.com** without local HTML (Desmos-native playback):

1. Enable **Actions** (account feature).
2. Export includes **`P`** (play gate), piecewise **`B(T)`** BPM from `tempo_map`, and ticker action on `T` (see `docs/tempo-map.md`).
3. User unmutes tones, sets ticker running, toggles **`P`** (or uses exported play/stop expressions).

V1 **shipped** path: API player + rAF. Ticker export is the next path so the same bundle is valid on the public calculator, not only embedded HTML.

## Fallback: paste-only

`expressions.md` lists all `F`, `G`, `tone` lines. User copies into Desmos, sets `T` slider 0→duration, unmutes, plays slider or ticker manually.

## Limits (empirical)

`capExpressionSize` (API, optional) limits to 500 LaTeX tokens per expression when enabled; default off.

No official cap on expression count. Warn only — thresholds in `report-schema.md` § soft limits. Chunk lanes by branches, LaTeX size, or `--chunk-beats`. Never hide active `tone()` expressions.

Default export is audio-only; use **`--viz`** only when you need the graph load.
