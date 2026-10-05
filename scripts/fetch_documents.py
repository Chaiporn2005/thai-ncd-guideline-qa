"""Fetch public PDF review copies locally; no manifest mutation or permission inference."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import urlopen

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,159}\Z")


def safe_path(base, document_id):
    if not ID_PATTERN.fullmatch(document_id):
        raise ValueError("unsafe document/run ID")
    base = Path(base).resolve()
    path = (base / document_id).resolve()
    if not path.is_relative_to(base):
        raise ValueError("path leaves local data directory")
    return path


def public_url(url):
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
        raise ValueError("expected a public HTTP(S) URL without credentials")
    if parts.hostname.lower() in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("not a public source URL")
    return urlunsplit((parts.scheme, parts.netloc, quote(parts.path, safe="/%:@!$&'()*+,;=-._~"), parts.query, ""))


def inspect_pdf(blob):
    if not blob[:1024].lstrip().startswith(b"%PDF-"):
        raise ValueError("response is not PDF bytes (possibly a login/viewer/error page)")
    reader = PdfReader(io.BytesIO(blob), strict=False)
    if reader.is_encrypted:
        raise ValueError("encrypted PDF held for manual review")
    pages = len(reader.pages)
    if pages < 1:
        raise ValueError("PDF has no pages")
    return {"sha256": hashlib.sha256(blob).hexdigest(), "pdf_pages": pages, "bytes": len(blob)}


def store_pdf(folder, blob):
    meta = inspect_pdf(blob)
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / "source.pdf"
    if not dest.resolve().is_relative_to(folder.resolve()):
        raise ValueError("source path leaves document directory")
    if dest.exists():
        old = hashlib.sha256(dest.read_bytes()).hexdigest()
        if old != meta["sha256"]:
            raise ValueError("existing source differs: preserve it and review edition before replacement")
    else:
        temporary = folder / "source.part"
        try:
            with temporary.open("xb") as stream:
                stream.write(blob)
            temporary.replace(dest)
        finally:
            if temporary.exists():
                temporary.unlink()
    return meta


def fetch_one(record, url, raw_root, timeout, max_bytes, host_times):
    folder = safe_path(raw_root, record["document_id"])
    cached = folder / "source.pdf"
    if not cached.resolve().is_relative_to(folder):
        raise ValueError("source path leaves document directory")
    if cached.exists():
        metadata = inspect_pdf(cached.read_bytes())
        if record.get("sha256") and record["sha256"] != metadata["sha256"]:
            raise ValueError("cached byte hash conflicts with manifest; held for review")
        return {"outcome": "cached", "network_attempts": 0, **metadata}
    url = public_url(url)
    host = urlsplit(url).hostname.lower()
    delay = 6.1 - (time.monotonic() - host_times.get(host, -1000))
    if delay > 0:
        time.sleep(delay)
    host_times[host] = time.monotonic()
    # Standard public GET, no cookies, user-agent impersonation, authentication or retries.
    with urlopen(url, timeout=timeout) as response:
        resolved = response.geturl()
        if response.status != 200:
            raise ValueError(f"HTTP {response.status}; no file saved")
        if int(response.headers.get("Content-Length", 0)) > max_bytes:
            raise ValueError("source exceeds configured byte limit")
        chunks, length = [], 0
        while True:
            chunk = response.read(min(1024 * 1024, max_bytes - length + 1))
            if not chunk:
                break
            chunks.append(chunk)
            length += len(chunk)
            if length > max_bytes:
                raise ValueError("source exceeds configured byte limit")
        blob = b"".join(chunks)
        # A restrictive response never gets an alternate request inside this function.
        metadata = store_pdf(folder, blob)
    if record.get("sha256") and record["sha256"] != metadata["sha256"]:
        return {"outcome": "downloaded_hash_conflict", "network_attempts": 1, "resolved_url": resolved,
                "review_required": "downloaded bytes differ from earlier in-memory hash", **metadata}
    return {"outcome": "downloaded", "network_attempts": 1, "resolved_url": resolved, **metadata}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/manifests/documents.jsonl")
    parser.add_argument("--cohort", type=Path, default=ROOT / "data/manifests/corpus_50_candidates.json")
    parser.add_argument("--links", type=Path, help="curator-verified URL overrides, JSON object keyed by document ID")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--start", type=int, default=0, help="offset into ordered cohort IDs")
    parser.add_argument("--document-id", action="append", help="restrict batch to specific selected IDs")
    parser.add_argument("--limit", type=int, default=30, help="maximum cohort records to inspect in this explicit batch")
    parser.add_argument("--max-attempts", type=int, default=30)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--max-mb", type=int, default=64)
    parser.add_argument("--local-review", action="store_true", help="explicit private review-copy purpose; not reuse/redistribution approval")
    args = parser.parse_args()
    if not args.local_review:
        parser.error("specify --local-review; source reuse rights must be reviewed separately")
    if not 0 < args.max_attempts <= 30 or not 0 < args.timeout <= 30 or not 0 < args.limit <= 55 or args.start < 0 or not 0 < args.max_mb <= 128:
        parser.error("invalid explicit batch/request limits")
    records = {r["document_id"]: r for r in [json.loads(x) for x in args.manifest.read_text(encoding="utf-8").splitlines() if x.strip()]}
    cohort = json.loads(args.cohort.read_text(encoding="utf-8"))
    selected = [x for values in cohort["groups"].values() for x in values]
    if len(set(selected)) != len(selected) or not set(selected) <= set(records):
        parser.error("cohort IDs must be unique and present in manifest")
    if args.document_id:
        if not set(args.document_id) <= set(selected):
            parser.error("requested document ID is outside selected cohort")
        selected = [x for x in selected if x in set(args.document_id)]
    overrides = json.loads(args.links.read_text(encoding="utf-8")) if args.links else {}
    if not isinstance(overrides, dict) or not set(overrides) <= set(records):
        parser.error("URL override keys must be selected cohort IDs")
    output = safe_path(ROOT / "data/agent_runs", args.run_id)
    output.mkdir(parents=True, exist_ok=True)
    log = output / "download.jsonl"
    if log.exists():
        parser.error("run log already exists; use a new registered run ID to preserve history")
    attempts, outcomes, host_times = 0, Counter(), {}
    for document_id in selected[args.start:args.start + args.limit]:
        record = records[document_id]
        url = overrides.get(document_id, record["download_url"])
        event = {"document_id": document_id, "requested_url": url, "retrieved_at": datetime.now(timezone.utc).isoformat(),
                 "purpose": "local_review", "reuse_permission_inferred": False}
        cached = safe_path(ROOT / "data/raw", document_id) / "source.pdf"
        receipt = cached.parent / "retrieval.json"
        prior = json.loads(receipt.read_text(encoding="utf-8")) if receipt.exists() else {}
        if prior.get("outcome") in {"access_restricted", "held_after_access_restriction"} and prior.get("requested_url") == url and not cached.exists():
            event.update(outcome="held_after_access_restriction", network_attempts=0)
        elif not url:
            event.update(outcome="no_download_url", network_attempts=0)
        elif not cached.exists() and not re.search(r"\.pdf(?:$|\?)", url, re.I) and document_id not in overrides:
            event.update(outcome="viewer_requires_public_download_link", network_attempts=0)
        elif not cached.exists() and attempts >= args.max_attempts:
            event.update(outcome="batch_attempt_limit", network_attempts=0)
        else:
            cached_before = cached.exists()
            try:
                event.update(fetch_one(record, url, ROOT / "data/raw", args.timeout, args.max_mb * 1024 * 1024, host_times))
            except HTTPError as exc:
                event.update(outcome="access_restricted" if exc.code in {401, 403, 429} else "http_error", http_status=exc.code,
                             network_attempts=0 if cached_before else 1, error=f"HTTP {exc.code}; stopped without retry/bypass")
            except (URLError, TimeoutError, ValueError, OSError) as exc:
                event.update(outcome="failed", network_attempts=0 if cached_before else 1, error=str(exc)[:500])
            except Exception as exc:
                event.update(outcome="invalid_pdf_or_read_error", network_attempts=0 if cached_before else 1, error=f"{type(exc).__name__}: {str(exc)[:400]}")
        attempts += event["network_attempts"]
        outcomes[event["outcome"]] += 1
        with log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
        cached.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(event, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"id": document_id, "outcome": event["outcome"], "attempts": attempts}, ensure_ascii=True), flush=True)
    summary = {"run_id": args.run_id, "network_attempts": attempts, "outcomes": dict(outcomes), "paid_api_calls": 0,
               "clinical_approval": False, "redistribution_approval": False}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
