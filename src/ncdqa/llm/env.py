"""Load `.env` into the process environment without ever printing or returning a secret (Track B).

Only KEY=VALUE lines are read (an optional `export ` prefix and surrounding quotes are accepted, `#` lines ignored). A variable that is
already set in the real environment is left alone, so a shell value wins over the file. Callers get the NAMES that were loaded, never the
values. The file is opened only when a script asks for it.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def load_env(path: Path | None = None) -> list[str]:
    path = path or ROOT / ".env"
    if not path.exists():
        return []
    loaded = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, _, value = line.partition("=")
        name, value = name.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if name and value and name not in os.environ:
            os.environ[name] = value
            loaded.append(name)
    return loaded


def is_set(name: str) -> bool:
    return bool(os.environ.get(name))
