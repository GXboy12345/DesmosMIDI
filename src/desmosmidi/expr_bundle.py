from __future__ import annotations

import json
from pathlib import Path

from desmosmidi.desmos_latex import DesmosExpression

FOLDER_CLOCK = "dmidi_clock"
FOLDER_HELPERS = "dmidi_helpers"
FOLDER_AUDIO = "dmidi_audio"
FOLDER_VIZ = "dmidi_viz"

FOLDER_SPECS = [
    {"type": "folder", "id": FOLDER_CLOCK, "title": "clock", "collapsed": True},
    {"type": "folder", "id": FOLDER_HELPERS, "title": "MIDI helpers", "collapsed": True},
    {"type": "folder", "id": FOLDER_AUDIO, "title": "audio", "collapsed": True},
    {"type": "folder", "id": FOLDER_VIZ, "title": "viz", "collapsed": True},
]


def folder_specs(*, audio_only: bool = False) -> list[dict]:
    if audio_only:
        return FOLDER_SPECS[:3]
    return FOLDER_SPECS


def expression_to_api(expr: DesmosExpression, *, hide_graph: bool = True) -> dict:
    if expr.role == "viz_roll":
        return {
            "id": expr.id,
            "type": "table",
            "folderId": FOLDER_VIZ,
            "columns": expr.table_columns or [],
            "color": "#64b4ff",
            "lineWidth": 5,
        }
    if expr.role == "viz_playhead":
        return {
            "id": expr.id,
            "type": "expression",
            "latex": expr.latex,
            "folderId": FOLDER_VIZ,
            "color": "#ff5a5a",
            "lineWidth": 2,
        }
    if expr.role == "viz_pcm":
        return {
            "id": expr.id,
            "type": "expression",
            "latex": expr.latex,
            "folderId": FOLDER_VIZ,
            "color": "#7ad4ff",
            "lineWidth": 2,
            "hidden": True,
        }
    if expr.role == "viz_list":
        return {
            "id": expr.id,
            "type": "expression",
            "latex": expr.latex,
            "folderId": FOLDER_VIZ,
            "hidden": True,
        }

    row: dict = {"id": expr.id, "latex": expr.latex, "type": "expression"}
    if expr.role == "clock":
        row["folderId"] = FOLDER_CLOCK
        return row
    if expr.role == "bass_ctrl":
        row["folderId"] = FOLDER_CLOCK
        row["slider"] = {
            "hardMin": True,
            "hardMax": True,
            "min": "0.25",
            "max": "3",
            "step": "0.05",
        }
        return row
    if expr.role == "decay_ctrl":
        row["folderId"] = FOLDER_CLOCK
        row["slider"] = {
            "hardMin": True,
            "hardMax": True,
            "min": "1",
            "max": "5",
            "step": "0.05",
        }
        return row
    if expr.role == "view_ctrl":
        row["folderId"] = FOLDER_CLOCK
        row["slider"] = {
            "hardMin": True,
            "hardMax": True,
            "min": "1",
            "max": "2",
            "step": "1",
        }
        return row
    if expr.role == "tone":
        row["folderId"] = FOLDER_AUDIO
        return row
    row["folderId"] = FOLDER_HELPERS
    if hide_graph:
        row["lineOpacity"] = 0
        row["points"] = False
    return row


def expressions_to_api(
    exprs: list[DesmosExpression],
    *,
    hide_graph: bool = True,
) -> list[dict]:
    return [expression_to_api(e, hide_graph=hide_graph) for e in exprs]


def _sort_key_clock(row: dict) -> tuple:
    rid = row.get("id", "")
    order = {"T": 0, "B": 1, "D": 2, "V": 3}
    return (order.get(rid, 9), rid)


