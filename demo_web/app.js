// The demo page: ask a question, show the cited answer (or the refusal / abstention), the path it took, and the evidence.
// Talks only to the local demo.py server (/api/showcase, /api/ask). Nothing is stored in the browser: the thread lives in memory until reload.
import { owl, logoMark } from "./owl.js";
import { traceSVG } from "./trace.js";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const num = (n) => new Intl.NumberFormat("th-TH").format(n);
const reduced = matchMedia("(prefers-reduced-motion: reduce)");

const MODE = { fixed: "pipeline คงที่", graph: "LangGraph", react: "ReAct agent" };
const VARIANT = { A: "A dense", B: "B hybrid", C: "C + rerank" };
const MASK = { phone: "เบอร์โทรศัพท์", name: "ชื่อ-นามสกุล", national_id: "เลขบัตรประชาชน", email: "อีเมล", hn: "เลขผู้ป่วย HN/AN" };
const STATUS = {
  answered:              { mood: "happy",  tone: "ok",   icon: "✓", label: "ตอบพร้อมแหล่งอ้างอิง" },
  abstained_model:       { mood: "unsure", tone: "warn", icon: "?", label: "งดตอบ: หลักฐานไม่พอ" },
  abstained_no_evidence: { mood: "unsure", tone: "warn", icon: "?", label: "งดตอบ: ไม่พบเอกสาร" },
  abstained_validator:   { mood: "unsure", tone: "warn", icon: "?", label: "งดตอบ: ไม่ผ่านการตรวจหลักฐาน" },
  refused_input:         { mood: "stop",   tone: "stop", icon: "✕", label: "ปฏิเสธคำถาม" },
  blocked_output:        { mood: "stop",   tone: "stop", icon: "✕", label: "ระงับคำตอบ" },
  parse_error:           { mood: "unsure", tone: "stop", icon: "!", label: "ผิดพลาด: รูปแบบคำตอบ" },
  truncated:             { mood: "unsure", tone: "stop", icon: "!", label: "ผิดพลาด: คำตอบยาวจนถูกตัด" },
  llm_error:             { mood: "unsure", tone: "stop", icon: "!", label: "ผิดพลาด: เรียกโมเดลไม่ได้" },
};
const REFUSAL = { individual_directive: "ขอสั่งยาหรือวินิจฉัยรายบุคคล", emergency: "อาการฉุกเฉิน", injection_pattern: "รูปแบบคำสั่งแฝง (prompt injection)", input_too_long: "คำถามยาวเกินกำหนด" };
const ABSTAIN_TIP = "ลองระบุโรค ระยะ หรือกลุ่มผู้ป่วยให้ชัดขึ้น เช่น “ผู้ป่วยเบาหวานที่มีโรคไตเรื้อรังระยะ 3”";

let busy = false;
let turnId = 0;
const traces = new Map();          // trace slot element -> response, redrawn when the column width changes

/* ---------- start ---------- */
$("logo-slot").innerHTML = logoMark();
$("welcome-owl").innerHTML = owl("hello", { live: true });
$("how-trace").innerHTML = traceSVG(null, 680, "how");
loadSamples();

/* ---------- samples ---------- */
async function loadSamples() {
  try {
    const list = await (await fetch("/api/showcase")).json();
    const groups = [];
    list.forEach((s, i) => {
      let g = groups.find((x) => x.name === (s.group || "ตัวอย่าง"));
      if (!g) groups.push((g = { name: s.group || "ตัวอย่าง", items: [] }));
      g.items.push({ ...s, i });
    });
    const html = groups.map((g) => `
      <div class="samples__group">
        <h3>${esc(g.name)}</h3>
        <ul>${g.items.map((s) => `
          <li><button type="button" class="sample" data-q="${esc(s.question)}">
            <span class="sample__q">${esc(s.question)}</span>
            <span class="sample__expect">ควรเห็น: ${esc(s.expect)}</span>
          </button></li>`).join("")}</ul>
      </div>`).join("");
    $("sample-groups").innerHTML = html;
    $("sheet-groups").innerHTML = html;
  } catch {
    $("sample-groups").innerHTML = `<p class="samples__loading">โหลดตัวอย่างไม่สำเร็จ ตรวจว่า <code>demo.py --web</code> ยังทำงานอยู่ แล้วโหลดหน้าใหม่</p>`;
  }
}
document.addEventListener("click", (e) => {
  const b = e.target.closest(".sample");
  if (!b || busy) return;
  $("sample-sheet").open && $("sample-sheet").close();
  ask(b.dataset.q);
});

