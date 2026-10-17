// The path one question took through the system (diagram-design: flowchart, single policy-evaluation trace).
// Built as HTML, not SVG: Thai glyph widths vary, so text must wrap inside its box instead of sitting at fixed coordinates.
// Five ordered stages + one outcome. Each stage reads ✓ ผ่าน · ✕ หยุดที่นี่ · ไม่ถึง in words, so the state never rests on colour alone.
// Accent goes on at most two elements: the stage that decided, and the outcome. Layout (row / column) follows the container width (app.css).

const STAGES = ["ตรวจคำถาม", "ค้นหลักฐาน", "โมเดลตอบ", "ตรวจทุกข้อ", "ตรวจคำตอบ"];

const STOP_AT = {   // status -> index of the stage that ended the run (5 = none: every stage passed)
  refused_input: 0, abstained_no_evidence: 1, abstained_model: 2, parse_error: 2, truncated: 2, llm_error: 2,
  abstained_validator: 3, blocked_output: 4, answered: 5,
};
const GUARD = { individual_directive: "ขอยารายบุคคล", emergency: "ฉุกเฉิน → 1669", injection_pattern: "คำสั่งแฝง", input_too_long: "ยาวเกินกำหนด" };
const MASK = { phone: "เบอร์", name: "ชื่อ", national_id: "เลขบัตร", email: "อีเมล", hn: "HN" };
const OUTCOME = {
  answered: "ตอบ + อ้างอิง", refused_input: "ปฏิเสธ", abstained_no_evidence: "งดตอบ", abstained_model: "งดตอบ",
  abstained_validator: "งดตอบ", blocked_output: "ระงับคำตอบ", parse_error: "ผิดพลาด", truncated: "ผิดพลาด", llm_error: "ผิดพลาด",
};
const WORD = { pass: ["✓", "ผ่าน"], stop: ["✕", "หยุดที่นี่"], skip: ["–", "ไม่ถึง"], idle: ["", ""] };

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const num = (n) => new Intl.NumberFormat("th-TH").format(n);

function details(d, stop) {
  const g = d.guard?.category;
  return [
    stop === 0 ? GUARD[g] || g || "ถูกกัน" : d.masked?.length ? "ปิดบัง " + d.masked.map((m) => MASK[m] || m).join(", ") : "ปกติ",
    stop === 1 ? "ไม่พบเอกสาร" : d.mode === "react" ? `ค้นเอง ${d.tool_steps ?? "?"} ครั้ง` : `top-5 · ${d.variant || "B"}`,
    { abstained_model: "โมเดลงดตอบ", parse_error: "รูปแบบผิด", truncated: "ยาวจนถูกตัด", llm_error: "เรียกไม่ได้" }[d.status]
      || (d.tokens ? `${num(d.tokens)} token${d.cached ? " · แคช" : ""}` : ""),
    stop === 3 ? "ไม่ผ่านทุกข้อ" : d.dropped?.length ? `ตัดทิ้ง ${d.dropped.length} ข้อ` : "ผ่านทุกข้อ",
    stop === 4 ? d.output_guard?.category || "ไม่ปลอดภัย" : "ปลอดภัย",
  ];
}

// d: the /api/ask response, or null for the idle diagram in the "how it works" dialog.
export function traceHTML(d, uid) {
  const stop = d ? STOP_AT[d.status] ?? 2 : null;
  const text = d ? details(d, stop) : STAGES.map(() => "");
  const state = (i) => (stop === null ? "idle" : i < stop ? "pass" : i === stop ? "stop" : "skip");
  const outcome = d ? OUTCOME[d.status] || d.status : "ผลลัพธ์";
  const summary = !d ? "ห้าขั้นที่ทุกคำถามต้องผ่าน: " + STAGES.join(" → ")
    : stop === 5 ? "ผ่านทั้งห้าขั้น จึงแสดงคำตอบพร้อมแหล่งอ้างอิง"
    : `ผ่าน ${stop} ขั้นแรก แล้วหยุดที่ขั้น${STAGES[stop]} ผลคือ${outcome}`;

  const steps = STAGES.map((name, i) => {
    const st = state(i);
    const [icon, word] = WORD[st];
    return `<li class="step step--${st}" style="--i:${i}">
      <span class="step__no" aria-hidden="true">${i + 1}</span>
      <span class="step__name">${esc(name)}</span>
      ${word ? `<span class="step__word"><span aria-hidden="true">${icon}</span> ${word}</span>` : ""}
      ${st !== "skip" && text[i] ? `<span class="step__detail">${esc(text[i])}</span>` : ""}
    </li>`;
  }).join("");
  const outAt = stop === null ? 5 : Math.min(stop, 4) + 1;   // in the replay the outcome lights right after the deciding stage

  return `<div class="trace${d ? " is-playing" : " trace--idle"}" id="trace-${esc(uid)}">
    <p class="sr-only">${esc(summary)}</p>
    <ol class="trace__steps" aria-hidden="true">
      ${steps}
      <li class="step step--out ${d ? "step--stop" : "step--idle"}" style="--i:${outAt}"><span class="step__name">${esc(outcome)}</span></li>
    </ol>
    ${d ? `<div class="trace__foot">
      <p class="trace__legend"><span class="lg lg--pass">✓ ผ่าน</span><span class="lg lg--stop">✕ หยุดที่นี่ = ขั้นที่ตัดสินผล</span><span class="lg lg--skip">– ไม่ถึง = ไม่ได้ทำขั้นนั้น</span></p>
      <button type="button" class="trace__replay" data-replay="trace-${esc(uid)}"><span aria-hidden="true">↻</span> เล่นซ้ำ</button>
    </div>` : ""}
  </div>`;
}