def sort_for_load(api_rows: list[dict], *, specs: list[dict] | None = None) -> list[dict]:
    """Folder row, then its members contiguously — required for Desmos folder UI."""
    folder_list = specs if specs is not None else FOLDER_SPECS
    groups: dict[str, list[dict]] = {spec["id"]: [] for spec in folder_list}
    for row in api_rows:
        if row.get("type") == "folder":
            continue
        fid = row.get("folderId")
        if fid in groups:
            groups[fid].append(row)

    groups[FOLDER_CLOCK].sort(key=_sort_key_clock)
    groups[FOLDER_HELPERS].sort(key=lambda r: r.get("id", ""))
    groups[FOLDER_AUDIO].sort(key=lambda r: r.get("id", ""))
    if FOLDER_VIZ in groups:
        groups[FOLDER_VIZ].sort(key=lambda r: r.get("id", ""))

    out: list[dict] = []
    for spec in folder_list:
        out.append(dict(spec))
        out.extend(groups[spec["id"]])
    return out


def write_expr_bundle(
    out_dir: Path,
    exprs: list[DesmosExpression],
    *,
    chunk_size: int = 12,
    hide_graph: bool = True,
    audio_only: bool = False,
) -> dict:
    specs = folder_specs(audio_only=audio_only)
    api = expressions_to_api(exprs, hide_graph=hide_graph)
    ordered = sort_for_load(api, specs=specs)
    expr_root = out_dir / "expr"
    expr_root.mkdir(parents=True, exist_ok=True)

    def _folder_groups(rows: list[dict]) -> list[list[dict]]:
        groups: list[list[dict]] = []
        i = 0
        while i < len(rows):
            if rows[i].get("type") == "folder":
                g = [rows[i]]
                i += 1
                while i < len(rows) and rows[i].get("type") != "folder":
                    g.append(rows[i])
                    i += 1
                groups.append(g)
            else:
                groups.append([rows[i]])
                i += 1
        return groups

    chunks: list[str] = []
    buf: list[dict] = []
    for group in _folder_groups(ordered):
        if len(group) > chunk_size:
            if buf:
                name = f"chunk-{len(chunks):04d}.json"
                rel = f"expr/{name}"
                (out_dir / rel).write_text(json.dumps(buf, separators=(",", ":")), encoding="utf-8")
                chunks.append(rel)
                buf = []
            name = f"chunk-{len(chunks):04d}.json"
            rel = f"expr/{name}"
            (out_dir / rel).write_text(json.dumps(group, separators=(",", ":")), encoding="utf-8")
            chunks.append(rel)
            continue
        if len(buf) + len(group) > chunk_size and buf:
            name = f"chunk-{len(chunks):04d}.json"
            rel = f"expr/{name}"
            (out_dir / rel).write_text(json.dumps(buf, separators=(",", ":")), encoding="utf-8")
            chunks.append(rel)
            buf = []
        buf.extend(group)
        if len(buf) >= chunk_size:
            name = f"chunk-{len(chunks):04d}.json"
            rel = f"expr/{name}"
            (out_dir / rel).write_text(json.dumps(buf, separators=(",", ":")), encoding="utf-8")
            chunks.append(rel)
            buf = []
    if buf:
        name = f"chunk-{len(chunks):04d}.json"
        rel = f"expr/{name}"
        (out_dir / rel).write_text(json.dumps(buf, separators=(",", ":")), encoding="utf-8")
        chunks.append(rel)

    manifest = {
        "schema": 4,
        "expression_count": len(api),
        "chunk_size": chunk_size,
        "chunks": chunks,
        "folders": specs,
        "audio_only": audio_only,
        "load_order": "folder_then_members",
        "hide_helper_graphs": hide_graph,
    }
    (expr_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (out_dir / "expressions.json").write_text(json.dumps(ordered, indent=2), encoding="utf-8")
    return manifest


def write_meta(
    out_dir: Path,
    *,
    duration_beats: float,
    tempo_map: list[dict],
    bass_cutoff_hz: float = 280.0,
    decay_per_beat: float = 0.65,
) -> None:
    meta = {
        "duration_beats": duration_beats,
        "tempo_map": tempo_map,
        "load": "expr/manifest.json",
        "bass_cutoff_hz": bass_cutoff_hz,
        "decay_per_beat": decay_per_beat,
    }
    (out_dir / "song.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
