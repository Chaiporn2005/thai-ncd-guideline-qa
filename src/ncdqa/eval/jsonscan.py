"""Find the JSON object we asked a judge for inside a reply that may carry fences, tool-call wrappers or a repeated object."""

from __future__ import annotations

import json


def object_with(text: str, key: str) -> dict:
    """First JSON object in `text` that has `key`. Raises ValueError when there is none."""
    dec, i = json.JSONDecoder(), 0
    while True:
        i = text.find("{", i)
        if i < 0:
            raise ValueError(f"no JSON object with {key!r} in the judge reply")
        try:
            obj, end = dec.raw_decode(text[i:])
        except json.JSONDecodeError:
            i += 1
            continue
        if isinstance(obj, dict) and key in obj:
            return obj
        i += 1
