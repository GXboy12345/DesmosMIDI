# Sharing exports

## V1 share story (locked)

1. `desmosmidi export` writes `dist/<song>/player.html` plus sidecar JSON.
2. **Local:** serve the export directory and open `player.html` (chunk and viz paths use `fetch`).
3. **Remote:** publish `dist/<song>/` to GitHub Pages, Cloudflare Pages, Netlify, or any static host — one URL, Play once.

```bash
cd dist/my-song && python3 -m http.server 8765
# http://localhost:8765/player.html
```

Opening `player.html` via `file://` often fails when expressions load from `expr/chunk-*.json` or `expr/viz-data.json`. Use a static server or `--inline-expressions` for a single-file expression list (viz sidecar still needs HTTP unless inlined in future work).

Hosted `desmos.com/calculator/<id>` is **manual only**: Save / Share in Desmos UI. No documented API to create graph IDs programmatically. No documented URL hash/query state loader for arbitrary generated state.

Community pattern to **load** an existing graph (not create):

```js
const response = await fetch("https://www.desmos.com/calculator/<id>", {
  headers: { Accept: "application/json" },
});
calculator.setState((await response.json()).state);
```

Source: [desmos-api-discuss](https://groups.google.com/g/desmos-api-discuss/c/kkQDgkeucVo)

## API key

The key is passed in the browser script URL — **not a server secret**. CLI reads `DESMOS_API_KEY` from `.env` and inlines into generated HTML at export time.

Do not commit generated HTML with a production key if the repo is public; regenerate locally or inject at deploy time.

Redistribution: see root [NOTICE](../NOTICE) for the Desmos API disclaimer (not affiliated; client-visible key; comply with Desmos terms).

## Artifacts

| File | Role |
| --- | --- |
| `player.html` | Primary playback (API v1.13, Play/Stop, rAF beat clock, optional viz) |
| `song.meta.json` | Tempo map, duration, viz pointers, `audio_only`, load hints (also inlined in HTML) |
| `expressions.json` | Folder-ordered full list for `setExpressions` / `setState` rebuild |
| `expr/manifest.json` + `chunk-*.json` | Chunked load when not using inline mode |
| `expr/viz-data.json` | Keyroll table (full export only) |
| `viz/notes.json` | Pitch range and pcm viewport metadata |
| `song.report.json` | Machine diagnostics (`report-schema.md`) |
| `expressions.md` | Manual paste fallback |

## Native Desmos (no custom HTML)

User can paste from `expressions.md`, enable Actions, drive `T` with ticker, unmute (Alt+M). Does **not** satisfy one-click Play UX or folder collapse automation.

## Audio-only share

Same hosting model; smaller expression count, no viz fetch. Status line in player shows `audio only`. Use for performance-sensitive sharing of long piano scores.
