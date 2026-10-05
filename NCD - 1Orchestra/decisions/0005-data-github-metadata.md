# 0005 — Publish reviewed data records

- Date: 2026-10-06
- Owner: coordinator
- Run: 20261006-data-github
- User request: อัปโฟเดอร์ data ลงใน github ให้หน่อย
- Follow-up: ใช้เป็นแค่การศึกษาได้ไหม

The user explicitly authorized uploading data to the existing private repository.
This satisfies the repository's user-authorization requirement for publication scope;
it does not provide a publisher licence. No additional permission evidence was supplied.

Publish existing manifests/schema plus 55 retrieval records, 33 extraction summaries,
39 reviewed historical agent output files and data folder READMEs/allowlists/inventory.
The source-body files remain held:39 PDFs,33 pages JSONL,6 OCR text and6 images.
Two Python cache files remain local as generated caches.
Do not change rights-review approval or clinical acceptance fields.

Educational purpose alone does not settle permission to redistribute full works.
Section32 includes noncommercial study subject to the general conditions in its first
paragraph; no case-specific legal conclusion is made here.
Siriraj Diabetes Centre explicitly requires prior permission for its teaching media.
Rechecked primary sources on2026-10-06:

- https://www.ipthailand.go.th/images/3534/2564/Copyright/Copyright_Act_TH.pdf
- https://si.mahidol.ac.th/Th/division/diabetes/ct_knowledges.asp

Track only metadata allowlisted by the child `.gitignore` files. Inspect staged paths,
parse JSON/JSONL, check hashes and source-body exclusion, then push without changing
repository visibility. Record the actual publication result in board/HANDOFF.
