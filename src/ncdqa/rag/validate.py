"""Check the model's output before anything is shown (the Validate step of Constrain -> Validate -> Recover -> Escalate).

The model answers as claims, each with the ids of the evidence that supports it. A claim is kept only if
  * its text is a non-empty string and it cites at least one id,
  * every cited id is one that was really sent (no invented citation),
  * every number in the claim also appears in the cited evidence (Thai digits and thousands separators normalised),
  * a number the USER wrote in the question (a year, a stage, "100 grams") may be repeated in the claim without being in the evidence, when `question` is given
    (profile N8; found in the 2026-10-12 error analysis: 6 of 13 dropped claims in dev+test were dropped only for such a number). Every other number must still be in the cited evidence.
  * optionally (`check_tokens`) every Latin word of 4+ characters in the claim also appears in the cited evidence, so a claim that
    smuggles in text from the question (a canary, a drug name the evidence never mentions) is dropped. It cannot catch text that was
    planted inside the evidence itself.
Dropped claims are reported with a reason; nothing is repaired or rewritten.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

_THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_LATIN = re.compile(r"[A-Za-z][A-Za-z0-9-]{3,}")
_FENCE = re.compile(r"^```(?:json)?\s*", re.I)


@dataclass
class Validation:
    parsed: bool
    abstain: bool = False
    kept: list[dict] = field(default_factory=list)       # {"text", "cite": [S-ids]}
    dropped: list[dict] = field(default_factory=list)    # {"text", "cite", "reason"}
    problem: str | None = None


def parse_output(text: str) -> dict | None:
    """The first complete JSON object in the text. Models sometimes add commentary after it or repeat it until the token limit;
    only the first object is read, so that does not turn a good answer into a failure."""
    s = _FENCE.sub("", text.strip())
    start = s.find("{")
    if start < 0:
        return None
    try:
        out, _ = json.JSONDecoder().raw_decode(s[start:])
    except json.JSONDecodeError:
        return None
    return out if isinstance(out, dict) else None


def numbers(text: str) -> set[str]:
    t = text.translate(_THAI_DIGITS)
    t = re.sub(r"(?<=\d),(?=\d{3}\b)", "", t)
    return set(_NUMBER.findall(t))


def validate(raw: str, evidence: dict[str, dict], check_claims: bool = True, check_tokens: bool = False, question: str | None = None) -> Validation:
    out = parse_output(raw)
    if out is None or not isinstance(out.get("claims", []), list):
        return Validation(False, problem="output is not the required JSON")
    if out.get("abstain") is True:
        return Validation(True, abstain=True)
    v = Validation(True)
    own = numbers(question) if question else set()          # numbers the user already stated
    for c in out.get("claims", []):
        text = c.get("text") if isinstance(c, dict) else None
        cite = c.get("cite") if isinstance(c, dict) else None
        if not isinstance(text, str) or not text.strip():
            v.dropped.append({"text": text, "cite": cite, "reason": "empty claim"})
            continue
        if not isinstance(cite, list) or not cite:
            v.dropped.append({"text": text, "cite": cite, "reason": "no citation"})
            continue
        bad = [x for x in cite if x not in evidence]
        if bad:
            v.dropped.append({"text": text, "cite": cite, "reason": f"citation not in the evidence sent: {bad}"})
            continue
        if check_claims:
            have = set().union(*(numbers(evidence[x]["text"]) for x in cite))
            missing = sorted(numbers(text) - have - own)
            if missing:
                v.dropped.append({"text": text, "cite": cite, "reason": f"number not in cited evidence: {missing}"})
                continue
        if check_tokens:
            cited = " ".join(evidence[x]["text"] for x in cite).lower()
            missing = sorted(t for t in set(_LATIN.findall(text)) if t.lower() not in cited)
            if missing:
                v.dropped.append({"text": text, "cite": cite, "reason": f"word not in cited evidence: {missing}"})
                continue
        v.kept.append({"text": text.strip(), "cite": cite})
    return v
