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
    header_max_share: float = 0.25   # the contextual header may use at most this share of the token budget

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
    heading: bool = False      # short title-like line that must stay with the text after it


def is_searchable(row: dict) -> bool:
    review = row.get("human_review") or {}
    return not row.get("index_exclusion") and (row["status"] in ("ok", "ok_minor_issues") or (
        row["status"] in ("ocr_unreviewed", "degraded") and review.get("outcome") in ("pass", "fix")))


def injection_flags(text: str) -> list[str]:
    return [name for name, pattern in INJECTION if pattern.search(text)]


def _cut_point(text: str, a: int, limit: int) -> int:
    """Where to cut `text[a:limit]` when no sentence boundary fits: last line break, else last space, else a word edge."""
    window = text[a:limit]
    for mark in ("\n", " "):
        at = window.rfind(mark)
        if at >= len(window) * 0.4:
            return a + at + 1
    try:
        from pythainlp.tokenize import word_tokenize
        edge = 0
        for word in word_tokenize(text[a:min(len(text), limit + 40)], engine="newmm", keep_whitespace=True):
            if a + edge + len(word) > limit:
                break
            edge += len(word)
        if edge >= len(window) * 0.4:
            return a + edge
    except Exception:  # pragma: no cover
        pass
    return limit


def _split_long(text: str, base: int, budget: int, count: CountTokens) -> list[tuple[int, int]]:
    """Spans (relative to the page) that cover `text`, each within `budget` tokens: sentences first, then characters."""
    spans: list[tuple[int, int]] = []
    pieces: list[str] = []
    try:
        from pythainlp.tokenize import sent_tokenize
        pieces = [p for p in sent_tokenize(text.replace("\n", " "), engine="crfcut") if p]
    except Exception:  # pragma: no cover - PyThaiNLP missing or model not downloadable
        pieces = []
    pos = 0
    for piece in pieces:
        at = text.replace("\n", " ").find(piece, pos)
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
            lo = _cut_point(text, a, lo)
            result.append((base + a, base + lo))
            a = lo
        result.append((base + a, base + b))
    return result


SENTENCE_END = re.compile(r"[.!?:;)\]\"”]\s*$")
FULL_LINE = 0.6            # a line shorter than this share of the page's usual line width ends its paragraph
HEADING_MAX_CHARS = 60
HTML_ROW_END = re.compile(r"</tr>\s*")


def _usual_width(lengths: list[int]) -> int:
    ordered = sorted(lengths)
    return ordered[int(len(ordered) * 0.9)] if len(ordered) >= 6 else (ordered[-1] if ordered else 0)


def page_lines(page: dict, budget: int, count: CountTokens) -> list[Line]:
    """Units of a page: paragraphs rebuilt from lines the PDF wrapped at the page width, table rows, list items.

    A paragraph longer than the budget is cut at sentence boundaries, never inside a sentence unless one sentence
    alone exceeds the budget. Short title-like lines are flagged so they stay with the text that follows.
    """
    text, number = page["text"], page["pdf_page"]
    physical: list[tuple[int, int, str, str, bool, str | None]] = []
    offset, boundary, table_header = 0, False, None
    for raw in text.split("\n"):
        start, end = offset, offset + len(raw)
        offset = end + 1
        if not raw.strip():
            boundary, table_header = True, None
            continue
        if "</tr>" in raw:  # OCR output keeps a whole HTML table on one line: one unit per row, first row as header
            pos = 0
            for match in HTML_ROW_END.finditer(raw):
                piece = raw[pos:match.end()]
                if piece.strip():
                    table_header = table_header or piece.strip()
                    physical.append((start + pos, start + match.end(), piece, "table", boundary,
                                     table_header if table_header != piece.strip() else None))
                    boundary = False
                pos = match.end()
            if raw[pos:].strip():
                physical.append((start + pos, end, raw[pos:], "table", boundary, table_header))
                boundary = False
            continue
        kind = "table" if TABLE_LINE.search(raw) else "list" if LIST_LINE.match(raw) else "prose"
        if kind == "table":
            table_header = table_header or raw.strip()
        else:
            table_header = None
        header = table_header if kind == "table" and table_header != raw.strip() else None
        physical.append((start, end, raw, kind, boundary, header))
        boundary = False

    width = _usual_width([len(r[2]) for r in physical if r[3] != "table"])
    groups: list[list[tuple]] = []
    for row in physical:
        if groups and not row[4] and row[3] == "prose" and groups[-1][-1][3] in ("prose", "list"):
            prev = groups[-1][-1][2]
            wrapped = len(prev) >= FULL_LINE * width and not (SENTENCE_END.search(prev) and len(prev) < 0.9 * width)
            if wrapped:
                groups[-1].append(row)
                continue
        groups.append([row])

    lines: list[Line] = []
    for n, group in enumerate(groups):
        start, end = group[0][0], group[-1][1]
        kind, header = group[0][3], group[0][5]
        unit = text[start:end]
        heading = (len(group) == 1 and kind == "prose" and len(unit) <= HEADING_MAX_CHARS
                   and not SENTENCE_END.search(unit) and n < len(groups) - 1)
        if count(unit) > budget:
            for k, (a, b) in enumerate(_split_long(unit, start, budget, count)):
                lines.append(Line(number, a, b, text[a:b], kind, k == 0, header))
        else:
            lines.append(Line(number, start, end, unit, kind, True, header, heading=heading))
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


def _header(title: str, section: tuple[str, ...], first: Line, enabled: bool, count: CountTokens | None = None,
            cap: int | None = None) -> str:
    """`title > section` plus the repeated table header line; the longest piece is shortened until it fits `cap` tokens."""
    if not enabled:
        return ""
    pieces = [title, *section, first.table_header or ""]

    def build() -> str:
        head = " > ".join(p for p in pieces[:-1] if p)
        return head + (f"\nหัวตาราง: {pieces[-1]}" if pieces[-1] else "")

    while cap is not None and count is not None and count(build()) > cap and max(map(len, pieces)) > 12:
        longest = max(range(len(pieces)), key=lambda k: len(pieces[k]))
        pieces[longest] = pieces[longest][:int(len(pieces[longest]) * 0.75)].rstrip() + "…"
    return build()


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
        header_tokens = min(count(" > ".join([meta["title"], *section])), int(cfg.max_tokens * cfg.header_max_share)) if cfg.contextual_header else 0
        for ln in page_lines(row, max(page_budget - header_tokens, 16), count):
            ln.section = section
            ln.new_section = new_section
            new_section = False
            lines.append(ln)

    chunks: list[dict] = []
    i = 0
    while i < len(lines):
        first = lines[i]
        header = _header(meta["title"], first.section, first, cfg.contextual_header, count,
                         int(cfg.max_tokens * cfg.header_max_share))
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
        while len(taken) > 1 and taken[-1].heading and j < len(lines) and lines[j].page == taken[-1].page + 0:
            taken.pop()  # a title-like line stays with the text that follows it
            j = i + len(taken)
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
