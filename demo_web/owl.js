// ฮูกไกด์: the demo's mascot, an owl in a white coat with a stethoscope, hand-built SVG (no image files, no library).
// owl(mood) returns markup; the mood follows the answer status so the character reacts to what the system did.
// Moods: hello (welcome, waving) · happy (answered) · think (waiting) · unsure (abstained) · stop (refused) · alert (emergency).

const BROWS = {
  hello:  ["M33 36 Q42 30 51 34", "M87 36 Q78 30 69 34"],
  happy:  ["M33 36 Q42 30 51 34", "M87 36 Q78 30 69 34"],
  think:  ["M33 32 Q42 26 51 31", "M87 36 L69 35"],
  unsure: ["M34 37 L51 31", "M86 37 L69 31"],
  stop:   ["M34 32 L51 37", "M86 32 L69 37"],
  alert:  ["M33 31 Q42 24 51 29", "M87 31 Q78 24 69 29"],
};

const LABEL = {
  hello: "ฮูกไกด์ นกฮูกใส่เสื้อกาวน์คล้องหูฟังแพทย์ กำลังโบกปีกทักทาย",
  happy: "ฮูกไกด์ยิ้ม: ตอบได้พร้อมแหล่งอ้างอิง",
  think: "ฮูกไกด์กำลังค้นหลักฐาน",
  unsure: "ฮูกไกด์ทำหน้าลังเล: หลักฐานไม่พอจะตอบ",
  stop: "ฮูกไกด์ยกปีกห้าม: คำถามนี้อยู่นอกขอบเขต",
  alert: "ฮูกไกด์ตกใจ: อาการฉุกเฉิน ให้โทร 1669",
};

