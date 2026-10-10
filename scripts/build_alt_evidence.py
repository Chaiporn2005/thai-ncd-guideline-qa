"""Find duplicate pages of each question's evidence and write them as `alt_evidence` (kind=duplicate).

Guidelines repeat tables, headers and whole passages: the evidence quote of a question is sometimes found verbatim on
other pages (a repeated table, a copy in another edition or document). A retriever that returns such a page is scored a
miss under the one-page gold rule. This script lists those pages deterministically: a page is a duplicate when it contains
the evidence quote (whitespace removed), every strong number of the gold answer, and the page as a whole is near-identical
to the gold page (5-character shingle Jaccard of at least `--min-page-similarity`). The page test matters: a generic table
row such as "เกณฑ์เป้าหมาย มากกว่าหรือเท่ากับร้อยละ 90" is repeated under many different indicators, and one survey table with
the same numbers is printed once per training topic. Those carry the quote but are not the same fact (tried: matching only
the text around the quote did not separate them; matching the whole page does: q001's copy in the sibling indicator
document scores 0.83, the look-alike tables 0.55-0.68). Nothing here judges meaning beyond that; a page that merely
restates the fact in other words is left to a person (`find_alt_evidence.py` proposes those).

Only one-evidence answerable questions get alternates (a multi_page question needs all its pages).

Usage:
    python -X utf8 scripts/build_alt_evidence.py --corpus data/processed/normalized-v11 \
        --questions data/agent_runs/20261010-silver-questions/questions_silver.jsonl \
                    data/agent_runs/20261011-supplement-questions/questions_supplement.jsonl \
        --out data/questions/alt_evidence_duplicates.jsonl
    # then, to bake them into a question file:   add --merge-into <questions.jsonl> --merged-out <new.jsonl>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ncdqa.retrieval import answer_match  # noqa: E402


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").split("\n") if x.strip()]


def collapse(text: str) -> str:
    return re.sub(r"[\s​]+", "", text)


def shingles(text: str) -> set[str]:
    return {text[k:k + 5] for k in range(max(0, len(text) - 4))}


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--questions", type=Path, nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--min-page-similarity", type=float, default=0.7, help="shingle Jaccard of the whole page, gold page vs duplicate")
    ap.add_argument("--merge-into", type=Path, help="question file to copy with alt_evidence filled in")
    ap.add_argument("--merged-out", type=Path)
    args = ap.parse_args(argv)

    editions = {json.loads(x)["document_id"]: json.loads(x)["edition_id"] for x in
                (ROOT / "data/manifests/documents.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()}
    pages: dict[tuple[str, int], tuple[str, str]] = {}

    for folder in sorted(p for p in args.corpus.iterdir() if (p / "pages.jsonl").exists()):
        for line in (folder / "pages.jsonl").read_text(encoding="utf-8").split("\n"):
            if line.strip():
                row = json.loads(line)
                if row.get("status") in ("ok", "ok_minor_issues", "ocr_unreviewed", "degraded") and not row.get("index_exclusion"):
                    pages[(folder.name, row["pdf_page"])] = (collapse(row["text"]), answer_match.normalize(row["text"]))

    found: dict[str, list[dict]] = {}
    seen_questions = 0
    for path in args.questions:
        for q in read_jsonl(path):
            if q.get("status") == "rejected" or not q["answerable"] or len(q["evidence"]) != 1:
                continue
            seen_questions += 1
            ev = q["evidence"][0]
            quote = collapse(ev["quote"])
            strong = answer_match.anchors(q["answer"])
            alts = []
            gold_text = pages[(ev["document_id"], ev["pdf_page"])][0]
            if quote not in gold_text:
                continue
            gold_shingles = shingles(gold_text)
            for (doc, page), (text, norm_text) in pages.items():
                if (doc, page) == (ev["document_id"], ev["pdf_page"]) or quote not in text:
                    continue
                if strong and not all(answer_match._has_anchor(norm_text, a) for a in strong):
                    continue
                if jaccard(gold_shingles, shingles(text)) < args.min_page_similarity:
                    continue
                alts.append({"document_id": doc, "edition_id": editions[doc], "pdf_page": page, "quote": ev["quote"],
                             "kind": "duplicate"})
            if alts:
                found[q["qid"]] = alts

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps({"qid": k, "alt_evidence": v}, ensure_ascii=False) + "\n" for k, v in sorted(found.items())),
                        encoding="utf-8", newline="\n")
    print(f"{len(found)} of {seen_questions} one-evidence questions have duplicate pages -> {args.out}")
    if args.merge_into:
        merged = []
        for q in read_jsonl(args.merge_into):
            if q["qid"] in found:
                q["alt_evidence"] = found[q["qid"]]
            merged.append(q)
        args.merged_out.write_text("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in merged), encoding="utf-8", newline="\n")
        print(f"merged -> {args.merged_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
