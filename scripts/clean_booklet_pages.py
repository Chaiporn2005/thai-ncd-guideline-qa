"""Remove repeated page furniture from the OCR text of the health-literacy booklet and record each page's category.

Every page of `ncd-ddc-health-literacy-fight-ncds-2566` is a scanned poster with the same furniture: a footer (agency
logo, hotline, social handle, book title), a strip of nine category tabs, and sometimes a second copy of the body that
the OCR model wrote after the first. Left in place, the footer and the nine tab labels make every page match every
disease query and pull all pages together in a vector space. What is removed here, and why it is safe:

  footer      short lines in the last lines of the page that match the footer wording (logo, hotline, handles, title);
  side tabs   a run of at least five consecutive tab-like lines that names at least four different tabs (a single
              line "โรคเบาหวาน" inside the body is never touched);
  duplicates  a body line that already occurred earlier on the same page (second copy), outside tables.

Every removed line is stored on the page (`boilerplate_removed`), numbers that would disappear are reported, and the
page's category comes from the image (the one solid tab; see side_tab_category.py), checked against the table of contents.

Usage:
    python -X utf8 scripts/clean_booklet_pages.py --source data/processed/normalized-v10 \
        --tabs data/agent_runs/20261008-sidebar/tabs.json --out data/processed/normalized-v11 \
        --manifest data/manifests/booklet_cleanup_normalized-v11.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import side_tab_category as tabs_mod  # noqa: E402

DOCUMENT = tabs_mod.DOCUMENT
INTRO_LABEL = "รู้เลขเสี่ยง (ภาพรวม ไม่มีหมวดโรค)"
FOOTER_ZONE = 18         # only the last non-empty lines of a page can be footer
FOOTER_MAX_CHARS = 80
FOOTER = re.compile(
    r"^(?:D[DPR]C|DRC|DPC)\s*กรมควบคุมโรค|Department of Disease Control|^กรมควบคุมโรค$|กองโรคไม่ติดต่อ|"
    r"Division of Non Communicable Diseases|MINISTRY OF PUBLIC HEALTH|^สายด่วน(?:\s*กรมควบคุมโรค)?(?:\s*1422)?$|^1422$|"
    r"^รอบรู้\s*สุขภาพ|ด้านโรคไม่ติดต่อ\s*@?\s*NCD|@NCD_D[PD]C|Google Play|App Store|"
    r"Health Literacy:\s*Together Fight NCDs|ประชาชนรอบรู้\s*สู้โรคไม่ติดต่อ|^-{3,}$|^\*{0,2}(?:กรมควบคุมโรค)\*{0,2}$",
    re.I)
TAB_STEMS = {
    "ความดัน": "โรคความดัน", "เบาหวาน": "โรคเบาหวาน", "ไต": "โรคไต", "หัวใจ": "โรคหัวใจ", "หลอดเลือด": "โรคหลอดเลือด",
    "อ้วน": "โรคอ้วน", "เกลือ": "การลดการบริโภค", "ไม่ติดต่อ": "โรคไม่ติดต่อ", "โควิด": "โควิด", "วันสำคัญ": "วันสำคัญ",
}
# The ministry/agency logo block printed at the top of every poster page; words that can only belong to it.
HEADER_WORDS = {"กระทรวงสาธารณสุข", "MINISTRY", "OF", "PUBLIC", "HEALTH", "กรมควบคุมโรค", "สถาบันป้องกันควบคุมโรคเขตเมือง",
                "Department", "Disease", "Control", "สถาบัน", "บำราศนราดูร"}
HEADER_ZONE = 6          # only among the first non-empty lines, and only on poster pages (pages with a tab strip)
TAB_LINE_MAX = 40
TAB_RUN_MIN_LINES = 5
TAB_RUN_MIN_DISTINCT = 4
DUPLICATE_MIN_CHARS = 8
EMPTY_AFTER_CLEANUP = 15   # a page left with fewer letters/digits than this carries no content of its own


def key_of(line: str) -> str:
    """A line without Markdown marks, bullets and spaces, so bold/bullet copies of a line compare equal."""
    return re.sub(r"[\s*#>\-•|_`]+", "", line)


def tab_stem(line: str) -> str | None:
    key = key_of(line)
    if not key or len(key) > TAB_LINE_MAX or key.startswith("<"):
        return None
    for stem, needle in TAB_STEMS.items():
        if needle.replace(" ", "") in key:
            return stem
    return None


def is_header_line(line: str) -> bool:
    words = line.strip("*# ").split()
    return bool(words) and all(w.strip("*#") in HEADER_WORDS for w in words)


def clean_page_text(text: str, poster: bool = False) -> tuple[str, dict[str, list[str]]]:
    lines = text.split("\n")
    removed: dict[str, list[str]] = {"header": [], "side_tabs": [], "duplicates": [], "footer": []}
    drop: set[int] = set()

    # side tabs: runs of consecutive tab-like lines (blank lines do not break a run)
    run: list[tuple[int, str]] = []

    def flush():
        if len(run) >= TAB_RUN_MIN_LINES and len({stem for _, stem in run}) >= TAB_RUN_MIN_DISTINCT:
            for idx, _ in run:
                drop.add(idx)
                removed["side_tabs"].append(lines[idx].strip())
        run.clear()

    for i, ln in enumerate(lines):
        if not ln.strip():
            continue
        stem = tab_stem(ln)
        if stem:
            run.append((i, stem))
        else:
            flush()
    flush()

    # duplicates: a body line already seen earlier on the page (not inside a table)
    seen: set[str] = set()
    for i, ln in enumerate(lines):
        if i in drop or not ln.strip() or ln.lstrip().startswith("<"):
            continue
        key = key_of(ln)
        if len(key) < DUPLICATE_MIN_CHARS:
            continue
        if key in seen:
            drop.add(i)
            removed["duplicates"].append(ln.strip())
        seen.add(key)

    # header logo block: only on poster pages, only among the first lines
    if poster:
        first = [i for i, ln in enumerate(lines) if ln.strip() and i not in drop][:HEADER_ZONE]
        for i in first:
            if is_header_line(lines[i]):
                drop.add(i)
                removed["header"].append(lines[i].strip())

    # footer: matching short lines among the last lines that are still left (tabs and the second copy are already gone,
    # so the footer is at the end however long the removed material was)
    remaining = [i for i, ln in enumerate(lines) if ln.strip() and i not in drop]
    for i in remaining[-FOOTER_ZONE:]:
        if len(lines[i].strip()) <= FOOTER_MAX_CHARS and FOOTER.search(lines[i].strip("*# ").strip()):
            drop.add(i)
            removed["footer"].append(lines[i].strip())

    kept = [ln for i, ln in enumerate(lines) if i not in drop]
    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()
    return cleaned, {k: v for k, v in removed.items() if v}


def signal(text: str) -> int:
    return len(re.findall(r"[ก-๙A-Za-z0-9]", text))


def numbers(text: str) -> Counter:
    return Counter(re.findall(r"\d+(?:[.,]\d+)?", text))


def category_for(page: int, tab_info: dict | None) -> dict | None:
    """Category of one page: the solid tab in the image, checked against the table of contents."""
    toc = tabs_mod.toc_tab(page)
    image = (tab_info or {}).get("active_from_image")
    strip = (tab_info or {}).get("tabs", 0) >= len(tabs_mod.TAB_LABELS)
    printed = page - tabs_mod.PRINTED_OFFSET
    if image:
        return {"tab": image, "label": tabs_mod.TAB_LABELS[image - 1], "source": "image_active_tab", "toc_tab": toc,
                "toc_agrees": toc == image}
    if strip and 6 <= printed <= 20:
        return {"tab": None, "label": INTRO_LABEL, "source": "image_all_tabs_pale", "toc_tab": None, "toc_agrees": True}
    opener = next((i for i, (a, _) in enumerate(tabs_mod.TOC_RANGES, 1) if a == printed), None)
    if opener and not strip:
        return {"tab": opener, "label": tabs_mod.TAB_LABELS[opener - 1], "source": "toc_section_opener", "toc_tab": opener,
                "toc_agrees": True}
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--tabs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error(f"{args.out} exists; corpus versions are never overwritten")
    tab_info = {int(k): v for k, v in json.loads(args.tabs.read_text(encoding="utf-8")).items()}

    totals, lost_numbers, pages_log, emptied, openers = Counter(), [], [], [], []
    for folder in sorted(p for p in args.source.iterdir() if (p / "pages.jsonl").exists()):
        rows = [json.loads(x) for x in (folder / "pages.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()]
        if folder.name == DOCUMENT:
            for row in rows:
                category = category_for(row["pdf_page"], tab_info.get(row["pdf_page"]))
                if category:
                    row["category"] = category
                if row.get("needs_ocr") and category and category["source"] == "toc_section_opener":
                    # A full-page section opener prints only the section title over pictures: the OCR model loops on it
                    # and there is no body to read. The title is the page's category, so nothing is OCR'd or invented.
                    row.pop("needs_ocr")
                    row["section_opener_title"] = category["label"]
                    row["index_exclusion"] = {"reason": "section_opener_title_only", "decided_by": "reviewer (chat 2026-10-09)",
                                              "decided_at": "2026-10-09"}
                    openers.append(row["pdf_page"])
                    continue
                if row.get("text_source") != "ocr" or not row.get("text"):
                    continue
                poster = (row.get("category") or {}).get("source") in ("image_active_tab", "image_all_tabs_pale",
                                                                       "toc_section_opener")
                cleaned, removed = clean_page_text(row["text"], poster)
                if removed:
                    # numbers that existed only in a removed second copy of the body would be lost content; furniture
                    # numbers (19 in "โควิด 19", 1422) are expected to go
                    vanished = set(numbers(row["text"])) - set(numbers(cleaned))
                    new_loss = {n: c for n, c in numbers("\n".join(removed.get("duplicates", []))).items() if n in vanished}
                    row.update(text_before_cleanup_sha256=hashlib.sha256(row["text"].encode("utf-8")).hexdigest(),
                               boilerplate_removed=removed, text=cleaned)
                    totals.update({k: len(v) for k, v in removed.items()})
                    if signal(cleaned) < EMPTY_AFTER_CLEANUP and not row.get("index_exclusion"):
                        row["index_exclusion"] = {"reason": "empty_after_booklet_cleanup", "decided_by": "rule: " + Path(__file__).name,
                                                  "decided_at": datetime.now(timezone.utc).date().isoformat()}
                        emptied.append(row["pdf_page"])
                    if new_loss:
                        lost_numbers.append({"page": row["pdf_page"], "numbers": new_loss})
                    pages_log.append({"page": row["pdf_page"], **{k: len(v) for k, v in removed.items()}})
        out_dir = args.out / folder.name
        out_dir.mkdir(parents=True)
        blob = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode("utf-8")
        (out_dir / "pages.jsonl").write_bytes(blob)
        summary = json.loads((folder / "normalization.json").read_text(encoding="utf-8"))
        summary.update(pages_jsonl_sha256=hashlib.sha256(blob).hexdigest(),
                       derived_from={"corpus_version": folder.parent.name, "pages_jsonl_sha256": summary["pages_jsonl_sha256"]},
                       created_at=datetime.now(timezone.utc).isoformat())
        (out_dir / "normalization.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                                    encoding="utf-8", newline="\n")
    manifest = {"corpus_version": args.out.name, "derived_from": args.source.name, "document": DOCUMENT,
                "removed_lines": dict(totals), "pages_changed": len(pages_log), "pages": pages_log,
                "numbers_lost_with_content": lost_numbers, "pages_empty_after_cleanup": emptied, "section_openers_without_ocr": openers,
                "rules": {"footer_zone_lines": FOOTER_ZONE, "tab_run_min_lines": TAB_RUN_MIN_LINES,
                          "tab_run_min_distinct": TAB_RUN_MIN_DISTINCT, "duplicate_min_chars": DUPLICATE_MIN_CHARS, "empty_after_cleanup_chars": EMPTY_AFTER_CLEANUP}}
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in manifest.items() if k != "pages"}, ensure_ascii=False)[:900])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
