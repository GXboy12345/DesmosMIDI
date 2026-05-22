from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from desmosmidi.models import DEFAULT_LIVE_BASS_MULT, DEFAULT_LIVE_DECAY_MULT

_TPL = Path(__file__).resolve().parent / "templates"


def render_player(api_key: str, meta: dict) -> str:
    env = Environment(loader=FileSystemLoader(str(_TPL)), autoescape=False)
    tpl = env.get_template("player.html.j2")
    right = max(meta.get("duration_beats", 8), 1.0)
    return tpl.render(
        api_key=api_key,
        meta_json=json.dumps(meta, separators=(",", ":")),
        duration_beats=right,
        title="DesmosMIDI",
        default_bass_mult=DEFAULT_LIVE_BASS_MULT,
        default_decay_mult=DEFAULT_LIVE_DECAY_MULT,
        default_bass_slider=int(round(DEFAULT_LIVE_BASS_MULT * 100)),
    )
