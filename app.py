"""Local web demo of the Thai NCD guideline Q&A (a thin web layer over demo.py; the answer pipeline itself is unchanged).

    python -X utf8 app.py                 # then open http://127.0.0.1:8000
    python -X utf8 app.py --port 8123 --no-log

Same setup as demo.py (docs/SETUP_GUIDE_MAC_TH.md): local index in data/index/ and TYPHOON_API_KEY in .env.
What it is: the frozen pipeline (retrieval variant B, top-5, validator N7/N8, OWASP guards, PII masking) behind one page.
What it is not: a deployed service. It listens on 127.0.0.1 only (there is no option to change that), takes one question at a
time, has no login, and every question is sent to the Typhoon API with the owner's key. The corpus text it shows is for use inside
the team only (decision 0008), so do not expose this port or put it on a public host. For study only: not medical advice.
G2 = B as in demo.py: only metadata is logged (data/index/demo_log/metadata.jsonl), never question or answer text; --no-log switches it off.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import demo  # noqa: E402  (demo.py puts src/ on the path and defines load(), log_metadata(), MESSAGES)

WEB = ROOT / "web"
STATIC = {"/": ("index.html", "text/html; charset=utf-8"), "/style.css": ("style.css", "text/css; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8")}
MAX_QUESTION_CHARS = 1000      # the OWASP input guard refuses longer questions anyway (800)
MAX_BODY_BYTES = 8192
EVIDENCE_CHARS = 2400
LOCAL_HOSTS = {"127.0.0.1", "localhost"}

STATE: dict = {"ready": False, "error": None, "pipe": None, "units": None, "args": None}
ASK_LOCK = threading.Lock()     # one question at a time: the models and the LLM client are shared


def load_in_background(args) -> None:
    try:
        STATE["pipe"], STATE["units"] = demo.load(args)
        STATE["ready"] = True
    except Exception:           # shown in the terminal; the page only gets a generic message (no paths or keys)
        traceback.print_exc()
        STATE["error"] = "โหลดระบบไม่สำเร็จ ดูข้อความใน terminal (ตรวจดัชนีใน data/index/ และ TYPHOON_API_KEY ใน .env)"


def build_payload(result: dict, units: dict) -> dict:
    t = result["trace"]
    status = result["status"]
    payload = {"status": status, "answer": None, "citations": [], "dropped": len(t.get("dropped_claims") or []),
               "masked": t.get("pii_masked") or [], "tokens": (t.get("usage") or {}).get("total_tokens"), "cached": t.get("cached"),
               "message": None, "disclaimer": demo.DISCLAIMER}
    if status == "answered":
        payload["answer"] = result["answer"]
        for c in result["citations"]:
            unit = units.get(c["chunk_id"]) or {}
            payload["citations"].append({"id": c["id"], "document_id": c["document_id"], "edition_id": c["edition_id"], "pages": c["pdf_pages"],
                                         "section": unit.get("section_path"), "text": (unit.get("text") or "")[:EVIDENCE_CHARS]})
    elif status == "refused_input":
        payload["message"] = (t.get("guard") or {}).get("message") or demo.MESSAGES["refused_input"]
    else:
        payload["message"] = demo.MESSAGES.get(status, status)
    return payload


def ask(question: str) -> dict:
    with ASK_LOCK:
        result = STATE["pipe"].answer(question)
    if not STATE["args"].no_log:
        demo.log_metadata(result, STATE["args"])
    return build_payload(result, STATE["units"])


class Handler(BaseHTTPRequestHandler):
    server_version = "ncd-demo"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *a):      # never log request bodies or paths with text
        sys.stderr.write("%s %s\n" % (self.command, urlsplit(self.path).path))

    def _local_only(self) -> bool:
        """Refuse DNS-rebinding and cross-site calls: any web page could otherwise POST to localhost and spend the owner's API quota."""
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]")
        if host not in LOCAL_HOSTS:
            return False
        origin = self.headers.get("Origin")
        return origin is None or (urlsplit(origin).hostname in LOCAL_HOSTS and urlsplit(origin).port == self.server.server_port)

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
                                                    "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj: dict) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        if not self._local_only():
            return self._json(403, {"error": "local only"})
        path = urlsplit(self.path).path
        if path == "/api/health":
            return self._json(200, {"ready": STATE["ready"], "error": STATE["error"]})
        if path in STATIC:
            name, ctype = STATIC[path]
            return self._send(200, (WEB / name).read_bytes(), ctype)
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if not self._local_only():
            return self._json(403, {"error": "local only"})
        if urlsplit(self.path).path != "/api/ask":
            return self._json(404, {"error": "not found"})
        if (self.headers.get("Content-Type") or "").split(";")[0].strip() != "application/json":
            return self._json(415, {"error": "JSON only"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._json(400, {"error": "bad length"})
        if n <= 0 or n > MAX_BODY_BYTES:
            return self._json(413, {"error": "body size"})
        try:
            question = json.loads(self.rfile.read(n).decode("utf-8")).get("question")
        except (ValueError, AttributeError, UnicodeDecodeError):
            return self._json(400, {"error": "bad JSON"})
        if not isinstance(question, str) or not question.strip():
            return self._json(400, {"error": "ใส่คำถามก่อน"})
        if len(question) > MAX_QUESTION_CHARS:
            return self._json(400, {"error": f"คำถามยาวเกิน {MAX_QUESTION_CHARS} ตัวอักษร"})
        if STATE["error"] or not STATE["ready"]:
            return self._json(503, {"error": STATE["error"] or "ระบบกำลังโหลดโมเดล รอสักครู่"})
        try:
            self._json(200, ask(question.strip()))
        except Exception:
            traceback.print_exc()
            self._json(500, {"error": "ตอบไม่สำเร็จ ดูข้อความใน terminal"})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-log", action="store_true", help="do not write the metadata log (G2 = B)")
    a = ap.parse_args()
    # the frozen demo settings: variant B, plain (non-graph) pipeline, all guards on
    STATE["args"] = SimpleNamespace(variant="B", graph=False, no_guard=False, no_log=a.no_log, show_evidence=False)
    threading.Thread(target=load_in_background, args=(STATE["args"],), daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"เปิดที่ http://127.0.0.1:{a.port}  (โหลดโมเดลประมาณ 20 วินาที; หยุดด้วย Ctrl+C)\n{demo.DISCLAIMER}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
