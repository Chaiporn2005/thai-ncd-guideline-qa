"""Demo: ask the Thai NCD guideline Q&A system a question and see a cited answer (or a refusal) with the evidence behind it.

    python -X utf8 demo.py "ค่าเป้าหมาย HbA1c ในผู้ป่วยเบาหวานคือเท่าไร"
    python -X utf8 demo.py                         # interactive: type questions, empty line to quit
    python -X utf8 demo.py "..." --graph           # the LangGraph version (adds one bounded retry when the model's reply is malformed)
    python -X utf8 demo.py "..." --variant A       # retrieval variant: A dense, B hybrid (default), C hybrid + reranker (slow on CPU, 15-36 s)
    python -X utf8 demo.py "..." --show-evidence   # also print the text of the chunks given to the model

What it runs (the frozen evaluation setup, configs/rag/frozen_v1.json): retrieve top-5 chunks (bge-m3 + Thai BM25), build the prompt, ask the LLM for cited claims,
then check every claim (the citation must be a chunk that was really sent; numbers and Latin words must appear in the cited chunk) and drop what fails.
Needs the local index (data/index/*, not in git) and TYPHOON_API_KEY in .env (see .env.example). The first start loads the models (about 20 s).
For study only: not medical advice, no diagnosis. Decisions (docs/decisions_guardrail_harness.md): G1 = B personal identifiers in the question are masked before anything is sent to the LLM,
so no identifier leaves the machine; G3 individual prescribing/diagnosis is refused and emergencies get the 1669 message; G2 = B the demo logs metadata only (no question or answer text) to
data/index/demo_log/metadata.jsonl, switch off with --no-log. O2 (OWASP, docs/owasp_guardrails.md): questions longer than 800 characters and known injection patterns are refused,
search results flagged as instruction-like are dropped, and an answer with markup, a link the evidence lacks, system-prompt text or personal data is withheld. The rule-based guards are
measured only on a silver set (src/ncdqa/rag/guards.py, src/ncdqa/rag/owasp_guards.py).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

DISCLAIMER = "เพื่อการศึกษาเท่านั้น ไม่ใช่คำแนะนำทางการแพทย์ ไม่วินิจฉัย ไม่สั่งหรือปรับยา ปรึกษาแพทย์/เภสัชกรสำหรับกรณีเฉพาะราย"
MESSAGES = {
    "abstained_model": "ระบบไม่พบหลักฐานในเอกสารที่เพียงพอจะตอบคำถามนี้ (โมเดลงดตอบ)",
    "abstained_validator": "คำตอบที่ได้ไม่ผ่านการตรวจหลักฐาน (citation/ตัวเลขไม่ตรงกับเอกสาร) จึงไม่แสดง",
    "abstained_no_evidence": "ไม่พบเอกสารที่เกี่ยวข้อง",
    "refused_input": "คำถามนี้ถูกปฏิเสธโดยตัวกรองอินพุต",
    "blocked_output": "ระบบไม่แสดงคำตอบนี้เพราะตรวจพบเนื้อหาที่ไม่ปลอดภัยในผลลัพธ์ (ลิงก์/โค้ด/ข้อมูลส่วนบุคคล/ข้อความภายในระบบ) กรุณาถามใหม่",
    "parse_error": "โมเดลตอบในรูปแบบที่ไม่ถูกต้อง ลองถามใหม่",
    "truncated": "คำตอบยาวเกินและถูกตัด ลองถามใหม่หรือใช้ --graph",
    "llm_error": "เรียกโมเดลไม่สำเร็จ (ตรวจ TYPHOON_API_KEY และเครือข่าย)",
}


def load(args):
    from ncdqa.llm.env import load_env
    from ncdqa.rag import owasp_guards as og
    from ncdqa.rag.guards import MaskingPipeline
    from ncdqa.rag.pipeline import DEFAULT_CONFIG, Pipeline
    load_env()
    guards = [] if args.no_guard else og.owasp_demo_guards()
    cfg = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    cfg["retrieval"]["variant"] = args.variant
    cfg["prompt"]["layers"]["validator_tokens"] = True       # validator profile N7 (frozen, decision E1)
    from ncdqa.llm.client import LLMClient, load_providers
    llm = cfg["llm"]
    provider = load_providers(ROOT / llm["providers_file"])[llm["provider"]]
    client = LLMClient(provider, ROOT / llm["cache_dir"] / f'{llm["provider"]}.jsonl')
    from ncdqa.retrieval.search import Retriever
    raw = Retriever()
    retriever = raw if args.no_guard else og.GuardedRetriever(raw)
    if args.graph:
        from ncdqa.rag.graph import GraphPipeline
        cfg["recover"] = {"max_retries": 1}
        pipe = GraphPipeline(retriever, client, cfg, guards)
    else:
        pipe = Pipeline(retriever, client, cfg, guards)
    if not args.no_guard:
        pipe = og.GuardedPipeline(pipe, text_of=lambda cid: raw.units[cid]["text"])      # output guard (OWASP LLM02/05/07)
        pipe = MaskingPipeline(pipe)                                                         # G1 = B, outermost: nothing identifiable reaches any later step
    return pipe, raw.units


LOG_PATH = ROOT / "data/index/demo_log/metadata.jsonl"


def log_metadata(result: dict, args) -> None:
    """G2 = B: metadata only. Never the question or the answer text, never the matched personal data (only which categories were masked)."""
    t = result["trace"]
    hits = t.get("hits") or []
    row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "status": result["status"], "variant": args.variant, "graph": args.graph, "n_hits": len(hits),
           "top_score": hits[0]["score"] if hits else None, "guard": (t.get("guard") or {}).get("category"), "pii_masked": t.get("pii_masked"),
           "tokens": (t.get("usage") or {}).get("total_tokens"), "cached": t.get("cached")}
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def show(result: dict, args, units: dict | None = None) -> None:
    if not args.no_log:
        log_metadata(result, args)
    print("\n" + "=" * 78)
    masked = result["trace"].get("pii_masked")
    if masked:
        print("(ระบบปิดบังข้อมูลที่ระบุตัวบุคคลในคำถามก่อนประมวลผล: " + ", ".join(masked) + " ข้อมูลสุขภาพส่วนที่เหลือยังอยู่ในคำถาม)")
    if result["status"] == "answered":
        print("คำตอบ:\n" + result["answer"])
        print("\nแหล่งอ้างอิง:")
        for c in result["citations"]:
            print(f'  [{c["id"]}] {c["document_id"]} (ฉบับ {c["edition_id"]}) หน้า PDF {c["pdf_pages"]}')
    elif result["status"] == "refused_input":
        print(result["trace"]["guard"]["message"])
    else:
        print(MESSAGES.get(result["status"], result["status"]))
    t = result["trace"]
    dropped = t.get("dropped_claims") or []
    if dropped:
        print(f"\n(ตัดทิ้ง {len(dropped)} ข้อที่ตรวจหลักฐานไม่ผ่าน: " + "; ".join(d["reason"][:60] for d in dropped[:3]) + ")")
    flags = [h["chunk_id"] for h in t.get("hits", []) if h.get("injection_flags")]
    if flags:
        print(f"(คำเตือน: chunk {len(flags)} ชิ้นมีข้อความคล้ายคำสั่งแฝง ถูกบันทึกธงไว้ ไม่ได้ทำตาม)")
    print(f"\nสถานะ: {result['status']} | token: {(t.get('usage') or {}).get('total_tokens', '-')} | cache: {t.get('cached', '-')}"
          + (f" | เส้นทาง graph: {' > '.join(t['graph_path'])}" if "graph_path" in t else ""))
    print(DISCLAIMER)
    if args.show_evidence and units is not None:
        print("\n--- หลักฐานที่ส่งให้โมเดล ---")
        for sid, cid in (t.get("evidence") or {}).items():
            print(f"[{sid}] {cid}\n{units[cid]['text'][:600]}\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("question", nargs="?", help="omit for interactive mode")
    ap.add_argument("--variant", choices=["A", "B", "C"], default="B")
    ap.add_argument("--graph", action="store_true", help="use the LangGraph version (one bounded retry on a malformed reply)")
    ap.add_argument("--show-evidence", action="store_true")
    ap.add_argument("--no-guard", action="store_true", help="switch off masking and the scope guard (individual prescribing/diagnosis, emergencies)")
    ap.add_argument("--no-log", action="store_true", help="do not write the metadata log (G2 = B)")
    args = ap.parse_args()
    pipe, all_units = load(args)
    units = all_units if args.show_evidence else None
    print(DISCLAIMER)
    if args.question:
        show(pipe.answer(args.question), args, units)
        return 0
    while True:
        try:
            q = input("\nคำถาม> ").strip()
        except EOFError:
            break
        if not q:
            break
        show(pipe.answer(q), args, units)
    return 0


if __name__ == "__main__":
    sys.exit(main())
