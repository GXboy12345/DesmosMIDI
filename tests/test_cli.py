from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from desmosmidi.cli import main
from desmosmidi.paths_util import default_out_dir

FIX = Path(__file__).parent / "fixtures" / "generated"


@pytest.fixture(scope="module", autouse=True)
def _fixtures():
    from desmosmidi.fixtures_gen import main as mk

    mk()


def test_default_out_dir_sanitizes():
    assert default_out_dir("My Song!.mid") == Path("dist/My-Song")
    assert default_out_dir(FIX / "c_major_chord.mid") == Path("dist/c_major_chord")


def test_check_rich_output(capsys):
    code = main(["check", str(FIX / "c_major_chord.mid")])
    assert code == 0
    out = capsys.readouterr().out
    assert "Check" in out or "beats" in out


def test_shorthand_build(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DESMOS_API_KEY", "test-key")
    monkeypatch.chdir(tmp_path)
    code = main([str(FIX / "c_major_chord.mid")])
    assert code == 0
    out = tmp_path / "dist" / "c_major_chord"
    assert (out / "player.html").is_file()
    meta = json.loads((out / "song.meta.json").read_text(encoding="utf-8"))
    assert meta.get("audio_only") is True


def test_inspect_json(capsys):
    code = main(["check", str(FIX / "c_major_chord.mid"), "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["schema_version"] == 1


def test_no_args_launches_tui():
    with patch("desmosmidi.app.run_app") as run:
        assert main([]) == 0
        run.assert_called_once()


def test_play_opens_browser(tmp_path, monkeypatch):
    monkeypatch.setenv("DESMOS_API_KEY", "test-key")
    monkeypatch.chdir(tmp_path)

    class FakeProc:
        def wait(self, timeout=None):
            return 0

        def terminate(self):
            pass

    with patch("desmosmidi.runner.subprocess.Popen", return_value=FakeProc()):
        with patch("desmosmidi.runner.webbrowser.open") as opn:
            code = main(["play", str(FIX / "c_major_chord.mid")])
    assert code == 0
    opn.assert_called_once()
