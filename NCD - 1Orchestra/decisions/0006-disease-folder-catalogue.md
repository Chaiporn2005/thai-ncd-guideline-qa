# 0006 — Disease folder catalogue

- Date: 2026-10-06
- Owner: coordinator / curator
- Run: 20261006-disease-folders
- User request: ช่วยจัดไฟล์เอกสารให้เป็น โฟเดอร์ได้ไหม ว่าเป็นของอะไรบ้าง ทำใน git ให้เลย
- Decision: implement and publish within the existing repository

Organize each canonical document as a metadata folder under data/by_disease:
DM17,HT10,LIPID13,optional CKD9,NCD_SERVICE6 plus excluded3 with existing reasons.
Each folder contains README/document.json linking issuer sources and any published
download/extraction/OCR summaries. Multi-disease tags remain visible; each record
occurs once, following the existing primary-group selection.

Use a deterministic builder and read-only consistency check. These files are derived
navigation/metadata; the canonical manifest remains the sole source of document truth.
Keep raw/processed paths compatible with the existing foreground tools and historical
receipts. No raw-source/body upload or rights/acceptance change is part of this task.
The previous upload inventory is a historical snapshot, not a live catalogue inventory.
