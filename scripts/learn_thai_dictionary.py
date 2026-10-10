"""Learn extra Thai words for newmm from the corpus itself (Track B): runs of short fragments that keep recurring together.

The default PyThaiNLP dictionary does not know much medical vocabulary, so newmm cuts such words into short fragments
("เมตฟอร์มิน" -> "เม", "ตฟอร์", "มิ", "น"). A word the dictionary lacks therefore shows up as the same run of short tokens
in many chunks. A run is kept as a word when
  * it has at least two tokens, every token has at most `--max-fragment` Thai characters, and the joined string has 4..24 characters;
  * it appears in at least `--min-df` chunks and in at least `--min-docs` documents;
  * at least one of its fragments is NOT a word of the default dictionary and `--min-cover` of that fragment's occurrences in the
    corpus lie inside this run (count(run) / count(fragment)). A word the dictionary lacks leaves such a fragment ("ตฟอร์"),
    whereas correct compounds ("ตัวชี้วัด") are made of dictionary words and are excluded. (Phrase scoring against the parts as in
    Mikolov et al. 2013 was tried first and kept correct compounds and function-word pairs, so it was dropped.)
  * the joined string is not already a word in the default dictionary.
The thresholds are our own choices (no paper fixes them for Thai); their effect is measured by the sweep, not assumed.

Usage:
    python -X utf8 scripts/learn_thai_dictionary.py --chunks data/index/chunks-v11-t512 --min-df 5 --out configs/retrieval/thai_dict_corpus_v11_df5.txt
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from pythainlp.corpus import thai_words
from pythainlp.tokenize import word_tokenize

THAI = re.compile(r"[฀-๿]+")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--chunks", type=Path, required=True)
    ap.add_argument("--min-df", type=int, default=5)
    ap.add_argument("--min-docs", type=int, default=2)
    ap.add_argument("--min-cover", type=float, default=0.7)
    ap.add_argument("--max-fragment", type=int, default=4)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    rows = [json.loads(x) for x in (args.chunks / "chunks.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()]
    known = set(thai_words())
    token_count: Counter = Counter()
    run_chunks: dict[str, set] = defaultdict(set)
    run_docs: dict[str, set] = defaultdict(set)
    run_parts: dict[str, tuple] = {}
    run_count: Counter = Counter()
    total = 0
    for row in rows:
        for segment in THAI.findall(row["text"]):
            tokens = word_tokenize(segment, engine="newmm", keep_whitespace=False)
            total += len(tokens)
            token_count.update(tokens)
            i = 0
            while i < len(tokens):
                j = i
                while j < len(tokens) and len(tokens[j]) <= args.max_fragment:
                    j += 1
                for a in range(i, j):  # every sub-run of 2..5 fragments inside the maximal run
                    for b in range(a + 2, min(j, a + 5) + 1):
                        joined = "".join(tokens[a:b])
                        if 4 <= len(joined) <= 24:
                            run_chunks[joined].add(row["chunk_id"])
                            run_docs[joined].add(row["document_id"])
                            run_parts.setdefault(joined, tuple(tokens[a:b]))
                            run_count[joined] += 1
                i = max(j, i + 1)

    kept = []
    for joined, chunks in run_chunks.items():
        parts = run_parts[joined]
        if joined in known or len(chunks) < args.min_df or len(run_docs[joined]) < args.min_docs:
            continue
        cover = max((run_count[joined] / token_count[p] for p in parts if p not in known), default=0.0)
        if cover >= args.min_cover:
            kept.append((joined, len(chunks), len(run_docs[joined]), round(cover, 2), "|".join(parts)))
    # a longer kept word replaces its own sub-words: keep a word only if no kept longer word contains it with the same support
    kept.sort(key=lambda r: (-len(r[0]), -r[1]))
    final: list[tuple] = []
    for r in kept:
        if not any(r[0] in f[0] and f[1] >= 0.8 * r[1] for f in final):
            final.append(r)
    final.sort(key=lambda r: -r[1])
    header = [f"# Learned Thai words for newmm. corpus={args.chunks.name} date={date.today().isoformat()} min_df={args.min_df} "
              f"min_docs={args.min_docs} min_cover={args.min_cover} max_fragment={args.max_fragment}",
              "# columns: word<TAB>chunk_df<TAB>doc_df<TAB>cover<TAB>fragments newmm produced. Method: scripts/learn_thai_dictionary.py"]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(header + [f"{w}\t{c}\t{d}\t{l}\t{p}" for w, c, d, l, p in final]) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"candidates": len(run_chunks), "kept_words": len(final), "out": str(args.out)}, ensure_ascii=False))
    for w, c, d, v, p in final[:60]:
        print(w, c, d, v, p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
