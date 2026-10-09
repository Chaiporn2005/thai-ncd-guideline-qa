"""Exploratory probe (not an evaluation): do specific-population pages enter results for adult questions?
Page-level BM25 over the pages that would be searchable in v8, population labels = the reviewer's labels."""
import json, math, re, sys, collections
from pathlib import Path
from pythainlp.tokenize import word_tokenize

v8 = Path(sys.argv[1])
rows = []
for f in sorted(v8.glob("*/pages.jsonl")):
    for l in f.read_text(encoding="utf-8").split("\n"):
        if not l.strip():
            continue
        r = json.loads(l)
        hr = r.get("human_review") or {}
        ok = r["status"] in ("ok", "ok_minor_issues") or (r["status"] in ("ocr_unreviewed", "degraded") and hr.get("outcome") in ("pass", "fix"))
        if ok and not r.get("index_exclusion") and (r.get("text") or "").strip():
            rows.append(r)
print("searchable pages", len(rows), collections.Counter(r["population"] for r in rows))


def tok(t):
    return [w.lower() for w in word_tokenize(t, engine="newmm", keep_whitespace=False) if len(w.strip()) > 1 and not re.fullmatch(r"[\W_]+", w)]


docs = [tok(r["text"]) for r in rows]
N = len(docs)
avgdl = sum(map(len, docs)) / N
df = collections.Counter(w for d in docs for w in set(d))
tfs = [collections.Counter(d) for d in docs]
k1, b = 1.5, 0.75


def search(q, k=10):
    qs = tok(q)
    scores = []
    for i, tf in enumerate(tfs):
        s = 0.0
        dl = len(docs[i])
        for w in qs:
            if w in tf:
                idf = math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5))
                s += idf * tf[w] * (k1 + 1) / (tf[w] + k1 * (1 - b + b * dl / avgdl))
        scores.append(s)
    order = sorted(range(N), key=lambda i: -scores[i])[:k]
    return [rows[i] for i in order]


ADULT = [
    "เป้าหมายระดับ HbA1c ในผู้ป่วยเบาหวานผู้ใหญ่",
    "ยาตัวแรกที่เลือกใช้รักษาเบาหวานชนิดที่ 2",
    "เกณฑ์วินิจฉัยโรคเบาหวานด้วยระดับน้ำตาลในเลือดขณะอดอาหาร",
    "ภาวะน้ำตาลในเลือดต่ำ รักษาอย่างไร",
    "ค่าความดันโลหิตเป้าหมายในผู้ป่วยความดันโลหิตสูง",
    "ข้อบ่งชี้การเริ่มยากลุ่มสแตติน",
    "การคัดกรองโรคเบาหวานควรทำอย่างไร",
    "การเริ่มยาฉีดอินซูลินและการปรับขนาดยา",
    "การตรวจติดตามภาวะแทรกซ้อนที่ตาและไต",
    "อาหารและการออกกำลังกายเพื่อควบคุมน้ำตาล",
    "เป้าหมายระดับน้ำตาลในเลือดก่อนอาหาร",
    "การป้องกันและรักษาแผลที่เท้า",
]
POP = {
    "pediatric": ["เบาหวานในเด็กและวัยรุ่น เป้าหมาย HbA1c", "ภาวะน้ำตาลต่ำในเด็กที่เป็นเบาหวานชนิดที่ 1", "การฉีดอินซูลินในเด็กเบาหวาน"],
    "pregnancy": ["เบาหวานขณะตั้งครรภ์ เกณฑ์การวินิจฉัย OGTT", "เป้าหมายระดับน้ำตาลในหญิงตั้งครรภ์ที่เป็นเบาหวาน", "การติดตามหลังคลอดในผู้ที่เป็นเบาหวานขณะตั้งครรภ์"],
    "elderly": ["อาหารสำหรับผู้สูงอายุที่เป็นเบาหวาน", "เป้าหมายน้ำตาลในผู้สูงอายุ"],
}
print("\nADULT-INTENT QUERIES: share of results from non-general pages")
tot5 = tot10 = n5 = n10 = 0
rowsout = []
for q in ADULT:
    res = search(q, 10)
    spec5 = sum(r["population"] != "general" for r in res[:5])
    spec10 = sum(r["population"] != "general" for r in res)
    tot5 += spec5; n5 += 5; tot10 += spec10; n10 += 10
    labs = [r["population"][0].upper() if r["population"] != "general" else "." for r in res]
    rowsout.append((q[:48], spec5, spec10, "".join(labs)))
for r in rowsout:
    print(f"  top5={r[1]} top10={r[2]} [{r[3]}]  {r[0]}")
print(f"  TOTAL non-general: top5 {tot5}/{n5} ({tot5/n5:.0%}), top10 {tot10}/{n10} ({tot10/n10:.0%}); queries with >=1 in top5: {sum(1 for r in rowsout if r[1])}/{len(ADULT)}")

print("\nPOPULATION-INTENT QUERIES: share of top5 from the matching label (and from general)")
for label, qs in POP.items():
    for q in qs:
        res = search(q, 5)
        m = sum(r["population"] == label for r in res)
        g = sum(r["population"] == "general" for r in res)
        mixed = sum(r["population"] == "mixed" for r in res)
        print(f"  {label:9s} match={m}/5 general={g} mixed={mixed}  {q[:50]}")
