from __future__ import annotations

import os
import re
from pathlib import Path


def load_env() -> None:
    env_path = Path.cwd() / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def api_key() -> str:
    load_env()
    return os.environ.get("DESMOS_API_KEY", "").strip()


def has_api_key() -> bool:
    return bool(api_key())


def save_api_key(key: str) -> Path:
    key = key.strip()
    env_path = Path.cwd() / ".env"
    line = f"DESMOS_API_KEY={key}\n"
    if env_path.is_file():
        text = env_path.read_text(encoding="utf-8")
        if "DESMOS_API_KEY" in text:
            text = re.sub(r"^DESMOS_API_KEY=.*$", line.strip(), text, flags=re.M)
            env_path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
        else:
            env_path.write_text(text + line, encoding="utf-8")
    else:
        env_path.write_text(line, encoding="utf-8")
    os.environ["DESMOS_API_KEY"] = key
    return env_path.resolve()
