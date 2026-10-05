"""Bounded, foreground, local PDF extraction and triage. No clinical approval."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader, __version__ as PYPDF_VERSION

TOOL_VERSION = "1.0"
RESERVED_NAMES = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)),
                  *(f"lpt{i}" for i in range(1, 10))}


class ExtractionError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def validate_id(value: str) -> str:
    if (not isinstance(value, str)
            or not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9_-])?", value)
            or value.split(".", 1)[0].casefold() in RESERVED_NAMES):
        raise ExtractionError("unsafe_document_id", f"Unsafe document ID: {value!r}")
    return value


def contained(base: Path, *parts: str) -> Path:
    root = base.resolve()
    path = root.joinpath(*parts).resolve()
    if not path.is_relative_to(root):
        raise ExtractionError("path_escape", f"Path leaves configured root: {path}")
    return path


def text_indicators(text: str) -> dict:
    controls = sum(unicodedata.category(c) == "Cc" and c not in "\r\n\t" for c in text)
    private_use = sum(unicodedata.category(c) == "Co" for c in text)
    duplicated_combining = sum(a == b and unicodedata.combining(b) != 0
                               for a, b in zip(text, text[1:]))
    return {"text_characters": len(text), "non_whitespace_characters": sum(not c.isspace() for c in text),
            "replacement_characters": text.count("\ufffd"), "control_characters": controls,
            "private_use_characters": private_use, "duplicated_combining_marks": duplicated_combining}


def image_count(page) -> int:
    """Count image references, including Form XObjects, without decoding image pixels."""
    visited = set()

    def walk(resources, depth=0):
        if not resources or depth > 8:
            return 0
        resources = resources.get_object()
        objects = resources.get("/XObject")
        if not objects:
            return 0
        objects = objects.get_object()
        count = 0
        for ref in objects.values():
            obj = ref.get_object()
            key = (getattr(ref, "idnum", None), id(obj))
            if key in visited:
                continue
            visited.add(key)
            if obj.get("/Subtype") == "/Image":
                count += 1
            elif obj.get("/Subtype") == "/Form":
                count += walk(obj.get("/Resources"), depth + 1)
        return count

    return walk(page.get("/Resources"))


def run_local(command: list[str], timeout: int = 60) -> None:
    try:
        result = subprocess.run(command, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ExtractionError("optional_tool_failed", str(exc)) from exc
    if result.returncode:
        error = result.stderr.decode("utf-8", errors="replace")[-1500:]
        raise ExtractionError("optional_tool_failed", f"Exit {result.returncode}: {error}")


def extract_document(record: dict, raw_root: Path, processed_root: Path, *, max_pages: int = 1000,
                     max_bytes: int = 150 * 1024 * 1024, render: bool = False, ocr: bool = False,
                     max_render_pages: int = 20, dpi: int = 150, ocr_languages: str = "tha+eng",
                     renderer: str = "pdftoppm", tesseract: str = "tesseract",
                     work_usage: dict | None = None) -> dict:
    # The CLI supplies this counter so even a failed/staged document consumes its run budget.
    if work_usage is None:
        work_usage = {"page_attempts": 0, "render_attempts": 0}
    doc_id = validate_id(record["document_id"])
    if max_pages < 1 or max_bytes < 1 or max_render_pages < 0 or not 72 <= dpi <= 300:
        raise ExtractionError("invalid_limits", "Positive page/byte limits and DPI72..300 required")
    doc_raw = contained(raw_root, doc_id)
    source = contained(doc_raw, "source.pdf")
    destination = contained(processed_root, doc_id)
    if not source.is_file():
        return {"document_id": doc_id, "outcome": "missing_local_file", "source_path": str(source)}
    if source.stat().st_size > max_bytes:
        raise ExtractionError("source_size_limit", f"PDF exceeds {max_bytes} bytes")
    with source.open("rb") as stream:
        data = stream.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ExtractionError("source_size_limit", "PDF grew past size limit while reading")
    digest = hashlib.sha256(data).hexdigest()
    expected_digest = record.get("sha256")
    if expected_digest is not None and (not isinstance(expected_digest, str)
                                        or expected_digest.casefold() != digest):
        raise ExtractionError("manifest_hash_mismatch", "Local PDF SHA-256 does not match the manifest; no output written")
    configuration = {"tool_version": TOOL_VERSION, "pypdf_version": PYPDF_VERSION,
                     "max_pages": max_pages, "render": render or ocr, "ocr": ocr,
                     "max_render_pages": max_render_pages, "dpi": dpi, "ocr_languages": ocr_languages,
                     "renderer": renderer if render or ocr else None, "tesseract": tesseract if ocr else None}
    if destination.exists():
        summary_path = contained(destination, "extraction.json")
        pages_path = contained(destination, "pages.jsonl")
        try:
            previous = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ExtractionError("incomplete_existing_output", "Existing output is not a reusable extraction") from exc
        if previous.get("source_sha256") != digest:
            raise ExtractionError("source_hash_changed", "Source changed; existing output preserved. Use a new processed root.")
        if previous.get("configuration") != configuration:
            raise ExtractionError("configuration_changed", "Extraction settings changed; existing output preserved.")
        if not pages_path.is_file() or hashlib.sha256(pages_path.read_bytes()).hexdigest() != previous.get("pages_jsonl_sha256"):
            raise ExtractionError("cached_output_corrupt", "Existing page output missing/changed; preserved for investigation")
        return {"document_id": doc_id, "outcome": "cached", "summary": previous}
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted:
            # Never guess passwords or silently try blank passwords.
            raise ExtractionError("encrypted_pdf", "PDF is encrypted; provide an explicitly decrypted review copy separately")
        page_count = len(reader.pages)
        if page_count == 0:
            raise ExtractionError("empty_pdf", "PDF contains no pages")
        labels = reader.page_labels
    except ExtractionError:
        raise
    except Exception as exc:
        raise ExtractionError("invalid_pdf", f"Cannot read PDF: {type(exc).__name__}: {exc}") from exc
    if render or ocr:
        if not shutil.which(renderer):
            raise ExtractionError("renderer_unavailable", f"Cannot find renderer: {renderer}")
        if ocr and not shutil.which(tesseract):
            raise ExtractionError("ocr_unavailable", f"Cannot find OCR tool: {tesseract}")
    processed_root.mkdir(parents=True, exist_ok=True)
    # All generated page files remain in staging until summary + page JSONL are complete.
    with tempfile.TemporaryDirectory(prefix=f".{doc_id}-", dir=processed_root) as temporary:
        staging = Path(temporary)
        pages = []
        rendered = 0
        for index in range(min(page_count, max_pages)):
            work_usage["page_attempts"] += 1
            try:
                page = reader.pages[index]
            except Exception as exc:
                raise ExtractionError("invalid_pdf_page", f"Cannot load PDF page {index + 1}: {exc}") from exc
            errors = []
            try:
                text = page.extract_text() or ""
            except Exception as exc:
                text = ""
                errors.append(f"text: {type(exc).__name__}: {exc}")
            try:
                images = image_count(page)
            except Exception as exc:
                images = None
                errors.append(f"images: {type(exc).__name__}: {exc}")
            indicators = text_indicators(text)
            flags = []
            if indicators["non_whitespace_characters"] == 0:
                flags.append("empty_text")
                flags.append("image_only_candidate" if images else "blank_or_vector_candidate")
            for key in ("replacement_characters", "control_characters", "private_use_characters", "duplicated_combining_marks"):
                if indicators[key]:
                    flags.append(key)
            if errors:
                flags.append("page_extraction_error")
            item = {"document_id": doc_id, "source_sha256": digest, "pdf_page": index + 1,
                    "pdf_page_label": labels[index] if index < len(labels) else None,
                    "printed_page_number": None, "text": text, "text_method": "pypdf.extract_text",
                    "indicators": indicators, "image_references": images, "flags": flags,
                    "errors": errors, "rendered_image": None, "ocr_text": None, "ocr_method": None}
            if (render or ocr) and flags and rendered < max_render_pages:
                rendered += 1
                work_usage["render_attempts"] += 1
                relative = Path("images") / f"page-{index + 1:04d}.png"
                image_path = staging / relative
                image_path.parent.mkdir(exist_ok=True)
                # Render the same byte snapshot that produced source_sha256, even if raw file changes.
                snapshot = staging / "_source_snapshot.pdf"
                if not snapshot.exists():
                    snapshot.write_bytes(data)
                try:
                    run_local([renderer, "-f", str(index + 1), "-l", str(index + 1), "-singlefile",
                               "-r", str(dpi), "-png", str(snapshot), str(image_path.with_suffix(""))])
                    if not image_path.is_file():
                        raise ExtractionError("optional_tool_failed", "Renderer did not produce image")
                    item["rendered_image"] = relative.as_posix()
                    if ocr:
                        prefix = staging / "ocr" / f"page-{index + 1:04d}"
                        prefix.parent.mkdir(exist_ok=True)
                        run_local([tesseract, str(image_path), str(prefix), "-l", ocr_languages])
                        item["ocr_text"] = prefix.with_suffix(".txt").read_text(encoding="utf-8")
                        item["ocr_method"] = f"tesseract:{ocr_languages}"
                except (ExtractionError, OSError, UnicodeError) as exc:
                    item["errors"].append(f"optional: {getattr(exc, 'code', 'optional_output_failed')}: {exc}")
                    item["flags"].append("optional_processing_error")
            pages.append(item)
        empty = sum("empty_text" in p["flags"] for p in pages)
        encoding = sum(any(p["indicators"][k] for k in ("replacement_characters", "control_characters",
                       "private_use_characters", "duplicated_combining_marks")) for p in pages)
        error_pages = sum(bool(p["errors"]) for p in pages)
        # Empty pages may be genuine blanks. This status is a conservative visual/OCR review queue.
        status = "needs_ocr" if empty else "encoding_issue" if encoding or error_pages else "extracted_unreviewed"
        pages_bytes = ("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in pages)).encode("utf-8")
        (staging / "pages.jsonl").write_bytes(pages_bytes)
        snapshot = staging / "_source_snapshot.pdf"
        if snapshot.exists():
            snapshot.unlink()
        summary = {"document_id": doc_id, "title": record.get("title"), "source_url": record.get("download_url"),
                   "source_path": str(source), "source_sha256": digest, "source_bytes": len(data),
                   "pdf_pages": page_count, "processed_pages": len(pages), "page_cap_applied": len(pages) < page_count,
                   "all_pdf_pages_processed": len(pages) == page_count, "empty_text_pages": empty,
                   "image_pages": sum((p["image_references"] or 0) > 0 for p in pages),
                   "encoding_indicator_pages": encoding, "error_pages": error_pages,
                   "text_characters": sum(p["indicators"]["text_characters"] for p in pages),
                   "replacement_characters": sum(p["indicators"]["replacement_characters"] for p in pages),
                   "control_characters": sum(p["indicators"]["control_characters"] for p in pages),
                   "private_use_characters": sum(p["indicators"]["private_use_characters"] for p in pages),
                   "duplicated_combining_marks": sum(p["indicators"]["duplicated_combining_marks"] for p in pages),
                   "rendered_pages": sum(p["rendered_image"] is not None for p in pages),
                   "render_attempts": rendered,
                   "ocr_pages": sum(p["ocr_text"] is not None for p in pages),
                   "extraction_status": status, "configuration": configuration,
                   "pages_jsonl_sha256": hashlib.sha256(pages_bytes).hexdigest(),
                   "created_at": datetime.now(timezone.utc).isoformat(),
                   "clinical_or_layout_qa_performed": False, "human_approval": None,
                   "notes": ["Flags are heuristics, not proof of faithful Thai text or clinical correctness.",
                             "PDF page labels are distinct from printed page numbers; printed numbers remain unknown.",
                             "OCR remains separate from original PDF text and does not clear review flags."]}
        (staging / "extraction.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if destination.exists():
            raise ExtractionError("output_race", "Destination appeared during extraction; existing output preserved")
        # Rename the completed directory; never replace another extraction directory.
        staging.rename(destination)
    return {"document_id": doc_id, "outcome": "extracted", "summary": summary}


def selected_records(manifest: Path, cohort: Path | None, document_ids: list[str]) -> list[dict]:
    records = []
    seen = set()
    for number, line in enumerate(manifest.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        doc_id = validate_id(item["document_id"])
        if doc_id.casefold() in seen:
            raise ExtractionError("duplicate_document_id", f"Duplicate/case-colliding document ID on line {number}")
        seen.add(doc_id.casefold())
        records.append(item)
    wanted = set(validate_id(x) for x in document_ids)
    if cohort:
        with cohort.open(encoding="utf-8-sig", newline="") as stream:
            csv_reader = csv.DictReader(stream)
            if not csv_reader.fieldnames or "document_id" not in csv_reader.fieldnames:
                raise ExtractionError("invalid_cohort", "Cohort CSV requires document_id column")
            cohort_ids = {validate_id(row["document_id"]) for row in csv_reader}
        wanted = wanted & cohort_ids if document_ids else cohort_ids
        missing = cohort_ids - {r["document_id"] for r in records}
        if missing:
            raise ExtractionError("unknown_document_id", f"Cohort IDs absent from manifest: {sorted(missing)}")
    missing = set(document_ids) - {r["document_id"] for r in records}
    if missing:
        raise ExtractionError("unknown_document_id", f"Requested IDs absent from manifest: {sorted(missing)}")
    # An explicit empty selection is empty, not an accidental request for the entire manifest.
    return [r for r in records if r["document_id"] in wanted] if cohort or document_ids else records


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/documents.jsonl"))
    parser.add_argument("--cohort", type=Path, help="CSV containing document_id; preserves manifest order")
    parser.add_argument("--document-id", action="append", default=[])
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--max-documents", type=int, default=60)
    parser.add_argument("--max-pages-per-document", type=int, default=1000)
    parser.add_argument("--max-total-pages", type=int, default=5000)
    parser.add_argument("--max-source-mb", type=int, default=150)
    parser.add_argument("--render", action="store_true", help="Opt-in image rendering for flagged pages")
    parser.add_argument("--ocr", action="store_true", help="Opt-in local OCR on rendered flagged pages; implies render")
    parser.add_argument("--max-render-pages-per-document", type=int, default=20)
    parser.add_argument("--max-total-render-pages", type=int, default=50)
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--ocr-languages", default="tha+eng")
    parser.add_argument("--renderer", default="pdftoppm")
    parser.add_argument("--tesseract", default="tesseract")
    args = parser.parse_args(argv)
    if min(args.max_documents, args.max_pages_per_document, args.max_total_pages, args.max_source_mb) < 1:
        parser.error("Document/page/byte limits must be positive")
    if min(args.max_render_pages_per_document, args.max_total_render_pages) < 0 or not 72 <= args.dpi <= 300:
        parser.error("Render limits must be nonnegative; DPI must be72..300")
    try:
        records = selected_records(args.manifest, args.cohort, args.document_id)
    except (ExtractionError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"outcome": "selection_error", "error_code": getattr(exc, "code", "invalid_input"),
                          "message": str(exc)}, ensure_ascii=False))
        return 2
    results = []
    remaining_pages = args.max_total_pages
    remaining_render = args.max_total_render_pages
    failures = 0
    present_attempts = 0
    for record in records:
        if present_attempts >= args.max_documents or remaining_pages <= 0:
            results.append({"document_id": record["document_id"], "outcome": "run_limit_reached"})
            continue
        work_usage = {"page_attempts": 0, "render_attempts": 0}
        try:
            result = extract_document(record, args.raw_dir, args.processed_dir,
                                      max_pages=min(args.max_pages_per_document, remaining_pages),
                                      max_bytes=args.max_source_mb * 1024 * 1024, render=args.render, ocr=args.ocr,
                                      max_render_pages=min(args.max_render_pages_per_document, remaining_render),
                                      dpi=args.dpi, ocr_languages=args.ocr_languages,
                                      renderer=args.renderer, tesseract=args.tesseract, work_usage=work_usage)
            if result["outcome"] != "missing_local_file":
                present_attempts += 1
            if result["outcome"] == "extracted":
                failures += bool(result["summary"]["error_pages"])
        except Exception as exc:
            present_attempts += 1
            failures += 1
            result = {"document_id": record["document_id"], "outcome": "error",
                      "error_code": getattr(exc, "code", "local_io_error"), "message": str(exc)}
        remaining_pages -= work_usage["page_attempts"]
        remaining_render -= work_usage["render_attempts"]
        result["work_usage"] = work_usage
        results.append(result)
    print(json.dumps({"tool": "extract_pages", "version": TOOL_VERSION, "results": results,
                      "attempted_present_documents": present_attempts, "document_failures": failures,
                      "page_attempts": args.max_total_pages - remaining_pages,
                      "render_attempts": args.max_total_render_pages - remaining_render,
                      "network_requests": 0, "paid_api_calls": 0, "manifest_modified": False},
                     ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
