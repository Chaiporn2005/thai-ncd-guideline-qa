"""Draw the supplementary test frame: pages from documents that the first silver run left thin in the test split.

The first run (141 questions) put 1 hypertension question in test, used 12 of 52 documents, and let some test questions
share a page. This frame adds pages only from (a) documents already in test and (b) documents that have no question yet,
so dev/test stay split by document. Documents under the Siriraj rights conflict are left out (their text would go to
an external model). Pages already used by a question, and their neighbours, are skipped; chosen pages are never adjacent
to each other. Pages are dealt alternately to two drafting agents; each gets some multi_page and unanswerable assignments.

Usage:
    python -X utf8 scripts/build_supplement_frame.py --corpus data/processed/normalized-v11 \
        --questions data/agent_runs/20261010-silver-questions/questions_silver.jsonl \
        --out-dir data/agent_runs/20261011-supplement-questions
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ncdqa.retrieval.chunking import is_searchable  # noqa: E402

# group -> (quota, documents). Documents already in test, or with no question yet.
PLAN = {
    "HT": (10, ["ht-ddc-hospital-management-update-2566", "ht-ddc-provincial-sodium-guide-undated", "ht-ths-public-leaflet-2567"]),
    "CKD": (10, ["ckd-anemia-guideline-2564", "ckd-palliative-2566", "ckd-treatment-leaflet-undated"]),
    "DM": (4, ["dm-educator-standards-2567", "dm-remission-service-2567"]),
    "NCD": (4, ["DDC-NCD-CLINIC-PLUS-ONLINE-USER-MANUAL-2566"]),
}
MIN_LETTERS = 350
MAX_PER_DOC = 5


def letters(text: str) -> int:
    return len(re.findall(r"[ก-๙A-Za-z0-9]", text))


def load_pages(folder: Path) -> dict[int, dict]:
    rows = {}
    for line in (folder / "pages.jsonl").read_text(encoding="utf-8").split("\n"):
        if line.strip():
            row = json.loads(line)
            rows[row["pdf_page"]] = row
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--questions", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=20261011)
    args = ap.parse_args(argv)

    questions = [json.loads(x) for x in args.questions.read_text(encoding="utf-8").split("\n") if x.strip()]
    used = {(e["document_id"], e["pdf_page"]) for q in questions for e in q["evidence"]}
    dev_docs = {q["evidence"][0]["document_id"] for q in questions if q["split"] == "dev"}
    rights = json.loads((ROOT / "data/manifests/rights_review_20261005.json").read_text(encoding="utf-8"))["records"]
    conflict = {r["document_id"] for r in rights if "rights_conflict" in json.dumps(r)}

    rng = random.Random(args.seed)
    chosen: list[dict] = []
    for group, (quota, docs) in PLAN.items():
        pool = []
        for doc in docs:
            assert doc not in dev_docs and doc not in conflict, doc
            rows = load_pages(args.corpus / doc)
            for page, row in rows.items():
                near_used = any((doc, page + d) in used for d in (-1, 0, 1))
                if is_searchable(row) and letters(row["text"]) >= MIN_LETTERS and not near_used:
                    pool.append((doc, page))
        rng.shuffle(pool)
        taken: list[tuple[str, int]] = []
        per_doc: Counter = Counter()
        for doc, page in pool:
            if len(taken) >= quota:
                break
            if per_doc[doc] >= MAX_PER_DOC or any(d == doc and abs(p - page) <= 1 for d, p in taken):
                continue
            taken.append((doc, page))
            per_doc[doc] += 1
        for doc, page in taken:
            chosen.append({"document_id": doc, "pdf_page": page, "group": group})

    chosen.sort(key=lambda p: (p["document_id"], p["pdf_page"]))
    cache: dict[str, dict[int, dict]] = {}
    for i, page in enumerate(chosen, 1):
        page["frame_id"] = f"x{i:03d}"
        page["agent"] = "astra" if i % 2 else "gemini"
        rows = cache.setdefault(page["document_id"], load_pages(args.corpus / page["document_id"]))
        nxt = rows.get(page["pdf_page"] + 1)
        page["next_ok"] = bool(nxt and is_searchable(nxt) and letters(nxt["text"]) >= 200)
        page["letters"] = letters(rows[page["pdf_page"]]["text"])

    # assignments: per agent 2 multi_page (next page searchable) and 3 unanswerable (distinct documents, HT/CKD first)
    for agent in ("astra", "gemini"):
        mine = [p for p in chosen if p["agent"] == agent]
        mp = [p for p in mine if p["next_ok"]]
        rng.shuffle(mp)
        for p in mp[:2]:
            p["extra"] = "multi_page"
        un_docs: set[str] = set()
        for p in sorted((p for p in mine if "extra" not in p), key=lambda p: ({"HT": 0, "CKD": 1}.get(p["group"], 2), rng.random())):
            if sum(q.get("extra") == "unanswerable" for q in mine) >= 3:
                break
            if p["document_id"] not in un_docs:
                p["extra"] = "unanswerable"
                un_docs.add(p["document_id"])

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "frame.json").write_text(json.dumps({"pages": chosen}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for agent in ("astra", "gemini"):
        with (args.out_dir / f"input_{agent}.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
            for p in (p for p in chosen if p["agent"] == agent):
                rows = cache[p["document_id"]]
                row = {k: p[k] for k in ("frame_id", "document_id", "pdf_page", "group", "extra") if k in p}
                row["text"] = rows[p["pdf_page"]]["text"]
                row["next_page_text"] = rows[p["pdf_page"] + 1]["text"] if p.get("extra") == "multi_page" else None
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"pages": len(chosen), "by_group": Counter(p["group"] for p in chosen),
                      "by_doc": Counter(p["document_id"] for p in chosen),
                      "by_agent_extra": Counter((p["agent"], p.get("extra", "-")) for p in chosen).most_common()},
                     ensure_ascii=False, default=dict, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