/* ---------- composer ---------- */
const input = $("composer-input");
function autosize() {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 168) + "px";
  input.style.overflowY = input.scrollHeight > 168 ? "auto" : "hidden";
}
input.addEventListener("input", autosize);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    $("composer").requestSubmit();
  }
});
$("composer").addEventListener("submit", (e) => {
  e.preventDefault();
  const q = input.value.trim();
  if (!q || busy) return;
  ask(q);
});

/* ---------- dialogs ---------- */
$("open-how").addEventListener("click", () => $("how").showModal());
$("open-samples").addEventListener("click", () => $("sample-sheet").showModal());
document.querySelectorAll("dialog").forEach((d) => {
  d.addEventListener("click", (e) => { if (e.target === d || e.target.closest("[data-close]")) d.close(); });
});
$("reset").addEventListener("click", () => {
  $("thread").innerHTML = "";
  traces.clear();
  document.body.classList.remove("has-thread");
  $("reset").disabled = true;
  input.focus();
});

/* ---------- ask ---------- */
async function ask(question) {
  busy = true;
  setBusy(true);
  input.value = "";
  autosize();
  document.body.classList.add("has-thread");
  $("reset").disabled = false;
  const mode = $("mode").value, variant = $("variant").value;
  const id = ++turnId;

  const turn = document.createElement("li");
  turn.className = "turn";
  turn.innerHTML = `
    <div class="ask"><p class="ask__text">${esc(question)}</p></div>
    <article class="reply reply--pending" aria-busy="true">
      <div class="reply__avatar">${owl("think", { live: true })}</div>
      <div class="reply__body">
        <p class="pending"><span>กำลังค้นหลักฐานและเรียบเรียงคำตอบ</span> <span class="pending__time" data-t>0.0 วินาที</span></p>
        <p class="pending__note">${mode === "react" ? "ReAct ค้นเองหลายรอบ อาจใช้เวลานานกว่า" : variant === "C" ? "reranker บน CPU อาจใช้ 15–36 วินาที" : "คำถามที่เคยถามแล้วตอบจากแคชทันที"}</p>
      </div>
    </article>`;
  $("thread").append(turn);
  turn.scrollIntoView({ behavior: reduced.matches ? "auto" : "smooth", block: "start" });

  const t0 = performance.now();
  const tick = setInterval(() => { turn.querySelector("[data-t]").textContent = ((performance.now() - t0) / 1000).toFixed(1) + " วินาที"; }, 100);
  let data;
  try {
    const r = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question, mode, variant }) });
    data = await r.json();
  } catch {
    data = { error: "network" };
  }
  clearInterval(tick);
  const reply = turn.querySelector(".reply");
  reply.outerHTML = data.error ? renderError(data, question) : renderReply(data, id);
  const placed = turn.querySelector(".reply");
  if (!data.error) {
    const slot = placed.querySelector(".trace-slot");
    traces.set(slot, data);
    drawTrace(slot);
  }
  busy = false;
  setBusy(false);
  input.focus({ preventScroll: true });
}

function setBusy(on) {
  $("send").disabled = on;
  $("send").classList.toggle("is-loading", on);
  $("send").querySelector(".send__label").textContent = on ? "กำลังตอบ" : "ถาม";
  document.querySelectorAll(".sample").forEach((b) => (b.disabled = on));
}

