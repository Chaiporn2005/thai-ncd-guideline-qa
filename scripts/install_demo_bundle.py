"""Unpack ncd_demo_bundle.zip into this clone and verify it (Track C).

    python -X utf8 scripts/install_demo_bundle.py ncd_demo_bundle.zip

Only paths under data/index/ and the manifest file are accepted (a zip with any other path is refused), every file is checked against BUNDLE_MANIFEST.json, and existing files are left alone
unless --force. Afterwards run: python -X utf8 demo.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ncdqa.rag import demo_support  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("bundle", type=Path)
    ap.add_argument("--force", action="store_true", help="overwrite files that already exist")
    args = ap.parse_args()
    with zipfile.ZipFile(args.bundle) as z:
        names = z.namelist()
        bad = [n for n in names if n != demo_support.MANIFEST_NAME and not n.startswith("data/index/") or ".." in Path(n).parts]
        if bad:
            sys.exit(f"refused: the zip holds paths outside data/index/: {bad[0]}")
        manifest = json.loads(z.read(demo_support.MANIFEST_NAME).decode("utf-8"))
        written = skipped = 0
        for name in names:
            if name == demo_support.MANIFEST_NAME:
                continue
            target = ROOT / name
            if target.exists() and not args.force:
                skipped += 1
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(name))
            written += 1
    (ROOT / demo_support.MANIFEST_NAME).write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    wrong = [rel for rel, digest in manifest["files"].items() if not (ROOT / rel).exists() or demo_support.sha256(ROOT / rel) != digest]
    print(f"installed {written} files, skipped {skipped} existing; checksum mismatches: {len(wrong)}")
    if wrong:
        print("  e.g.", wrong[0], "(use --force to overwrite)")
        return 1
    print("next: python -X utf8 demo.py --check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
