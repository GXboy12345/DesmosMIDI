from __future__ import annotations

import re
import subprocess
from pathlib import Path


def strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def looks_like_midi(path: str) -> bool:
    p = Path(path)
    if p.suffix.lower() in (".mid", ".midi"):
        return True
    return p.is_file()


def default_out_dir(midi: str | Path) -> Path:
    stem = Path(midi).stem
    safe = re.sub(r"[^\w\-.]+", "-", stem).strip("-") or "song"
    return Path("dist") / safe


def resolve_midi(path: str) -> Path:
    p = Path(strip_quotes(path)).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f"No such MIDI file: {p}")
    return p.resolve()


def select_midi_dialog(title: str = "Select a MIDI file") -> Path | None:
    safe = title.replace("\\", "\\\\").replace('"', '\\"')
    script = (
        'tell application "System Events"\n'
        "  activate\n"
        f'  set midiFile to choose file with prompt "{safe}" '
        'of type {"mid", "midi", "public.midi-audio"}\n'
        "  return POSIX path of midiFile\n"
        "end tell"
    )
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip())
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None
