# ทรัพยากรและ claims

ไม่มี paid API budget ที่ผู้ใช้อนุมัติไว้สำหรับ runner
ตัวเลขใน collection config เป็นข้อเสนอด้านการออกแบบ ไม่ใช่สิทธิเริ่มใช้เงิน
ใช้เครื่องมือที่ session มีอยู่ภายในงานที่ได้รับมอบหมาย; meter ที่ไม่มีให้ unknown

| ทรัพยากร | เพดานเสนอ / สถานะ | การใช้งาน |
| --- | --- | --- |
| Workers | <=3 + coordinator 1 | จำกัดตาม slots จริงด้วย; roles ใช้ต่อกันได้ |
| Search | <=8 queries และ <=10 candidates/scout | ต้องเก็บ actual query log |
| Full document retrieval | <=30/run ตาม decision 0002 | rights/access gates ก่อนดึง; allocation ล่าสุดอยู่ใน ledger |
| Requests | timeout 30s, retry <=1, <=10/host/min | หยุดเมื่อ access restricted |
| Model tokens | <=40,000/run เสนอ | ยังไม่มี provider/model หรือ meter |
| API spend | $5/run เสนอ; authorized new paid API spend $0 | ต้องเลือก provider และได้รับงบจริงก่อน |
| CPU/GPU | CPU baseline required; GPU ไม่มี allocation | ระบุเครื่องจริงก่อน experiment |
| Clinical review | ยังไม่มี reviewer ที่ได้รับมอบหมาย | acceptance/gold answers รอคนตรวจ |

ค่า canonical สำหรับ runner ที่จะสร้างอยู่ใน
[collection_agents.json](../configs/collection_agents.json); ขณะนี้ไม่มี runtime enforcement

## Ledger — append-only events

| Event / actual date | Kind | Claim / owner | Scope / limit / usage | State or evidence |
| --- | --- | --- | --- | --- |
| init-20261005 / 2026-10-05 | initialization | none / coordinator | ตั้งโครงเท่านั้น; usage unknown | ไม่มี active claim จากการตั้งโครง |

ก่อนงานจริง append `claim` พร้อม ID, owner, stream/run, เครื่องมือ/อุปกรณ์, limits และ timestamp
เมื่อเสร็จ append `usage` และ `release` อ้าง claim เดิม
Active claims คือ claim events ที่ยังไม่มี release ไม่ใช่การนับทุกแถวในตาราง
เจ้าของแจ้ง coordinator ผ่าน BOARD; coordinator เป็น writer ของ ledger
ไม่มี scheduler หรือ watcher คอย reclaim ทรัพยากรอัตโนมัติ

## Claims — 20261005-ncd-plus10

| Event / actual timestamp | Kind | Claim / owner | Scope / limit / usage | State or evidence |
| --- | --- | --- | --- | --- |
| plus10-DM / 2026-10-05T20:41:16+07:00 | claim | plus10-DM / DM scout | 8 queries, 10 new candidates, <=3 full PDFs | active until release |
| plus10-HT / 2026-10-05T20:41:16+07:00 | claim | plus10-HT / HT scout | 8 queries, 10 new candidates, <=3 full PDFs | active until release |
| plus10-LIPID / 2026-10-05T20:41:16+07:00 | claim | plus10-LIPID / LIPID scout | 8 queries, 10 new candidates, <=4 full PDFs | active until release |

### Claim updates — PDF-only wave 2

| Event / actual date | Kind | Claim / owner | Scope / limit / usage | Evidence |
| --- | --- | --- | --- | --- |
| plus10-wave2 / 2026-10-05 | claim update | plus10-DM, plus10-HT, plus10-LIPID / assigned scouts | 8 additional queries/scout wave2, unchanged 10 final candidates/scout and fullPDF allocation3/3/4 | user clarified PDF/manual only; actual usage logged by wave |

### Allocation update — decision 0002

- Date: 2026-10-05
- New full-document cap: 30/run, overriding earlier proposed10 and perstream3/3/4 for thisrun
- Claims updated: plus10-DM <=8; plus10-HT <=14; plus10-LIPID <=8 total fullPDF fetches acrosswaves
- Existing tools only, no paid API allocation; source access/rights and human review gates unchanged
- Evidence: [decision0002](decisions/0002-pdf-source-verification.md)

### Reallocation — same 30-fetch cap

- Date: 2026-10-05
- Claim update: plus10-DM <=8, plus10-HT <=12, plus10-LIPID <=10 PDF retrieval attempts total acrosswaves
- Purpose: LIPID large-file source verification after webtool size limits; normalfetchonly, no bypass
- Counting clarification: attempts including toolsize/timeout failures counted conservatively; successes reported separately
- No increase to total30 or paid API allocation

### Verification suballocation — coordinator

- Date: 2026-10-05
- Claims: plus10-DM <=8, plus10-HT <=10, plus10-LIPID <=10, plus10-VERIFY <=2 PDF retrieval attempts (total30)
- plus10-VERIFY owner: coordinator as verifier/curator; <=4 targetedqueries forweakHTmanuallinks/replacements
- HTworker informed tostopfetches at10; no newparallelworker orpaidAPIbudget

### Curation verification run — 20261005-ncd-plus10-curation

- Date: 2026-10-05
- Claim: plus10-CURATION / coordinator-verifier
- Limits: <=8 targetedsearchqueries, <=6 fullPDFverificationattempts; newrunwithinconfigcap30
- Purpose: resolvePDF/leafletdedup andform-gated/missingdownloadreplacements beforefinalcatalog
- No newworkerorpaidAPI; donorclaimsfromfirstcollectionwillreleasewithactualusagereport

### Release and usage — 20261005-ncd-plus10

| Event / actual date | Kind | Claim / owner | Actual usage | State/evidence |
| --- | --- | --- | --- | --- |
| close-DM / 2026-10-05 | usage + release | plus10-DM / DMscout | 10queries;8successfulPDFbodies incl1excluded; otherfailedtoolcallsreportedseparately | released; researchreport |
| close-HT / 2026-10-05 | usage + release | plus10-HT / HTscout | 16queries;10uniquePDFtargets,6retrieved incl2excluded,4failed | released |
| close-LIPID / 2026-10-05 | usage + release | plus10-LIPID / LIPIDscout | 16queries;10PDFattempts,8retrieved incl1excluded,2failed | released |
| close-VERIFY / 2026-10-05 | usage + release | plus10-VERIFY / coordinator | 4queries;2PDFtargetsfailed403/404 | released |
| close-CURATION / 2026-10-05 | usage + release | plus10-CURATION / coordinator | 4queries;3PDFattempts,1retrieved2failed(size/403) | released |

Budgetaccountingnote: DMreported8successfulbodies plusotherfailedtoolcalls, not8totalrequests; successfulfull-bodycapandlaterconservativeattemptcapwerenotuniformlymetered. Do notclaimruntimebudgetenforcement. Modeltokens/APIcostunknown, no newpaidAPIinvoked.

Allcollectionclaimsreleased; no activeworkers. Evidence: [researchrun](../research/20261005-ncd-plus10.md).
