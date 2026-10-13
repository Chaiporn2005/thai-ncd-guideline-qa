"""Demo: ask the Thai NCD guideline Q&A system a question and see a cited answer (or a refusal) with the evidence behind it.

    python -X utf8 demo.py --check                  # is this machine ready? (packages, local data bundle, API key, model cache) with the exact fix for anything missing
    python -X utf8 demo.py "ค่าเป้าหมาย HbA1c ในผู้ป่วยเบาหวานคือเท่าไร"
    python -X utf8 demo.py                          # interactive: type questions, empty line to quit
    python -X utf8 demo.py --web                    # local web page at http://127.0.0.1:8780 (nine ready-made showcase questions, evidence panel, permanent disclaimer)
    python -X utf8 demo.py --warm                   # run the showcase questions once (downloads the embedding model, fills the answer cache so they also run offline)
    python -X utf8 demo.py "..." --graph            # the LangGraph version (same path as the plain pipeline, plus one bounded retry on a malformed reply)
    python -X utf8 demo.py "..." --agent react      # the ReAct agent (searches by itself; about 5x the tokens, no better answers: see the report)
    python -X utf8 demo.py "..." --variant C        # retrieval variant: A dense, B hybrid (default), C hybrid + reranker (slow on CPU, 15-36 s)
    python -X utf8 demo.py "..." --show-evidence    # also print the text of the chunks given to the model

What it runs (frozen evaluation setup, configs/rag/frozen_v1.json): input guards (personal identifiers masked, individual prescribing/diagnosis refused, emergencies get 1669, length cap, injection
patterns) -> retrieve top-5 (bge-m3 + Thai BM25) -> prompt -> LLM typhoon-v2.5-30b-a3b-instruct -> check every claim (the citation must be a chunk that was sent; numbers and Latin words must appear in the
cited chunk; numbers the user typed are allowed) -> output guard (markup, links, system-prompt text, personal data) -> answer with document, edition and PDF page.
Needs: the local data bundle (data/index/..., not in git), TYPHOON_API_KEY in .env, internet on the first start (model download of several GB, API). Everything the demo answered once is cached, so a repeated question runs offline.
For study only: not medical advice. Decisions: docs/decisions_guardrail_harness.md. G2: only metadata is logged (data/index/demo_log/metadata.jsonl, off with --no-log), never the question or the answer.
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
LOG_PATH = ROOT / "data/index/demo_log/metadata.jsonl"


class Demo:
    """Loads the models and the index once; builds one pipeline per (mode, variant) on first use. mode: fixed | graph | react | react-graph."""

    def __init__(self, guard: bool = True, log: bool = True):
        from ncdqa.llm.client import LLMClient, load_providers
        from ncdqa.llm.env import load_env
        from ncdqa.rag import demo_support
        from ncdqa.rag.pipeline import DEFAULT_CONFIG
        from ncdqa.retrieval.search import Retriever
        load_env()
        self.guard, self.log = guard, log
        self.cfg = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
        llm = self.cfg["llm"]
        provider = load_providers(ROOT / llm["providers_file"])[llm["provider"]]
        self.cache_dir = ROOT / demo_support.DEMO_CACHE_DIR            # a separate cache: what the demo answered, small enough to hand to a teammate
        self.client = LLMClient(provider, self.cache_dir / f'{llm["provider"]}.jsonl')
        self.raw = Retriever()
        self.units = self.raw.units
        self._pipes: dict = {}

    def _config(self, mode: str, variant: str) -> dict:
        if mode.startswith("react"):
            cfg = json.loads((ROOT / "configs/rag/react_v1.json").read_text(encoding="utf-8"))
            cfg["agent"].update({"seed_search": True, "max_steps": 3})              # the settings of frozen_react_v1
        else:
            cfg = json.loads(json.dumps(self.cfg))
            cfg["recover"] = {"max_retries": 1} if mode == "graph" else cfg["recover"]
        cfg["retrieval"]["variant"] = variant
        layers = cfg["prompt"]["layers"]
        layers["validator_tokens"] = True                       # validator profile N7 (frozen, decision E1)
        layers["validator_question_numbers"] = True             # N8: a number the user wrote may be repeated in a claim (docs/error_analysis_track_c.md)
        return cfg

    def pipeline(self, mode: str = "fixed", variant: str = "B"):
        key = (mode, variant)
        if key in self._pipes:
            return self._pipes[key]
        from ncdqa.rag import owasp_guards as og
        from ncdqa.rag.guards import MaskingPipeline
        cfg = self._config(mode, variant)
        guards = [] if not self.guard else og.owasp_demo_guards()
        retriever = self.raw if not self.guard else og.GuardedRetriever(self.raw)
        if mode == "react":
            from ncdqa.rag.react_agent import ReactAgent
            pipe = ReactAgent(retriever, self.client, cfg, guards)
        elif mode == "react-graph":
            from ncdqa.rag.react_graph import GraphReactAgent
            pipe = GraphReactAgent(retriever, self.client, cfg, guards)
        elif mode == "graph":
            from ncdqa.rag.graph import GraphPipeline
            pipe = GraphPipeline(retriever, self.client, cfg, guards)
        else:
            from ncdqa.rag.pipeline import Pipeline
            pipe = Pipeline(retriever, self.client, cfg, guards)
        if self.guard:
            pipe = og.GuardedPipeline(pipe, text_of=lambda cid: self.units[cid]["text"])      # output guard (OWASP LLM02/05/07)
            pipe = MaskingPipeline(pipe)                                                         # G1 = B, outermost: nothing identifiable reaches any later step
        self._pipes[key] = pipe
        return pipe

    def ask(self, question: str, mode: str = "fixed", variant: str = "B") -> dict:
        t0 = time.perf_counter()
        result = self.pipeline(mode, variant).answer(question)
        result["trace"]["demo_seconds"] = round(time.perf_counter() - t0, 2)
        if self.log:
            self._log(result, mode, variant)
        return result

    def _log(self, result: dict, mode: str, variant: str) -> None:
        """G2 = B: metadata only. Never the question or the answer text, never the matched personal data (only which categories were masked)."""
        t = result["trace"]
        hits = t.get("hits") or []
        row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "status": result["status"], "mode": mode, "variant": variant, "n_hits": len(hits),
               "top_score": hits[0]["score"] if hits else None, "guard": (t.get("guard") or {}).get("category"), "pii_masked": t.get("pii_masked"),
               "tokens": (t.get("usage") or {}).get("total_tokens"), "cached": t.get("cached"), "seconds": t.get("demo_seconds")}
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def show(result: dict, show_evidence: bool, units: dict | None) -> None:
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
    path = t.get("graph_path") or t.get("react_path")
    print(f"\nสถานะ: {result['status']} | token: {(t.get('usage') or {}).get('total_tokens', '-')} | cache: {t.get('cached', '-')} | {t.get('demo_seconds', '-')} วินาที"
          + (f" | เส้นทาง: {' > '.join(path)}" if path else ""))
    print(DISCLAIMER)
    if show_evidence and units is not None:
        print("\n--- หลักฐานที่ส่งให้โมเดล ---")
        for sid, cid in (t.get("evidence") or {}).items():
            print(f"[{sid}] {cid}\n{units[cid]['text'][:600]}\n")


PAGE = """<!doctype html><html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Thai NCD Guideline Q&A</title><style>
:root{--bg:#f6f8fb;--card:#fff;--ink:#14213d;--mut:#5b6b82;--line:#d9e1ec;--acc:#1d4ed8;--warn:#b45309;--bad:#b91c1c;--ok:#047857}
@media(prefers-color-scheme:dark){:root{--bg:#0f172a;--card:#16213a;--ink:#e6edf7;--mut:#9fb0c8;--line:#2a3a5a;--acc:#7aa2ff;--warn:#fbbf24;--bad:#f87171;--ok:#34d399}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,"Noto Sans Thai","Tahoma",sans-serif}
.bar{position:sticky;top:0;background:var(--warn);color:#fff;padding:8px 16px;font-size:14px;text-align:center;z-index:5}
main{max-width:980px;margin:0 auto;padding:16px}h1{font-size:22px;margin:8px 0}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin:12px 0}
textarea{width:100%;min-height:76px;border:1px solid var(--line);border-radius:8px;padding:10px;background:var(--bg);color:var(--ink);font:inherit}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:8px}select,button{padding:8px 12px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--ink);font:inherit}
button.primary{background:var(--acc);color:#fff;border-color:var(--acc);cursor:pointer}button.chip{cursor:pointer;font-size:14px;text-align:left}
.chips{display:flex;flex-wrap:wrap;gap:6px}.badge{display:inline-block;padding:2px 9px;border-radius:99px;font-size:13px;border:1px solid var(--line)}
.ok{color:var(--ok)}.bad{color:var(--bad)}.warn{color:var(--warn)}.mut{color:var(--mut);font-size:14px}pre{white-space:pre-wrap;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:10px;font:14px/1.5 inherit}
details{margin-top:8px}ul{padding-left:20px}
</style></head><body><div class="bar">เพื่อการศึกษาเท่านั้น ไม่ใช่คำแนะนำทางการแพทย์ ไม่วินิจฉัย ไม่สั่งหรือปรับยา ปรึกษาแพทย์/เภสัชกรสำหรับกรณีเฉพาะราย</div>
<main><h1>Thai NCD Guideline Q&amp;A</h1><div class="mut">ถามความรู้จากแนวทางเวชปฏิบัติ NCD (เบาหวาน ความดัน ไขมัน ไต) ระบบตอบจากเอกสารพร้อมแหล่งอ้างอิง หรืองดตอบ</div>
<div class="card"><label for="q"><b>คำถาม</b></label><textarea id="q" placeholder="พิมพ์คำถามภาษาไทย..."></textarea>
<div class="row"><select id="mode" aria-label="pipeline"><option value="fixed">pipeline คงที่ (แนะนำ)</option><option value="graph">LangGraph</option><option value="react">ReAct agent (ช้า/แพงกว่า)</option></select>
<select id="variant" aria-label="retrieval"><option value="B">B hybrid (ค่าเริ่มต้น)</option><option value="A">A dense</option><option value="C">C +rerank (ช้าบน CPU)</option></select>
<button class="primary" id="go">ถาม</button><span id="busy" class="mut"></span></div>
<div class="mut" style="margin-top:10px">ตัวอย่างคำถาม (กดเพื่อใส่ในกล่อง)</div><div class="chips" id="chips"></div></div>
<div id="out"></div></main>
<script>
const $=id=>document.getElementById(id);
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
fetch('/api/showcase').then(r=>r.json()).then(list=>{$('chips').innerHTML=list.map((s,i)=>`<button class="chip" data-i="${i}" title="${esc(s.expect)}">${esc(s.label)}</button>`).join('');
 $('chips').onclick=e=>{const b=e.target.closest('button');if(b){$('q').value=list[b.dataset.i].question;$('q').focus();}};});
async function ask(){const q=$('q').value.trim();if(!q)return;$('busy').textContent='กำลังประมวลผล...';$('go').disabled=true;
 try{const r=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,mode:$('mode').value,variant:$('variant').value})});
  const d=await r.json();render(d);}catch(e){$('out').innerHTML='<div class="card bad">เรียกระบบไม่สำเร็จ: '+esc(e)+'</div>';}
 $('busy').textContent='';$('go').disabled=false;}
