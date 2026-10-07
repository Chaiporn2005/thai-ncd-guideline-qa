"""Build a local HTML page for a person to review proposed OCR corrections page by page.

Reads the page list, the proposals (JSONL) and the corpus text, and writes review.html next to the
images. The page shows each source image beside the current text with proposed edits highlighted,
lets the reviewer accept/reject each edit and decide each page, keeps progress in the browser, and
exports a decisions JSON for scripts/apply_ocr_review.py (via a converter). Nothing is uploaded.

Usage:
    python -X utf8 scripts/build_ocr_review_page.py --audit-dir data/agent_runs/20261007-codex-audit \
        --pages round2_pages.json --findings round2_findings.jsonl --corpus data/processed/normalized-v6
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PRIORITY = {"sign": 0, "number": 1, "drug": 2, "unit": 3, "remove": 4, "word": 5}
# The merge step strips printed page numbers on purpose, so "missing" notes that only mention them are not gaps.
PAGE_NUMBER_ONLY = re.compile(r"^\s*(เลขหน้า(พิมพ์)?\s*\S+[^,;]*|printed (footer )?page( number)?\s*\S*[^,;]*|"
                              r"footer page \S+[^,;]*|page number[^,;]*)[\s.]*$", re.I)

PAGE_TEMPLATE = """<!doctype html>
<html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OCR Review</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1d2330;--muted:#5d6675;--line:#d9dee6;--del:#ffd9d9;--ins:#d6f5dd;--warn:#fff3cd;--accent:#2457c5}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--card:#1d2128;--ink:#e6e9ee;--muted:#9aa3b2;--line:#323844;--del:#5a2a2a;--ins:#24472e;--warn:#4a4020;--accent:#7aa2ff}}
*{box-sizing:border-box}body{margin:0;font-family:"Sarabun","Tahoma",sans-serif;background:var(--bg);color:var(--ink)}
header{position:sticky;top:0;z-index:5;background:var(--card);border-bottom:1px solid var(--line);padding:10px 16px;display:flex;gap:12px;flex-wrap:wrap;align-items:center}
header b{font-size:15px}.pill{padding:2px 8px;border-radius:12px;background:var(--bg);border:1px solid var(--line);font-size:13px}
button,select{font:inherit;padding:5px 10px;border-radius:6px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer}
button.primary{background:var(--accent);color:#fff;border-color:var(--accent)}
main{padding:12px 16px;max-width:1500px;margin:auto}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:0 0 16px;padding:12px}
.card.done{opacity:.72}.head{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:8px}
.key{font-weight:700}.grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px}
@media (max-width:900px){.grid{grid-template-columns:1fr}}
.img{max-height:85vh;overflow:auto;border:1px solid var(--line);border-radius:6px;background:#fff}.img img{width:100%;display:block}
pre{white-space:pre-wrap;word-break:break-word;font-family:inherit;font-size:14px;line-height:1.55;margin:0;max-height:85vh;overflow:auto;border:1px solid var(--line);border-radius:6px;padding:8px}
del{background:var(--del);text-decoration:line-through}ins{background:var(--ins);text-decoration:none}
table{width:100%;border-collapse:collapse;margin-top:8px;font-size:14px}td,th{border-top:1px solid var(--line);padding:5px;text-align:left;vertical-align:top}
.k-sign,.k-number,.k-drug,.k-unit{background:var(--warn);font-weight:700}.notes{color:var(--muted);font-size:13px;margin:6px 0}
.decide{display:flex;gap:14px;flex-wrap:wrap;margin-top:8px;align-items:center}textarea{width:100%;min-height:38px;font:inherit;margin-top:6px;background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:6px}
</style></head><body>
<header><b>OCR Review</b><span class="pill" id="progress"></span>
<label>แสดง <select id="filter"><option value="all">ทั้งหมด</option><option value="critical">มีแก้ตัวเลข/เครื่องหมาย/ชื่อยา</option>
<option value="edits">มีข้อเสนอแก้</option><option value="flag">content_missing / invented / unreadable</option><option value="todo">ยังไม่ตัดสิน</option></select></label>
<button class="primary" id="export">Export decisions (JSON)</button><span class="pill">บันทึกอัตโนมัติในเบราว์เซอร์นี้</span></header>
<main id="list"></main>
<script>
const DATA = __DATA__;
const STORE = "ocr-review-" + DATA.review_id;
let state = {};
try { state = JSON.parse(localStorage.getItem(STORE) || "{}"); } catch (e) { state = {}; }
function save(){ try { localStorage.setItem(STORE, JSON.stringify(state)); } catch (e) {} progress(); }
function esc(s){ return s.replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])); }
function defaults(p){ return {page: "", edits: p.edits.map(e => e.confidence === "high"), note: ""}; }
function st(p){ if(!state[p.key]) state[p.key] = defaults(p); return state[p.key]; }
function preview(p, s){
  let t = esc(p.text);
  p.edits.forEach((e, i) => { const o = esc(e.old); if(!o) return;
    const rep = s.edits[i] ? `<del>${o}</del><ins>${esc(e.new)}</ins>` : `<mark>${o}</mark>`;
    t = t.split(o).join(rep); });
  return t;
}
function card(p){
  const s = st(p); const div = document.createElement("section"); div.className = "card" + (s.page ? " done" : ""); div.id = p.key;
  const rows = p.edits.map((e, i) => `<tr><td><input type="checkbox" data-i="${i}" ${s.edits[i] ? "checked" : ""}></td>
    <td class="k-${e.kind}">${e.kind}${e.valid ? "" : " ⚠ ไม่พบ/ซ้ำในข้อความ"}</td><td><del>${esc(e.old)}</del></td><td><ins>${esc(e.new)}</ins></td><td>${e.confidence}</td><td>${esc(e.evidence||"")}</td></tr>`).join("");
  div.innerHTML = `<div class="head"><span class="key">${p.key}</span><span class="pill">${p.group}</span><span class="pill">AI: ${p.verdict}</span>
    ${p.critical ? '<span class="pill k-sign">ตัวเลข/เครื่องหมาย/ชื่อยา</span>' : ""}</div>
    ${p.notes ? `<div class="notes">หมายเหตุ AI: ${esc(p.notes)}</div>` : ""}${p.missing ? `<div class="notes">เนื้อหาที่ขาด: ${esc(p.missing)}</div>` : ""}
    <div class="grid"><div class="img"><img loading="lazy" src="${p.image}" alt="${p.key}"></div><pre>${preview(p, s)}</pre></div>
    ${p.edits.length ? `<table><tr><th>ใช้</th><th>ชนิด</th><th>เดิม</th><th>ใหม่</th><th>มั่นใจ</th><th>หลักฐาน</th></tr>${rows}</table>` : ""}
    <div class="decide">หน้านี้:
      <label><input type="radio" name="d-${p.key}" value="accept" ${s.page==="accept"?"checked":""}> ใช้ (พร้อมข้อแก้ที่ติ๊ก)</label>
      <label><input type="radio" name="d-${p.key}" value="reject" ${s.page==="reject"?"checked":""}> ไม่ใช้หน้านี้</label>
      <label><input type="radio" name="d-${p.key}" value="later" ${s.page==="later"?"checked":""}> ต้องแก้เพิ่ม/ดูทีหลัง</label></div>
    <textarea placeholder="หมายเหตุของผู้ตรวจ (ถ้ามี)">${esc(s.note||"")}</textarea>`;
  div.querySelectorAll("input[type=checkbox]").forEach(cb => cb.onchange = () => { s.edits[+cb.dataset.i] = cb.checked; div.querySelector("pre").innerHTML = preview(p, s); save(); });
  div.querySelectorAll("input[type=radio]").forEach(r => r.onchange = () => { s.page = r.value; div.classList.add("done"); save(); });
  div.querySelector("textarea").oninput = e => { s.note = e.target.value; save(); };
  return div;
}
function render(){
  const f = document.getElementById("filter").value; const list = document.getElementById("list"); list.innerHTML = "";
  DATA.pages.filter(p => f==="all" || (f==="critical" && p.critical) || (f==="edits" && p.edits.length) ||
    (f==="flag" && ["content_missing","text_invented","unreadable"].includes(p.verdict)) || (f==="todo" && !st(p).page))
    .forEach(p => list.appendChild(card(p)));
  progress();
}
function progress(){ const done = DATA.pages.filter(p => st(p).page).length;
  document.getElementById("progress").textContent = `ตัดสินแล้ว ${done}/${DATA.pages.length}`; }
