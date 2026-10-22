"""Build chunks.jsonl from a normalized corpus version (Track B, L1).

Usage:
    python -X utf8 scripts/build_chunks.py --corpus data/processed/normalized-v11 --max-tokens 256 \
        --tokenizer intfloat/multilingual-e5-base --passage-prefix "passage: " --out data/index/chunks-v11-t256
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ncdqa.retrieval.chunking import ChunkConfig, build_document_chunks  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--tokenizer", required=True, help="HF model id whose tokenizer counts tokens")
    ap.add_argument("--max-tokens", type=int, required=True)
    ap.add_argument("--passage-prefix", default="")
    ap.add_argument("--no-header", action="store_true")
    ap.add_argument("--no-merge-pages", action="store_true")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.out.exists():
        sys.exit(f"{args.out} exists: chunk sets are immutable, choose a new --out")

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(args.tokenizer)
    limit = getattr(tok, "model_max_length", None)
    count = lambda text: len(tok(text, add_special_tokens=True, truncation=False)["input_ids"])  # noqa: E731
    cfg = ChunkConfig(name=Path(args.out).name, max_tokens=args.max_tokens, contextual_header=not args.no_header,
                      passage_prefix=args.passage_prefix, merge_pages=not args.no_merge_pages)

    manifest = {json.loads(x)["document_id"]: json.loads(x) for x in
                (ROOT / "data/manifests/documents.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()}
    groups = {r["document_id"]: r["primary_group"] for r in
              json.loads((ROOT / "data/by_disease/index.json").read_text(encoding="utf-8"))["records"]}
    chunks, per_doc = [], {}
    for folder in sorted(p for p in args.corpus.iterdir() if (p / "pages.jsonl").exists()):
        meta = {**manifest[folder.name], "primary_group": groups[folder.name]}
        if meta["primary_group"] == "EXCLUDED":
            continue
        rows = [json.loads(x) for x in (folder / "pages.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()]
        made = build_document_chunks(meta, rows, cfg, count, args.tokenizer, args.corpus.name)
        per_doc[folder.name] = len(made)
        chunks += made

    args.out.mkdir(parents=True)
    body = "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in chunks)
    (args.out / "chunks.jsonl").write_text(body, encoding="utf-8", newline="\n")
    tokens = sorted(c["token_count"] for c in chunks)
    stats = {"corpus_version": args.corpus.name, "chunk_config_id": cfg.config_id, "tokenizer": args.tokenizer,
             "tokenizer_model_max_length": limit, "max_tokens": cfg.max_tokens, "chunks": len(chunks),
             "documents_with_chunks": sum(1 for v in per_doc.values() if v),
             "token_count": {"min": tokens[0], "median": tokens[len(tokens) // 2], "p95": tokens[int(len(tokens) * .95)],
                             "max": tokens[-1]},
             "over_limit": sum(t > cfg.max_tokens for t in tokens),
             "chunk_types": dict(Counter(c["chunk_type"] for c in chunks)),
             "populations": dict(Counter(c["population"] for c in chunks)),
             "injection_flagged": sum(bool(c["injection_flags"]) for c in chunks),
             "chunks_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()}
    (args.out / "chunk_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
