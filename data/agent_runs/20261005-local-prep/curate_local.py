from pathlib import Path
import collections
import csv
import hashlib
import importlib.metadata
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
root = Path.cwd()
run = root / 'data/agent_runs/20261005-local-prep'
manifest_path = root / 'data/manifests/documents.jsonl'
lines = manifest_path.read_text(encoding='utf-8').splitlines()
records = [json.loads(x) for x in lines]
lookup = {r['document_id']: r for r in records}
cohort = json.loads((root / 'data/manifests/corpus_50_candidates.json').read_text(encoding='utf-8'))
ids = [x for group in cohort['groups'].values() for x in group]
groups = {x: g for g, values in cohort['groups'].items() for x in values}
rights = json.loads((root / 'data/manifests/rights_review_20261005.json').read_text(encoding='utf-8'))
rights_lookup = {r['document_id']: r for r in rights['records']}
links = json.loads((run / 'verified_links.json').read_text(encoding='utf-8'))
rows, download_events = [], []
for name in ['20261005-download01', '20261005-download02', '20261005-download03', '20261005-download04']:
    download_events += [json.loads(x) for x in (root / 'data/agent_runs' / name / 'download.jsonl').read_text(encoding='utf-8').splitlines()]
for docid in ids:
    record = lookup[docid]
    raw_folder = root / 'data/raw' / docid
    receipt = json.loads((raw_folder / 'retrieval.json').read_text(encoding='utf-8'))
    source = raw_folder / 'source.pdf'
    held = rights_lookup[docid]['automated_extraction_hold']
    downloaded = source.is_file()
    summary_path = root / 'data/processed' / docid / 'extraction.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8')) if summary_path.exists() else None
    if downloaded:
        assert receipt['outcome'] == 'downloaded'
        assert hashlib.sha256(source.read_bytes()).hexdigest() == receipt['sha256']
        if record['sha256']:
            assert record['sha256'] == receipt['sha256']
        record['sha256'] = receipt['sha256']
        record['pdf_pages'] = receipt['pdf_pages']
        record['content_access'] = 'full_document'
        if docid in links and links[docid] != record['download_url']:
            old_url = record['download_url']
            record['download_url'] = links[docid]
            record['alternate_urls'] = list(dict.fromkeys([u for u in [*record['alternate_urls'], old_url] if u != record['download_url']]))
        note = f" Local preparation20261005: public review copy saved at data/raw/{docid}/source.pdf; actual SHA256/page count verified; no redistribution or clinical approval."
        if summary:
            assert not held
            assert summary['source_sha256'] == receipt['sha256'] and summary['all_pdf_pages_processed']
            record['status'] = 'extracted'
            record['extraction_status'] = summary['extraction_status']
            note += f" pypdf6.10.0 extracted all{summary['processed_pages']} PDF pages for private fidelity review; flags {summary['extraction_status']}, no layout/numeric QA pass."
        elif held:
            record['redistribution_status'] = 'restricted'
            note += ' Automatic extraction/RAG held: explicit Siriraj Diabetes Center prior-permission notice.'
        if docid == 'ht-guideline-2567':
            note += ' Retrieved existing verified Bangkok government mirror because issuer PDF was previously403; cover confirms Thai Hypertension Society/2567; byte equivalence to issuer remains untested.'
        if docid == 'DDC-NCD-CLINIC-PLUS-ONLINE-USER-MANUAL-2566':
            note += ' Alternative public portal Download anchor verified;34-page file cover names exact NCD Clinic Plus Online manual and DDC group. Byte/edition equivalence to denied DDC uploads copy remains pending.'
        if docid == 'ht-siriraj-uncontrolled-opd-2564':
            note += ' pypdf reported recovered cross-reference warnings during reads; inspect source before relying on extracted content.'
    else:
        note = f" Local preparation20261005: local PDF not saved; outcome {receipt['outcome']}; prior web identity/content access is historical evidence, not a local usable corpus copy."
    assert 'Local preparation20261005:' not in record['verification_notes'], 'Do not curate this run twice'
    record['verification_notes'] += note
    if held:
        record['redistribution_status'] = 'restricted'
    assert record['human_review'] is None and record['status'] != 'accepted'
    ocr_path = root / 'data/processed/ocr-review-v1' / docid / 'extraction.json'
    ocr = json.loads(ocr_path.read_text(encoding='utf-8')) if ocr_path.exists() else {}
    if summary:
        queue_state = 'private_extraction_unreviewed'
        action = 'check Thai glyphs, blank pages, tables/reading order, adult sections, currency/edition and rights; human review before acceptance'
    elif held:
        queue_state = 'explicit_permission_hold'
        action = 'record issuer permission before automatic extraction/use/adaptation; raw copy is private review only'
    elif receipt['outcome'] == 'access_restricted':
        queue_state = 'access_restricted'
        action = 'use a legitimate issuer/partner channel or team-provided lawful copy; do not retry/bypass403'
    else:
        queue_state = 'viewer_without_working_pdf'
        action = 'obtain an issuer-provided PDF or review manual access; do not convert hidden page assets into a document'
    rows.append({'primary_group': groups[docid], 'document_id': docid, 'title': record['title'],
                 'local_pdf': downloaded, 'raw_path': f'data/raw/{docid}/source.pdf' if downloaded else None,
                 'download_outcome': receipt['outcome'], 'retrieval_url': receipt['requested_url'],
                 'sha256': receipt.get('sha256'), 'pdf_pages': receipt.get('pdf_pages'),
                 'processed_path': f'data/processed/{docid}/pages.jsonl' if summary else None,
                 'processed_pages': summary['processed_pages'] if summary else 0,
                 'extraction_status': summary['extraction_status'] if summary else 'held_or_not_started',
                 'empty_text_pages': summary['empty_text_pages'] if summary else None,
                 'encoding_indicator_pages': summary['encoding_indicator_pages'] if summary else None,
                 'ocr_sample_pages': ocr.get('ocr_pages', 0),
                 'automated_extraction_hold': held, 'rag_ingestion_hold': True,
                 'review_queue_state': queue_state, 'next_action': action})

