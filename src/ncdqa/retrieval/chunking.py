"""Structural, table-aware chunking of normalized page text (Track B, L1).

Input is the per-document `pages.jsonl` of a normalized corpus version. Output rows follow
`data/schemas/rag/chunk.schema.json`. Rules:

* Only searchable pages are chunked (status ok/ok_minor_issues, or ocr_unreviewed/degraded with a human review of
  pass/fix, and no `index_exclusion`). A chunk never crosses a gap left by a page that is not searchable, nor a
  chapter heading.
* The unit is a line of page text. Lines are packed greedily up to the token budget; when the budget is hit the chunk
  is closed at the last paragraph boundary (blank line or heading) if that keeps at least half the budget.
* Table lines are kept together; when a table runs over several chunks the table's first line is repeated in
  `header_text` so every row group stays readable.
* A line longer than the budget is split at Thai sentence boundaries (PyThaiNLP), then by characters.
* `text` is verbatim: for one page it is `page_text[char_start:char_end]`; across pages the page slices are joined
  with "\n". Token counts use the embedding model's own tokenizer, including special tokens, and never exceed
  `max_tokens` (header and passage prefix included).
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import page_context  # noqa: E402

CountTokens = Callable[[str], int]

TABLE_LINE = re.compile(r"\t|\|| {3,}\S| \S+ +\d+(?:\.\d+)? +\d+(?:\.\d+)?")
LIST_LINE = re.compile(r"^\s*(?:[-•●▪*]|\d{1,2}[.)]|[ก-ฮ][.)])\s*\S")
INJECTION = [
    ("ignore_instructions", re.compile(r"ignore (?:all |any |the )?(?:previous|prior|above) (?:instructions|prompts?)", re.I)),
    ("ignore_instructions_th", re.compile(r"(?:ละเว้น|เพิกเฉย|ลืม)(?:คำสั่ง|ข้อความ)(?:ก่อนหน้า|ข้างต้น|ทั้งหมด)")),
    ("role_override", re.compile(r"(?:you are now|act as|system prompt|<\|im_start\|>)", re.I)),
]


@dataclass
class ChunkConfig:
    name: str
    max_tokens: int
    contextual_header: bool = True
    passage_prefix: str = ""
    min_fill_for_boundary: float = 0.5
    merge_pages: bool = True

    @property
    def config_id(self) -> str:
        return f"{self.name}-t{self.max_tokens}-h{int(self.contextual_header)}-m{int(self.merge_pages)}"


@dataclass
class Line:
    page: int
    start: int
    end: int
    text: str
    kind: str                  # prose | list | table
    boundary_before: bool      # blank line or heading directly before
    table_header: str | None = None
    section: tuple[str, ...] = ()
    new_section: bool = False


def is_searchable(row: dict) -> bool:
    review = row.get("human_review") or {}
    return not row.get("index_exclusion") and (row["status"] in ("ok", "ok_minor_issues") or (
        row["status"] in ("ocr_unreviewed", "degraded") and review.get("outcome") in ("pass", "fix")))


def injection_flags(text: str) -> list[str]:
    return [name for name, pattern in INJECTION if pattern.search(text)]


def _split_long(text: str, base: int, budget: int, count: CountTokens) -> list[tuple[int, int]]:
    """Spans (relative to the page) that cover `text`, each within `budget` tokens: sentences first, then characters."""
    spans: list[tuple[int, int]] = []
    pieces: list[str] = []
    try:
        from pythainlp.tokenize import sent_tokenize
        pieces = [p for p in sent_tokenize(text, engine="crfcut") if p]
    except Exception:  # pragma: no cover - PyThaiNLP missing or model not downloadable
        pieces = []
    pos = 0
    for piece in pieces:
        at = text.find(piece, pos)
        if at < 0:
            pieces = []
            break
        spans.append((at, at + len(piece)))
        pos = at + len(piece)
    if not pieces:
        spans = [(0, len(text))]
    result: list[tuple[int, int]] = []
    for a, b in spans:
        while count(text[a:b]) > budget:
            lo, hi = a + 1, b
            while lo < hi:  # longest prefix within budget
                mid = (lo + hi + 1) // 2
                lo, hi = (mid, hi) if count(text[a:mid]) <= budget else (lo, mid - 1)
            result.append((base + a, base + lo))
            a = lo
        result.append((base + a, base + b))
    return result


def page_lines(page: dict, budget: int, count: CountTokens) -> list[Line]:
    text, number = page["text"], page["pdf_page"]
    lines: list[Line] = []
    offset, boundary, table_header = 0, False, None
    for raw in text.split("\n"):
        start, end = offset, offset + len(raw)
        offset = end + 1
        if not raw.strip():
            boundary, table_header = True, None
            continue
        kind = "table" if TABLE_LINE.search(raw) else "list" if LIST_LINE.match(raw) else "prose"
        if kind == "table":
            table_header = table_header or raw.strip()
        else:
            table_header = None
        header = table_header if kind == "table" and table_header != raw.strip() else None
        if count(raw) > budget:
            for a, b in _split_long(raw, start, budget, count):
                lines.append(Line(number, a, b, text[a:b], kind, boundary, header))
                boundary = False
        else:
            lines.append(Line(number, start, end, raw, kind, boundary, header))
            boundary = False
    return lines


def _chunk_type(lines: list[Line]) -> str:
    kinds = {ln.kind for ln in lines}
    if kinds == {"table"}:
        return "table_rows"
    if kinds == {"list"}:
        return "list"
    if kinds == {"prose"}:
        return "prose"
    return "mixed"


def _text_of(lines: list[Line], pages: dict[int, str]) -> str:
    out, order = [], []
    for ln in lines:
        if ln.page not in order:
            order.append(ln.page)
    for number in order:
        mine = [ln for ln in lines if ln.page == number]
        out.append(pages[number][mine[0].start:mine[-1].end])
    return "\n".join(out)


def _header(title: str, section: tuple[str, ...], first: Line, enabled: bool) -> str:
    if not enabled:
        return ""
    parts = [title, *section]
    head = " > ".join(p for p in parts if p)
    if first.table_header:
        head += f"\nหัวตาราง: {first.table_header}"
    return head


def build_document_chunks(meta: dict, rows: Iterable[dict], cfg: ChunkConfig, count: CountTokens, tokenizer_name: str,
                          corpus_version: str) -> list[dict]:
    rows = sorted(rows, key=lambda r: r["pdf_page"])
    pages = {r["pdf_page"]: r for r in rows if is_searchable(r)}
    texts = {n: r["text"] for n, r in pages.items()}
    section: tuple[str, ...] = ()
    lines: list[Line] = []
    for number in sorted(pages):
        row = pages[number]
        heading = page_context.section_heading(row["text"])
        new_section = heading is not None
        if heading:
            section = (heading,)
        page_budget = cfg.max_tokens - count(cfg.passage_prefix) - 8
        for ln in page_lines(row, max(page_budget - count(" > ".join([meta["title"], *section])) if cfg.contextual_header else page_budget, 16), count):
            ln.section = section
            ln.new_section = new_section
            new_section = False
            lines.append(ln)

    chunks: list[dict] = []
    i = 0
    while i < len(lines):
        first = lines[i]
        header = _header(meta["title"], first.section, first, cfg.contextual_header)
        overhead = count(cfg.passage_prefix + header + ("\n" if header else ""))
        limit = cfg.max_tokens - overhead
        taken = [first]
        used = count(first.text)
        j = i + 1
        full = False
        while j < len(lines):
            nxt = lines[j]
            gap = nxt.page != taken[-1].page and nxt.page != taken[-1].page + 1
            if gap or nxt.new_section or (nxt.page != taken[-1].page and not cfg.merge_pages):
                break
            if used + count(nxt.text) + 1 > limit:
                full = True
                break
            taken.append(nxt)
            used += count(nxt.text) + 1
            j += 1
        if full:  # closed by size: back up to the last paragraph boundary if that keeps enough of the budget
            for cut in range(len(taken) - 1, 0, -1):
                if lines[i + cut].boundary_before:
                    if sum(count(t.text) for t in taken[:cut]) >= cfg.min_fill_for_boundary * limit:
                        taken, j = taken[:cut], i + cut
                    break
        text = _text_of(taken, texts)
        while count(cfg.passage_prefix + header + ("\n" if header else "") + text) > cfg.max_tokens and len(taken) > 1:
            taken.pop()
            j = i + len(taken)
            text = _text_of(taken, texts)
        total = count(cfg.passage_prefix + header + ("\n" if header else "") + text)
        if total > cfg.max_tokens:  # a single line is still too long with its header: split it smaller and retry
            only = taken[0]
            pieces = _split_long(only.text, only.start, max(limit - (total - cfg.max_tokens) - 4, 8), count)
            if len(pieces) < 2:  # cannot shrink further: fail loudly instead of looping
                raise ValueError(f"{meta['document_id']} p{only.page}: line cannot fit {cfg.max_tokens} tokens")
            lines[i:i + 1] = [Line(only.page, a, b, texts[only.page][a:b], only.kind, only.boundary_before and k == 0,
                                   only.table_header, only.section, only.new_section and k == 0)
                              for k, (a, b) in enumerate(pieces)]
            continue
        start_page, end_page = taken[0].page, taken[-1].page
        statuses = sorted({pages[n]["status"] for n in range(start_page, end_page + 1) if n in pages})
        populations = {pages[n].get("population", "general") for n in range(start_page, end_page + 1) if n in pages}
        category = next((c["label"] for n in range(start_page, end_page + 1) if n in pages
                         for c in [pages[n].get("category")] if c), None)
        chunk = {
            "chunk_id": f"{meta['document_id']}:p{start_page:03d}-p{end_page:03d}:{len(chunks):03d}",
            "corpus_version": corpus_version, "chunk_config_id": cfg.config_id,
            "document_id": meta["document_id"], "edition_id": meta["edition_id"],
            "source_sha256": pages[start_page]["source_sha256"],
            "pdf_page_start": start_page, "pdf_page_end": end_page,
            "pdf_page_label_start": pages[start_page].get("pdf_page_label"),
            "char_start": taken[0].start,
            "char_end": [ln for ln in taken if ln.page == end_page][-1].end,
            "section_path": list(taken[0].section), "chunk_type": _chunk_type(taken), "text": text,
            "header_text": header, "token_count": total, "tokenizer": tokenizer_name,
            "source_page_statuses": statuses, "injection_flags": injection_flags(text),
            "primary_group": meta["primary_group"], "disease_tags": meta.get("disease_tags", []),
            "document_type": meta["document_type"],
            "population": populations.pop() if len(populations) == 1 else "mixed", "category": category,
        }
        chunks.append(chunk)
        i = max(j, i + 1)
    return chunks
