"""Read-only workflow inspection; never starts agents or consumes paid APIs."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "AGENTS.md", "README.md", "plan.md", "board.md", "HANDOFF.md", "PROGRESS.md",
    "runs/LOG.md", "research/notes.md", "NCD - 0Protocol/README.md",
    "NCD - 0Protocol/PROTOCOL.md", "NCD - 0Protocol/templates/HANDOFF.md",
    "NCD - 0Protocol/templates/STATUS.md", "NCD - 0Protocol/templates/RUN.md",
    "NCD - 1Orchestra/README.md", "NCD - 1Orchestra/GOVERNANCE.md",
    "NCD - 1Orchestra/PLAN.md", "NCD - 1Orchestra/BOARD.md",
    "NCD - 1Orchestra/RESOURCES.md", "NCD - 1Orchestra/status/OVERVIEW.md",
    "NCD - 1Orchestra/proposals/TEMPLATE.md", "NCD - 1Orchestra/decisions/TEMPLATE.md",
]
ROLE_PROMPTS = {
    "scout": "agents/scout.md", "curator": "agents/curator.md",
    "rag_engineer": "agents/rag_engineer.md", "evaluator": "agents/evaluator.md",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def local_file(value):
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("file path must be a nonempty repository-relative POSIX path")
    path = Path(value)
    if path.is_absolute() or ":" in value or ".." in path.parts:
        raise ValueError("file path must stay within the repository")
    result = (ROOT / path).resolve()
    if not result.is_relative_to(ROOT) or not result.is_file():
        raise ValueError("missing file or path outside repository: " + value)
    return result


def registry_errors(registry):
    errors = []
    if not isinstance(registry, dict):
        return ["registry must be an object"]
    if registry.get("version") != 1 or registry.get("coordinator_role") != "coordinator":
        errors.append("unsupported registry version/coordinator")
    if registry.get("runtime_status") != "file_based_protocol_only":
        errors.append("runtime_status must describe this file-based scaffold")
    rows = registry.get("workstreams")
    if not isinstance(rows, list) or not rows:
        return errors + ["workstreams must be a nonempty array"]
    seen = set()
    status_paths = set()
    graph = {}
    for row in rows:
        if not isinstance(row, dict):
            errors.append("each workstream must be an object")
            continue
        stream = row.get("id")
        if not isinstance(stream, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", stream):
            errors.append("invalid workstream ID")
            continue
        if stream in seen:
            errors.append("duplicate workstream ID: " + stream)
        seen.add(stream)
        role = row.get("owner_role")
        if not isinstance(role, str) or role not in ROLE_PROMPTS:
            errors.append(stream + ": unknown owner role")
        elif row.get("role_prompt") != ROLE_PROMPTS[role]:
            errors.append(stream + ": owner role/prompt mismatch")
        for field in ("role_prompt", "status_file"):
            try:
                local_file(row.get(field))
            except ValueError as exc:
                errors.append(stream + ": " + field + ": " + str(exc))
        status_path = row.get("status_file")
        if isinstance(status_path, str):
            if status_path in status_paths:
                errors.append(stream + ": status file shared by multiple streams")
            status_paths.add(status_path)
        if not isinstance(row.get("scope"), str) or not row["scope"].strip():
            errors.append(stream + ": missing scope")
        deps = row.get("depends_on")
        if not isinstance(deps, list) or any(not isinstance(dep, str) for dep in deps):
            errors.append(stream + ": depends_on must be an array of IDs")
            deps = []
        elif len(deps) != len(set(deps)):
            errors.append(stream + ": duplicate dependency")
        graph[stream] = deps
    for stream, deps in graph.items():
        for dep in deps:
            if dep not in seen:
                errors.append(stream + ": unknown dependency " + dep)
    visiting, visited = set(), set()

    def visit(stream):
        if stream in visiting:
            raise ValueError("dependency cycle involving " + stream)
        if stream in visited:
            return
        visiting.add(stream)
        for dep in graph.get(stream, []):
            if dep in graph:
                visit(dep)
        visiting.remove(stream)
        visited.add(stream)

    try:
        for stream in graph:
            visit(stream)
    except ValueError as exc:
        errors.append(str(exc))
    return errors


def workflow_errors(registry):
    errors = registry_errors(registry)
    for name in REQUIRED:
        try:
            local_file(name)
        except ValueError as exc:
            errors.append(str(exc))
    config = read_json(ROOT / "configs/collection_agents.json")
    if not isinstance(config, dict):
        return errors + ["collection config must be an object"]
    if config.get("paid_api_spend_authorized") is not False:
        errors.append("this scaffold has no authorized paid API spend")
    if config.get("authorized_paid_api_budget_usd") != 0:
        errors.append("authorized paid API budget must be 0 until a real user decision")
    if config.get("max_parallel_workers") != 3:
        errors.append("worker limit differs from current Orchestra allocation")
    paths = {ROOT / name for name in REQUIRED}
    for folder in ("NCD - 0Protocol", "NCD - 1Orchestra", "docs", "agents", "research", "runs"):
        paths.update((ROOT / folder).rglob("*.md"))
    for path in sorted(paths):
        if not path.is_file():
            continue
        # Checks local inline links, not remote availability or Markdown anchors.
        for raw in re.findall(r"\]\((<[^>]+>|[^)]+)\)", path.read_text(encoding="utf-8")):
            target = raw[1:-1] if raw.startswith("<") else raw
            if target.startswith("#") or urlsplit(target).scheme:
                continue
            relative = unquote(urlsplit(target).path)
            if not relative:
                continue
            destination = (path.parent / relative).resolve()
            if not destination.is_relative_to(ROOT) or not destination.exists():
                errors.append(str(path.relative_to(ROOT)) + ": broken local link " + target)
    return errors


def status(registry):
    manifest = ROOT / "data/manifests/documents.jsonl"
    records = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    streams = []
    for row in registry["workstreams"]:
        content = local_file(row["status_file"]).read_text(encoding="utf-8")
        match = re.search(r"^- State: (.+)$", content, re.MULTILINE)
        streams.append({"id": row["id"], "owner_role": row["owner_role"],
                        "state_snapshot": match.group(1) if match else "unknown",
                        "depends_on": row["depends_on"], "status_file": row["status_file"]})
    return {"runtime": registry["runtime_status"], "dispatch_performed": False,
            "manifest_records": len(records), "document_status_counts": dict(Counter(r["status"] for r in records)),
            "scope_fit_counts": dict(Counter(r["scope_fit"] for r in records)),
            "workstreams": streams,
            "note": "Manifest counts are live; stream files are snapshots, not active-worker telemetry. Counts do not constitute clinical approval or course equivalence."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "status"])
    parser.add_argument("--registry", type=Path, default=ROOT / "configs/workstreams.json")
    args = parser.parse_args()
    try:
        registry = read_json(args.registry)
        errors = workflow_errors(registry) if args.command == "check" else registry_errors(registry)
        result = {"ok": not errors, "errors": errors} if errors or args.command == "check" else status(registry)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if errors else 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
