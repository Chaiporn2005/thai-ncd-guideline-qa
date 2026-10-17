// The path one question took through the system, drawn as inline SVG (diagram-design: flowchart, single policy-evaluation trace).
// Five ordered stages + one outcome. Each stage reads ✓ ผ่าน · ✕ หยุดที่นี่ · ไม่ถึง in words, so the state never rests on colour alone.
// Accent goes on at most two elements: the stage that decided, and the outcome. Colours come from tokens.css (the page's own skin).

const STAGES = [
  { key: "input",    name: "ตรวจคำถาม" },
  { key: "retrieve", name: "ค้นหลักฐาน" },
  { key: "llm",      name: "โมเดลตอบ" },
  { key: "validate", name: "ตรวจทุกข้อ" },
  { key: "output",   name: "ตรวจคำตอบ" },
];

const STOP_AT = {   // status -> index of the stage that ended the run (5 = none: every stage passed)
  refused_input: 0, abstained_no_evidence: 1, abstained_model: 2, parse_error: 2, truncated: 2, llm_error: 2,
  abstained_validator: 3, blocked_output: 4, answered: 5,
};

const GUARD = {
  individual_directive: "ขอสั่งยา/วินิจฉัยรายบุคคล", emergency: "อาการฉุกเฉิน → 1669", injection_pattern: "รูปแบบคำสั่งแฝง",
  input_too_long: "ยาวเกินกำหนด",
};
const MASK = { phone: "เบอร์โทร", name: "ชื่อ", national_id: "เลขบัตร", email: "อีเมล", hn: "HN" };
const OUTCOME = {
  answered: "ตอบ + อ้างอิง", refused_input: "ปฏิเสธ", abstained_no_evidence: "งดตอบ", abstained_model: "งดตอบ",
  abstained_validator: "งดตอบ", blocked_output: "ระงับคำตอบ", parse_error: "ผิดพลาด", truncated: "ผิดพลาด", llm_error: "ผิดพลาด",
};

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const num = (n) => (n == null ? "" : new Intl.NumberFormat("th-TH").format(n));

function details(d) {
  const stop = STOP_AT[d.status] ?? 2;
  const g = d.guard?.category;
  const out = [];
  out[0] = stop === 0 ? GUARD[g] || g || "ถูกกัน" : d.masked?.length ? "ปิดบัง: " + d.masked.map((m) => MASK[m] || m).join(", ") : "ปกติ";
  out[1] = stop === 1 ? "ไม่พบเอกสาร" : d.mode === "react" ? `agent ค้นเอง ${d.tool_steps ?? "?"} ครั้ง` : `top-5 · ${d.variant || "B"}`;
  out[2] = { abstained_model: "โมเดลงดตอบ", parse_error: "รูปแบบผิด", truncated: "ยาวจนถูกตัด", llm_error: "เรียกโมเดลไม่ได้" }[d.status]
        || (d.tokens ? `${num(d.tokens)} token${d.cached ? " · แคช" : ""}` : "");
  out[3] = stop === 3 ? "ไม่ผ่านทุกข้อ" : d.dropped?.length ? `ตัดทิ้ง ${d.dropped.length} ข้อ` : "ผ่านทุกข้อ";
  out[4] = stop === 4 ? (d.output_guard?.category || "ไม่ปลอดภัย") : "ปลอดภัย";
  return { stop, text: out };
}

function stateOf(i, stop) {
  if (stop === null) return "idle";
  if (i < stop) return "pass";
  return i === stop ? "stop" : "skip";
}

const WORD = { pass: "✓ ผ่าน", stop: "✕ หยุดที่นี่", skip: "ไม่ถึง", idle: "" };

