from __future__ import annotations

from pathlib import Path
import json

import pytest

from desmosmidi.models import ExportConfig
from desmosmidi.midi_parse import load_midi
from desmosmidi.notes import extract_notes, peak_audible_polyphony, to_audible
from desmosmidi.piano_gate import filter_events, gate_channels
from desmosmidi.pipeline import build_from_file, export_bundle
from desmosmidi.voices import allocate_lanes

FIX = Path(__file__).parent / "fixtures" / "generated"


@pytest.fixture(scope="module", autouse=True)
def _fixtures():
    from desmosmidi.fixtures_gen import main

    main()


def _cfg(**kw) -> ExportConfig:
    return ExportConfig(**kw)


def test_c_major_chord_lanes():
    br, _, _, _ = build_from_file(FIX / "c_major_chord.mid", _cfg())
    assert br.peak_physical >= 3
    assert len(br.lanes) >= 3
    holds = [a for a in br.audible if not a.is_release_tail]
    assert len(holds) == 3
    assert all(abs(a.end_beat - 2.08) < 0.01 for a in holds)
    assert abs(holds[0].start_beat - holds[1].start_beat) < 0.01


def test_sustain_effective_end():
    br, _, _, _ = build_from_file(FIX / "sustain_cc64.mid", _cfg())
    main = [s for s in br.segments if not s.is_release_tail]
    assert main
    assert main[0].effective_end_beat >= 2.4


def test_reattack_cut():
    br, _, _, _ = build_from_file(FIX / "reattack_same_pitch.mid", _cfg())
    assert br.reattacks_cut >= 1
    assert any(s.is_release_tail for s in br.segments)


def test_tempo_segments():
    parsed = load_midi(FIX / "tempo_changes.mid")
    assert len(parsed.tempo_segments) >= 3


def test_gate_drums_fail():
    _, _, _, meta = build_from_file(FIX / "drum_channel_fail.mid", _cfg())
    assert meta.get("errors")


def test_gate_non_piano_fail():
    _, _, _, meta = build_from_file(FIX / "non_piano_strings_fail.mid", _cfg())
    assert meta.get("errors")


def test_bass_gain_boost():
    from desmosmidi.envelopes import peak_gain

    g = 0.12
    lo = peak_gain(100, 55.0, g)
    hi = peak_gain(100, 440.0, g)
    assert lo > hi


def test_gain_audit_never_over_cap():
    from desmosmidi.envelopes import audit_gains, max_gain, midi_to_hz, peak_gain

    br, _, _, _ = build_from_file(FIX / "c_major_chord.mid", _cfg())
    aud = audit_gains(br.audible, _cfg(), br.peak_audible)
    assert aud["export_over_cap_count"] == 0
    assert aud["peak_gain_max"] <= 10.0
    for seg in br.audible:
        f = midi_to_hz(seg.pitch)
        assert peak_gain(seg.velocity, f, 0.12) <= max_gain(f) + 1e-9


def test_two_hand_ok():
    br, _, exprs, _ = build_from_file(FIX / "two_hand_two_channel.mid", _cfg())
    assert br.segments
    assert any("\\operatorname{tone}" in e.latex for e in exprs)
    assert any(e.id == "B" for e in exprs)
    tone = next(e for e in exprs if e.id.startswith("tone_"))
    assert "B-1" in tone.latex and "\\operatorname{sign}" in tone.latex


def test_export_default_audio_only(tmp_path):
    import os

    key = os.environ.get("DESMOS_API_KEY", "test-key")
    export_bundle(
        FIX / "c_major_chord.mid",
        tmp_path / "default",
        _cfg(),
        api_key=key,
        command="test",
    )
    meta = json.loads((tmp_path / "default" / "song.meta.json").read_text(encoding="utf-8"))
    assert meta.get("audio_only") is True
    assert meta.get("viz") is None
    assert not (tmp_path / "default" / "viz").exists()
    assert not (tmp_path / "default" / "expr" / "viz-data.json").exists()


