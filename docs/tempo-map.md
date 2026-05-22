# Tempo map and beat timeline

## Units

| Unit | Meaning |
| --- | --- |
| Tick | MIDI delta accumulation |
| Beat | Quarter note: `tick / ticks_per_beat` |
| Second | `mido.tick2second` with tempo map |
| BPM | `60_000_000 / tempo_us_per_quarter` |

**`T` in exported LaTeX is beats**, not seconds.

## Parsing

1. `ticks_per_beat` from file.
2. Merge type 0/1 tracks; stable sort by absolute tick.
3. Record `set_tempo` → segments `{start_beat, bpm}`.
4. Never sum raw deltas without tempo conversion.

## API player clock (V1 primary)

`player.html` integrates beats on `requestAnimationFrame`:

```js
function bpmAtBeat(beat) {
  let bpm = tempoMap[0].bpm;
  for (const seg of tempoMap) {
    if (beat >= seg.beat) bpm = seg.bpm;
    else break;
  }
  return bpm;
}

// each frame:
T += dt_seconds * (bpmAtBeat(T) / 60);
calc.setExpression({ id: "T", latex: "T=" + T.toFixed(6) });
```

Play click: `updateSettings({ muted: false })` then start rAF. One user gesture.

Sources: [API v1.13](https://www.desmos.com/api/v1.13/docs/index.html), [Tone](https://help.desmos.com/hc/en-us/articles/21373904717197-Tone)

Ticker-only on desmos.com **cannot** unmute in the same gesture — not V1 UX.

## Ticker recipe (optional native Desmos)

For paste-into-desmos.com experiments ([Actions](https://help.desmos.com/hc/en-us/articles/4407725009165-Actions)):

```latex
T=0
P=0
B\left(T\right)=\left\{0\le T<16:120,16\le T<24:90,24\le T<40:132,120\right\}
```

Ticker action:

```latex
T\to\left\{P=1:T+\frac{dt}{1000}\cdot\frac{B\left(T\right)}{60},T\right\}
```

Play: `P\to1`. Stop: `P\to0,T\to0`.

User must unmute tones and start ticker manually.

## Graph bounds

```js
setMathBounds({ left: 0, right: duration_beats, bottom: -1, top: 1 });
```

Y axis unused for audio; frequency lives inside `tone()`.

## Frame quantization

Beat clock updates at display rate (~60 Hz). Warn on notes shorter than ~0.03s at local tempo (`SHORT_NOTE_FRAME_QUANTIZATION` in report).
