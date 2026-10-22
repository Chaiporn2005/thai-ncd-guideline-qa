// The demo page: ask a question, show the cited answer (or the refusal / abstention), the path it took, and the evidence.
// Talks only to the local demo.py server (/api/showcase, /api/ask). Nothing is stored in the browser: the thread lives in memory until reload.
import { owl, logoMark } from "./owl.js";
import { traceHTML } from "./trace.js";

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
let inflight = null;                // AbortController of the question being answered

// Settings: kept in this browser only (a convenience, not data); the page works the same without storage.
const store = { get(k) { try { return localStorage.getItem("ncd-demo:" + k); } catch { return null; } },
                set(k, v) { try { localStorage.setItem("ncd-demo:" + k, v); } catch {} } };
const radio = (name) => document.querySelector(`input[name="${name}"]:checked`).value;

/* ---------- start ---------- */
$("logo-slot").innerHTML = logoMark();
$("welcome-owl").innerHTML = owl("hello", { live: true });
$("how-trace").innerHTML = traceHTML(null, "how");
followPointer($("welcome-owl"));
restoreSettings();
loadSamples();

/* ---------- samples: suggested questions for everyone, the test set for testers and the presentation ---------- */
async function loadSamples() {
  try {
    const list = await (await fetch("/api/showcase")).json();
    const sample = (s, showExpect) => `<li><button type="button" class="sample" data-q="${esc(s.question)}">
        <span class="sample__q">${esc(s.question)}</span>${showExpect ? `<span class="sample__expect">ควรเห็น: ${esc(s.expect)}</span>` : ""}
      </button></li>`;
    const suggest = list.filter((s) => s.kind !== "test");
    const groups = [];
    list.filter((s) => s.kind === "test").forEach((s) => {
      let g = groups.find((x) => x.name === s.group);
      if (!g) groups.push((g = { name: s.group, items: [] }));
      g.items.push(s);
    });
    const suggestHTML = `<div class="samples__group samples__group--wide"><ul>${suggest.map((s) => sample(s, false)).join("")}</ul></div>`;
    $("sample-groups").innerHTML = suggestHTML;
    $("sheet-suggest").innerHTML = suggestHTML;
    $("sheet-test").innerHTML = groups.map((g) => `<div class="samples__group"><h3>${esc(g.name)}</h3><ul>${g.items.map((s) => sample(s, true)).join("")}</ul></div>`).join("");
  } catch {
    $("sample-groups").innerHTML = `<p class="samples__loading">โหลดคำถามแนะนำไม่สำเร็จ ยังพิมพ์คำถามเองได้ตามปกติ</p>`;
  }
}
// tabs in the samples sheet (arrow keys move between them)
const tabs = [$("tab-suggest"), $("tab-test")];
function selectTab(t) {
  tabs.forEach((x) => { const on = x === t; x.setAttribute("aria-selected", on); x.tabIndex = on ? 0 : -1; $(x.getAttribute("aria-controls")).hidden = !on; });
  t.focus({ preventScroll: true });
}
tabs.forEach((t, i) => {
  t.addEventListener("click", () => selectTab(t));
  t.addEventListener("keydown", (e) => { if (e.key === "ArrowRight" || e.key === "ArrowLeft") selectTab(tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length]); });
});
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
input.addEventListener("input", () => { autosize(); if (!busy) $("send").disabled = !input.value.trim(); });
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
$("open-settings").addEventListener("click", () => $("settings").showModal());
$("settings").addEventListener("change", saveSettings);
$("stop").addEventListener("click", () => inflight?.abort());

