# Quickstart

Turn a piano MIDI file into something you open in the browser and play.

## 1. One-time setup

```bash
cd /path/to/DesmosMIDI
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
desmosmidi setup
```

`setup` saves a free Desmos API key to `.env` — [desmos.com/my-api](https://www.desmos.com/my-api)

## 2. Use the app (easiest)

```bash
desmosmidi
```

Opens a **terminal UI** (same idea as `autosort`): pick a MIDI file, Check, Build, or Play. macOS **Open…** uses the native file picker.

## 3. Or use one command

```bash
desmosmidi play path/to/your-song.mid
```

Builds `dist/your-song/`, starts a local server, opens the player in your browser. Click **Play** once in the page.

Build only (no browser):

```bash
desmosmidi path/to/your-song.mid
```

Preview first:

```bash
desmosmidi check path/to/your-song.mid
```

Optional keyroll + waveform (heavier; can be unstable):

```bash
desmosmidi path/to/your-song.mid --viz
```

## More

[README.md](README.md) · [docs/cli.md](docs/cli.md)
