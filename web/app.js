"use strict";
/* Front end of the local demo. All text from the server (answer, evidence, document ids) is inserted with textContent, never as HTML.
   Motion follows Apple's fluid-interface rules: feedback on press (CSS :active), springs instead of fixed-duration animations,
   the source sheet tracks the pointer 1:1, hands the release velocity to a spring and projects momentum to pick where it lands,
   rubber-bands past its top edge, and can be grabbed again in mid-flight (it always restarts from its live position). */

const $ = (id) => document.getElementById(id);
const form = $("form"), input = $("q"), sendBtn = $("send"), chips = [...document.querySelectorAll(".chip")];
const resultEl = $("result"), statusEl = $("status"), statusText = $("statusText"), bar = $("bar");
const sheet = $("sheet"), scrim = $("scrim"), sheetBody = $("sheetBody");
const reduceMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- spring: from the current value, inherits velocity, interruptible ---------- */
function spring({ from, to, velocity = 0, response = 0.4, damping = 1, onUpdate, onDone }) {
  const w = (2 * Math.PI) / response, k = w * w, c = 2 * damping * w;
  let x = from, v = velocity, last = performance.now(), raf = 0, stopped = false;
  const ctl = { get x() { return x; }, get v() { return v; }, stop() { stopped = true; cancelAnimationFrame(raf); } };
  function tick(now) {
    if (stopped) return;
    const dt = Math.min((now - last) / 1000, 1 / 30); last = now;
    const steps = Math.max(1, Math.ceil(dt * 240)), h = dt / steps;
    for (let i = 0; i < steps; i++) { v += (-k * (x - to) - c * v) * h; x += v * h; }
    if (Math.abs(x - to) < 0.2 && Math.abs(v) < 8) { x = to; onUpdate(x); if (onDone) onDone(); return; }
    onUpdate(x);
    raf = requestAnimationFrame(tick);
  }
  raf = requestAnimationFrame(tick);
  return ctl;
}
/* where a release with velocity v (px/s) would come to rest: exponential deceleration, like scroll views */
const project = (v, rate = 0.998) => ((v / 1000) * rate) / (1 - rate);
/* resistance that grows the further past the edge: real things slow down before they stop */
const rubberband = (over, dim, c = 0.55) => (over * dim * c) / (dim + c * Math.abs(over));

/* ---------- status + readiness ---------- */
function setStatus(kind, text) { statusEl.className = "status " + kind; statusText.textContent = text; }
function setEnabled(on) { input.disabled = sendBtn.disabled = !on; chips.forEach((b) => (b.disabled = !on)); }

async function waitUntilReady() {
  for (;;) {
    try {
      const r = await (await fetch("/api/health", { cache: "no-store" })).json();
      if (r.error) { setStatus("error", "โหลดไม่สำเร็จ"); showNotice("โหลดระบบไม่สำเร็จ", r.error, true); return; }
      if (r.ready) { setStatus("ready", "พร้อมใช้งาน"); setEnabled(true); input.focus(); return; }
    } catch (_) { setStatus("error", "ติดต่อเซิร์ฟเวอร์ไม่ได้"); }
    await new Promise((res) => setTimeout(res, 1000));
  }
}

/* ---------- rendering ---------- */
let enterAnim = null;
function mountCard(card) {
  if (enterAnim) enterAnim.stop();
  resultEl.replaceChildren(card);
  if (reduceMotion()) return;
  card.style.opacity = "0";
  enterAnim = spring({ from: 8, to: 0, response: 0.4, damping: 1, onUpdate: (y) => {
    card.style.transform = `translate3d(0,${y}px,0)`; card.style.opacity = String(1 - Math.min(1, Math.max(0, y) / 8));
  }, onDone: () => { card.style.transform = ""; card.style.opacity = ""; } });
}
const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };

function showLoading() {
  const card = el("div", "card");
  card.append(el("p", "phase", "กำลังค้นหาหลักฐานและเรียบเรียงคำตอบ"));
  const sk = el("div", "skeleton"); sk.append(el("i"), el("i"), el("i"));
  card.append(sk);
  mountCard(card);
}
function showNotice(title, message, warn) {
  const card = el("div", "card");
  card.append(el("p", "empty-title", title));
  card.append(el("p", warn ? "note warn" : "note", message));
  mountCard(card);
}