export function owl(mood = "happy", { live = false, title = true } = {}) {
  const m = BROWS[mood] ? mood : "happy";
  const raised = m === "hello" || m === "stop";
  const wide = m === "alert";
  const pupilR = wide ? 4.6 : 6;
  const look = m === "unsure" ? 2.5 : 0;
  const eye = (cx) => `
    <g class="owl__eye">
      <circle cx="${cx}" cy="52" r="${wide ? 13.5 : 12.5}" fill="var(--owl-eye)" stroke="var(--owl-feather-dark)" stroke-width="1"/>
      <g class="owl__pupil">
        <circle cx="${cx + (cx < 60 ? 1 : -1)}" cy="${53 + look}" r="${pupilR}" fill="var(--owl-pupil)"/>
        <circle cx="${cx + (cx < 60 ? 3.2 : 1.2)}" cy="${50.5 + look}" r="1.9" fill="var(--owl-eye)"/>
      </g>
    </g>`;
  const wing = (side) => {
    const r = side === "r";
    const up = r && raised;
    const d = r ? "M98 72 C106 82 104 98 94 106 C90 96 88 86 86 76 Z" : "M22 72 C14 82 16 98 26 106 C30 96 32 86 34 76 Z";
    const cuff = r ? "M92 100 Q96 103 99 101" : "M28 100 Q24 103 21 101";
    return `<g class="owl__wing owl__wing--${side}${up ? " owl__wing--up" : ""}"${up ? ' transform="rotate(-128 94 76)"' : ""}>
      <path d="${d}" fill="var(--owl-coat)" stroke="var(--owl-coat-line)" stroke-width="1.2" stroke-linejoin="round"/>
      <path d="${cuff}" fill="none" stroke="var(--owl-coat-line)" stroke-width="1.2" stroke-linecap="round"/>
    </g>`;
  };
  return `<svg class="owl owl--${m}${live ? " owl--live" : ""}" viewBox="0 0 120 122" ${title ? `role="img" aria-label="${LABEL[m]}"` : 'aria-hidden="true"'} focusable="false">
    <path d="M33 31 L26 10 Q39 15 47 25 Z" fill="var(--owl-feather-dark)"/>
    <path d="M87 31 L94 10 Q81 15 73 25 Z" fill="var(--owl-feather-dark)"/>
    ${raised ? "" : wing("r")}
    ${wing("l")}
    <path d="M60 17 C86 17 101 36 101 62 C101 92 84 112 60 112 C36 112 19 92 19 62 C19 36 34 17 60 17 Z" fill="var(--owl-feather)"/>
    <path d="M23 78 C26 98 41 112 60 112 C79 112 94 98 97 78 C92 74 84 71 75 70 L60 97 L45 70 C36 71 28 74 23 78 Z" fill="var(--owl-coat)" stroke="var(--owl-coat-line)" stroke-width="1.2" stroke-linejoin="round"/>
    <path d="M45 70 L52 89 M75 70 L68 89" fill="none" stroke="var(--owl-coat-line)" stroke-width="1.2" stroke-linecap="round"/>
    <path d="M55 78 L60 81 L65 78 M56.5 85 L60 87.5 L63.5 85" fill="none" stroke="var(--owl-feather-dark)" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" opacity="0.7"/>
    <rect x="72" y="89" width="13" height="10" rx="2" fill="none" stroke="var(--owl-coat-line)" stroke-width="1.2"/>
    <rect x="75" y="84" width="3" height="9" rx="1.2" fill="var(--color-accent)"/>
    <path d="M44 71 C42 84 50 95 60 96 C70 95 78 84 76 71" fill="none" stroke="var(--owl-steth)" stroke-width="2.6" stroke-linecap="round"/>
    <path d="M60 96 C60 102 55 104 51 103.5" fill="none" stroke="var(--owl-steth)" stroke-width="2.2" stroke-linecap="round"/>
    <circle cx="47.5" cy="103.5" r="4.6" fill="var(--owl-steth-metal)" stroke="var(--owl-steth)" stroke-width="1.6"/>
    ${raised ? wing("r") : ""}
    <circle cx="45" cy="52" r="19" fill="var(--owl-face)"/>
    <circle cx="75" cy="52" r="19" fill="var(--owl-face)"/>
    <ellipse cx="60" cy="59" rx="10" ry="12" fill="var(--owl-face)"/>
    ${m === "hello" || m === "happy" ? '<circle cx="31" cy="67" r="4.5" fill="var(--owl-blush)" opacity="0.75"/><circle cx="89" cy="67" r="4.5" fill="var(--owl-blush)" opacity="0.75"/>' : ""}
    ${eye(45)}${eye(75)}
    <path d="${BROWS[m][0]} ${BROWS[m][1]}" fill="none" stroke="var(--owl-feather-dark)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M60 58 L54.5 63.5 Q60 73 65.5 63.5 Z" fill="var(--owl-beak)"/>
    <ellipse cx="50" cy="113.5" rx="6" ry="3.4" fill="var(--owl-beak)"/>
    <ellipse cx="70" cy="113.5" rx="6" ry="3.4" fill="var(--owl-beak)"/>
    ${m === "alert" ? '<g class="owl__bang"><circle cx="104" cy="22" r="11" fill="var(--color-stop)"/><path d="M104 15 L104 24" stroke="var(--owl-eye)" stroke-width="3" stroke-linecap="round"/><circle cx="104" cy="29" r="1.8" fill="var(--owl-eye)"/></g>' : ""}
  </svg>`;
}

// The logo mark: the owl's face perched on an open guideline book, on a medical-blue tile.
export function logoMark() {
  return `<svg class="logo-mark" viewBox="0 0 40 40" aria-hidden="true" focusable="false">
    <rect width="40" height="40" rx="11" fill="var(--brand-tile)"/>
    <path d="M8.5 14 L7.5 5.5 L14 10.5 Z M31.5 14 L32.5 5.5 L26 10.5 Z" fill="var(--brand-face)"/>
    <circle cx="14.5" cy="17" r="7" fill="var(--brand-face)"/>
    <circle cx="25.5" cy="17" r="7" fill="var(--brand-face)"/>
    <circle cx="15" cy="17.5" r="3.2" fill="var(--owl-pupil)"/>
    <circle cx="25" cy="17.5" r="3.2" fill="var(--owl-pupil)"/>
    <circle cx="16.2" cy="16.3" r="1" fill="var(--brand-face)"/>
    <circle cx="26.2" cy="16.3" r="1" fill="var(--brand-face)"/>
    <path d="M20 20 L18 22.4 Q20 25.8 22 22.4 Z" fill="var(--owl-beak)"/>
    <path d="M8 29.5 Q14 27.8 19.4 30 L19.4 34.6 Q14 32.4 8 34 Z M32 29.5 Q26 27.8 20.6 30 L20.6 34.6 Q26 32.4 32 34 Z" fill="var(--brand-face)"/>
  </svg>`;
}
