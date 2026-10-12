"""Pack the local data a teammate needs to run demo.py into one zip (Track C). The index is NOT in git because it holds corpus text (the Siriraj leaflets among it, decision 0008): share the zip
inside the team only (private drive), never publicly.

    python -X utf8 scripts/make_demo_bundle.py --out ncd_demo_bundle.zip

Contents: the three index folders named in configs/retrieval/serve_v1.json (parent chunks, child chunks, dense vectors), the demo answer cache (data/index/llm_cache/demo, so the showcase questions
also run offline) and BUNDLE_MANIFEST.json (sha256 of every file; `demo.py --check` uses it). The API key is never included.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ncdqa.rag import demo_support  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=ROOT / "ncd_demo_bundle.zip")
    ap.add_argument("--no-cache", action="store_true", help="leave the demo answer cache out")
    args = ap.parse_args()
    if args.out.exists():
        sys.exit(f"{args.out} exists, choose another --out")
    cfg = json.loads((ROOT / "configs/retrieval/serve_v1.json").read_text(encoding="utf-8"))
    folders = [ROOT / rel for rel in cfg["paths"].values()]
    if not args.no_cache and (ROOT / demo_support.DEMO_CACHE_DIR).exists():
        folders.append(ROOT / demo_support.DEMO_CACHE_DIR)
    files = sorted(p for folder in folders for p in folder.rglob("*") if p.is_file())
    missing = [p for p in demo_support.required_paths() if not p.exists()]
    if missing:
        sys.exit(f"missing required files, build the index first: {missing[0]}")
    manifest = {"created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "retrieval_config": cfg["id"],
                "note": "corpus text inside: share privately in the team, never publicly (decision 0008)",
                "files": {p.relative_to(ROOT).as_posix(): demo_support.sha256(p) for p in files}}
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr(demo_support.MANIFEST_NAME, json.dumps(manifest, ensure_ascii=False, indent=1))
        for p in files:
            z.write(p, p.relative_to(ROOT).as_posix())
    print(f"{args.out}  {args.out.stat().st_size / 1e6:.1f} MB, {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
