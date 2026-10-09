"""Find the active side tab (the category a page belongs to) of a booklet whose pages carry a vertical tab strip.

The booklet `ncd-ddc-health-literacy-fight-ncds-2566` prints nine tabs down the right edge of every content page. Only
the active tab is solid and dark; the other eight are pale pastels. OCR reads the labels of all nine tabs on every page,
so every page looks as if it belonged to every category. This module reads the strip from the page image instead:
it cuts the strip into tabs by the white gaps, scores each tab by colour saturation, and calls a tab active when it is
saturated and clearly more saturated than every other tab. The result can be checked against the table of contents,
which gives the category of each printed page range (printed page = PDF page - 2 in this book).

Usage:
    python -X utf8 scripts/side_tab_category.py --images data/agent_runs/20261008-codex-reocr/img_all \
        --corpus data/processed/normalized-v10 --out data/agent_runs/20261008-sidebar/tabs.json
"""

from __future__ import annotations

import argparse
import colorsys
import json
from pathlib import Path

from PIL import Image

DOCUMENT = "ncd-ddc-health-literacy-fight-ncds-2566"
TAB_LABELS = ["โรคความดันโลหิตสูง", "โรคเบาหวาน", "โรคไต", "โรคหัวใจ", "โรคหลอดเลือดสมอง (Stroke)", "โรคอ้วน",
              "การลดการบริโภคเกลือและโซเดียม", "โรคไม่ติดต่อ กับวันสำคัญ", "โรคไม่ติดต่อ กับโควิด 19"]
# Printed page ranges from the table of contents (pages 4-6 of the PDF); printed page = PDF page - PRINTED_OFFSET.
TOC_RANGES = [(21, 29), (30, 39), (40, 43), (44, 48), (49, 53), (54, 59), (60, 68), (69, 84), (85, 200)]
PRINTED_OFFSET = 2
STRIPS = {"right": (0.925, 0.985), "left": (0.012, 0.075)}  # odd pages carry the tabs on the right edge, even pages on the left
WHITE = 238                 # a row whose lightest colour channel is below this is part of a tab
MIN_TAB_HEIGHT = 20
ACTIVE_SATURATION = 0.5     # an active tab is solid: saturation above this
ACTIVE_MARGIN = 0.3         # and clearly above the next most saturated tab


def find_tabs(image: Image.Image) -> list[dict]:
    """Tabs of the side that carries the full strip (right edge on odd pages, left edge on even pages)."""
    best: list[dict] = []
    for side in STRIPS:
        tabs = _strip_tabs(image, STRIPS[side])
        for tab in tabs:
            tab["side"] = side
        if len(tabs) > len(best):
            best = tabs
    return best


def _strip_tabs(image: Image.Image, band: tuple[float, float]) -> list[dict]:
    """Cut one edge strip into coloured tabs; the page-number box near the bottom is not a tab."""
    im = image.convert("RGB")
    width, height = im.size
    x0, x1 = int(width * band[0]), int(width * band[1])
    rows = []
    for y in range(height):
        px = [im.getpixel((x, y)) for x in range(x0, x1, 2)]
        rows.append(tuple(sum(p[c] for p in px) / len(px) for c in range(3)))
    tabs, start = [], None
    for y, colour in enumerate(rows + [(255, 255, 255)]):
        coloured = min(colour) < WHITE
        if coloured and start is None:
            start = y
        elif not coloured and start is not None:
            if y - start >= MIN_TAB_HEIGHT:
                sub = rows[start:y]
                r, g, b = (sum(c[i] for c in sub) / len(sub) for i in range(3))
                h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                tabs.append({"y0": start, "y1": y, "saturation": round(s, 3), "value": round(v, 3), "rgb": [round(r), round(g), round(b)]})
            start = None
    return [t for t in tabs if t["saturation"] > 0.03 or t["value"] < 0.85][: len(TAB_LABELS) + 1]


def active_tab(tabs: list[dict]) -> int | None:
    """Index (1-based, top to bottom) of the active tab, or None when no tab is clearly solid."""
    if len(tabs) < len(TAB_LABELS):
        return None
    candidates = tabs[: len(TAB_LABELS)]
    order = sorted(range(len(candidates)), key=lambda i: -candidates[i]["saturation"])
    top, second = candidates[order[0]]["saturation"], candidates[order[1]]["saturation"]
    return order[0] + 1 if top >= ACTIVE_SATURATION and top - second >= ACTIVE_MARGIN else None


def toc_tab(pdf_page: int) -> int | None:
    printed = pdf_page - PRINTED_OFFSET
    for index, (a, b) in enumerate(TOC_RANGES, 1):
        if a <= printed <= b:
            return index
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--images", type=Path, required=True, help="folder with <document>-p<N>.png page images")
    parser.add_argument("--pages", type=int, default=96)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = {}
    for page in range(1, args.pages + 1):
        path = args.images / f"{DOCUMENT}-p{page}.png"
        if not path.exists():
            continue
        tabs = find_tabs(Image.open(path))
        result[page] = {"tabs": len(tabs), "active_from_image": active_tab(tabs), "active_from_toc": toc_tab(page),
                        "side": tabs[0]["side"] if tabs else None, "saturations": [t["saturation"] for t in tabs],
                        "tab_boxes": [[t["y0"], t["y1"]] for t in tabs]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    both = [p for p, r in result.items() if r["active_from_image"] and r["active_from_toc"]]
    agree = [p for p in both if result[p]["active_from_image"] == result[p]["active_from_toc"]]
    print(json.dumps({"pages": len(result), "with_tab_strip": sum(r["tabs"] >= 9 for r in result.values()),
                      "image_found_active": sum(bool(r["active_from_image"]) for r in result.values()),
                      "compared": len(both), "agree": len(agree), "disagree": [p for p in both if p not in agree]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