/* ---------- render ---------- */
function renderReply(d, id) {
  const s = STATUS[d.status] || { mood: "unsure", tone: "warn", icon: "?", label: d.status };
  const emergency = d.status === "refused_input" && d.guard?.category === "emergency";
  const mood = emergency ? "alert" : s.mood;
  const meta = [MODE[d.mode] || d.mode, VARIANT[d.variant] || d.variant,
    d.tokens ? `${num(d.tokens)} token` : null, d.cached ? "จากแคช" : null, d.seconds != null ? `${d.seconds} วินาที` : null].filter(Boolean);

  let body = "";
  if (d.masked?.length) {
    body += `<div class="note note--mask"><p><strong>ปิดบังก่อนประมวลผล:</strong> ${esc(d.masked.map((m) => MASK[m] || m).join(", "))}</p>
      <p class="note__sub">ระบบส่งต่อเป็น: <q>${esc(d.question_shown)}</q></p></div>`;
  }
  if (d.status === "answered") {
    const pages = Object.fromEntries((d.citations || []).map((c) => [c.id, c]));
    const claims = d.claims?.length ? d.claims : [{ text: d.answer, cite: [] }];
    body += `<ul class="claims">${claims.map((c) => `<li>${esc(c.text)} ${(c.cite || []).map((sid) => citeChip(sid, pages[sid], id)).join("")}</li>`).join("")}</ul>`;
    body += `<div class="sources"><h3>แหล่งอ้างอิง</h3><ul>${(d.citations || []).map((c) => `
      <li><span class="sid">${esc(c.id)}</span> <span class="doc">${esc(c.document_id)}</span>
      <span class="pg">${c.edition_id && c.edition_id !== c.document_id ? `ฉบับ ${esc(c.edition_id)} · ` : ""}หน้า PDF ${esc(dash(c.pdf_pages))}</span></li>`).join("")}</ul></div>`;
  } else if (emergency) {
    body += `<div class="note note--alert"><p class="call">โทร <a href="tel:1669">1669</a></p><p>${esc(d.guard.message)}</p></div>`;
  } else if (d.status === "refused_input") {
    body += `<p class="reason"><strong>เหตุผล:</strong> ${esc(REFUSAL[d.guard?.category] || d.guard?.category || "ตัวกรองอินพุต")}</p><p>${esc(d.guard?.message || d.message)}</p>`;
  } else if (d.status === "blocked_output") {
    body += `<p>${esc(d.output_guard?.message || d.message)}</p>`;
  } else {
    body += `<p>${esc(d.message || d.status)}</p>${d.status.startsWith("abstained") ? `<p class="tip">${esc(ABSTAIN_TIP)}</p>` : ""}`;
  }
  if (d.dropped?.length) {
    body += `<details class="dropped"><summary>ตัดทิ้ง ${d.dropped.length} ข้อที่ตรวจหลักฐานไม่ผ่าน</summary><ul>${d.dropped.map((r) => `<li>${esc(dropReason(r))}</li>`).join("")}</ul></details>`;
  }
  const flagged = (d.evidence || []).filter((e) => e.flagged).length;
  if (flagged) body += `<p class="tip">หลักฐาน ${flagged} ชิ้นมีข้อความคล้ายคำสั่งแฝง ระบบบันทึกธงไว้และไม่ทำตาม</p>`;

  return `<article class="reply reply--${s.tone}" aria-labelledby="st-${id}">
    <div class="reply__avatar">${owl(mood)}</div>
    <div class="reply__body">
      <header class="reply__head">
        <p class="status status--${s.tone}" id="st-${id}"><span class="status__icon" aria-hidden="true">${s.icon}</span>${esc(emergency ? "อาการฉุกเฉิน: แนะนำโทร 1669" : s.label)}</p>
        <p class="meta">${meta.map(esc).join(" · ")}</p>
      </header>
      ${body}
      <section class="path" aria-label="เส้นทางของคำถามนี้">
        <h3>เส้นทางของคำถามนี้${d.path?.length ? ` <span class="path__nodes">${esc(d.path.join(" › "))}</span>` : ""}</h3>
        <div class="trace-slot" data-uid="t${id}"></div>
      </section>
      ${evidenceBlock(d, id)}
    </div>
  </article>`;
}

function citeChip(sid, c, id) {
  const pg = c ? ` · น.${dash(c.pdf_pages)}` : "";
  return `<button type="button" class="cite" data-ev="ev-${id}-${esc(sid)}" aria-label="ดูหลักฐาน ${esc(sid)}${esc(pg)}">${esc(sid)}${esc(pg)}</button>`;
}