function render(d){if(d.error){$('out').innerHTML='<div class="card bad">'+esc(d.error)+'</div>';return;}
 const cls=d.status==='answered'?'ok':(d.status.startsWith('abstained')?'warn':'bad');let h='<div class="card">';
 h+=`<span class="badge ${cls}">${esc(d.status)}</span> <span class="mut">token ${esc(d.tokens??'-')} · cache ${esc(d.cached??'-')} · ${esc(d.seconds)} วินาที${d.path?' · '+esc(d.path.join(' > ')):''}</span>`;
 if(d.masked&&d.masked.length)h+=`<p class="warn">ระบบปิดบังข้อมูลที่ระบุตัวบุคคลก่อนประมวลผล: ${esc(d.masked.join(', '))}</p>`;
 if(d.status==='answered'){h+='<h3>คำตอบ</h3><pre>'+esc(d.answer)+'</pre><b>แหล่งอ้างอิง</b><ul>'+d.citations.map(c=>`<li>[${esc(c.id)}] ${esc(c.document_id)} · ฉบับ ${esc(c.edition_id)} · หน้า PDF ${esc(c.pdf_pages)}</li>`).join('')+'</ul>';}
 else{h+='<p>'+esc((d.guard&&d.guard.message)||(d.output_guard&&d.output_guard.message)||d.message||d.status)+'</p>';}
 if(d.dropped&&d.dropped.length)h+='<p class="mut">ตัดทิ้งข้อที่ตรวจหลักฐานไม่ผ่าน: '+esc(d.dropped.join('; '))+'</p>';
 if(d.evidence&&d.evidence.length)h+='<details><summary>หลักฐานที่ส่งให้โมเดล ('+d.evidence.length+' ชิ้น)</summary>'+d.evidence.map(e=>`<p><b>[${esc(e.id)}]</b> ${esc(e.document)} · หน้า ${esc(e.pages)}</p><pre>${esc(e.text)}</pre>`).join('')+'</details>';
 $('out').innerHTML=h+'</div>';}