def test_export_writes_player_with_viz(tmp_path):
    import os

    key = os.environ.get("DESMOS_API_KEY", "test-key")
    export_bundle(
        FIX / "c_major_chord.mid",
        tmp_path / "chord",
        _cfg(audio_only=False),
        api_key=key,
        command="test",
    )
    assert (tmp_path / "chord" / "player.html").is_file()
    assert (tmp_path / "chord" / "song.meta.json").is_file()
    assert (tmp_path / "chord" / "expr" / "manifest.json").is_file()
    html = (tmp_path / "chord" / "player.html").read_text()
    assert "manifest.json" in html
    assert key in html
    assert "Keyroll" in html
    assert "Keyroll scroll" not in html
    assert "No render" in html
    assert (tmp_path / "chord" / "viz" / "notes.json").is_file()
    meta = json.loads((tmp_path / "chord" / "song.meta.json").read_text(encoding="utf-8"))
    assert meta.get("viz", {}).get("note_count", 0) >= 1
    ordered = json.loads((tmp_path / "chord" / "expressions.json").read_text(encoding="utf-8"))
    g = next(x for x in ordered if x.get("id", "").startswith("g_l"))
    assert g.get("hidden") is not True
    assert g.get("secret") is not True
    assert g.get("lineOpacity") == 0
    assert "g_{l" in g["latex"]
    assert "D\\cdot" in g["latex"]
    tone = next(x for x in ordered if x.get("id", "").startswith("tone_l"))
    assert "\\operatorname{tone}" in tone["latex"]
    assert "f_{l" in tone["latex"]
    assert ordered[0]["type"] == "folder"
    assert ordered[1]["id"] == "T"
    assert ordered[2]["id"] == "B"
    assert ordered[2]["latex"] == "B=1.6"
    assert ordered[3]["id"] == "D"
    assert ordered[3]["latex"] == "D=3.65"
    assert (tmp_path / "chord" / "expr" / "viz-data.json").is_file()
    assert any(r.get("id") == "viz_playhead" for r in ordered)
    pcm = next(x for x in ordered if x.get("id") == "pcm_sum")
    assert "\\operatorname{pcm}\\left(x\\right)" in pcm["latex"]
    assert "frac{1}" in pcm["latex"]
    assert "12" in pcm["latex"] and "cdot" in pcm["latex"] and "frac{1}" in pcm["latex"]
    viz_data = json.loads((tmp_path / "chord" / "expr" / "viz-data.json").read_text(encoding="utf-8"))
    kr = next(x for x in viz_data if x.get("id") == "keyroll")
    assert len(kr["columns"]) == 2
    assert "undefined" in kr["columns"][0]["values"]


def test_export_audio_only(tmp_path):
    import os

    key = os.environ.get("DESMOS_API_KEY", "test-key")
    export_bundle(
        FIX / "c_major_chord.mid",
        tmp_path / "audio",
        _cfg(audio_only=True),
        api_key=key,
        command="test",
    )
    meta = json.loads((tmp_path / "audio" / "song.meta.json").read_text(encoding="utf-8"))
    assert meta.get("audio_only") is True
    assert meta.get("viz") is None
    assert not (tmp_path / "audio" / "viz").exists()
    assert not (tmp_path / "audio" / "expr" / "viz-data.json").exists()
    ordered = json.loads((tmp_path / "audio" / "expressions.json").read_text(encoding="utf-8"))
    ids = {r.get("id") for r in ordered}
    assert "pcm_sum" not in ids
    assert "keyroll" not in ids
    assert "viz_playhead" not in ids
    assert "V" not in ids
    assert "tone_l0c0" in ids or any(x.startswith("tone_") for x in ids)
    folder_ids = {r.get("id") for r in ordered if r.get("type") == "folder"}
    assert "dmidi_viz" not in folder_ids
    html = (tmp_path / "audio" / "player.html").read_text()
    assert '"audio_only":true' in html.replace(" ", "") or '"audio_only": true' in html