function renderAnswer(data) {
  const byId = new Map(data.citations.map((c) => [c.id, c]));
  const card = el("div", "card");
  card.append(el("h2", null, "คำตอบ"));
  const p = el("p", "answer");
  for (const part of data.answer.split(/(\[S\d+\])/)) {
    const m = /^\[(S\d+)\]$/.exec(part);
    if (m && byId.has(m[1])) {
      const b = el("button", "cite", m[1]); b.type = "button"; b.setAttribute("aria-label", `เปิดแหล่งอ้างอิง ${m[1]}`);
      b.addEventListener("click", () => openSheet(byId.get(m[1]), b));
      p.append(b);
    } else if (part) p.append(document.createTextNode(part));
  }
  card.append(p);

  if (data.citations.length) {
    const box = el("div", "sources");
    for (const c of data.citations) {
      const row = el("button", "src"); row.type = "button";
      const meta = el("span", "meta");
      meta.append(el("span", "doc", c.document_id), el("span", "pg", `หน้า PDF ${c.pages}`));
      row.append(el("span", "badge", c.id), meta, el("span", "chev", "›"));
      row.addEventListener("click", () => openSheet(c, row));
      box.append(row);
    }
    card.append(box);
  }
  appendNotes(card, data);
  mountCard(card);
}

function appendNotes(card, data) {
  if (data.masked && data.masked.length) card.append(el("p", "note", "ระบบปิดบังข้อมูลที่ระบุตัวบุคคลในคำถามก่อนประมวลผล: " + data.masked.join(", ") + " (ข้อมูลสุขภาพส่วนที่เหลือยังอยู่ในคำถาม)"));
  if (data.dropped) card.append(el("p", "note", `ตัดทิ้ง ${data.dropped} ข้อความที่ตรวจหลักฐานไม่ผ่าน (ตัวเลขหรือคำไม่ตรงกับเอกสารที่อ้าง)`));
  const bits = [];
  if (data.tokens != null) bits.push(`${Number(data.tokens).toLocaleString("th-TH")} token`);
  if (data.cached) bits.push("คำตอบจากแคช");
  if (bits.length) card.append(el("p", "meta-line", bits.join(" · ")));
}

function render(data) {
  if (data.status === "answered") return renderAnswer(data);
  const refused = data.status === "refused_input" || data.status === "blocked_output";
  const card = el("div", "card");
  card.append(el("p", "empty-title", refused ? "ระบบไม่ตอบคำถามนี้" : "ยังตอบจากเอกสารไม่ได้"));
  card.append(el("p", refused ? "note warn" : "note", data.message || data.status));
  appendNotes(card, data);
  mountCard(card);
}

/* ---------- asking ---------- */
let inflight = null;
async function ask(question) {
  question = question.trim();
  if (!question) return;
  if (inflight) inflight.abort();           // a new question replaces the old one; never lock the input
  const ctl = inflight = new AbortController();
  showLoading();
  sendBtn.classList.add("busy");
  try {
    const res = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }), signal: ctl.signal });
    const data = await res.json();
    if (ctl !== inflight) return;
    if (!res.ok) return showNotice("ส่งคำถามไม่สำเร็จ", data.error || `ข้อผิดพลาด ${res.status}`, true);
    render(data);
  } catch (e) {
    if (e.name === "AbortError") return;
    showNotice("ส่งคำถามไม่สำเร็จ", "ติดต่อเซิร์ฟเวอร์ไม่ได้ ตรวจว่า app.py ยังรันอยู่", true);
  } finally { if (ctl === inflight) { inflight = null; sendBtn.classList.remove("busy"); } }
}
form.addEventListener("submit", (e) => { e.preventDefault(); ask(input.value); });
input.addEventListener("keydown", (e) => { if (e.key === "Enter" && e.isComposing) e.preventDefault(); });
chips.forEach((b) => b.addEventListener("click", () => { input.value = b.dataset.q; ask(b.dataset.q); }));
addEventListener("scroll", () => bar.classList.toggle("scrolled", scrollY > 4), { passive: true });

/* ---------- source sheet ---------- */
let y = 0, anim = null, drag = null, lastFocus = null, isOpen = false;
const hideDistance = () => sheet.offsetHeight + 48;
const inertTargets = () => document.querySelectorAll(".bar, .page, .foot");
function setY(v) {
  y = v; sheet.style.transform = `translate3d(0,${v}px,0)`;
  scrim.style.opacity = String(1 - Math.min(1, Math.max(0, v / hideDistance())));
}
function stopAnim() { if (anim) { anim.stop(); anim = null; } }

