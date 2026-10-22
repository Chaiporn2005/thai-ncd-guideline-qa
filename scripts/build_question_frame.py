"""Draw the page sample from which silver questions are written (Track B dev/test set, step 1).

Pages are drawn from the searchable pages of a corpus version, stratified so the questions cover every disease group
and document type and over-represent the page populations (pediatric/pregnancy/elderly) that the population-tag
experiment needs. Documents under the Siriraj rights conflict are left out unless `--include-rights-conflict` is
given, because their text would be sent to an external model. The draw is seeded and recorded; nothing here writes
questions.

Usage:
    python -X utf8 scripts/build_question_frame.py --corpus data/processed/normalized-v11 --pages 120 \
        --out data/agent_runs/20261010-silver-questions/frame.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ncdqa.retrieval.chunking import is_searchable  # noqa: E402

MIN_LETTERS = 350          # pages with less text rarely hold an answerable fact
MAX_PER_DOC = 4
MAX_PER_DOC_POPULATION = 8  # population pages sit in few documents, so they may exceed the general cap
POPULATION_QUOTA = {"pediatric": 10, "pregnancy": 6, "elderly": 6}


def letters(text: str) -> int:
    return len(re.findall(r"[ก-๙A-Za-z0-9]", text))


def doc_hash_split(document_id: str) -> str:
    """Whole documents go to one split so a test question never shares a source page neighbourhood with dev."""
    return "test" if int(hashlib.sha256(document_id.encode()).hexdigest(), 16) % 3 == 0 else "dev"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--pages", type=int, default=120)
    ap.add_argument("--seed", type=int, default=20261010)
    ap.add_argument("--include-rights-conflict", action="store_true")
    ap.add_argument("--only-rights-conflict", action="store_true", help="draw only from the Siriraj-conflict documents (supplementary frame)")
    ap.add_argument("--prefix", default="f", help="frame id prefix")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    docs = {json.loads(x)["document_id"]: json.loads(x) for x in
            (ROOT / "data/manifests/documents.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()}
    groups = {r["document_id"]: r["primary_group"] for r in
              json.loads((ROOT / "data/by_disease/index.json").read_text(encoding="utf-8"))["records"]}
    rights = {r["document_id"]: r for r in
              json.loads((ROOT / "data/manifests/rights_review_20261005.json").read_text(encoding="utf-8"))["records"]}
    conflict = {k for k, v in rights.items() if "rights_conflict" in json.dumps(v)}

    pool: list[dict] = []
    left_out: Counter = Counter()
    for folder in sorted(p for p in args.corpus.iterdir() if (p / "pages.jsonl").exists()):
        doc = folder.name
        if groups.get(doc) == "EXCLUDED":
            continue
        if args.only_rights_conflict and doc not in conflict:
            continue
        if doc in conflict and not (args.include_rights_conflict or args.only_rights_conflict):
            left_out["rights_conflict"] += 1
            continue
        for line in (folder / "pages.jsonl").read_text(encoding="utf-8").split("\n"):
            if not line.strip():
                continue
            row = json.loads(line)
            if is_searchable(row) and letters(row["text"]) >= MIN_LETTERS:
                pool.append({"document_id": doc, "pdf_page": row["pdf_page"], "group": groups[doc],
                             "document_type": docs[doc]["document_type"], "population": row.get("population", "general"),
                             "letters": letters(row["text"]), "split": doc_hash_split(doc)})

    rng = random.Random(args.seed)
    rng.shuffle(pool)
    chosen: list[dict] = []
    per_doc: Counter = Counter()

    def take(candidates, n, cap=MAX_PER_DOC):
        for page in candidates:
            if n <= 0:
                break
            key = (page["document_id"], page["pdf_page"])
            if per_doc[page["document_id"]] < cap and key not in {(c["document_id"], c["pdf_page"]) for c in chosen}:
                chosen.append(page)
                per_doc[page["document_id"]] += 1
                n -= 1

    for population, quota in POPULATION_QUOTA.items():
        take([p for p in pool if p["population"] == population], quota, MAX_PER_DOC_POPULATION)
    # then round-robin over (group, document_type) strata until the page budget is met
    strata: dict[tuple, list[dict]] = defaultdict(list)
    for page in pool:
        strata[(page["group"], page["document_type"])].append(page)
    while len(chosen) < args.pages and any(strata.values()):
        for key in sorted(strata):
            if len(chosen) >= args.pages:
                break
            while strata[key]:
                page = strata[key].pop()
                if per_doc[page["document_id"]] < MAX_PER_DOC and (page["document_id"], page["pdf_page"]) not in {
                        (c["document_id"], c["pdf_page"]) for c in chosen}:
                    chosen.append(page)
                    per_doc[page["document_id"]] += 1
                    break
    chosen.sort(key=lambda p: (p["document_id"], p["pdf_page"]))
    for i, page in enumerate(chosen, 1):
        page["key"] = f"{page['document_id']}:p{page['pdf_page']}"
        page["frame_id"] = f"{args.prefix}{i:03d}"

    summary = {"corpus_version": args.corpus.name, "seed": args.seed, "pool_pages": len(pool), "pages": len(chosen),
               "left_out_documents": dict(left_out), "documents": len({p["document_id"] for p in chosen}),
               "by_group": dict(Counter(p["group"] for p in chosen)),
               "by_document_type": dict(Counter(p["document_type"] for p in chosen)),
               "by_population": dict(Counter(p["population"] for p in chosen)),
               "by_split": dict(Counter(p["split"] for p in chosen)),
               "pool_by_population": dict(Counter(p["population"] for p in pool)),
               "letters_total": sum(p["letters"] for p in chosen)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"summary": summary, "pages": chosen}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
