# CLI

For most people: [Quickstart.md](../Quickstart.md).

Stack matches **autosort**: **Textual** TUI when you run `desmosmidi` with no arguments, **Rich** tables/panels/progress for terminal commands, **Click** for parsing.

## Everyday use

| Action | Command |
| --- | --- |
| Open UI | `desmosmidi` |
| First-time API key | `desmosmidi setup` |
| Build player | `desmosmidi your-song.mid` |
| Build + browser | `desmosmidi play your-song.mid` |
| Preview file | `desmosmidi check your-song.mid` |
| Visualization | add `--viz` (off by default) |

You do not type `export` — a `.mid` path alone runs **build**.

## Terminal UI

- Path field + **Open…** (macOS file picker via AppleScript)
- **Check** / **Build** / **Play** / **Setup**
- **Visualization** checkbox (off by default)
- Log panel with markup
- Keys: `o` open, `c` check, `b` build, `p` play, `s` setup, `q` quit

## CLI output

- `check` → Rich table panel
- `build` / `play` → progress spinner, green **Ready** panel with player URL
- `setup` → writes `.env`

## Hidden / script aliases

`export`, `inspect`, `make-fixtures` — same behavior as before, not shown in main help.

Full flags: `desmosmidi build --help`

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | OK |
| 1 | Missing file or API key |
| 2 | Piano check failed at build |
| 3 | No notes (`check`) |