function openSheet(c, trigger) {
  stopAnim();
  $("sheetTitle").textContent = c.document_id;
  $("sheetSub").textContent = [`ฉบับ ${c.edition_id}`, `หน้า PDF ${c.pages}`, Array.isArray(c.section) ? c.section.join(" › ") : c.section].filter(Boolean).join(" · ");
  sheetBody.replaceChildren(el("p", "sheet-note", "ข้อความจากเอกสารที่ส่งให้โมเดลเป็นหลักฐานสำหรับ " + c.id + " (ตัดตามความยาวที่ส่งมา) ใช้ตรวจว่าคำตอบตรงกับเอกสาร ไม่ใช่การรับรองทางคลินิก"), el("p", "evidence", c.text || "(ไม่มีข้อความ)"));
  sheetBody.tabIndex = 0;
  if (!isOpen) { lastFocus = trigger; sheet.hidden = false; scrim.hidden = false; setY(hideDistance()); inertTargets().forEach((n) => (n.inert = true)); }
  isOpen = true;
  sheetBody.scrollTop = 0;
  if (reduceMotion()) setY(0);
  else anim = spring({ from: y, to: 0, response: 0.4, damping: 1, onUpdate: setY, onDone: () => (anim = null) });   // a tap carries no momentum: no bounce
  sheet.focus({ preventScroll: true });
}
function finishClose() {
  anim = null; isOpen = false; sheet.hidden = true; scrim.hidden = true;
  inertTargets().forEach((n) => (n.inert = false));
  if (lastFocus && document.contains(lastFocus)) lastFocus.focus({ preventScroll: true });
}
function closeSheet(velocity = 0) {
  if (!isOpen) return;
  stopAnim();
  if (reduceMotion()) { setY(hideDistance()); return finishClose(); }
  anim = spring({ from: y, to: hideDistance(), velocity, response: 0.35, damping: 1, onUpdate: setY, onDone: finishClose });
}

function onDown(e) {
  if (e.button !== 0 || e.target.closest("#close")) return;
  stopAnim();                                  // grab it mid-flight: continue from where it is on screen
  try { e.currentTarget.setPointerCapture(e.pointerId); } catch (_) { /* not every pointer can be captured; the window listeners below still track it */ }
  drag = { id: e.pointerId, startPointer: e.clientY, startY: y, samples: [{ t: e.timeStamp, y }] };
  addEventListener("pointermove", onMove); addEventListener("pointerup", onUp); addEventListener("pointercancel", onUp);
}
function onMove(e) {
  if (!drag || e.pointerId !== drag.id) return;
  const target = drag.startY + (e.clientY - drag.startPointer);          // respects where it was grabbed
  setY(target < 0 ? -rubberband(-target, 320) : target);
  drag.samples.push({ t: e.timeStamp, y: target });
  while (drag.samples.length > 2 && e.timeStamp - drag.samples[0].t > 100) drag.samples.shift();
}
function onUp(e) {
  if (!drag || e.pointerId !== drag.id) return;
  const s = drag.samples.filter((p) => e.timeStamp - p.t <= 100), a = s[0], b = s[s.length - 1];   // only the last 100 ms before release: pausing before letting go means no throw
  const v = e.type === "pointercancel" || s.length < 2 || b.t === a.t ? 0 : ((b.y - a.y) / (b.t - a.t)) * 1000;     // px/s, finger velocity at release
  drag = null;
  removeEventListener("pointermove", onMove); removeEventListener("pointerup", onUp); removeEventListener("pointercancel", onUp);
  const projected = y + project(v);                                      // where a throw would end up
  if (projected > sheet.offsetHeight * 0.45) return closeSheet(v);
  if (reduceMotion()) return setY(0);
  anim = spring({ from: y, to: 0, velocity: v, response: 0.35, damping: Math.abs(v) > 300 ? 0.8 : 1, onUpdate: setY, onDone: () => (anim = null) });   // bounce only if the gesture carried momentum
}
for (const h of [$("grab"), $("sheetHead")]) h.addEventListener("pointerdown", onDown);
$("close").addEventListener("click", () => closeSheet());
scrim.addEventListener("click", () => closeSheet());
addEventListener("keydown", (e) => { if (e.key === "Escape" && isOpen) closeSheet(); });

setEnabled(false);
waitUntilReady();
