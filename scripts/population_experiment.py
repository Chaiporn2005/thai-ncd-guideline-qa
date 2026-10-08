"""Does tagging pages by population (adult / child / pregnancy / elderly) improve retrieval? A small, repeatable comparison.

Two steps:
  sample    pick pages for an agent to write silver questions from: general pages that are textually close to
            population-specific pages (where a wrong-population hit is most likely), and population-specific pages.
            Writes questions_input.json (page text included; the pages are redacted corpus text).
  evaluate  read the silver questions (JSONL) and compare retrieval strategies with and without the tags.

Retrieval here is page-level BM25 over Thai word tokens (PyThaiNLP newmm): a stand-in for the lexical half of the real
pipeline. It says nothing about dense retrieval or the reranker. Questions are silver (agent-written, not yet human
checked) and few, so every number comes with a bootstrap interval and should be read as direction, not proof.

Usage:
    python -X utf8 scripts/population_experiment.py sample --corpus data/processed/normalized-v8 --out <dir>
    python -X utf8 scripts/population_experiment.py evaluate --corpus data/processed/normalized-v8 --questions <silver.jsonl> --out <dir>
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import page_context as pc  # noqa: E402

SPECIAL = {"pediatric", "pregnancy", "elderly"}
SEED = 20261008
K1, B = 1.5, 0.75
STRATA = {"adult_near_special": 24, "pediatric": 6, "pregnancy": 5, "elderly": 5, "mixed": 4}

# Asker detection from the question text only, as the real system would have to do it. Plain words are used here
# (unlike page scoring) because a question that says "เด็ก" or "ตั้งครรภ์" is asking about that population.
ASKER_PATTERNS = {
    "pediatric": re.compile(r"เด็ก|วัยรุ่น|ทารก|ลูก(?:สาว|ชาย)?อายุ|อายุ\s*\d+\s*(?:ขวบ|เดือน)|ลูกของ|บุตร|นักเรียน|pediatric|children", re.I),
    "pregnancy": re.compile(r"ตั้งครรภ์|มีครรภ์|ครรภ์|คลอด|ให้นมบุตร|GDM|gestational|pregnan", re.I),
    "elderly": re.compile(r"ผู้สูงอายุ|สูงวัย|คุณ(?:ตา|ยาย|ปู่|ย่า)|อายุ\s*(?:6\d|7\d|8\d|9\d)\s*ปี|geriatric|elderly", re.I),
}


def load_pages(corpus: Path) -> list[dict]:
    rows = []
    for f in sorted(corpus.glob("*/pages.jsonl")):
        for line in f.read_text(encoding="utf-8").split("\n"):
            if not line.strip():
                continue
            r = json.loads(line)
            review = r.get("human_review") or {}
            ok = r["status"] in ("ok", "ok_minor_issues") or (
                r["status"] in ("ocr_unreviewed", "degraded") and review.get("outcome") in ("pass", "fix"))
            if ok and not r.get("index_exclusion") and (r.get("text") or "").strip():
                r["key"] = f"{r['document_id']}:p{r['pdf_page']}"
                r.setdefault("population", "general")
                rows.append(r)
    return rows


def tokenize(text: str) -> list[str]:
    from pythainlp.tokenize import word_tokenize
    return [w.lower() for w in word_tokenize(text, engine="newmm", keep_whitespace=False)
            if len(w.strip()) > 1 and not re.fullmatch(r"[\W_]+", w)]


class BM25:
    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.docs = [tokenize(r["text"]) for r in rows]
        self.tf = [Counter(d) for d in self.docs]
        self.n = len(rows)
        self.avgdl = sum(map(len, self.docs)) / self.n
        self.df = Counter(w for d in self.docs for w in set(d))
        self.index = {r["key"]: i for i, r in enumerate(rows)}

    def scores(self, query: str) -> list[float]:
        terms = tokenize(query)
        out = []
        for i, tf in enumerate(self.tf):
            dl, s = len(self.docs[i]), 0.0
            for w in terms:
                f = tf.get(w)
                if f:
                    idf = math.log(1 + (self.n - self.df[w] + 0.5) / (self.df[w] + 0.5))
                    s += idf * f * (K1 + 1) / (f + K1 * (1 - B + B * dl / self.avgdl))
            out.append(s)
        return out


def spread(items: list, n: int) -> list:
    if len(items) <= n:
        return items
    return [items[round(i * (len(items) - 1) / (n - 1))] for i in range(n)]


def sample(corpus: Path, out: Path) -> int:
    rows = load_pages(corpus)
    bm25 = BM25(rows)
    rng = random.Random(SEED)
    special = [r for r in rows if r["population"] in SPECIAL]
    near: dict[str, int] = {}
    for r in special:
        scores = bm25.scores(" ".join(r["text"].split())[:250])
        for i in sorted(range(len(rows)), key=lambda j: -scores[j]):
            if rows[i]["population"] == "general" and rows[i]["document_id"] != "" and len(rows[i]["text"]) > 300:
                near[rows[i]["key"]] = near.get(rows[i]["key"], 0) + 1
                break
    adult_pool = sorted(near, key=lambda k: (-near[k], k))
    chosen = {"adult_near_special": spread(sorted(adult_pool[:80]), STRATA["adult_near_special"])}
    for label in ("pediatric", "pregnancy", "elderly", "mixed"):
        pool = sorted(r["key"] for r in rows if r["population"] == label and len(r["text"]) > 300)
        chosen[label] = spread(pool, STRATA[label])
    by_key = {r["key"]: r for r in rows}
    items = []
    for stratum, keys in chosen.items():
        for k in keys:
            r = by_key[k]
            items.append({"id": f"q{len(items) + 1:02d}", "key": k, "stratum": stratum, "page_population": r["population"],
                          "text": r["text"][:3500]})
    rng.shuffle(items)
    for n, item in enumerate(items, 1):
        item["id"] = f"q{n:02d}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "questions_input.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"pages": len(items), "strata": dict(Counter(i["stratum"] for i in items))}, ensure_ascii=False))
    return 0


def detect_asker(question: str) -> str | None:
    hits = [label for label, pattern in ASKER_PATTERNS.items() if pattern.search(question)]
    return hits[0] if len(hits) == 1 else None


def rank(bm25: BM25, question: str, mode: str, asker: str | None, penalty: float = 0.7, boost: float = 1.3, k: int = 10):
    """Top-k page keys for one strategy. asker is the population the strategy believes the question is about."""
    scores = bm25.scores(question)
    labels = [r["population"] for r in bm25.rows]
    if mode == "none":
        pass
    elif mode == "hard":      # asker named: only that population's pages (and mixed); otherwise adult pages only
        for i, lab in enumerate(labels):
            allowed = (lab in (asker, "mixed")) if asker else (lab not in SPECIAL)
            if not allowed:
                scores[i] = -1.0
    elif mode == "exclude_other":  # never hides general pages: drops the population pages that do not match the asker
        for i, lab in enumerate(labels):
            if lab in SPECIAL and lab != asker:
                scores[i] = -1.0
    elif mode == "soft":
        for i, lab in enumerate(labels):
            if asker and lab == asker:
                scores[i] *= boost
            elif lab in SPECIAL and lab != asker:
                scores[i] *= penalty
    order = sorted(range(len(scores)), key=lambda j: -scores[j])[:k]
    return [bm25.rows[i]["key"] for i in order if scores[i] > 0]


def metrics(ranked: list[str], relevant: set[str], lenient: set[str]) -> dict:
    def first(rel):
        for pos, key in enumerate(ranked, 1):
            if key in rel:
                return pos
        return None
    s, l = first(relevant), first(lenient)
    return {"r5": int(s is not None and s <= 5), "r10": int(s is not None and s <= 10), "mrr": (1 / s) if s else 0.0,
            "lr5": int(l is not None and l <= 5), "lr10": int(l is not None and l <= 10)}


def bootstrap_delta(a: list[float], b: list[float], rng: random.Random, n: int = 2000) -> tuple[float, float, float]:
    diffs = [y - x for x, y in zip(a, b)]
    mean = sum(diffs) / len(diffs)
    boots = sorted(sum(rng.choice(diffs) for _ in diffs) / len(diffs) for _ in range(n))
    return mean, boots[int(0.025 * n)], boots[int(0.975 * n)]


def evaluate(corpus: Path, questions: Path, out: Path) -> int:
    rows = load_pages(corpus)
    bm25 = BM25(rows)
    qs = [json.loads(x) for x in questions.read_text(encoding="utf-8").split("\n") if x.strip()]
    by_key = {r["key"]: r for r in rows}
    neighbours = {}
    for r in rows:
        neighbours[r["key"]] = {f"{r['document_id']}:p{r['pdf_page'] + d}" for d in (-1, 0, 1)} & set(by_key) | {r["key"]}
    strategies = {
        "S0 no tags": ("none", False, {}),
        "S1 hard filter (detected asker)": ("hard", False, {}),
        "S1o hard filter (true asker)": ("hard", True, {}),
        "S2 drop other populations (detected)": ("exclude_other", False, {}),
        "S2o drop other populations (true asker)": ("exclude_other", True, {}),
        "S3a soft x0.8 / boost x1.2 (detected)": ("soft", False, {"penalty": 0.8, "boost": 1.2}),
        "S3b soft x0.5 / boost x1.5 (detected)": ("soft", False, {"penalty": 0.5, "boost": 1.5}),
        "S3ao soft x0.8 / boost x1.2 (true asker)": ("soft", True, {"penalty": 0.8, "boost": 1.2}),
    }
    detected = [detect_asker(q["question"]) for q in qs]
    true_asker = [None if q["asker"] == "adult" else q["asker"] for q in qs]
    detect_hits = sum(d == t for d, t in zip(detected, true_asker))
    results: dict[str, list[dict]] = {}
    wrong5: dict[str, list[int]] = {}
    for name, (mode, oracle, params) in strategies.items():
        per, wrong = [], []
        for q, det, tru in zip(qs, detected, true_asker):
            ranked = rank(bm25, q["question"], mode, tru if oracle else det, **params)
            rel = set(q["relevant_keys"])
            per.append(metrics(ranked, rel, set().union(*(neighbours[k] for k in rel if k in neighbours))))
            wrong.append(sum(by_key[k]["population"] in SPECIAL for k in ranked[:5]) if q["asker"] == "adult" else 0)
        results[name], wrong5[name] = per, wrong
    rng = random.Random(SEED)
    base = results["S0 no tags"]
    groups = {"all": list(range(len(qs))), "adult questions": [i for i, q in enumerate(qs) if q["asker"] == "adult"],
              "population questions": [i for i, q in enumerate(qs) if q["asker"] != "adult"]}
    lines = [f"# Population tags: with vs without (BM25 page-level, {len(qs)} silver questions)", "",
             f"asker detected from the question text correctly: {detect_hits}/{len(qs)}",
             f"questions by asker: {dict(Counter(q['asker'] for q in qs))}", ""]
    report = {"questions": len(qs), "detect_correct": detect_hits, "groups": {}}
    for gname, idx in groups.items():
        lines += [f"## {gname} (n={len(idx)})", "", "| strategy | Recall@5 | Recall@10 | MRR@10 | lenient R@5 | Δ R@5 vs S0 [95% CI] | wrong-population pages in top 5 (adult questions) |",
                  "| --- | ---: | ---: | ---: | ---: | --- | ---: |"]
        report["groups"][gname] = {}
        for name, per in results.items():
            sub = [per[i] for i in idx]
            r5 = [m["r5"] for m in sub]
            mean, lo, hi = bootstrap_delta([base[i]["r5"] for i in idx], r5, rng)
            w = sum(wrong5[name][i] for i in idx)
            wn = 5 * sum(1 for i in idx if qs[i]["asker"] == "adult")
            row = {"recall5": sum(r5) / len(sub), "recall10": sum(m["r10"] for m in sub) / len(sub),
                   "mrr": sum(m["mrr"] for m in sub) / len(sub), "lenient_recall5": sum(m["lr5"] for m in sub) / len(sub),
                   "delta_recall5": mean, "ci": [lo, hi], "wrong_pop_top5": w, "wrong_pop_slots": wn}
            report["groups"][gname][name] = row
            lines.append(f"| {name} | {row['recall5']:.2f} | {row['recall10']:.2f} | {row['mrr']:.3f} | {row['lenient_recall5']:.2f} | "
                         f"{mean:+.2f} [{lo:+.2f}, {hi:+.2f}] | {w}/{wn if wn else '-'} |")
        lines.append("")
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(lines))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample")
    s.add_argument("--corpus", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    e = sub.add_parser("evaluate")
    e.add_argument("--corpus", type=Path, required=True)
    e.add_argument("--questions", type=Path, required=True)
    e.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    return sample(args.corpus, args.out) if args.cmd == "sample" else evaluate(args.corpus, args.questions, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
