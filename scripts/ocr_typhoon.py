"""OCR flagged pages of a normalized corpus with the Typhoon OCR API, one shard per API key.

Selects pages whose normalized status is empty/garbled/degraded, skips empty pages that have no
image (genuinely blank), and splits the sorted page list into shards (page i goes to shard
i % num_shards). Each person runs their own shard with their own key, read from an environment
variable; the key is never printed or written. Results are appended to
<out-dir>/shard-<i>-of-<n>.jsonl, so an interrupted run resumes without repeating pages.

The source PDFs and the normalized corpus are not modified. Every OCR row is
status "ocr_unreviewed" until a person checks it; merging OCR text into a corpus version is a
separate step.

Usage:
    python scripts/ocr_typhoon.py --shard 0 --num-shards 2 --dry-run
    $env:TYPHOON_OCR_API_KEY = "<your key>"   # in your own shell, or:
    python -X utf8 scripts/ocr_typhoon.py --shard 0 --num-shards 2 --env-file .env --api-key-env TYPHOON_OCR_API_KEY_A
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OCR_STATUSES = ("empty", "garbled", "degraded")
MAX_PER_MINUTE = 18          # service limit is 20/min and 2/s per the Typhoon docs; keep a margin
MIN_INTERVAL_S = 60 / MAX_PER_MINUTE
MAX_RETRIES = 5


def select_pages(pages_root: Path, raw_root: Path, statuses: tuple[str, ...]) -> tuple[list[dict], list[dict]]:
    """Return (pages to OCR, skipped blank pages), sorted by document and page."""
    selected, skipped = [], []
    for pages_file in sorted(pages_root.glob("*/pages.jsonl")):
        doc_id = pages_file.parent.name
        rows = [json.loads(line) for line in pages_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        flagged = [r for r in rows if r["status"] in statuses]
        if not flagged:
            continue
        pdf_path = raw_root / doc_id / "source.pdf"
        reader = PdfReader(pdf_path)
        for row in flagged:
            item = {"document_id": doc_id, "pdf_page": row["pdf_page"], "normalized_status": row["status"],
                    "source_sha256": row["source_sha256"], "pdf_path": str(pdf_path)}
            has_image = len(reader.pages[row["pdf_page"] - 1].images) > 0
            if row["status"] == "empty" and not has_image:
                skipped.append(item)
            else:
                selected.append(item)
    return selected, skipped


def load_env_file(path: Path) -> None:
    """Read KEY=VALUE lines into os.environ without printing values; existing variables win."""
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name, value = name.strip(), value.strip().strip('"').strip("'")
        if name and value and not os.environ.get(name):
            os.environ[name] = value


def done_keys(out_file: Path) -> set[tuple[str, int]]:
    if not out_file.exists():
        return set()
    keys = set()
    for line in out_file.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if row.get("outcome") == "ocr_done":
                keys.add((row["document_id"], row["pdf_page"]))
    return keys


def utf8_ready() -> bool:
    """typhoon-ocr reads `pdfinfo -enc UTF-8` in text mode; on Windows the locale codepage fails
    on Thai PDF metadata and subprocess silently returns stdout=None. UTF-8 mode avoids that."""
    return sys.platform != "win32" or bool(sys.flags.utf8_mode)


def is_rate_limit(exc: Exception) -> bool:
    return getattr(exc, "status_code", None) == 429 or type(exc).__name__ == "RateLimitError"


def ocr_page(item: dict, api_key: str, model: str, task_type: str) -> str:
    from typhoon_ocr import ocr_document  # imported lazily so --dry-run works without the package

    return ocr_document(pdf_or_image_path=item["pdf_path"], page_num=item["pdf_page"], api_key=api_key,
                        model=model, task_type=task_type)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pages-root", type=Path, default=ROOT / "data/processed/normalized-v2")
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/raw")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "data/processed/ocr-typhoon-v1")
    parser.add_argument("--shard", type=int, required=True)
    parser.add_argument("--num-shards", type=int, required=True)
    parser.add_argument("--statuses", nargs="+", default=list(OCR_STATUSES), choices=OCR_STATUSES)
    parser.add_argument("--document-id", action="append", default=[], help="limit to these documents")
    parser.add_argument("--limit", type=int, default=None, help="maximum pages in this shard (e.g. a CER sample)")
    parser.add_argument("--api-key-env", default="TYPHOON_OCR_API_KEY")
    parser.add_argument("--env-file", type=Path, default=None, help="local KEY=VALUE file, e.g. .env (git-ignored)")
    parser.add_argument("--model", default="typhoon-ocr")
    parser.add_argument("--task-type", default="v1.5")
    parser.add_argument("--dry-run", action="store_true", help="list the shard without network calls")
    args = parser.parse_args(argv)
    if not 0 <= args.shard < args.num_shards:
        parser.error("--shard must be in 0..num_shards-1")

    pages, skipped = select_pages(args.pages_root, args.raw_dir, tuple(args.statuses))
    if args.document_id:
        pages = [p for p in pages if p["document_id"] in set(args.document_id)]
    shard = [p for i, p in enumerate(pages) if i % args.num_shards == args.shard]
    if args.limit is not None:
        shard = shard[:args.limit]
    out_file = args.out_dir / f"shard-{args.shard}-of-{args.num_shards}.jsonl"
    done = done_keys(out_file)
    todo = [p for p in shard if (p["document_id"], p["pdf_page"]) not in done]
    plan = {"selected_pages_all_shards": len(pages), "skipped_blank_pages": len(skipped),
            "shard_pages": len(shard), "already_done": len(shard) - len(todo), "to_run": len(todo),
            "estimated_minutes": round(len(todo) / MAX_PER_MINUTE, 1), "out_file": str(out_file)}
    if args.dry_run:
        print(json.dumps({"dry_run": True, **plan,
                          "pages": [f"{p['document_id']}:p{p['pdf_page']}" for p in todo]}, indent=2))
        return 0

    if not utf8_ready():
        parser.error("on Windows run with UTF-8 mode: python -X utf8 scripts/ocr_typhoon.py ...")
    if args.env_file:
        load_env_file(args.env_file)
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        parser.error(f"set {args.api_key_env} in your shell or in the --env-file")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    meta = {"model": args.model, "task_type": args.task_type, "typhoon_ocr_version": version("typhoon-ocr"),
            "shard": args.shard, "num_shards": args.num_shards,
            "key_fingerprint": hashlib.sha256(api_key.encode()).hexdigest()[:8]}
    counts = {"ocr_done": 0, "failed": 0}
    last_call = 0.0
    for number, item in enumerate(todo, start=1):
        row = {k: item[k] for k in ("document_id", "pdf_page", "normalized_status", "source_sha256")}
        for attempt in range(MAX_RETRIES + 1):
            wait = MIN_INTERVAL_S - (time.monotonic() - last_call)
            if wait > 0:
                time.sleep(wait)
            last_call = time.monotonic()
            started = time.monotonic()
            try:
                text = ocr_page(item, api_key, args.model, args.task_type)
                row.update(outcome="ocr_done", ocr_markdown=text, status="ocr_unreviewed",
                           latency_s=round(time.monotonic() - started, 2), attempts=attempt + 1)
                break
            except Exception as exc:  # network/API errors are recorded, never re-raised mid-run
                if is_rate_limit(exc) and attempt < MAX_RETRIES:
                    time.sleep(min(60, 5 * 2 ** attempt))
                    continue
                row.update(outcome="failed", error=f"{type(exc).__name__}: {str(exc)[:300]}", attempts=attempt + 1)
                break
        row.update(meta, created_at=datetime.now(timezone.utc).isoformat())
        with out_file.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        counts[row["outcome"]] += 1
        print(json.dumps({"n": number, "of": len(todo), "page": f"{item['document_id']}:p{item['pdf_page']}",
                          "outcome": row["outcome"]}), flush=True)
    print(json.dumps({**plan, **counts, "paid_api_calls": counts["ocr_done"] + counts["failed"]}, indent=2))
    return 0 if counts["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
