"""Demo: ask the Thai NCD guideline Q&A system a question and see a cited answer (or a refusal) with the evidence behind it.

    python -X utf8 demo.py "ค่าเป้าหมาย HbA1c ในผู้ป่วยเบาหวานคือเท่าไร"
    python -X utf8 demo.py                         # interactive: type questions, empty line to quit
    python -X utf8 demo.py "..." --graph           # the LangGraph version (adds one bounded retry when the model's reply is malformed)
    python -X utf8 demo.py "..." --variant A       # retrieval variant: A dense, B hybrid (default), C hybrid + reranker (slow on CPU, 15-36 s)
    python -X utf8 demo.py "..." --show-evidence   # also print the text of the chunks given to the model

What it runs (the frozen evaluation setup, configs/rag/frozen_v1.json): retrieve top-5 chunks (bge-m3 + Thai BM25), build the prompt, ask the LLM for cited claims,
then check every claim (the citation must be a chunk that was really sent; numbers and Latin words must appear in the cited chunk) and drop what fails.
Needs the local index (data/index/*, not in git) and TYPHOON_API_KEY in .env (see .env.example). The first start loads the models (about 20 s).
For study only: not medical advice, no diagnosis, no personal data handling (rule-based input guards G1/G3 are on by default, src/ncdqa/rag/guards.py; they are measured only on a silver set).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

DISCLAIMER = "เพื่อการศึกษาเท่านั้น ไม่ใช่คำแนะนำทางการแพทย์ ไม่วินิจฉัย ไม่สั่งหรือปรับยา ปรึกษาแพทย์/เภสัชกรสำหรับกรณีเฉพาะราย"
MESSAGES = {
    "abstained_model": "ระบบไม่พบหลักฐานในเอกสารที่เพียงพอจะตอบคำถามนี้ (โมเดลงดตอบ)",
    "abstained_validator": "คำตอบที่ได้ไม่ผ่านการตรวจหลักฐาน (citation/ตัวเลขไม่ตรงกับเอกสาร) จึงไม่แสดง",
    "abstained_no_evidence": "ไม่พบเอกสารที่เกี่ยวข้อง",
    "refused_input": "คำถามนี้ถูกปฏิเสธโดยตัวกรองอินพุต",
    "parse_error": "โมเดลตอบในรูปแบบที่ไม่ถูกต้อง ลองถามใหม่",
    "truncated": "คำตอบยาวเกินและถูกตัด ลองถามใหม่หรือใช้ --graph",
    "llm_error": "เรียกโมเดลไม่สำเร็จ (ตรวจ TYPHOON_API_KEY และเครือข่าย)",
}


def load(args):
    from ncdqa.llm.env import load_env
    from ncdqa.rag.guards import default_guards
    from ncdqa.rag.pipeline import DEFAULT_CONFIG, Pipeline
    load_env()
    guards = [] if args.no_guard else default_guards()
    cfg = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    cfg["retrieval"]["variant"] = args.variant
    cfg["prompt"]["layers"]["validator_tokens"] = True       # validator profile N7 (frozen, decision E1)
    from ncdqa.llm.client import LLMClient, load_providers
    llm = cfg["llm"]
    provider = load_providers(ROOT / llm["providers_file"])[llm["provider"]]
    client = LLMClient(provider, ROOT / llm["cache_dir"] / f'{llm["provider"]}.jsonl')
    from ncdqa.retrieval.search import Retriever
    retriever = Retriever()
    if args.graph:
        from ncdqa.rag.graph import GraphPipeline
        cfg["recover"] = {"max_retries": 1}
        return GraphPipeline(retriever, client, cfg, guards)
    return Pipeline(retriever, client, cfg, guards)


def show(result: dict, args, units: dict | None = None) -> None:
    print("\n" + "=" * 78)
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
    ap.add_argument("--no-guard", action="store_true", help="switch off the input guards (personal data, individual prescribing/diagnosis, emergencies)")
    args = ap.parse_args()
    pipe = load(args)
    units = None
    if args.show_evidence:
        units = pipe.retriever.retriever.units if args.graph else pipe.retriever.units
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