// d: the /api/ask response, or null for the idle diagram in the "how it works" dialog. width: the container's width in CSS px.
export function traceSVG(d, width, uid) {
  const info = d ? details(d) : { stop: null, text: STAGES.map(() => "") };    // the dialog explains each stage in its own list
  const outcomeText = d ? OUTCOME[d.status] || d.status : "ผลลัพธ์";
  const vertical = width < 600;
  const id = `trace-${uid}`;
  const desc = d
    ? (info.stop === 5 ? "คำถามผ่านทั้งห้าขั้น จึงแสดงคำตอบพร้อมแหล่งอ้างอิง"
      : `คำถามผ่าน ${info.stop} ขั้นแรก แล้วหยุดที่ขั้น${STAGES[info.stop].name} ผลคือ${outcomeText}`)
    : "ห้าขั้นที่ทุกคำถามต้องผ่านก่อนจะได้คำตอบ: ตรวจคำถาม ค้นหลักฐาน โมเดลตอบ ตรวจทุกข้อ และตรวจคำตอบ";
  const nodes = [];
  const lines = [];
  const geo = vertical ? verticalGeo() : horizontalGeo();

  STAGES.forEach((s, i) => {
    const st = stateOf(i, info.stop);
    nodes.push(geo.node(i, s.name, WORD[st], st === "skip" ? "" : info.text[i], st));   // a stage that never ran has nothing to report
    const next = i + 1;
    const nextState = next < 5 ? stateOf(next, info.stop) : info.stop === null ? "idle" : info.stop === 5 ? "pass" : "skip";
    lines.push(geo.link(i, nextState === "skip" ? "skip" : "on", id));
  });
  const outState = info.stop === null ? "idle" : "stop";
  nodes.push(geo.outcome(outcomeText, outState, d?.status));

  return `<svg class="trace trace--${vertical ? "v" : "h"}" viewBox="0 0 ${geo.w} ${geo.h}" role="img" aria-labelledby="${id}-title ${id}-desc" focusable="false">
    <title id="${id}-title">เส้นทางของคำถามผ่านระบบ</title>
    <desc id="${id}-desc">${esc(desc)}</desc>
    <defs>
      <marker id="${id}-arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" class="trace__head"/></marker>
      <marker id="${id}-arrow-skip" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" class="trace__head trace__head--skip"/></marker>
    </defs>
    ${lines.join("")}
    ${nodes.join("")}
    ${geo.legend(info.stop === null)}
  </svg>`;
}

function horizontalGeo() {
  const W = 100, H = 76, Y = 8, GAP = 16, X0 = 4, OW = 92;
  const x = (i) => X0 + i * (W + GAP);
  return {
    w: x(5) + OW + 4, h: 162,
    node: (i, name, word, detail, st) => `
      <g class="trace__node trace__node--${st}">
        <rect x="${x(i)}" y="${Y}" width="${W}" height="${H}" rx="8" class="trace__mask"/>
        <rect x="${x(i)}" y="${Y}" width="${W}" height="${H}" rx="8" class="trace__box"/>
        <rect x="${x(i) + 8}" y="${Y + 8}" width="16" height="13" rx="2" class="trace__tag"/>
        <text x="${x(i) + 16}" y="${Y + 18}" class="trace__tagtext" text-anchor="middle">${i + 1}</text>
        <text x="${x(i) + W / 2}" y="${Y + 44}" class="trace__name" text-anchor="middle">${esc(name)}</text>
        <text x="${x(i) + W / 2}" y="${Y + 64}" class="trace__word" text-anchor="middle">${esc(word)}</text>
        ${wrap(detail, 13).map((t, k) => `<text x="${x(i) + W / 2}" y="${Y + H + 18 + k * 15}" class="trace__detail" text-anchor="middle">${esc(t)}</text>`).join("")}
      </g>`,
    link: (i, st, id) => `<line x1="${x(i) + W}" y1="${Y + H / 2}" x2="${x(i + 1) - 1}" y2="${Y + H / 2}" class="trace__link trace__link--${st}" marker-end="url(#${id}-arrow${st === "skip" ? "-skip" : ""})"/>`,
    outcome: (text, st, status) => `
      <g class="trace__node trace__node--out trace__node--${st}" data-status="${esc(status || "")}">
        <rect x="${x(5)}" y="${Y + 10}" width="${OW}" height="${H - 20}" rx="26" class="trace__mask"/>
        <rect x="${x(5)}" y="${Y + 10}" width="${OW}" height="${H - 20}" rx="26" class="trace__box"/>
        <text x="${x(5) + OW / 2}" y="${Y + H / 2 + 5}" class="trace__name" text-anchor="middle">${esc(text)}</text>
      </g>`,
    legend: (idle) => legendRow(4, 146, idle),
  };
}

