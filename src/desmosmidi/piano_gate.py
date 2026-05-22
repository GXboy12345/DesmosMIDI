from __future__ import annotations

from desmosmidi.models import ExportConfig, ParsedMidi

ACCEPTED = {0, 1}
GM_DRUM = 9


def gate_channels(parsed: ParsedMidi, cfg: ExportConfig) -> tuple[set[int], list[dict], list[dict], list[dict]]:
    warnings: list[dict] = []
    errors: list[dict] = []
    ch_info: list[dict] = []
    blocked: list[dict] = []
    allowed: set[int] = set()

    if parsed.drum_note_count > 0 and not cfg.strip_drums:
        errors.append(
            {
                "code": "DRUM_CHANNEL",
                "severity": "error",
                "message": f"Channel 10 has {parsed.drum_note_count} drum notes",
            }
        )

    for ch, count in parsed.channel_note_counts.items():
        if ch == GM_DRUM:
            if cfg.strip_drums:
                warnings.append(
                    {
                        "code": "STRIPPED_DRUMS",
                        "severity": "warn",
                        "message": "Stripped channel 10 drum notes",
                    }
                )
            continue
        if cfg.channel is not None and (ch + 1) != cfg.channel:
            continue
        prog = parsed.programs.get(ch)
        if prog is None and cfg.assume_piano_default:
            prog = 0
            warnings.append(
                {
                    "code": "MISSING_PROGRAM_ASSUMED_PIANO",
                    "severity": "warn",
                    "message": f"Channel {ch + 1}: no program_change; assumed Acoustic Grand (0)",
                }
            )
        if cfg.allow_any_program:
            allowed.add(ch)
            ch_info.append(
                {
                    "channel": ch,
                    "note_count": count,
                    "programs": [prog] if prog is not None else [],
                    "accepted": True,
                    "reason": "allow-any-program",
                }
            )
            continue
        if prog is not None and prog in ACCEPTED:
            allowed.add(ch)
            ch_info.append(
                {
                    "channel": ch,
                    "note_count": count,
                    "programs": [prog],
                    "accepted": True,
                    "reason": f"program {prog}",
                }
            )
        elif prog is not None:
            if cfg.strip_non_piano:
                warnings.append(
                    {
                        "code": "STRIPPED_NON_PIANO",
                        "severity": "warn",
                        "message": f"Stripped channel {ch + 1} program {prog}",
                    }
                )
            else:
                blocked.append(
                    {
                        "channel": ch,
                        "program": prog,
                        "note_count": count,
                        "reason": f"program {prog} not in {sorted(ACCEPTED)}",
                    }
                )

    if blocked and cfg.piano_only:
        for b in blocked:
            errors.append(
                {
                    "code": "NON_PIANO_CHANNEL",
                    "severity": "error",
                    "message": b["reason"],
                }
            )

    return allowed, warnings, errors, ch_info


def filter_events(
    events: list[tuple[int, object]],
    allowed: set[int],
    cfg: ExportConfig,
) -> list[tuple[int, object]]:
    out: list[tuple[int, object]] = []
    for tick, msg in events:
        if msg.is_meta:
            out.append((tick, msg))
            continue
        if not hasattr(msg, "channel"):
            out.append((tick, msg))
            continue
        ch = msg.channel
        if ch == GM_DRUM:
            if cfg.strip_drums:
                continue
            out.append((tick, msg))
            continue
        if cfg.channel is not None and (ch + 1) != cfg.channel:
            continue
        if ch not in allowed:
            continue
        out.append((tick, msg))
    return out
