"""Build a local HTML report that shows a reviewer how side-tab categories, page furniture and OCR repeats were handled.

For the health-literacy booklet it shows, page by page: the tab strip cropped from the page image with the nine tabs'
saturation (the one solid tab is the category), the category found three ways (solid tab in the image, the table of
contents, and "the last section-opener page before this one"), the lines removed from the OCR text (footer, header logo,
side-tab labels, second copy of the body), and the pages where the OCR itself went wrong (labels of tabs that do not
exist, a body written twice, a page that timed out). Page text is embedded, so write the report to an ignored folder.

Usage:
    python -X utf8 scripts/build_sidebar_report.py --before data/processed/normalized-v10 --after data/processed/normalized-v11 \
        --tabs data/agent_runs/20261008-sidebar/tabs.json --images data/agent_runs/20261008-sidebar/img \
        --decisions data/ocr_review_decisions_reocr-v9.json --out data/agent_runs/20261008-sidebar
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import side_tab_category as tabs_mod  # noqa: E402

DOCUMENT = tabs_mod.DOCUMENT
INVENTED_TAB = re.compile(r"ภัยพิบัติ|วัณโรค|ไข้หวัด|ลมติดต่อ|โรควัณ|สาธารณสุข$")
CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#1d2330;--muted:#5d6675;--line:#d9dee6;--accent:#2457c5;--del:#ffd9d9;--ok:#d6f5dd;--warn:#fff3cd}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--card:#1d2128;--ink:#e6e9ee;--muted:#9aa3b2;--line:#323844;--accent:#7aa2ff;--del:#5a2a2a;--ok:#24472e;--warn:#4a4020}}
body{margin:0;font-family:"Sarabun","Tahoma",sans-serif;background:var(--bg);color:var(--ink);font-size:14px}
main{max-width:1400px;margin:auto;padding:16px}h2{margin:28px 0 8px}h3{margin:0 0 6px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px;margin:0 0 14px}
table{border-collapse:collapse;width:100%}td,th{border-top:1px solid var(--line);padding:4px 6px;text-align:left;vertical-align:top}
.muted{color:var(--muted)}.pill{padding:1px 8px;border-radius:12px;border:1px solid var(--line);font-size:12px;color:var(--muted)}
.bars{display:inline-flex;gap:2px;align-items:flex-end;height:34px}.bars i{display:block;width:9px;background:#b9c4d4;border-radius:2px 2px 0 0}.bars i.on{background:#1b6fd1}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}img{max-width:100%;border:1px solid var(--line);border-radius:6px;background:#fff}
.rm{background:var(--del);text-decoration:line-through}.keep{background:var(--ok)}pre{white-space:pre-wrap;font-family:inherit;margin:0;font-size:13px;max-height:340px;overflow:auto}
.bad{background:var(--warn)}a{color:var(--accent)}
"""


def crop_strip(image_path: Path, info: dict, out: Path) -> bool:
    if not info["tab_boxes"] or not info["side"]:
        return False
    im = Image.open(image_path).convert("RGB")
    w, h = im.size
    band = tabs_mod.STRIPS[info["side"]]
    x0, x1 = int(w * (band[0] - 0.01)), int(w * (band[1] + 0.005))
    crop = im.crop((x0, 0, x1, h))
    draw = ImageDraw.Draw(crop)
    for n, ((y0, y1), sat) in enumerate(zip(info["tab_boxes"], info["saturations"]), 1):
        solid = n == info["active_from_image"]
        draw.rectangle((0, y0, crop.width - 1, y1), outline=(20, 110, 30) if solid else (150, 150, 150), width=4 if solid else 1)
    crop.thumbnail((140, 420))
    crop.save(out)
    return True


def diff_html(before: str, removed: dict[str, list[str]]) -> str:
    gone = {key: list(lines) for key, lines in removed.items()}
    out = []
    for line in before.split("\n"):
        stripped = line.strip()
        label = next((k for k, v in gone.items() if stripped and stripped in v), None)
        if label:
            gone[label].remove(stripped)
            out.append(f'<span class="rm" title="{label}">{html.escape(line)}</span>')
        else:
            out.append(html.escape(line))
    return "\n".join(out)


