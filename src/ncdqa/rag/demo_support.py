"""Support code for demo.py (Track C): environment check, result serialisation, showcase questions. No model is loaded here, so everything is testable without the index.

    python -X utf8 demo.py --check          # what is missing on this machine, and the exact command that fixes it

The check answers "can a teammate run the demo on a fresh clone?": Python version, packages, the local data bundle (the index is not in git: it holds corpus text), the LLM provider file, the API key
(only whether it is set, never its value) and whether the embedding model is already in the Hugging Face cache (first start downloads about 2.3 GB).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKAGES = {"sentence_transformers": "sentence-transformers", "faiss": "faiss-cpu", "bm25s": "bm25s", "pythainlp": "pythainlp", "numpy": "numpy", "yaml": "PyYAML", "langgraph": "langgraph (only for --graph / --agent langgraph / react)"}
OPTIONAL_PACKAGES = {"langgraph"}
SHOWCASE_PATH = ROOT / "docs/demo/showcase_questions.json"
MANIFEST_NAME = "BUNDLE_MANIFEST.json"
DEMO_CACHE_DIR = "data/index/llm_cache/demo"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def hf_cache_dir() -> Path:
    base = os.environ.get("HF_HUB_CACHE") or os.path.join(os.environ.get("HF_HOME") or os.path.join(os.path.expanduser("~"), ".cache", "huggingface"), "hub")
    return Path(base)


def required_paths() -> list[Path]:
    cfg = json.loads((ROOT / "configs/retrieval/serve_v1.json").read_text(encoding="utf-8"))
    out = []
    for key, rel in cfg["paths"].items():
        base = ROOT / rel
        out += [base / "chunks.jsonl"] if "chunks" in key else [base / "vectors.npy", base / "chunk_ids.json", base / "index_manifest.json"]
    return out


def check_environment(root: Path = ROOT) -> list[dict]:
    """[{name, ok, detail, fix}]; `fix` is a command or an instruction, empty when ok."""
    rows: list[dict] = []

    def add(name, ok, detail, fix=""):
        rows.append({"name": name, "ok": bool(ok), "detail": detail, "fix": "" if ok else fix})

    add("Python 3.12+", sys.version_info >= (3, 12), sys.version.split()[0], "uv venv --python 3.12 .venv   (then activate it)")
    for mod, pip_name in PACKAGES.items():
        found = importlib.util.find_spec(mod) is not None
        add(f"package {mod}", found or mod in OPTIONAL_PACKAGES, "installed" if found else ("not installed (optional)" if mod in OPTIONAL_PACKAGES else "not installed"),
            "uv pip install -r requirements-rag.txt -r requirements-agent.txt")
    missing = [p for p in required_paths() if not p.exists()]
    add("local data bundle (index + chunks)", not missing, "all files present" if not missing else f"{len(missing)} files missing, e.g. {missing[0].relative_to(root)}",
        "get ncd_demo_bundle.zip from the team (private, not in git) and run: python -X utf8 scripts/install_demo_bundle.py ncd_demo_bundle.zip")
    manifest = root / MANIFEST_NAME
    if manifest.exists() and not missing:
        entries = json.loads(manifest.read_text(encoding="utf-8"))["files"]
        bad = [rel for rel, digest in entries.items() if (root / rel).exists() and sha256(root / rel) != digest]
        add("bundle files match the manifest", not bad, "checksums ok" if not bad else f"{len(bad)} files differ, e.g. {bad[0]}", "install the bundle again (a file was changed or damaged)")
    prov = root / "configs/llm/providers.yaml"
    add("configs/llm/providers.yaml", prov.exists(), "present" if prov.exists() else "missing", "copy configs/llm/providers.example.yaml configs/llm/providers.yaml")
    env_ok = bool(os.environ.get("TYPHOON_API_KEY"))
    envfile = root / ".env"
    if not env_ok and envfile.exists():
        env_ok = any(line.strip().startswith("TYPHOON_API_KEY=") and line.strip().split("=", 1)[1].strip() for line in envfile.read_text(encoding="utf-8").splitlines())
    add("TYPHOON_API_KEY (value is never printed)", env_ok, "set" if env_ok else "not set", "copy .env.example .env and put the key after TYPHOON_API_KEY= (ask the team for it); cached demo questions work without it")
    model_dir = hf_cache_dir() / "models--BAAI--bge-m3"
    add("embedding model BAAI/bge-m3 in the local cache", model_dir.exists(), "cached" if model_dir.exists() else "not cached: the first start downloads about 2.3 GB",
        "run once with internet before the presentation: python -X utf8 demo.py --warm")
    cache = root / DEMO_CACHE_DIR
    n = sum(1 for _ in cache.glob("*.jsonl")) if cache.exists() else 0
    add("demo answer cache (lets the showcase questions run offline)", n > 0, f"{n} cache file(s)" if n else "empty", "optional: python -X utf8 demo.py --warm (needs the API key once) or install the bundle that contains it")
    return rows


def render_check(rows: list[dict]) -> str:
    lines = []
    for r in rows:
        lines.append(f'[{"OK" if r["ok"] else "!!"}] {r["name"]}: {r["detail"]}' + (f'\n     fix: {r["fix"]}' if r["fix"] else ""))
    blockers = [r for r in rows if not r["ok"] and r["name"] not in ("embedding model BAAI/bge-m3 in the local cache", "demo answer cache (lets the showcase questions run offline)")
                and not r["name"].startswith("TYPHOON_API_KEY")]
    lines.append("")
    lines.append("READY to run the demo." if not blockers else f"NOT ready: {len(blockers)} blocking item(s) above (the key and the caches are not blockers for cached questions).")
    return "\n".join(lines)


def load_showcase() -> list[dict]:
    return json.loads(SHOWCASE_PATH.read_text(encoding="utf-8")) if SHOWCASE_PATH.exists() else []


def serialize(result: dict, units: dict | None = None, evidence_chars: int = 700) -> dict:
    """What the web page needs: status, answer, citations, the masked question, guard messages and (optionally) the evidence text. Never the raw input."""
    t = result.get("trace", {})
    out = {"status": result["status"], "answer": result.get("answer"), "question_shown": result.get("question"), "citations": result.get("citations", []),
           "masked": t.get("pii_masked"), "guard": (t.get("guard") or {}) and {"category": t["guard"].get("category"), "message": t["guard"].get("message")},
           "output_guard": result.get("output_guard"), "dropped": [d.get("reason") for d in (t.get("dropped_claims") or [])][:5],
           "tokens": (t.get("usage") or {}).get("total_tokens"), "cached": t.get("cached"), "tool_steps": t.get("n_tool_calls"), "path": t.get("graph_path") or t.get("react_path")}
    if units is not None:
        out["evidence"] = [{"id": sid, "chunk_id": cid, "document": units[cid]["document_id"], "pages": f'{units[cid]["pdf_page_start"]}-{units[cid]["pdf_page_end"]}',
                            "text": units[cid]["text"][:evidence_chars]} for sid, cid in (t.get("evidence") or {}).items() if cid in units]
    return out
