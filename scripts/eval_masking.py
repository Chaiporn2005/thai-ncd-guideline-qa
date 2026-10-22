"""Measure PII masking (decision G1 = B) on a SILVER set (Track C).

    python -X utf8 scripts/eval_masking.py --questions data/handoff/track_c_20261012/questions_all_reviewed.jsonl --out data/index/runs/guard/masking_silver.json

For each case: the secret string must be gone from the masked question and the rest of the question must be kept. Two groups: `easy` (the forms the rules were written for, same silver set as
eval_input_guard.py) and `adversarial` (forms a user could really type that the rules were NOT written for: Thai digits, spaced digits, a name without a title, an e-mail spelled with "at"). False
positives: how many of the 162 real project questions (and a few borderline ones) are changed by masking. Silver: written and labelled by the AI that wrote the rules, no human review.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ncdqa.rag import guards  # noqa: E402
from ncdqa.rag.guardrail_eval import wilson  # noqa: E402


def make_id(first12: str) -> str:
    return first12 + str((11 - sum(int(first12[i]) * (13 - i) for i in range(12)) % 11) % 10)


ID1, ID2 = make_id("310090123456"), make_id("120045678901")
EASY = [  # (question, secret, words of the health question that must survive)
    (f"เลขบัตรประชาชน {ID1} เป็นเบาหวานต้องตรวจอะไร", ID1, "เบาหวาน"),
    (f"{ID2[0]}-{ID2[1:5]}-{ID2[5:10]}-{ID2[10:12]}-{ID2[12]} ความดันสูงควรกินยาอะไร", ID2[1:5], "ความดันสูง"),
    ("โทร 081-234-5678 เรื่องผลเลือด", "081-234-5678", "ผลเลือด"),
    ("เบอร์ผม 0891234567 ขอผลตรวจน้ำตาล", "0891234567", "ผลตรวจน้ำตาล"),
    ("ส่งผลมาที่ patient.name@hospital.go.th ได้ไหม", "patient.name@hospital.go.th", "ได้ไหม"),
    ("somying_k@gmail.com เป็นไขมันสูง", "somying_k@gmail.com", "ไขมันสูง"),
    ("HN 7654321 ตรวจ HbA1c แล้วสูง", "7654321", "HbA1c"),
    ("ผู้ป่วย AN: 123456 ควรให้ยาอะไร", "123456", "ควรให้ยาอะไร"),
    ("นายสมชาย ใจดี เป็นเบาหวานมา 5 ปี", "สมชาย ใจดี", "เบาหวานมา 5 ปี"),
    ("นางสาวสมหญิง รักสุข ความดัน 160/100", "สมหญิง รักสุข", "160/100"),
    ("น.ส.วิภา แสนดี ไตเสื่อม", "วิภา แสนดี", "ไตเสื่อม"),
]
ADVERSARIAL = [
    ("โทร ๐๘๑-๒๓๔-๕๖๗๘ เรื่องผลเลือด", "๐๘๑-๒๓๔-๕๖๗๘", "ผลเลือด"),
    ("เบอร์ 0 8 1 2 3 4 5 6 7 8 ขอผลตรวจน้ำตาล", "0 8 1 2 3 4 5 6 7 8", "ผลตรวจน้ำตาล"),
    ("เบอร์ +66 81 234 5678 เรื่องผลเลือด", "81 234 5678", "ผลเลือด"),
    ("ส่งมาที่ somchai at hospital dot com ได้ไหม", "somchai at hospital dot com", "ได้ไหม"),
    ("คุณสมชาย ใจดี เป็นเบาหวาน", "สมชาย ใจดี", "เบาหวาน"),
    ("สมชาย ใจดี อายุ 60 ปี น้ำตาล 250", "สมชาย ใจดี", "น้ำตาล 250"),
    (f"เลขบัตร {ID1.translate(str.maketrans('0123456789', '๐๑๒๓๔๕๖๗๘๙'))} ตรวจเบาหวาน", ID1.translate(str.maketrans('0123456789', '๐๑๒๓๔๕๖๗๘๙')), "ตรวจเบาหวาน"),   # a valid ID typed in Thai digits (v1 of this case had 14 digits by mistake)
]
BORDERLINE_OK = [
    "ผู้ป่วยอายุ 55 ปี ความดัน 150/95 ตามแนวทางจัดเป็นความดันสูงระดับใด", "HbA1c 8.2 ถือว่าควบคุมไม่ดีตามแนวทางหรือไม่", "ผู้ป่วยโรคไตเรื้อรังระยะ 4 ควรจำกัดโซเดียมวันละกี่มิลลิกรัม",
    "ตัวชี้วัดปีงบประมาณ 2565 มีเป้าหมายร้อยละ 90", "โทรสายด่วน 1669 เมื่อมีอาการฉุกเฉิน", "สายด่วน สปสช 1330 โทรได้ตลอด 24 ชั่วโมง", "นายแพทย์ผู้เชี่ยวชาญควรปรับยาอย่างไรตามแนวทาง",
]


def run(cases):
    rows = []
    for q, secret, keep in cases:
        masked, cats = guards.mask_pii(q)
        rows.append({"secret_removed": secret not in masked, "rest_kept": keep in masked, "categories": cats})
    n = len(rows)
    return {"n": n, "secret_removed": {"k": sum(r["secret_removed"] for r in rows), "ci95": list(wilson(sum(r["secret_removed"] for r in rows), n))},
            "rest_kept": sum(r["rest_kept"] for r in rows), "missed": [cases[i][0][:40] for i, r in enumerate(rows) if not r["secret_removed"]]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--questions", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        sys.exit(f"{args.out} exists, choose a new --out")
    qs = [json.loads(x) for x in args.questions.read_text(encoding="utf-8").split("\n") if x.strip()]
    real = [q["question"] for q in qs if q["status"] == "gold" and q["split"] in ("dev", "test")]
    changed_real = [q for q in real if guards.mask_pii(q)[0] != q]
    changed_border = [q for q in BORDERLINE_OK if guards.mask_pii(q)[0] != q]
    out = {"label_status": "silver (AI-written cases, no human review)", "easy": run(EASY), "adversarial": run(ADVERSARIAL),
           "false_positive_real_questions": {"changed": len(changed_real), "n": len(real), "ci95": list(wilson(len(changed_real), len(real)))},
           "false_positive_borderline": {"changed": len(changed_border), "n": len(BORDERLINE_OK), "which": [q[:40] for q in changed_border]}}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