document.getElementById("filter").onchange = render;
document.getElementById("export").onclick = () => {
  const out = {review_id: DATA.review_id, exported_at: new Date().toISOString(), decisions: DATA.pages.map(p => { const s = st(p);
    return {key: p.key, page: s.page || "undecided", accepted_edits: p.edits.filter((e,i) => s.edits[i]), note: s.note || ""}; })};
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([JSON.stringify(out, null, 1)], {type: "application/json"}));
  a.download = `ocr_review_decisions_${DATA.review_id}.json`; a.click();
};
render();
</script></body></html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--pages", required=True)
    parser.add_argument("--findings", required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--review-id", default="round2")
    args = parser.parse_args()

    pages = json.loads((args.audit_dir / args.pages).read_text(encoding="utf-8"))
    findings = {}
    for line in (args.audit_dir / args.findings).read_text(encoding="utf-8").split("\n"):
        if line.strip():
            r = json.loads(line)
            findings[r["key"]] = r
    texts = {}
    for f in args.corpus.glob("*/pages.jsonl"):
        for line in f.read_text(encoding="utf-8").split("\n"):
            if line.strip():
                r = json.loads(line)
                texts[f"{r['document_id']}:p{r['pdf_page']}"] = r["text"]

    items, missing = [], []
    for p in pages:
        f = findings.get(p["key"])
        if f is None:
            missing.append(p["key"])
            continue
        edits = [e for e in f.get("edits", []) if e.get("old")]
        text = texts[p["key"]]
        for e in edits:
            e["valid"] = text.count(e["old"]) == 1
        verdict, missing_text = f.get("verdict", ""), f.get("missing", "")
        if verdict == "content_missing" and PAGE_NUMBER_ONLY.match(missing_text.strip()):
            verdict = "fixed" if edits else "text_ok"
            missing_text = f"(ขาดเฉพาะเลขหน้าพิมพ์ ซึ่งตัดออกโดยตั้งใจ) {missing_text}"
        items.append({"key": p["key"], "group": p["group"], "image": p["image"], "text": text,
                      "verdict": verdict, "notes": f.get("notes", ""), "missing": missing_text,
                      "edits": edits, "critical": any(e.get("kind") in ("sign", "number", "drug", "unit") for e in edits)})
    items.sort(key=lambda x: (not x["critical"], not x["edits"],
                              x["verdict"] not in ("content_missing", "text_invented", "unreadable"), x["key"]))
    payload = {"review_id": args.review_id, "pages": items}
    out = args.audit_dir / "review.html"
    out.write_text(PAGE_TEMPLATE.replace("__DATA__", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")),
                   encoding="utf-8")
    invalid = sum(1 for i in items for e in i["edits"] if not e["valid"])
    print(json.dumps({"pages": len(items), "missing_findings": missing, "edits": sum(len(i["edits"]) for i in items),
                      "invalid_edits": invalid, "critical_pages": sum(i["critical"] for i in items),
                      "output": str(out)}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
