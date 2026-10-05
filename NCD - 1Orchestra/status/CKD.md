# CKD optional collection status

- Owner role: scout
- Active worker: none; last session: assigned CKD scout
- Updated: 2026-10-05
- State: source_collection_complete
- Last run: 20261005-ncd-50

## Assignment

หา 6 new distinct Thai adult CKD PDF/manual works ไม่ซ้ำ 43 records เดิม
ไม่ใช้ CKD one-page JPG, mirror หรือบทของ CPG เพื่อเพิ่มยอด
ผู้ใช้อนุญาต optional CKD collection ใน [decision 0003](../decisions/0003-collection-at-least-50.md)
clinical inclusion/rights/QA ยังรอ review

## Output / resources

`data/agent_runs/20261005-ncd-50/CKD.jsonl` และ actual research log
Claim `ncd50-CKD`: <=8 queries, <=8 PDF retrieval attempts, <=10 candidates

## 2026-10-05 — scout handoff

- Coordinator reallocated2 existing reservePDF attempts: finalCKD cap10, no newsearchallocation.
- Published evidence: [canonical metadata](../../data/manifests/documents.jsonl),
  [actual query/access log](../../research/20261005-ncd-50-CKD.md).
- Metadata validation passed:6records/6workIDs/source_verified6/accepted0.
- Actualusage:8queries;10PDFretrievalattempts including failed/refetch attempts;
  7successfulattempts,3failures,6distinct PDFs. No morequery/fetch performed.
- Types:3clinicalguidelines,2servicemanuals,1publiceducation work, allsupporting/optionalCKD.
- AdultCKD anemia/nutrition/prevention plus advancedrenalservice and adultglomerular
  chronicprotection; mixedpediatric/acute sections require exclusion duringextraction.
- GlomerularPDF frontmatter/body verifies adultCKD/ESKD progression relevance.
  MobileHD body/makerlist/precisepopulationQA pending despite actual8pagePDFretrieval.
- Rights/currentclinicalcurrency/extraction/numericQA/humanreview remain pending;
  nullhashes and approvals, no rawPDFs saved or newpaidAPI.
- Sourcecollection complete, no activeworker. Curator canonicalmerge and coordinator
  resourceclaim release pending; scout does not edit sharedledger/manifest.
