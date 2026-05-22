# Envelopes — gain channel

V1: pure `tone()` sine. Timbre is Desmos’s oscillator; shape is **`G(T)`**, **`F(T)`**, and live sliders **`B`**, **`D`**.

## Variables

| Symbol | Meaning |
| --- | --- |
| `s` | Segment start beat |
| `k` | Physical key-up beat |
| `e` | Effective end (sustain-resolved) |
| `r` | `release_beats` (default 0.08) |
| `a` | Peak gain after velocity + polyphony scale |
| `d` | `decay_per_beat` at export (default 0.65), frequency-scaled |
| `D` | Live decay multiplier in player (default **3.65**, slider 1–5) |
| `B` | Live bass multiplier (default **1.6**, slider ~0.25–3×) |

Frequency: `f(m) = 440·2^((m-69)/12)` Hz.

Gain clamp (Desmos): `min(10, 660/frequency)`.

Source: [Tone help](https://help.desmos.com/hc/en-us/articles/21373904717197-Tone)

## Held interval (exponential)

Exported LaTeX uses the live `D` symbol:

```latex
s\le T<e:\quad a\cdot e^{-D\cdot d(T-s)}
```

where `d(f) = decay_per_beat * min(1, max(0.22, f/440))`.

## Release ramp

```latex
e\le T<e+r:\quad a\cdot e^{-D\cdot d(f)(e-s)}\cdot\left(1-\frac{T-e}{r}\right)
```

Release-tail segments (reattack) use a linear fade from decayed peak.

Combined `G(T)` for one segment: piecewise branches as in `envelopes.g_branch_latex`.

## Bass boost (`B`)

Below `bass_cutoff_hz` (280 Hz, `ExportConfig.bass_cutoff_hz`):

```latex
\operatorname{tone}\left(F(T), G(T)\cdot\left(1+(B-1)\cdot\frac{\operatorname{sign}(cutoff-F(T))+1}{2}\right)\right)
```

`B=1` is neutral; default export/player **1.6**.

## Sustain

Physical `note_off` at `k` while CC64 down: set `e = pedal_up_beat`, not `k`.

## Reattack

New `note_on` same `(channel, pitch)` before prior `audible_end`:

1. Close prior held branch at reattack beat `t_cut`.
2. Emit release tail `[t_cut, t_cut + r)` on prior lane (or new lane if overlap).
3. Open new segment at `t_cut` on a lane that is free for `[t_cut, audible_end_new)`.

V1 uses **separate lanes** when release overlaps new attack (no merged-gain on same pitch).

## Velocity and polyphony

```python
a = global_gain * (velocity / 127) ** 1.5 * freq_gain_mult(frequency)
freq_gain_mult(f) = min(2.8, sqrt(280 / f)) for f < 280 Hz else 1
decay(f) = decay_per_beat * min(1, max(0.22, f / 440))
global_gain = min(0.15, 0.6 / sqrt(max(1, peak_audible_polyphony)))
a = min(a, min(10, 660 / frequency))
```

## Silence

`G=0` outside branches. Keep `F(T)` at fallback (20 Hz floor in export) when silent.

## CLI vs player

| Knob | Where | Default |
| --- | --- | --- |
| `--decay-per-beat` | Export `d` in each branch | 0.65 |
| `D` slider | Live multiplier in `e^{-D·d…}` | 3 |
| `B` slider | Live bass in `tone()` | 1.6 |
| `--release-beats` | Export tail length | 0.08 |
| `--global-gain` | Export peak scale | auto |

Tuning long repertoire: adjust **`D`** in the player first; change **`--decay-per-beat`** when regenerating the bundle.

## V2

SoundFont-like envelopes stay out of V1; same `G(T)` machinery may later drive harmonic weights.