changed = {r['document_id']: r for r in records}
manifest_path.write_text(''.join((line if json.loads(line) == changed[json.loads(line)['document_id']] else json.dumps(changed[json.loads(line)['document_id']], ensure_ascii=False)) + '\n' for line in lines), encoding='utf-8')
private_ids = [r['document_id'] for r in rows if r['local_pdf'] and not r['automated_extraction_hold']]
with (root / 'data/manifests/private_review_selection.csv').open('w', encoding='utf-8-sig', newline='') as stream:
    writer = csv.writer(stream); writer.writerow(['document_id']); writer.writerows([x] for x in private_ids)
fields = list(rows[0])
with (root / 'data/manifests/local_preparation_20261005.csv').open('w', encoding='utf-8-sig', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
downloaded_rows = [r for r in rows if r['local_pdf']]
assert len(downloaded_rows) == len({r['sha256'] for r in downloaded_rows})
summary = {'run_id': '20261005-local-prep', 'selected_candidate_works': len(rows),
           'local_pdf_files': len(downloaded_rows), 'local_unique_byte_hashes': len({r['sha256'] for r in downloaded_rows}),
           'local_pdf_pages': sum(r['pdf_pages'] for r in downloaded_rows),
           'private_extracted_documents': len(private_ids), 'private_extracted_pages': sum(r['processed_pages'] for r in rows),
           'extraction_status_counts': dict(collections.Counter(r['extraction_status'] for r in rows if r['processed_pages'])),
           'automatic_extraction_holds': sum(r['automated_extraction_hold'] for r in rows),
           'remaining_access_restricted': sum(r['review_queue_state'] == 'access_restricted' for r in rows),
           'remaining_manual_viewers': sum(r['review_queue_state'] == 'viewer_without_working_pdf' for r in rows),
           'network_pdf_attempts': sum(r['network_attempts'] for r in download_events),
           'ocr_sample_documents': sum(r['ocr_sample_pages'] > 0 for r in rows),
           'ocr_sample_pages': sum(r['ocr_sample_pages'] for r in rows),
           'accepted_records': 0, 'paid_api_calls': 0,
           'notes': ['Download/extraction copies stay locally ignored; no PDF, text or images published.',
                     'Historical web access does not imply a saved local PDF; use these per-document local outcomes.',
                     'All RAG use remains held for rights, faithful extraction/adult scope/currency and actual human review.',
                     'OCR sample has observed word/unit corruption and spacing/column-order issues; not accepted or substituted for source PDF text.'],
           'documents': rows}
(root / 'data/manifests/local_preparation_20261005.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
with (root / 'data/manifests/local_download_events_20261005.jsonl').open('w', encoding='utf-8') as stream:
    stream.writelines(json.dumps(r, ensure_ascii=False) + '\n' for r in download_events)

# Keep current selected metadata CSV consistent; preserve earlier collection snapshots/logs.
cp = root / 'data/manifests/corpus_50_candidates.csv'
with cp.open(encoding='utf-8-sig', newline='') as stream:
    csv_fields = csv.DictReader(stream).fieldnames
with cp.open('w', encoding='utf-8-sig', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=csv_fields); writer.writeheader()
    for docid in ids:
        r = lookup[docid]
        writer.writerow({'primary_group': groups[docid], **{k: r[k] for k in csv_fields if k != 'primary_group'}})
cohort['notes'][-1] = 'Original collection stored no raw PDFs; current local preparation state is in local_preparation_20261005.json. Course accepted corpus still not certified.'
(root / 'data/manifests/corpus_50_candidates.json').write_text(json.dumps(cohort, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
for name in ['VIEWER_RIGHTS', 'MANUAL_RIGHTS', 'MIRROR_DDC_DM', 'MIRROR_CRA_PORTAL']:
    content = (run / (name + '_research.md')).read_text(encoding='utf-8')
    (root / f'research/20261005-local-prep-{name}.md').write_text(content, encoding='utf-8')
runtime = {'python': sys.version, 'packages': {name: importlib.metadata.version(name) for name in ['pypdf', 'pdfplumber', 'reportlab', 'Pillow']},
           'ocr_languages_checked': ['tha', 'eng', 'osd'], 'local_tools': ['pdftoppm', 'pdfinfo', 'tesseract'],
           'project_venv_created': False, 'SentenceTransformers_installed_by_this_run': False, 'paid_api_calls': 0}
(root / 'data/manifests/ingestion_runtime_20261005.json').write_text(json.dumps(runtime, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in summary.items() if k not in ['notes', 'documents']}, ensure_ascii=False, indent=2))