def load(corpus: Path) -> dict[int, dict]:
    rows = {}
    for line in (corpus / DOCUMENT / "pages.jsonl").read_text(encoding="utf-8").split("\n"):
        if line.strip():
            row = json.loads(line)
            rows[row["pdf_page"]] = row
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw-ocr", type=Path, default=None, help="corpus version with the OCR as the model wrote it (before review)")
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--tabs", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    before, after = load(args.before), load(args.after)
    raw = load(args.raw_ocr) if args.raw_ocr else {}
    invented_raw = sorted(p for p, r in raw.items() if r.get("reocr") and INVENTED_TAB.search(r["text"]))
    tabs = {int(k): v for k, v in json.loads(args.tabs.read_text(encoding="utf-8")).items()}
    rejected = {int(d["key"].split(":p")[1]) for d in json.loads(args.decisions.read_text(encoding="utf-8"))["decisions"]
                if d["page"] != "accept"}
    crops = args.out / "crops"
    crops.mkdir(parents=True, exist_ok=True)

    # category three ways
    openers = {a + tabs_mod.PRINTED_OFFSET: i for i, (a, _) in enumerate(tabs_mod.TOC_RANGES, 1)}
    by_opener, current = {}, None
    for page in sorted(tabs):
        if page in openers and tabs[page]["tabs"] < 9:
            current = openers[page]
        by_opener[page] = current
    compared = [p for p in tabs if tabs[p]["active_from_image"] and by_opener[p]]
    agree_toc = sum(tabs[p]["active_from_image"] == tabs[p]["active_from_toc"] for p in compared)
    agree_opener = sum(tabs[p]["active_from_image"] == by_opener[p] for p in compared)
    pale_pages = [p for p in tabs if tabs[p]["tabs"] >= 9 and not tabs[p]["active_from_image"]]
    no_strip = [p for p in tabs if tabs[p]["tabs"] < 9]
    removed_totals = Counter()
    for row in after.values():
        for key, lines in (row.get("boilerplate_removed") or {}).items():
            removed_totals[key] += len(lines)

    parts = [f"<!doctype html><html lang='th'><head><meta charset='utf-8'><title>Sidebar report</title><style>{CSS}</style></head><body><main>",
             "<h1>รายงาน: แถบหมวด, footer และเนื้อหาซ้ำของหนังสือ health literacy</h1>",
             "<p class='muted'>เปิดจากเซิร์ฟเวอร์ในเครื่อง (ลิงก์ภาพใช้ path สัมพัทธ์) · ข้อความหน้าถูกฝังในไฟล์นี้ จึงไม่ขึ้น Git</p>"]

    parts.append("<h2>1. สรุป</h2><div class='card'><table>"
                 f"<tr><td>หน้ามีแถบหมวดครบ 9 แถบ</td><td>{sum(t['tabs'] >= 9 for t in tabs.values())} จาก {len(tabs)} หน้า (หน้าคี่แถบอยู่ขวา หน้าคู่แถบอยู่ซ้าย)</td></tr>"
                 f"<tr><td>เจอแถบสีเข้มแถบเดียว (หมวดของหน้า)</td><td>{sum(bool(t['active_from_image']) for t in tabs.values())} หน้า</td></tr>"
                 f"<tr><td>แถบจางทั้ง 9 (ไม่มีหมวดโรค = ส่วน \"รู้เลขเสี่ยง\" เลขพิมพ์ 6–20)</td><td>{len(pale_pages)} หน้า: {', '.join(map(str, pale_pages))}</td></tr>"
                 f"<tr><td>ไม่มีแถบ (ปก/สารบัญ/<b>หน้าเปิดหมวด</b>/ท้ายเล่ม)</td><td>{len(no_strip)} หน้า: {', '.join(map(str, no_strip))}</td></tr>"
                 f"<tr><td><b>สีในภาพ ตรงกับสารบัญ</b></td><td><b>{agree_toc} จาก {len(compared)}</b></td></tr>"
                 f"<tr><td><b>สีในภาพ ตรงกับวิธี \"หน้าเปิดหมวดแล้วต่อเนื่องไป\"</b></td><td><b>{agree_opener} จาก {len(compared)}</b></td></tr>"
                 f"<tr><td>บรรทัดที่ตัดจากข้อความ OCR</td><td>footer {removed_totals['footer']} · โลโก้ด้านบน {removed_totals['header']} · ชื่อแถบหมวด {removed_totals['side_tabs']} · เนื้อหาซ้ำ {removed_totals['duplicates']}</td></tr>"
                 "</table></div>")

    # dark vs pale examples
    parts.append("<h2>2. แถบสีเข้ม (ใช้งานอยู่) กับสีจาง: ตัวอย่าง</h2><p class='muted'>กรอบเขียว = แถบที่ระบบเลือกว่าสีเข้ม · แท่งกราฟ = ความอิ่มสีของแต่ละแถบ (สูง = เข้ม) แถบเข้มสูง 0.85 ส่วนแถบจางไม่เกิน ~0.2</p><div class='grid'>")
    examples = [13, 34, 62, 75, 76, 88, 32, 7]
    for page in examples:
        if page not in tabs:
            continue
        info = tabs[page]
        has_crop = crop_strip(args.images / f"{DOCUMENT}-p{page}.png", info, crops / f"p{page}.png")
        bars = "".join(f"<i class='{'on' if n == info['active_from_image'] else ''}' style='height:{max(3, int(s * 34))}px' title='{s}'></i>"
                       for n, s in enumerate(info["saturations"][:9], 1))
        verdict = (tabs_mod.TAB_LABELS[info["active_from_image"] - 1] if info["active_from_image"]
                   else "ไม่มีแถบสีเข้ม (ทั้ง 9 จาง)" if info["tabs"] >= 9 else "ไม่มีแถบหมวดในหน้านี้ (หน้าเปิดหมวด/ปก/สารบัญ)")
        parts.append(f"<div class='card'><h3>หน้า PDF {page} <span class='pill'>พิมพ์ {page - tabs_mod.PRINTED_OFFSET}</span></h3>"
                     f"<a href='img/{DOCUMENT}-p{page}.png' target='_blank'><img src='img/{DOCUMENT}-p{page}.png' width='260'></a>"
                     f"{f' <img src=crops/p{page}.png>' if has_crop else ''}<div class='bars'>{bars}</div><div><b>{html.escape(verdict)}</b></div></div>")
    parts.append("</div>")

    # table of all pages
    parts.append("<h2>3. ทุกหน้า: หมวดสามวิธี และสิ่งที่ตัด</h2><div class='card'><table><tr><th>หน้า</th><th>แถบ</th><th>หมวดจากสีในภาพ</th><th>หมวดจากสารบัญ</th><th>หมวดจากหน้าเปิดหมวด</th><th>ตัดแล้ว (footer/โลโก้/แถบ/ซ้ำ)</th><th>หมายเหตุ</th></tr>")
    for page in sorted(tabs):
        info, row = tabs[page], after.get(page, {})
        rem = row.get("boilerplate_removed") or {}
        img_l = tabs_mod.TAB_LABELS[info["active_from_image"] - 1] if info["active_from_image"] else ("(จางทั้งหมด)" if info["tabs"] >= 9 else "—")
        toc_l = tabs_mod.TAB_LABELS[info["active_from_toc"] - 1] if info["active_from_toc"] else "—"
        op_l = tabs_mod.TAB_LABELS[by_opener[page] - 1] if by_opener.get(page) else "—"
        notes = []
        if page in rejected:
            notes.append("คุณเลือกไม่ใช้ในรอบแรก (อนุมัติแล้ว)")
        if page in no_strip:
            notes.append("ไม่มีแถบ")
        if any(INVENTED_TAB.search(x) for x in rem.get("side_tabs", [])):
            notes.append("OCR อ่านแถบจางเป็นชื่อที่ไม่มีจริง")
        mismatch = info["active_from_image"] and info["active_from_toc"] and info["active_from_image"] != info["active_from_toc"]
        parts.append(f"<tr class='{'bad' if mismatch else ''}'><td><a href='img/{DOCUMENT}-p{page}.png' target='_blank'>{page}</a></td><td>{info['side'] or '—'}</td>"
                     f"<td>{html.escape(img_l)}</td><td>{html.escape(toc_l)}</td><td>{html.escape(op_l)}</td>"
                     f"<td>{len(rem.get('footer', []))}/{len(rem.get('header', []))}/{len(rem.get('side_tabs', []))}/{len(rem.get('duplicates', []))}</td>"
                     f"<td>{html.escape('; '.join(notes))}</td></tr>")
    parts.append("</table></div>")

    # before / after
    parts.append("<h2>4. ข้อความก่อน → หลัง (แดงขีดฆ่า = ถูกตัด)</h2><div class='grid'>")
    for page in (13, 34, 62 if 62 in after else 60, 75, 76, 88):
        if page not in before or not after[page].get("boilerplate_removed"):
            continue
        rem = after[page]["boilerplate_removed"]
        parts.append(f"<div class='card'><h3>หน้า {page} <span class='pill'>{len(before[page]['text'])} → {len(after[page]['text'])} ตัวอักษร</span></h3>"
                     f"<pre>{diff_html(before[page]['text'], rem)}</pre></div>")
    parts.append("</div>")

    # OCR repeats and errors
    dup_pages = [p for p, r in after.items() if (r.get("boilerplate_removed") or {}).get("duplicates")]
    invented = [p for p, r in after.items() if any(INVENTED_TAB.search(x) for x in (r.get("boilerplate_removed") or {}).get("side_tabs", []))]
    parts.append("<h2>5. หน้าที่ OCR ทำซ้ำหรือผิด</h2><div class='card'>"
                 f"<p><b>เนื้อหาถูกเขียนซ้ำสองรอบ</b> {len(dup_pages)} หน้า ({', '.join(map(str, sorted(dup_pages)))}) · "
                 f"<b>อ่านแถบจางเป็นชื่อที่ไม่มีจริง</b> (เช่น \"ภัยพิบัติ\", \"วัณโรค\", \"ไข้หวัดใหญ่\") ตอนที่โมเดล OCR เขียน {len(invented_raw)} หน้า "
                 f"({', '.join(map(str, invented_raw))}) → เหลือ {len(invented)} หน้าหลังข้อเสนอแก้ที่คุณอนุมัติ · "
                 "<b>หมดเวลาสองครั้ง (โมเดลตอบวน)</b> หน้า 71 (ยังไม่มีข้อความ)</p></div><div class='grid'>")
    for page in sorted(dup_pages)[:6]:
        rem = after[page]["boilerplate_removed"]
        parts.append(f"<div class='card'><h3>หน้า {page}: ซ้ำ {len(rem['duplicates'])} บรรทัด</h3>"
                     f"<a href='img/{DOCUMENT}-p{page}.png' target='_blank'><img src='img/{DOCUMENT}-p{page}.png' width='220'></a>"
                     f"<pre>{html.escape(chr(10).join(rem['duplicates'][:8]))}</pre></div>")
    parts.append("</div>")

    # rejected pages
    parts.append("<h2>6. 12 หน้าที่คุณเลือกไม่ใช้รอบแรก ลักษณะเป็นอย่างไร</h2><p class='muted'>เกือบทั้งหมดคือหน้าเปิดหมวดแบบเต็มหน้า (ไม่มีแถบข้าง) ที่ภาพเป็นหลัก ข้อความน้อย</p><div class='grid'>")
    for page in sorted(rejected):
        text = after.get(page, {}).get("text", "")
        parts.append(f"<div class='card'><h3>หน้า {page} <span class='pill'>{'ไม่มีแถบ' if page in no_strip else 'มีแถบ'}</span> <span class='pill'>{len(text)} ตัวอักษร</span></h3>"
                     f"<a href='img/{DOCUMENT}-p{page}.png' target='_blank'><img src='img/{DOCUMENT}-p{page}.png' width='220'></a>"
                     f"<pre>{html.escape(text[:260])}</pre></div>")
    parts.append("</div></main></body></html>")
    out = args.out / "sidebar_report.html"
    out.write_text("\n".join(parts), encoding="utf-8", newline="\n")
    print(json.dumps({"out": str(out), "compared": len(compared), "agree_toc": agree_toc, "agree_opener": agree_opener,
                      "pale_pages": pale_pages, "no_strip": no_strip, "dup_pages": sorted(dup_pages), "invented_tab_pages_raw_ocr": invented_raw, "invented_tab_pages_after": sorted(invented)},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
