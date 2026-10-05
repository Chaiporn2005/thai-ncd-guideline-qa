from pathlib import Path
import collections
import csv
import importlib.util
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
root = Path.cwd()
run = root / 'data/agent_runs/20261005-ncd-50'
manifest = root / 'data/manifests/documents.jsonl'
old = [json.loads(x) for x in manifest.read_text(encoding='utf-8').splitlines()]
assert len(old) == 43, 'Run exactly once against original 43 records'
new = []
for name in ['CKD', 'NCD_SERVICE', 'CORE']:
    rows = [json.loads(x) for x in (run / (name + '.jsonl')).read_text(encoding='utf-8').splitlines() if x.strip()]
    for r in rows:
        if 'ckd' in r['disease_tags']:
            r['disease_tags'] = ['chronic_kidney_disease' if t == 'ckd' else t for t in r['disease_tags']]
        assert r['status'] == 'source_verified' and r['human_review'] is None
    new.extend(rows)
rows = old + new
spec = importlib.util.spec_from_file_location('validator', root / 'scripts/validate_manifest.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
schema = json.loads((root / 'data/schemas/document.schema.json').read_text(encoding='utf-8'))
errors, warnings = validator.inspect(list(enumerate(rows, 1)), schema)
assert not errors, errors
assert not warnings, warnings
assert len({r['title'] for r in rows}) == len(rows)
excluded = {
    'ckd-one-page-undated': 'JPG และอาจเป็น summary ของ guideline; ไม่ใช่ PDF/คู่มือในยอดเป้าหมาย',
    'ckd-primary-care-screening-undated': 'ยังไม่ยืนยันว่าเป็นงานอิสระหรือส่วนที่ตัดจาก CKD guideline',
    'ht-ddc-covid-vaccine-screening-2564': 'แนวทางเฉพาะการฉีดวัคซีน COVID-19 ในปี 2564; กันออกจากชุด Q&A NCD ทั่วไป',
}
eligible = [r for r in rows if r['document_id'] not in excluded]
assert len(eligible) >= 50
assert len({r['work_id'] for r in eligible}) == len(eligible)
for r in old:
    if r['document_id'].startswith('ckd-') and r['scope_fit'] == 'requires_scope_expansion':
        r['scope_fit'] = 'supporting'
        r['verification_notes'] += ' Collection scope explicitly authorized by user on 2026-10-05 (decision0003): optional CKD supporting candidate only, not core or human clinical inclusion approval. Target-count exclusions are recorded separately in corpus_50_candidates.json.'
manifest.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')

def group(r):
    if r['document_id'].startswith('DDC-NCD-'):
        return 'NCD_SERVICE'
    for prefix, label in [('dm-', 'DM'), ('ht-', 'HT'), ('lipid-', 'LIPID'), ('ckd-', 'CKD'), ('ncd-', 'NCD_SERVICE')]:
        if r['document_id'].startswith(prefix):
            return label
    raise ValueError(r['document_id'])

groups = {g: [r['document_id'] for r in eligible if group(r) == g] for g in ['DM', 'HT', 'LIPID', 'CKD', 'NCD_SERVICE']}
cohort = {
    'run_id': '20261005-ncd-50', 'accessed_at': '2026-10-05',
    'manifest_records': len(rows), 'selected_candidate_works': len(eligible),
    'accepted_records': 0, 'count_unit': 'provisional distinct authored work; one primary bucket per work',
    'groups': groups, 'new_document_ids': [r['document_id'] for r in new],
    'excluded_from_target': [{'document_id': k, 'reason': v} for k, v in excluded.items()],
    'notes': ['PDF/manual sources only; standalone PDF patient education is included, not every item is a clinical guideline.',
              'Source identity verification is not full-body or clinical review. Final content/hash dedup, rights, adult scope, currency and human review remain pending.',
              'CKD is optional; advanced/renal service works do not become core disease requirements.',
              'Whole multi-topic books counted once, not chapters. Mirrors and printings not multiplied.',
              'Manual e-book viewers remain candidates with download verification pending.',
              'No raw PDF files persisted; course minimum not certified by this candidate count.']
}
(root / 'data/manifests/corpus_50_candidates.json').write_text(json.dumps(cohort, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
fields = ['primary_group', 'document_id', 'work_id', 'title', 'publisher', 'document_type', 'edition', 'landing_url', 'download_url', 'content_access', 'pdf_pages', 'redistribution_status', 'status', 'scope_fit', 'population', 'verification_notes']
with (root / 'data/manifests/corpus_50_candidates.csv').open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    for r in eligible:
        writer.writerow({'primary_group': group(r), **{k: r[k] for k in fields if k != 'primary_group'}})

labels = {'DM': 'เบาหวาน', 'HT': 'ความดันโลหิตสูง', 'LIPID': 'ไขมันในเลือดผิดปกติ', 'CKD': 'CKD — optional', 'NCD_SERVICE': 'NCD Clinic Plus / ระบบบริการ'}
types = {'clinical_guideline': 'แนวทางเวชปฏิบัติ', 'service_manual': 'คู่มือบริการ', 'patient_education': 'PDF ให้ความรู้', 'report': 'รายงาน/ถอดบทเรียน'}
access = {'full_document': 'ดึง PDF ได้; QA ค้าง', 'viewer_only': 'เปิด viewer; body ค้าง', 'link_verified_only': 'ตรวจลิงก์; body ค้าง', 'blocked': 'การเข้าถึงติดขัด', 'not_checked': 'ยังไม่ตรวจเนื้อหา'}
def safe(s):
    return str(s).replace('|', '\\|').replace('\n', ' ')
lines = ['# เอกสารไทย NCDs ครบอย่างน้อย 50 — รายการที่เลือกไว้', '', 'ตรวจแหล่ง: 5 ตุลาคม 2569 (2026-10-05)', '',
         f'รวม **{len(eligible)} candidate works** จาก manifest {len(rows)} รายการ โดยกัน 3 รายการออกจากยอดเป้าหมาย',
         f'รอบนี้เพิ่ม {len(new)} งาน ครอบคลุมโรคหลัก CKD optional และ NCD Clinic Plus/คุณภาพบริการ', '',
         'ทั้งหมดเป็นแนวทาง/เอกสารหน่วยงานไทยสำหรับบริบทไทย รวม PDF ให้ความรู้และคู่มือ ไม่ใช่ clinical guideline ทุกชิ้น',
         '**accepted = 0**: ยังต้องตรวจสิทธิ ฉบับ ความซ้ำจากเนื้อหา/OCR และให้คนตรวจ ก่อนถือว่าเป็น corpus พร้อมทำ RAG หรือผ่านเกณฑ์วิชา',
         'ไม่มี PDF ต้นฉบับบันทึกใน data/raw/ หรืออัปโหลดใน Git; ไม่ตีความ public download เป็นสิทธิแจกจ่าย', '',
         '| หมวดหลักสำหรับนับ | จำนวน |', '| --- | ---: |']
lines += [f'| {labels[g]} | {len(ids)} |' for g, ids in groups.items()]
lines += ['', 'เอกสารข้ามโรคนับในหมวดเดียว; ทั้งเล่มนับหนึ่งงาน ไม่แยกบทหรือรุ่นพิมพ์เป็นหลายเอกสาร',
          'ปีเก่าหรือไม่ทราบปีต้องตรวจความทันสมัย; CKD ผู้ใหญ่/ภาวะแทรกซ้อนและบริการทดแทนไตเป็น optional scope',
          'PDF บางเล่มปนเนื้อหาเด็ก/โรคไตเฉียบพลัน ต้องจำกัด adult CKD sections ระหว่าง extraction', '',
          '[CSV สำหรับเลือก/กรอง](../data/manifests/corpus_50_candidates.csv) • [IDs และเหตุผลการนับ](../data/manifests/corpus_50_candidates.json) • [actual research log](../research/20261005-ncd-50.md)', '']
index = 0
for g, ids in groups.items():
    lines += [f'## {labels[g]} — {len(ids)} งาน', '', '| # | เอกสาร / แหล่งผู้จัดทำ | ประเภท | ไฟล์/คู่มือ | สถานะเนื้อหา |', '| ---: | --- | --- | --- | --- |']
    for r in eligible:
        if group(r) != g:
            continue
        index += 1
        url = r['download_url'] or r['landing_url']
        kind = 'PDF' if re.search(r'\.pdf(?:$|\?)', url, re.I) else ('Drive PDF viewer' if 'drive.google' in url else 'คู่มือ/viewer')
        lines.append(f"| {index} | [{safe(r['title'])}]({r['landing_url']}) — {safe(r['publisher'])} | {types[r['document_type']]} | [{kind}]({url}) | {access[r['content_access']]} |")
    lines += ['']
lines += ['## กันออกจากยอดเป้าหมาย', '', '| document_id | เหตุผล |', '| --- | --- |']
lines += [f'| `{k}` | {v} |' for k, v in excluded.items()]
lines += ['', 'ทั้ง 3 รายการยังอยู่ใน manifest เพื่อรักษาประวัติ ไม่ใช่การลบแหล่งหรืออนุมัติเอกสารอื่น', '',
          'ข้อจำกัดเฉพาะเอกสาร (ประชากร, encoding, publisher restrictions, ฉบับ/การเข้าถึง) อยู่ใน CSV/manifest',
          'เอกสาร Siriraj Diabetes Center บางชิ้นมีข้อความสงวนสิทธิ ต้องตรวจ permission ก่อนใช้เนื้อหา', '']
(root / 'docs/source_catalog_50.md').write_text('\n'.join(lines), encoding='utf-8')
for name in ['CKD', 'NCD_SERVICE', 'CORE']:
    log = (run / (name + '_research.md')).read_text(encoding='utf-8')
    log = log.replace('[CORE.jsonl](CORE.jsonl)', '[canonical manifest](../data/manifests/documents.jsonl)')
    (root / f'research/20261005-ncd-50-{name}.md').write_text(log, encoding='utf-8')
print(json.dumps({'manifest': len(rows), 'selected': len(eligible), 'new': len(new), 'groups': {g: len(ids) for g, ids in groups.items()}, 'content_access': dict(collections.Counter(r['content_access'] for r in eligible)), 'types': dict(collections.Counter(r['document_type'] for r in eligible))}, ensure_ascii=False, indent=2))