function evidenceBlock(d, id) {
  if (!d.evidence?.length) return "";
  return `<details class="evidence" id="evd-${id}">
    <summary>หลักฐาน ${d.evidence.length} ชิ้นที่ส่งให้โมเดล${d.status === "answered" ? ` <span class="evidence__count">(อ้างในคำตอบ ${d.evidence.filter((e) => e.cited).length} ชิ้น)</span>` : ""}</summary>
    <ol>${d.evidence.map((e) => `
      <li class="ev${e.cited ? " ev--cited" : ""}" id="ev-${id}-${esc(e.id)}" tabindex="-1">
        <p class="ev__head"><span class="sid">${esc(e.id)}</span> <span class="doc">${esc(e.document)}</span> · หน้า ${esc(dash(e.pages))}
          ${e.score != null ? `<span class="ev__score">คะแนนค้น ${Number(e.score).toFixed(3)}</span>` : ""}
          ${e.cited ? `<span class="ev__tag">อ้างในคำตอบ</span>` : ""}${e.flagged ? `<span class="ev__tag ev__tag--flag">มีธงคำสั่งแฝง</span>` : ""}</p>
        <p class="ev__text">${esc(e.text)}…</p>
      </li>`).join("")}</ol>
  </details>`;
}

function renderError(d, question) {
  return `<article class="reply reply--stop">
    <div class="reply__avatar">${owl("unsure")}</div>
    <div class="reply__body">
      <p class="status status--stop"><span class="status__icon" aria-hidden="true">!</span>เรียกระบบไม่สำเร็จ</p>
      <p>${d.error === "network" ? "หน้าเว็บติดต่อ demo.py ไม่ได้ ตรวจว่าหน้าต่างที่รัน <code>python -X utf8 demo.py --web</code> ยังเปิดอยู่" : esc(d.error)}</p>
      <button type="button" class="chip-btn" data-retry="${esc(question)}">ถามอีกครั้ง</button>
    </div>
  </article>`;
}
document.addEventListener("click", (e) => {
  const r = e.target.closest("[data-retry]");
  if (r && !busy) { r.closest(".turn").remove(); ask(r.dataset.retry); }
  const c = e.target.closest(".cite");
  if (c) {
    const ev = document.getElementById(c.dataset.ev);
    if (!ev) return;
    ev.closest("details").open = true;
    document.querySelectorAll(".ev--focus").forEach((x) => x.classList.remove("ev--focus"));
    ev.classList.add("ev--focus");
    ev.scrollIntoView({ behavior: reduced.matches ? "auto" : "smooth", block: "center" });
    ev.focus({ preventScroll: true });
  }
});

function dropReason(r) {
  const list = (s) => s.replace(/^[^:]*:\s*/, "").replace(/[[\]']/g, "");
  if (r.startsWith("word not in cited evidence")) return "มีคำที่ไม่อยู่ในหลักฐานที่อ้าง: " + list(r);
  if (r.startsWith("number not in cited evidence")) return "มีตัวเลขที่ไม่อยู่ในหลักฐานที่อ้าง: " + list(r);
  if (r.startsWith("citation not in the evidence sent")) return "อ้างหลักฐานที่ไม่ได้ส่งให้โมเดล: " + list(r);
  if (r.startsWith("group named in the question")) return "กลุ่มประชากรในคำถามไม่อยู่ในหลักฐาน: " + list(r);
  return { "no citation": "ไม่มีการอ้างอิง", "empty claim": "ข้อความว่าง", "denial next to answering claims": "ข้อความปฏิเสธที่ขัดกับข้อที่ตอบ" }[r] || r;
}
const dash = (p) => String(p ?? "").replace(/^(\d+)-(\d+)$/, (m, a, b) => (a === b ? a : `${a}–${b}`));

/* ---------- trace drawing: horizontal on wide columns, vertical on narrow ---------- */
function drawTrace(slot) {
  const d = traces.get(slot);
  if (d) slot.innerHTML = traceSVG(d, slot.clientWidth, slot.dataset.uid);
}
const ro = new ResizeObserver((entries) => {
  for (const e of entries) {
    const slot = e.target;
    const v = slot.clientWidth < 600 ? "v" : "h";
    if (slot.dataset.layout !== v) { slot.dataset.layout = v; drawTrace(slot); }
  }
});
new MutationObserver(() => document.querySelectorAll(".trace-slot:not([data-watched])").forEach((s) => { s.dataset.watched = "1"; ro.observe(s); }))
  .observe($("thread"), { childList: true, subtree: true });