$('go').onclick=ask;$('q').addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey))ask();});
</script></body></html>"""


def serve(demo: Demo, port: int) -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    from ncdqa.rag import demo_support
    lock = __import__("threading").Lock()          # one question at a time: the models are shared

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            if self.path in ("/", "/index.html"):
                self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif self.path == "/api/showcase":
                self._send(200, json.dumps(demo_support.load_showcase(), ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self):  # noqa: N802
            if self.path != "/api/ask":
                return self._send(404, b"not found", "text/plain")
            try:
                n = min(int(self.headers.get("Content-Length", "0")), 20000)
                req = json.loads(self.rfile.read(n).decode("utf-8"))
                q, mode, variant = str(req.get("question", ""))[:5000], req.get("mode", "fixed"), req.get("variant", "B")
                if mode not in ("fixed", "graph", "react") or variant not in ("A", "B", "C"):
                    raise ValueError("bad mode or variant")
                with lock:
                    result = demo.ask(q, mode, variant)
                data = demo_support.serialize(result, demo.units)
                data["seconds"] = result["trace"].get("demo_seconds")
                data["message"] = MESSAGES.get(result["status"])
            except Exception as err:  # noqa: BLE001  report the type only: a message could echo request details
                data = {"error": f"เกิดข้อผิดพลาด: {type(err).__name__}"}
            self._send(200, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def log_message(self, *args):  # no request log: the request body holds the question
            return

    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)         # localhost only
    print(f"เปิดเบราว์เซอร์ที่ http://127.0.0.1:{port}   (Ctrl+C เพื่อหยุด)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog="see the top of demo.py for every mode")
    ap.add_argument("question", nargs="?", help="omit for interactive mode")
    ap.add_argument("--check", action="store_true", help="check this machine (packages, data bundle, key, model cache) and print what to fix")
    ap.add_argument("--web", action="store_true", help="start the local web page")
    ap.add_argument("--port", type=int, default=8780)
    ap.add_argument("--warm", action="store_true", help="run the showcase questions once to download the model and fill the answer cache")
    ap.add_argument("--variant", choices=["A", "B", "C"], default="B")
    ap.add_argument("--graph", action="store_true", help="use the LangGraph version")
    ap.add_argument("--agent", choices=["fixed", "langgraph", "react"], help="pipeline kind (react = ReAct agent in plain Python)")
    ap.add_argument("--show-evidence", action="store_true")
    ap.add_argument("--no-guard", action="store_true", help="switch off masking, the scope/injection/length guards and the output guard (for ablation only)")
    ap.add_argument("--no-log", action="store_true", help="do not write the metadata log (G2 = B)")
    args = ap.parse_args()
    if args.check:
        from ncdqa.rag import demo_support
        print(demo_support.render_check(demo_support.check_environment()))
        return 0
    mode = "react" if args.agent == "react" else ("graph" if (args.graph or args.agent == "langgraph") else "fixed")
    demo = Demo(guard=not args.no_guard, log=not args.no_log)
    if args.web:
        serve(demo, args.port)
        return 0
    if args.warm:
        from ncdqa.rag import demo_support
        for i, s in enumerate(demo_support.load_showcase(), 1):
            r = demo.ask(s["question"], "fixed", "B")
            print(f'[{i}] {s["label"]}: {r["status"]} ({r["trace"].get("demo_seconds")} s)')
        return 0
    print(DISCLAIMER)
    units = demo.units if args.show_evidence else None
    if args.question:
        show(demo.ask(args.question, mode, args.variant), args.show_evidence, units)
        return 0
    while True:
        try:
            q = input("\nคำถาม> ").strip()
        except EOFError:
            break
        if not q:
            break
        show(demo.ask(q, mode, args.variant), args.show_evidence, units)
    return 0


if __name__ == "__main__":
    sys.exit(main())