function verticalGeo() {
  const W = 312, H = 48, X = 4, GAP = 14, Y0 = 4;
  const y = (i) => Y0 + i * (H + GAP);
  return {
    w: 320, h: y(5) + 44 + 52,
    node: (i, name, word, detail, st) => `
      <g class="trace__node trace__node--${st}">
        <rect x="${X}" y="${y(i)}" width="${W}" height="${H}" rx="8" class="trace__mask"/>
        <rect x="${X}" y="${y(i)}" width="${W}" height="${H}" rx="8" class="trace__box"/>
        <rect x="${X + 10}" y="${y(i) + 17}" width="16" height="13" rx="2" class="trace__tag"/>
        <text x="${X + 18}" y="${y(i) + 27}" class="trace__tagtext" text-anchor="middle">${i + 1}</text>
        <text x="${X + 36}" y="${y(i) + 21}" class="trace__name">${esc(name)}</text>
        <text x="${X + 36}" y="${y(i) + 38}" class="trace__detail">${esc(detail)}</text>
        <text x="${X + W - 12}" y="${y(i) + 21}" class="trace__word" text-anchor="end">${esc(word)}</text>
      </g>`,
    link: (i, st, id) => `<line x1="${X + 18}" y1="${y(i) + H}" x2="${X + 18}" y2="${y(i + 1) - 1}" class="trace__link trace__link--${st}" marker-end="url(#${id}-arrow${st === "skip" ? "-skip" : ""})"/>`,
    outcome: (text, st, status) => `
      <g class="trace__node trace__node--out trace__node--${st}" data-status="${esc(status || "")}">
        <rect x="${X}" y="${y(5)}" width="${W}" height="44" rx="22" class="trace__mask"/>
        <rect x="${X}" y="${y(5)}" width="${W}" height="44" rx="22" class="trace__box"/>
        <text x="${X + W / 2}" y="${y(5) + 27}" class="trace__name" text-anchor="middle">${esc(text)}</text>
      </g>`,
    legend: (idle) => legendRow(4, y(5) + 44 + 22, idle, true),
  };
}

function legendRow(x0, yl, idle, narrow = false) {
  if (idle) return "";
  const items = [["✓ ผ่าน", "pass"], ["✕ หยุดที่นี่ = ขั้นที่ตัดสินผล", "stop"], ["ไม่ถึง = ไม่ได้ทำขั้นนั้น", "skip"]];
  const xs = narrow ? [0, 74, 196] : [0, 80, 300];
  return `<line x1="${x0}" y1="${yl - 12}" x2="${narrow ? 316 : 676}" y2="${yl - 12}" class="trace__rule"/>` +
    items.map(([t, k], n) => `<text x="${x0 + xs[n]}" y="${yl + 6}" class="trace__legend trace__legend--${k}">${esc(narrow ? t.split(" = ")[0] : t)}</text>`).join("");
}

function wrap(text, max) {     // two lines at most under a node; Thai has no spaces, so break on the separators we wrote ourselves
  const s = String(text || "");
  if (s.length <= max) return [s];
  const cut = Math.max(s.lastIndexOf(" ", max), s.lastIndexOf("·", max), s.lastIndexOf(",", max));
  return cut > 4 ? [s.slice(0, cut).trim(), s.slice(cut + 1).trim()] : [s];
}