function restoreSettings() {
  for (const name of ["mode", "variant"]) {
    const v = store.get(name), el = v && document.querySelector(`input[name="${name}"][value="${CSS.escape(v)}"]`);
    if (el) el.checked = true;
  }
  $("show-details").checked = store.get("details") === "1";
  summarize();
}
function saveSettings() {
  store.set("mode", radio("mode")); store.set("variant", radio("variant")); store.set("details", $("show-details").checked ? "1" : "0");
  summarize();
}
function summarize() {
  const m = radio("mode"), v = radio("variant");
  $("settings-summary").textContent = `${MODE[m]} · ${VARIANT[v]}`;
  $("open-settings").classList.toggle("is-changed", m !== "fixed" || v !== "B");
}
document.querySelectorAll("dialog").forEach((d) => {
  d.addEventListener("click", (e) => { if (e.target === d || e.target.closest("[data-close]")) d.close(); });
});
$("reset").addEventListener("click", () => {
  $("thread").innerHTML = "";
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
  const mode = radio("mode"), variant = radio("variant");
  const id = ++turnId;

  const turn = document.createElement("li");
  turn.className = "turn";
  turn.innerHTML = `
    <div class="ask"><p class="ask__text">${esc(question)}</p></div>
    <article class="reply reply--pending" aria-busy="true">
      <div class="reply__avatar">${owl("think", { live: true })}</div>
      <div class="reply__body">
        <p class="pending"><span>กำลังค้นหลักฐานและเรียบเรียงคำตอบ</span> <span class="pending__time" data-t>0.0 วินาที</span></p>
        <p class="pending__note">${esc(MODE[mode])} · ${esc(VARIANT[variant])}${variant === "C" ? " · reranker บน CPU ช้า (ครั้งแรกราว 3 นาที)" : mode === "react" ? " · agent ค้นเองหลายรอบ" : ""}</p>
      </div>
    </article>`;
  $("thread").append(turn);
  turn.scrollIntoView({ behavior: reduced.matches ? "auto" : "smooth", block: "start" });

  const t0 = performance.now();
  const tick = setInterval(() => { turn.querySelector("[data-t]").textContent = ((performance.now() - t0) / 1000).toFixed(1) + " วินาที"; }, 100);
  let data;
  inflight = new AbortController();
  try {
    const r = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question, mode, variant }), signal: inflight.signal });
    data = await r.json();
  } catch (err) {
    data = { error: err.name === "AbortError" ? "aborted" : "network" };
  }
  inflight = null;
  clearInterval(tick);
  const reply = turn.querySelector(".reply");
  reply.outerHTML = data.error ? renderError(data, question) : renderReply(data, id);
  const placed = turn.querySelector(".reply");
  if (!data.error) {
    placed.querySelector(".reply__avatar svg")?.classList.add("owl--arrive");   // the owl hops once: the answer is here
  }
  busy = false;
  setBusy(false);
  $("send").disabled = !input.value.trim();
  input.focus({ preventScroll: true });
}

function setBusy(on) {
  $("send").hidden = on;           // while answering, the button becomes "cancel"
  $("stop").hidden = !on;
  $("send").disabled = on;
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
    body += `<ul class="claims">${claims.map((c, k) => `<li style="--i:${k}">${esc(c.text)} ${(c.cite || []).map((sid) => citeChip(sid, pages[sid], id)).join("")}</li>`).join("")}</ul>`;
    body += `<div class="sources"><h3>แหล่งอ้างอิง</h3><ul>${(d.citations || []).map((c) => `
      <li data-src="${id}-${esc(c.id)}"><span class="sid">${esc(c.id)}</span> <span class="doc">${esc(c.document_id)}</span>
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
        ${d.status === "answered" ? `<button type="button" class="copy" data-copy="${id}"><span class="copy__label">คัดลอกคำตอบ</span></button>` : ""}
      </header>
      ${body}
      <details class="tech"${$("show-details").checked ? " open" : ""}>
        <summary>ดูว่าระบบตอบอย่างไร <span class="tech__meta">${meta.map(esc).join(" · ")}</span></summary>
        <section class="path" aria-label="เส้นทางของคำถามนี้">
          <h3>เส้นทางของคำถามนี้${d.path?.length ? ` <span class="path__nodes">${esc(d.path.join(" › "))}</span>` : ""}</h3>
          ${traceHTML(d, "t" + id)}
        </section>
        ${evidenceBlock(d, id)}
      </details>
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
  if (d.error === "aborted") return `<article class="reply reply--warn">
    <div class="reply__avatar">${owl("unsure")}</div>
    <div class="reply__body">
      <p class="status status--warn"><span class="status__icon" aria-hidden="true">–</span>ยกเลิกแล้ว</p>
      <p class="tip">ถ้าเครื่องยังประมวลผลคำถามนี้อยู่ คำถามถัดไปจะเริ่มเมื่อคำถามนี้เสร็จ</p>
      <button type="button" class="chip-btn" data-retry="${esc(question)}">ถามอีกครั้ง</button>
    </div>
  </article>`;
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
    for (let p = ev.parentElement; p; p = p.parentElement) if (p.tagName === "DETAILS") p.open = true;
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

/* ---------- motion: the path replay and the owl ---------- */
document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-replay]");
  if (!b) return;
  const t = document.getElementById(b.dataset.replay);
  t.classList.remove("is-playing");
  void t.offsetWidth;                 // restart the CSS animation
  t.classList.add("is-playing");
});

