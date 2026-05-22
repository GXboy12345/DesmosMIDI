from pathlib import Path

from desmosmidi.viz_export import audible_to_viz_notes, write_viz_notes
from desmosmidi.models import AudibleSegment


def test_audible_to_viz_skips_release_tail():
    audible = [
        AudibleSegment(0, 60, 80, 0.0, 1.0, False),
        AudibleSegment(0, 60, 40, 1.0, 1.5, True),
    ]
    notes = audible_to_viz_notes(audible)
    assert len(notes) == 1
    assert notes[0]["p"] == 60


def test_write_viz_notes(tmp_path):
    audible = [AudibleSegment(0, 72, 100, 0.0, 2.0, False)]
    payload = write_viz_notes(tmp_path, audible)
    p = Path(tmp_path) / "viz" / "notes.json"
    assert p.is_file()
    assert payload["pitch_min"] == 72
    assert (Path(tmp_path) / "expr" / "viz-data.json").is_file()