// Hovering or focusing a citation chip lights the matching row in the source list.
const srcFor = (chip) => document.querySelector(`[data-src="${chip.dataset.ev.replace(/^ev-/, "")}"]`);
for (const [on, off] of [["pointerover", "pointerout"], ["focusin", "focusout"]]) {
  document.addEventListener(on, (e) => { const c = e.target.closest?.(".cite"); if (c) srcFor(c)?.classList.add("is-lit"); });
  document.addEventListener(off, (e) => { const c = e.target.closest?.(".cite"); if (c) srcFor(c)?.classList.remove("is-lit"); });
}

// The welcome owl looks at the pointer: pupils move at most 3 units inside the eye. Off for reduced motion and touch-only screens.
function followPointer(host) {
  if (reduced.matches || !matchMedia("(hover: hover)").matches) return;
  let raf = 0, px = 0, py = 0;
  addEventListener("pointermove", (e) => {
    px = e.clientX; py = e.clientY;
    if (raf) return;
    raf = requestAnimationFrame(() => {
      raf = 0;
      const r = host.getBoundingClientRect();
      const dx = px - (r.left + r.width / 2), dy = py - (r.top + r.height * 0.42);
      const len = Math.hypot(dx, dy) || 1, k = Math.min(1, len / 240);
      host.style.setProperty("--look-x", ((dx / len) * 3 * k).toFixed(2) + "px");
      host.style.setProperty("--look-y", ((dy / len) * 2.4 * k).toFixed(2) + "px");
    });
  }, { passive: true });
}

// opening "how the system answered" replays the path, so the animation is seen when the panel is
document.addEventListener("toggle", (e) => {
  if (!e.target.matches?.("details.tech") || !e.target.open) return;
  const t = e.target.querySelector(".trace");
  t.classList.remove("is-playing"); void t.offsetWidth; t.classList.add("is-playing");
}, true);

// copy the answer as plain text with its sources (the label change is the feedback: no toast)
document.addEventListener("click", async (e) => {
  const b = e.target.closest("[data-copy]");
  if (!b) return;
  const card = b.closest(".reply__body");
  const claims = [...card.querySelectorAll(".claims li")].map((li) => "• " + li.textContent.replace(/\s+/g, " ").trim());
  const srcs = [...card.querySelectorAll(".sources li")].map((li) => li.textContent.replace(/\s+/g, " ").trim());
  try {
    await navigator.clipboard.writeText([...claims, "", "แหล่งอ้างอิง", ...srcs].join("\n"));
    b.dataset.state = "done"; b.querySelector(".copy__label").textContent = "คัดลอกแล้ว";
  } catch {
    b.dataset.state = "error"; b.querySelector(".copy__label").textContent = "คัดลอกไม่ได้";
  }
  setTimeout(() => { delete b.dataset.state; b.querySelector(".copy__label").textContent = "คัดลอกคำตอบ"; }, 2500);
});
