"""Repair Thai PDF text for retrieval review: font maps, legacy encodings, page quality gate.

Reads local `data/raw/<id>/source.pdf`, re-extracts each page with pypdf after in-memory
font-map repairs, normalizes Thai text and writes a separate processed root. Source PDFs and
the original extraction are never modified. No clinical approval, network access or paid API.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import io
import json
import math
import re
import shutil
import statistics
import struct
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader, __version__ as PYPDF_VERSION
from pypdf.generic import DecodedStreamObject, NameObject

try:  # Optional: page geometry for underlined comparison signs. Without it the check is reported as unavailable.
    import pdfplumber
except ImportError:  # pragma: no cover - depends on the local environment
    pdfplumber = None

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_pages as base  # noqa: E402  (shared ID/path/rights helpers)

TOOL_VERSION = "1.0"
ExtractionError = base.ExtractionError

CONSONANT = "\u0e01-\u0e2e"
MARK = "\u0e31\u0e34-\u0e3a\u0e47-\u0e4e"  # Thai combining vowels, tone marks and signs
TONE = "\u0e48-\u0e4b"
THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")

# Positional glyph variants in the Microsoft Thai private-use block U+F700..U+F71A.
PUA_BASE = ["\u0e10", "\u0e34", "\u0e35", "\u0e36", "\u0e37", "\u0e48", "\u0e49", "\u0e4a", "\u0e4b",
            "\u0e4c", "\u0e48", "\u0e49", "\u0e4a", "\u0e4b", "\u0e4c", "\u0e0d", "\u0e31", "\u0e4d",
            "\u0e47", "\u0e48", "\u0e49", "\u0e4a", "\u0e4b", "\u0e4c", "\u0e38", "\u0e39", "\u0e3a"]
PUA_MAP = {0xF700 + i: c for i, c in enumerate(PUA_BASE)}

# C1 positional codes seen in Windows Thai font exports. Only codes observed in this corpus
# and confirmed from word context (e.g. ป\x86วย = ป่วย, เป\x9aน = เป็น) are mapped.
WINDOWS_POSITIONAL = {0x81: "\u0e34", 0x82: "\u0e35", 0x86: "\u0e48", 0x87: "\u0e49", 0x8B: "\u0e48",
                      0x8C: "\u0e49", 0x8F: "\u0e4c", 0x98: "\u0e31", 0x9A: "\u0e47"}
# Apple Mac OS Thai codes 0x80..0xA0 that differ from TIS-620; confirmed from word context.
MAC_THAI = {0x83: "\u0e48", 0x84: "\u0e49", 0x85: "\u0e4a", 0x86: "\u0e4b", 0x87: "\u0e4c",
            0x88: "\u0e48", 0x89: "\u0e49", 0x8A: "\u0e4a", 0x8B: "\u0e4b", 0x8C: "\u0e4c",
            0x8D: "\u201c", 0x8E: "\u201d", 0x8F: "\u0e4d", 0x92: "\u0e31", 0x93: "\u0e47",
            0x94: "\u0e34", 0x95: "\u0e35", 0x96: "\u0e36", 0x97: "\u0e37", 0x98: "\u0e48",
            0x99: "\u0e49", 0x9A: "\u0e4a", 0x9B: "\u0e4b", 0x9C: "\u0e4c", 0xA0: " "}
# Glyph names such as /ToTao or /SaraIi2 leak from fonts with unmapped /Differences.
THAI_GLYPH_NAMES = {unicodedata.name(chr(c)).removeprefix("THAI CHARACTER ").title().replace(" ", ""): chr(c)
                    for c in range(0x0E01, 0x0E5C) if unicodedata.name(chr(c), "").startswith("THAI CHARACTER")}

# TH Sarabun (New/PSK) glyph order, used only for subsets that keep original glyph IDs.
# ASCII and Thai ranges were confirmed against 1,000+ consistent ToUnicode entries in this corpus;
# variants 0x156..0x170 follow the U+F700 positional order (confirmed for 0x158/0x160/0x161/0x164/0x168).
SARABUN_EXTRA = {0x73: "±", 0x74: "²", 0x131: "–", 0x132: "—", 0x134: "’", 0x136: "“", 0x137: "”",
                 0x13B: "•", 0x152: "≤", 0x153: "≥", 0x173: "fi", 0x174: "fl", 0x1F0: " "}
SARABUN_FONT = re.compile(r"TH ?Sarabun", re.IGNORECASE)
SARABUN_MIN_GLYPHS = 0x12D
SARABUN_MIN_AGREEMENT = 0.85
OCR_MIN_THAI_LETTERS = 50


def sarabun_char(gid: int) -> str | None:
    if 0x01 <= gid <= 0x5F:
        return chr(gid + 0x1F)
    if 0xD6 <= gid <= 0x10F:
        return chr(gid + 0xD2B)
    if 0x110 <= gid <= 0x12C:
        return chr(gid + 0xD2F)
    if 0x156 <= gid <= 0x170:
        return PUA_BASE[gid - 0x156]
    return SARABUN_EXTRA.get(gid)


def parse_tounicode(data: bytes) -> dict[int, str] | None:
    """Parse bfchar/simple bfrange entries; None when the CMap uses syntax this parser cannot
    round-trip (range arrays, multi-character ranges, surrogates), so the font is left untouched."""
    mapping = {}
    text = data.decode("latin-1")

    def chars(hex_text):
        return "".join(chr(int(hex_text[i:i + 4], 16)) for i in range(0, len(hex_text), 4))
    for block in re.findall(r"beginbfchar(.*?)endbfchar", text, re.S):
        for src, dst in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]*)>", block):
            mapping[int(src, 16)] = chars(dst)
    for block in re.findall(r"beginbfrange(.*?)endbfrange", text, re.S):
        for start, end, array in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[([^\]]*)\]", block):
            values = re.findall(r"<([0-9A-Fa-f]*)>", array)
            codes = range(int(start, 16), int(end, 16) + 1)
            if len(values) != len(codes):
                return None
            mapping.update({code: chars(value) for code, value in zip(codes, values)})
        block = re.sub(r"<[0-9A-Fa-f]+>\s*<[0-9A-Fa-f]+>\s*\[[^\]]*\]", "", block)
        for start, end, dst in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block):
            if len(dst) > 4:
                return None
            first = int(dst, 16)
            for offset, code in enumerate(range(int(start, 16), int(end, 16) + 1)):
                mapping[code] = chr(first + offset)
    if any(0xD800 <= ord(c) <= 0xDFFF for value in mapping.values() for c in value):
        return None
    return mapping


def tounicode_stream(mapping: dict[int, str], font) -> DecodedStreamObject:
    # Type0 (Identity-H) fonts use two-byte codes; simple TrueType/Type1 fonts use one byte.
    digits = 4 if font.get("/Subtype") == "/Type0" else 2
    items = sorted(mapping.items())
    lines = ["/CIDInit /ProcSet findresource begin", "12 dict begin", "begincmap",
             "/CMapName /Repaired-UCS def", "/CMapType 2 def",
             "1 begincodespacerange", f"<{0:0{digits}X}> <{16 ** digits - 1:0{digits}X}>", "endcodespacerange"]
    for i in range(0, len(items), 100):
        block = items[i:i + 100]
        lines.append(f"{len(block)} beginbfchar")
        lines += [f"<{code:0{digits}X}> <{''.join(f'{ord(c):04X}' for c in value)}>" for code, value in block]
        lines.append("endbfchar")
    lines += ["endcmap", "CMapName currentdict /CMap defineresource pop", "end", "end"]
    stream = DecodedStreamObject()
    stream.set_data("\n".join(lines).encode("ascii"))
    return stream


def truetype_glyph_count(data: bytes) -> int | None:
    try:
        tables = struct.unpack(">H", data[4:6])[0]
        for i in range(tables):
            tag, _, offset, _ = struct.unpack(">4sIII", data[12 + 16 * i:28 + 16 * i])
            if tag == b"maxp":
                return struct.unpack(">H", data[offset + 4:offset + 6])[0]
    except struct.error:
        return None
    return None


def _font_objects(reader):
    seen = set()
    for page in reader.pages:
        resources = page.get("/Resources")
        fonts = resources.get_object().get("/Font") if resources else None
        if not fonts:
            continue
        for ref in fonts.get_object().values():
            font = ref.get_object()
            key = getattr(ref, "idnum", None) or id(font)
            if key not in seen:
                seen.add(key)
                yield font


def repair_sarabun_font(font) -> tuple[str, int]:
    """Rebuild a TH Sarabun Type0 ToUnicode map from glyph IDs; return (action, entries changed)."""
    if font.get("/Subtype") != "/Type0" or not SARABUN_FONT.search(str(font.get("/BaseFont", ""))):
        return "not_applicable", 0
    descendant = font["/DescendantFonts"][0].get_object()
    descriptor = descendant.get("/FontDescriptor")
    descriptor = descriptor.get_object() if descriptor else {}
    if descendant.get("/CIDToGIDMap", "/Identity") != "/Identity" or "/FontFile2" not in descriptor:
        return "skip_not_identity_truetype", 0
    glyphs = truetype_glyph_count(descriptor["/FontFile2"].get_object().get_data())
    if glyphs is None or glyphs < SARABUN_MIN_GLYPHS:
        # Compact subsets renumber glyphs, so the original glyph order cannot be assumed.
        return "skip_compact_subset", 0
    if "/ToUnicode" in font:
        old = parse_tounicode(font["/ToUnicode"].get_object().get_data())
        if old is None:
            return "skip_unparsed_cmap", 0
        thai = [(g, u) for g, u in old.items() if 0xD6 <= g <= 0x12C and len(u) == 1 and u != "\ufffd"]
        if not thai or sum(sarabun_char(g) == u for g, u in thai) / len(thai) < SARABUN_MIN_AGREEMENT:
            return "skip_low_agreement", 0
        new, changed = dict(old), 0
        for gid, value in old.items():
            expected = sarabun_char(gid)
            if expected and expected != value and (0xD6 <= gid <= 0x12C or 0x156 <= gid <= 0x170
                                                  or value == "\ufffd" or len(value) > 1):
                new[gid] = expected
                changed += 1
        if not changed:
            return "unchanged", 0
        font[NameObject("/ToUnicode")] = tounicode_stream(new, font)
        return "repaired_tounicode", changed
    new = {gid: sarabun_char(gid) or "\ufffd" for gid in range(1, glyphs)}
    font[NameObject("/ToUnicode")] = tounicode_stream(new, font)
    return "added_tounicode", len(new)


def repair_sara_aa_font(font) -> tuple[str, int]:
    """Exporter bug: the SARA AA glyph is labelled SARA AM while NIKHAHIT is left unmapped,
    either as U+FFFD or as a second SPACE glyph (seen in CordiaUPC italic: \u0e01\u0e33\u0e41\u0e1f\u0e14\u0e33 for \u0e01\u0e32\u0e41\u0e1f\u0e14\u0e33)."""
    if "/ToUnicode" not in font:
        return "not_applicable", 0
    old = parse_tounicode(font["/ToUnicode"].get_object().get_data())
    if old is None or len(old) > 5000:
        return "not_applicable", 0
    values = list(old.values())
    am = [g for g, u in old.items() if u == "\u0e33"]
    unmapped = [g for g, u in old.items() if u == "\ufffd"]
    unmapped_nikhahit = bool(unmapped) or values.count(" ") >= 2
    if len(am) != 1 or "\u0e32" in values or not unmapped_nikhahit:
        return "not_applicable", 0
    if len(unmapped) == 1 and am[0] > unmapped[0]:
        # Thai glyphs follow Unicode order (SARA AA U+0E32 before NIKHAHIT U+0E4D), so an unmapped glyph
        # *before* the SARA AM label is SARA AA itself (Siriraj foot manual: \u0e40\u0e17\u0e49\ufffd for \u0e40\u0e17\u0e49\u0e32); the label is
        # a real \u0e33 or a NIKHAHIT, and the text rule folds the resulting \u0e33\u0e32 back into \u0e33.
        old[unmapped[0]] = "\u0e32"
        font[NameObject("/ToUnicode")] = tounicode_stream(old, font)
        return "filled_sara_aa", 1
    old[am[0]] = "\u0e32"
    font[NameObject("/ToUnicode")] = tounicode_stream(old, font)
    return "remapped_sara_aa", 1


def repair_nikhahit_space_font(font) -> tuple[str, int]:
    """Exporter bug: NIKHAHIT is labelled as a second SPACE glyph (น ้าตาล for น้ำตาล).

    Applied only when a font has two or more SPACE glyphs and one of them immediately follows the
    THANTHAKHAT glyph, matching the Unicode-ordered glyph layout of Thai fonts (U+0E4C, U+0E4D).
    """
    if "/ToUnicode" not in font:
        return "not_applicable", 0
    old = parse_tounicode(font["/ToUnicode"].get_object().get_data())
    if old is None or len(old) > 5000 or "ํ" in old.values():
        return "not_applicable", 0
    spaces = [code for code, value in old.items() if value == " "]
    candidates = [code for code in spaces if old.get(code - 1) == "์"]
    if len(spaces) < 2 or len(candidates) != 1:
        return "not_applicable", 0
    old[candidates[0]] = "ํ"
    font[NameObject("/ToUnicode")] = tounicode_stream(old, font)
    return "remapped_nikhahit_space", 1


def repair_cluster_font(font) -> tuple[str, int]:
    """Exporter bug: a consonant glyph is labelled with the first cluster it appeared in (e.g. คื).

    Only consonant + combining-mark labels are reduced, and only when every mark also has its own
    glyph in the same font, so genuine multi-character glyphs such as ฤๅ are left unchanged.
    """
    if "/ToUnicode" not in font:
        return "not_applicable", 0
    old = parse_tounicode(font["/ToUnicode"].get_object().get_data())
    if old is None or len(old) > 5000:
        return "not_applicable", 0
    singles = {u for u in old.values() if len(u) == 1}
    changed = 0
    for gid, value in old.items():
        if (re.fullmatch(rf"[{CONSONANT}][{MARK}]{{1,3}}", value)
                and all(mark in singles for mark in value[1:])):
            old[gid] = value[0]
            changed += 1
    if not changed:
        return "not_applicable", 0
    font[NameObject("/ToUnicode")] = tounicode_stream(old, font)
    return "reduced_cluster_labels", changed


def _family_key(font) -> tuple[str, str]:
    """(subset prefix, family) for sibling fonts such as PSL-Bundit and PSL-Bundit-Bold in one export."""
    name = str(font.get("/BaseFont", "")).lstrip("/")
    prefix, _, family = name.rpartition("+")
    family = re.sub(r"[-,]?(Bold|Italic|BoldItalic|Oblique)+$", "", family, flags=re.IGNORECASE)
    return prefix, family


def repair_from_siblings(fonts) -> int:
    """Fill U+FFFD entries from sibling fonts of the same export that map that code to one character.

    In the Siriraj foot-care manual, PSL-Bundit-Bold leaves SARA AA (0x9F) as U+FFFD while PSL-Bundit maps
    0x9F to า; without this the SARA AM rule would misread the bold font's real ำ glyph.
    """
    maps = {}
    for font in fonts:
        if "/ToUnicode" in font and font.get("/Subtype") == "/Type0":
            mapping = parse_tounicode(font["/ToUnicode"].get_object().get_data())
            if mapping is not None and len(mapping) <= 5000:
                maps[id(font)] = (font, mapping)
    groups = collections.defaultdict(list)
    for font, mapping in maps.values():
        prefix, family = _family_key(font)
        if prefix:
            groups[(prefix, family)].append((font, mapping))
    def same_layout(a, b):
        # Compact subsets renumber codes per font (DBSodaX vs DBSodaX-Bold), so a sibling only counts
        # when the codes both fonts map agree almost everywhere.
        shared = [c for c in a if c in b and len(a[c]) == 1 and len(b[c]) == 1 and "�" not in (a[c], b[c])]
        return len(shared) >= 15 and sum(a[c] == b[c] for c in shared) >= 0.9 * len(shared)

    changed = 0
    for members in groups.values():
        for font, mapping in members:
            fixed = 0
            siblings = [m for f, m in members if f is not font and same_layout(mapping, m)]
            for code, value in mapping.items():
                if value != "�":
                    continue
                votes = {m[code] for m in siblings if m.get(code) not in (None, "�")}
                if len(votes) == 1 and len(next(iter(votes))) == 1:
                    mapping[code] = votes.pop()
                    fixed += 1
            if fixed:
                font[NameObject("/ToUnicode")] = tounicode_stream(mapping, font)
                changed += fixed
    return changed


def repair_fonts(reader) -> dict:
    actions = collections.Counter()
    changed = 0
    fonts = list(_font_objects(reader))
    sibling_fixes = repair_from_siblings(fonts)
    if sibling_fixes:
        actions["filled_from_sibling_fonts"] += sibling_fixes
        changed += sibling_fixes
    for font in fonts:
        action, count = repair_sarabun_font(font)
        if action != "not_applicable":
            actions[action] += 1
            changed += count
        if action == "not_applicable" or action.startswith("skip"):
            for repair in (repair_sara_aa_font, repair_nikhahit_space_font, repair_cluster_font):
                action, count = repair(font)
                if action != "not_applicable":
                    actions[action] += 1
                    changed += count
    return {"font_actions": dict(sorted(actions.items())), "tounicode_entries_written_or_changed": changed}


QUOTE_LIKE = set("“”‘’«»—–…•")


def _decode_runs(text: str, encoding: str, table: dict[int, str], counts: collections.Counter,
                 rule: str, safe_symbols: set[str]) -> str:
    """Decode runs of legacy (non-ASCII, non-Thai) characters, also when glued to Thai text."""
    def decode(match):
        run = match.group(0)
        start, end = match.span()
        before = text[start - 1] if start else ""
        after = text[end] if end < len(text) else ""
        if all(c in safe_symbols for c in run):
            return run
        # A lone quote or dash touching real Thai letters is genuine punctuation, not a legacy byte.
        if len(run) == 1 and run in QUOTE_LIKE and any("ก" <= c <= "๛" for c in (before, after) if c):
            return run
        raw = _legacy_bytes(run, encoding)
        if raw is None:
            return run
        out = []
        for byte in raw:
            if byte in table:
                out.append(table[byte])
            elif byte >= 0xA1:
                out.append(bytes([byte]).decode("cp874", errors="replace"))
            else:
                out.append(chr(byte))
        counts[rule] += 1
        return "".join(out)
    # Runs exclude ASCII and Thai; NO-BREAK SPACE stays inside a run because in MacRoman it is
    # byte 0xCA (Thai SO SUA). Runs touching ASCII letters belong to accented Latin words (café).
    return re.sub(r"(?<![A-Za-z])[^\x00-\x7f฀-๿]+(?![A-Za-z])", decode, text)


def _legacy_bytes(token: str, encoding: str) -> bytes | None:
    """Recover the font's byte codes; C1 controls pass through as their own byte values."""
    out = bytearray()
    # pypdf can emit GREEK MU where the font byte was MICRO SIGN (0xB5).
    for char in token.replace("\u03bc", "\u00b5"):
        try:
            out += char.encode(encoding)
        except UnicodeEncodeError:
            if 0x80 <= ord(char) <= 0x9F:
                out.append(ord(char))
            else:
                return None
    return bytes(out)


# Genuine symbols that also occur in correctly encoded cp1252 documents; a run made only of these
# is kept. Mac Thai documents get no such list because these code points carry Thai letters there.
LEGACY_SAFE_SYMBOLS = set("\u00bc\u00bd\u00be\u00b0\u00b1\u00d7\u00f7\u00b2\u00b3\u00b5\u00b7\u2022\u2013\u2014\u201c\u201d\u2018\u2019\u2026\u00ae\u00a9\u2122\u00a7\u00b6")


def legacy_decode(text: str, decoder: str | None, counts: collections.Counter) -> str:
    if decoder:
        # pypdf can emit compatibility forms (OHM SIGN U+2126 for MacRoman Ω 0xBD); NFC maps them back.
        text = unicodedata.normalize("NFC", text)
    if decoder == "mac_thai":
        return _decode_runs(text, "mac_roman", MAC_THAI, counts, "mac_thai_runs", set())
    if decoder == "cp1252_cp874_tokens":
        return _decode_runs(text, "cp1252", WINDOWS_POSITIONAL, counts, "cp1252_cp874_runs", LEGACY_SAFE_SYMBOLS)
    if decoder:
        raise ExtractionError("invalid_config", f"Unknown legacy decoder: {decoder}")
    return text


def _sub(pattern, replacement, text, counts, rule):
    new, n = re.subn(pattern, replacement, text)
    if n:
        counts[rule] += n
    return new


def normalize_text(text: str, options: dict | None = None, counts: collections.Counter | None = None) -> str:
    """Deterministic Thai normalization. Never changes digits except Thai-to-Arabic numerals."""
    options = options or {}
    counts = counts if counts is not None else collections.Counter()
    text = legacy_decode(text, options.get("legacy_decoder"), counts)
    text = _sub(r"/([A-Z][A-Za-z]+?)\d*(?=/|\s|$)",
                lambda m: THAI_GLYPH_NAMES.get(m.group(1), m.group(0)), text, counts, "glyph_name_tokens")
    text = _sub(r"(?<=[\u0e01-\u0e4e])[\x80-\x9f]",
                lambda m: WINDOWS_POSITIONAL.get(ord(m.group(0)), m.group(0)), text, counts, "c1_positional")
    pua = sum(ord(c) in PUA_MAP for c in text)
    if pua:
        text = text.translate(PUA_MAP)
        counts["pua_positional"] += pua
    # Symbol-font private-use glyphs (Wingdings/Symbol bullets) carry no retrievable text.
    text = _sub(r"[\uf000-\uf0ff]", " ", text, counts, "symbol_pua_removed")
    text = text.replace("\r", "").replace("\t", " ").replace("\u00a0", " ")
    text = _sub(r"[\u200b-\u200d\ufeff\u00ad]", "", text, counts, "zero_width_removed")
    digits = sum(c in "๐๑๒๓๔๕๖๗๘๙" for c in text)
    if digits:
        text = text.translate(THAI_DIGITS)
        counts["thai_digits"] += digits
    # Some word-processor fonts export NIKHAHIT as a space (ส าหรับ, น ้าตาล). Converted only for
    # documents verified in the config, before space cleanup can hide the pattern.
    if options.get("dropped_sara_am"):
        text = _sub(rf"(?<=[{CONSONANT}]) ([{TONE}]?)\u0e32", "\\1\u0e33", text, counts, "dropped_sara_am")
        text = _sub(rf"(?<=[{CONSONANT}][{TONE}]) \u0e32", "\u0e33", text, counts, "dropped_sara_am")
    # A line break or space can never precede a Thai combining mark; when the mark is spaced on
    # both sides (e.g. ผู้ป ่ วย), the trailing space is also an extraction artifact.
    text = _sub(rf"(?<=[{CONSONANT}{MARK}])[ ]*\n[ ]*(?=[{MARK}])", "", text, counts, "line_break_before_mark")
    text = _sub(rf"(?<=[{CONSONANT}]) +([{MARK}]+) (?=[{CONSONANT}\u0e30\u0e32\u0e33\u0e40-\u0e44])",
                r"\1", text, counts, "spaced_marks_joined")
    text = _sub(rf"(?<=[{CONSONANT}{MARK}]) +(?=[{MARK}])", "", text, counts, "space_before_mark")
    text = _sub(rf"([{MARK}])\1+", r"\1", text, counts, "duplicate_marks")
    # NIKHAHIT (or its unmapped U+FFFD glyph) + optional tone + SARA AA is SARA AM.
    text = _sub(rf"(?<=[{CONSONANT}{TONE}])\ufffd([{TONE}]?) ?\u0e32", "\\1\u0e33", text, counts, "sara_am_composed")
    text = _sub(rf"(?<=[{CONSONANT}{TONE}])\u0e4d([{TONE}]?) ?\u0e32", "\\1\u0e33", text, counts, "sara_am_composed")
    text = _sub(rf"([{TONE}])\u0e4d ?\u0e32", "\\1\u0e33", text, counts, "sara_am_composed")
    # SARA AM is never followed by SARA AA; "ำา" comes from a NIKHAHIT glyph labelled ำ plus its า glyph.
    text = _sub(r"\u0e33 ?\u0e32", "\u0e33", text, counts, "sara_am_composed")
    # SARA A/AA/AM never begin a syllable, so a preceding space is an extraction artifact.
    text = _sub(rf"(?<=[{CONSONANT}{TONE}]) +(?=[\u0e30\u0e32\u0e33])", "", text, counts, "space_before_following_vowel")
    # Letter-spaced headings (เ บ า ห ว า น): four or more single Thai clusters separated by spaces.
    cluster = (rf"(?:[\u0e40-\u0e44]?[{CONSONANT}][{MARK}]{{0,3}}[\u0e30\u0e32\u0e33\u0e45]?"
               rf"|[\u0e30\u0e32\u0e33\u0e40-\u0e46])")
    text = _sub(rf"(?<!\S)(?:{cluster} ){{3,}}{cluster}(?!\S)", lambda m: m.group(0).replace(" ", ""),
                text, counts, "letter_spacing_joined")
    text = _sub(rf"([{TONE}])([\u0e31\u0e34-\u0e37\u0e47])", r"\2\1", text, counts, "tone_vowel_order")
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def quality(text: str) -> dict:
    thai_letters = len(re.findall(r"[\u0e01-\u0e2e\u0e30\u0e32\u0e33\u0e40-\u0e44]", text))
    latin_letters = len(re.findall(r"[A-Za-z]", text))
    marks = len(re.findall(rf"[{MARK}]", text))
    orphan = len(re.findall(rf"(?:^|[^{CONSONANT}{MARK}\u0e24\u0e26])[{MARK}]", text, re.M))
    tones = len(re.findall(rf"[{TONE}]", text))
    # Latin-1 letters touching Thai letters are almost always undecoded font bytes (e.g. \u0e19\u00cf\u0e49\u0e32).
    latin1_in_thai = len(re.findall(r"(?<=[\u0e01-\u0e4e])[\u00c0-\u00ff]|[\u00c0-\u00ff](?=[\u0e01-\u0e4e])", text))
    # Accented Latin letters inside tokens with no ASCII letters are undecoded font bytes (\u00d6\u0107\u00f8\u00fc\u0109\u00ee\u0109\u00dd,
    # \u00e2\u00c3\u00a4\u00cb\u00c5\u00cd\u00b4); accented names in reference lists (Kov\u00e1cs, \u0141ukasz) keep ASCII letters and do not count.
    # \u00d7 \u00f7 and lone symbols such as \u00d8 (diameter) are genuine; mojibake comes in runs of two or more.
    mojibake = 0
    for token in text.split():
        accented = re.findall(r"[\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u024f]", token)
        if len(accented) >= 2 and not re.search(r"[A-Za-z]", token):
            mojibake += len(accented)
    garble = (text.count("\ufffd") + sum(unicodedata.category(c) in ("Cc", "Co") and c not in "\n" for c in text)
              + mojibake + latin1_in_thai)
    return {"characters": len(text), "non_whitespace": sum(not c.isspace() for c in text),
            "thai_letters": thai_letters, "latin_letters": latin_letters, "thai_marks": marks,
            "orphan_marks": orphan, "tone_marks_per_100_thai": round(100 * tones / thai_letters, 2) if thai_letters else None,
            "garbled_characters": garble, "replacement_characters": text.count("\ufffd"),
            "nul_characters": text.count("\x00")}


def page_status(q: dict) -> str:
    """empty/garbled pages are OCR candidates; degraded pages keep PDF text but need review."""
    if q["non_whitespace"] < 20:
        return "empty"
    letters = q["thai_letters"] + q["latin_letters"]
    defects = q["garbled_characters"] + q["orphan_marks"]
    if q["nul_characters"] > 2 or defects > max(5, 0.05 * letters):
        # NUL replaces tone marks ambiguously (่ or ้), so such pages cannot be repaired from text.
        return "garbled"
    if defects > max(3, 0.01 * letters):
        return "degraded"
    if defects:
        return "ok_minor_issues"
    return "ok"


def strip_running_lines(pages: list[str]) -> tuple[list[str], list[list[str]]]:
    """Remove running headers/footers and page numbers at page edges, and short watermark lines
    (e.g. "สงวนลิขสิทธิ์" on 150 HT guideline pages) repeated anywhere on at least half of the pages.
    Removed lines are returned per page so the source wording stays on record."""
    def exact(line):
        return re.sub(r"\s+", "", line)

    def numbered(line):
        return re.sub(r"\d+", "#", exact(line))
    exact_edges, numbered_edges, anywhere = collections.Counter(), collections.Counter(), collections.Counter()
    page_offsets = collections.defaultdict(collections.Counter)
    for index, text in enumerate(pages):
        lines = [x for x in text.split("\n") if x.strip()]
        exact_edges.update({exact(x) for x in lines[:3] + lines[-3:]})
        anywhere.update({exact(x) for x in lines if len(exact(x)) <= 40})
        for line in {numbered(x): x for x in lines[:3] + lines[-3:]}.values():
            numbered_edges[numbered(line)] += 1
            page_offsets[numbered(line)].update({int(n) - index for n in set(re.findall(r"\d{1,4}", line))})
    # Identical lines need 25% of pages. Lines equal only after masking numbers must appear on 40%
    # of pages and carry a number that tracks the PDF page (printed page = PDF page + constant), so
    # recurring captions such as "ตารางที่ 2" are not mistaken for running headers.
    repeated_exact = {k for k, n in exact_edges.items() if n >= max(4, 0.25 * len(pages))}
    repeated_numbered = {k for k, n in numbered_edges.items() if n >= max(4, 0.40 * len(pages))
                         and page_offsets[k] and page_offsets[k].most_common(1)[0][1] >= 0.8 * n}
    watermarks = {k for k, n in anywhere.items() if n >= 0.5 * len(pages) and re.search(r"[^\d\W]", k)}
    if len(pages) < 8:
        repeated_exact, repeated_numbered, watermarks = set(), set(), set()
    cleaned, removed = [], []
    for text in pages:
        lines = text.split("\n")
        content = [i for i, x in enumerate(lines) if x.strip()]
        edges = set(content[:3] + content[-3:])
        drop = {i for i in edges if exact(lines[i]) in repeated_exact or numbered(lines[i]) in repeated_numbered
                or re.fullmatch(r"[-–\s]*\d{1,4}[-–\s]*", lines[i])}
        drop |= {i for i in content if exact(lines[i]) in watermarks}
        removed.append([lines[i] for i in sorted(drop)])
        cleaned.append("\n".join(x for i, x in enumerate(lines) if i not in drop).strip())
    return cleaned, removed


SUPERSCRIPT_DIGITS = str.maketrans("0123456789-–", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁻")
SUPERSCRIPT_RUN = re.compile(r"[\d,\-– ]*\d[\d,\-– ]*")
FIGURE_MIN_IMAGE_SHARE = 0.25
FIGURE_MAX_TEXT = 700
FIGURE_FULL_PAGE_SHARE = 0.98
FIGURE_FULL_PAGE_MAX_TEXT = 150


def attached_to_preceding_text(before: str) -> bool:
    """Citation superscripts sit directly after a word, number or closing mark (AKI⁴⁶, 25⁷⁰, ยา⁸).

    Body numbers set in a smaller Latin font inside Thai text follow a space ("อายุ 35 ปี") or a slash
    ("1/3 ถ้วย"), and "3.3" after a digit and period is a decimal or list number, not a citation.
    """
    if not before:
        return False
    last = before[-1]
    if last in ".," and len(before) > 1 and before[-2].isdigit():
        return False
    return last.isalnum() or "ก" <= last <= "๛" or last in ")]%.,”\""


def extract_page(page) -> tuple[str, dict]:
    """pypdf text plus layout signals from the same pass.

    Raised digit runs set in a smaller font become Unicode superscripts, so citation numbers no longer
    merge into values ("ร้อยละ 25⁷⁰", not "2570"). Superscripts keep what is printed; whether a run is a
    citation or an exponent (กก./ม.²) is not inferred. Image area is measured to find figure pages whose
    only extractable text is a caption.
    """
    runs, image_area = [], [0.0]
    resources = page.get("/Resources")
    xobjects = resources.get_object().get("/XObject") if resources else None
    xobjects = xobjects.get_object() if xobjects else {}

    def before(operator, operands, cm, tm):
        if operator == b"Do" and operands and operands[0] in xobjects:
            if xobjects[operands[0]].get_object().get("/Subtype") == "/Image":
                image_area[0] += abs(cm[0] * cm[3] - cm[1] * cm[2])

    def visit(text, cm, tm, font, size):
        scale = math.hypot(tm[0], tm[1]) * math.hypot(cm[0], cm[1])
        runs.append((text, size * scale, tm[5] * cm[3] + cm[5]))

    text = page.extract_text(visitor_text=visit, visitor_operand_before=before) or ""
    sizes = [size for run, size, _ in runs for char in run if not char.isspace()]
    median = statistics.median(sizes) if sizes else 0
    edits, cursor, baseline, group_end = [], 0, None, None
    for run, size, y in runs:
        position = text.find(run, cursor) if run else -1
        if position < 0:
            continue  # the visitor can report text that extract_text dropped (e.g. a repeated header)
        cursor = position + len(run)
        if not run.strip() or not median:
            continue
        if size >= 0.8 * median:
            baseline = y
        elif (SUPERSCRIPT_RUN.fullmatch(run.strip()) and baseline is not None
              and 0.15 * median < y - baseline < 0.8 * median):
            # Citations in this corpus are raised 0.29-0.39 x the body size; a run 1.6x higher is on
            # another line (brochure layouts), not a superscript.
            # The raised run can sit in its own text block, so pypdf wraps it in line breaks; join it back.
            start = position - 1 if position and text[position - 1] == "\n" else position
            gap = text[group_end:position] if group_end is not None else None
            continues_group = gap is not None and re.fullmatch(r"[\s,\-–]*", gap) and (
                re.search(r"[,\-–]", gap) or run.strip()[:1] in ",-–")
            if continues_group:
                # Next citation in a group (⁷⁰, ⁷¹): keep its separators, drop pypdf's line breaks.
                edits.append((group_end, cursor, gap.replace("\n", "") + run.strip().translate(SUPERSCRIPT_DIGITS)))
                group_end = cursor
                continue
            if attached_to_preceding_text(text[:start]) and not run[:1].isspace():
                start = max(start, edits[-1][1]) if edits else start
                edits.append((start, cursor, run.strip().translate(SUPERSCRIPT_DIGITS)))
                group_end = cursor
                continue
        if not re.fullmatch(r"[,\-–]+", run.strip()):
            group_end = None  # separators inside a citation group keep it open
    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    box = page.mediabox
    page_area = abs(float(box.width) * float(box.height)) or 1.0
    return text, {"superscript_runs": len(edits), "image_share": round(min(image_area[0] / page_area, 1.0), 3)}


def underlined_signs(plumber_page) -> list[bool]:
    """For each "<" or ">" in content order, whether a thin rule as wide as the glyph sits under it.

    Word-processor PDFs draw ≥/≤ as an underlined >/<; the text layer only has ">" (CKD 2565 p29).
    """
    signs = [c for c in plumber_page.chars if c["text"] in "<>"]
    rules = [o for o in plumber_page.rects + plumber_page.lines if o["height"] <= 1.5]
    flags = []
    for char in signs:
        width, height = char["x1"] - char["x0"], char["bottom"] - char["top"]
        flags.append(any(min(o["x1"], char["x1"]) - max(o["x0"], char["x0"]) >= 0.7 * width
                         and o["x1"] - o["x0"] <= 2.5 * width
                         and char["top"] + 0.5 * height <= o["top"] <= char["bottom"] + 3 for o in rules))
    return flags


def apply_underlined_signs(text: str, flags: list[bool]) -> tuple[str, str, int]:
    """Convert underlined signs by occurrence order; refuse when the two layers disagree on the count."""
    if not any(flags):
        return text, "no_underlined_signs", 0
    positions = [m.start() for m in re.finditer(r"[<>]", text)]
    if len(positions) != len(flags):
        return text, "unverified", 0
    chars = list(text)
    for position, flag in zip(positions, flags):
        if flag:
            chars[position] = "≥" if chars[position] == ">" else "≤"
    return "".join(chars), "converted", sum(flags)


def dedupe_layered_lines(text: str) -> tuple[str, int]:
    """Drop lines whose content already appeared on the page (documents with stacked text layers).

    Compared without whitespace and list bullets, because each layer wraps lines differently. Enabled
    per document only: ordinary tables can legitimately repeat rows.
    """
    seen, kept, removed = "", [], 0
    for line in text.split("\n"):
        key = re.sub(r"[\s❶-➓•]", "", line)
        if len(key) >= 20 and key in seen:
            removed += 1
            continue
        seen += key
        kept.append(line)
    return "\n".join(kept), removed


def load_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    documents = config.get("documents")
    if not isinstance(documents, dict):
        raise ExtractionError("invalid_config", "Config requires a documents object")
    allowed = {"legacy_decoder", "dropped_sara_am", "dedupe_layered_text", "review_hold_pages", "evidence"}
    for doc_id, options in documents.items():
        base.validate_id(doc_id)
        if not isinstance(options, dict) or set(options) - allowed:
            raise ExtractionError("invalid_config", f"Unsupported options for {doc_id}")
        holds = options.get("review_hold_pages", {})
        if not isinstance(holds, dict) or not all(str(p).isdigit() and isinstance(n, str) and n for p, n in holds.items()):
            raise ExtractionError("invalid_config", f"review_hold_pages for {doc_id} must map page numbers to notes")
    return documents


def ocr_page(data: bytes, page_number: int, staging: Path, dpi: int, languages: str,
             renderer: str, tesseract: str) -> str:
    snapshot = staging / "_source_snapshot.pdf"
    if not snapshot.exists():
        snapshot.write_bytes(data)
    image = staging / "_ocr" / f"page-{page_number:04d}"
    image.parent.mkdir(exist_ok=True)
    base.run_local([renderer, "-f", str(page_number), "-l", str(page_number), "-singlefile",
                    "-r", str(dpi), "-png", str(snapshot), str(image)])
    base.run_local([tesseract, str(image.with_suffix(".png")), str(image), "-l", languages], timeout=180)
    return image.with_suffix(".txt").read_text(encoding="utf-8")


def normalize_document(record: dict, raw_root: Path, out_root: Path, options: dict, *, ocr: bool = False,
                       max_ocr_pages: int = 0, dpi: int = 300, ocr_languages: str = "tha+eng",
                       renderer: str = "pdftoppm", tesseract: str = "tesseract",
                       max_bytes: int = 150 * 1024 * 1024, usage: dict | None = None) -> dict:
    usage = usage if usage is not None else {"page_attempts": 0, "ocr_attempts": 0}
    doc_id = base.validate_id(record["document_id"])
    source = base.contained(base.contained(raw_root, doc_id), "source.pdf")
    destination = base.contained(out_root, doc_id)
    if not source.is_file():
        return {"document_id": doc_id, "outcome": "missing_local_file"}
    if destination.exists():
        return {"document_id": doc_id, "outcome": "existing_output_preserved",
                "message": "Use a new --out-dir for another revision; outputs are never overwritten"}
    if source.stat().st_size > max_bytes:
        raise ExtractionError("source_size_limit", f"PDF exceeds {max_bytes} bytes")
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    expected = record.get("sha256")
    if expected is not None and expected.casefold() != digest:
        raise ExtractionError("manifest_hash_mismatch", "Local PDF SHA-256 does not match the manifest")
    if ocr and (not shutil.which(renderer) or not shutil.which(tesseract)):
        raise ExtractionError("ocr_unavailable", "Renderer or Tesseract not found")
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise ExtractionError("encrypted_pdf", "PDF is encrypted")
        labels = reader.page_labels
        font_report = repair_fonts(reader)
    except ExtractionError:
        raise
    except Exception as exc:
        raise ExtractionError("invalid_pdf", f"Cannot read PDF: {type(exc).__name__}: {exc}") from exc

    counts_per_page, extracted, normalized, errors, layout = [], [], [], [], []
    plumber = None
    try:
        for index, page in enumerate(reader.pages):
            usage["page_attempts"] += 1
            page_errors = []
            try:
                text, signals = extract_page(page)
            except Exception as exc:
                text, signals = "", {"superscript_runs": 0, "image_share": None}
                page_errors.append(f"text: {type(exc).__name__}: {exc}")
            signals["comparison_signs"], signals["underlined_signs_converted"] = "no_signs", 0
            if re.search(r"[<>]", text):
                if pdfplumber is None:
                    signals["comparison_signs"] = "unavailable"
                else:
                    try:
                        plumber = plumber or pdfplumber.open(io.BytesIO(data))
                        text, state, converted = apply_underlined_signs(text, underlined_signs(plumber.pages[index]))
                        signals["comparison_signs"], signals["underlined_signs_converted"] = state, converted
                    except Exception as exc:
                        signals["comparison_signs"] = "unverified"
                        page_errors.append(f"signs: {type(exc).__name__}: {exc}")
            counts = collections.Counter()
            extracted.append(text)
            page_text = normalize_text(text, options, counts)
            if options.get("dedupe_layered_text"):
                page_text, dropped = dedupe_layered_lines(page_text)
                if dropped:
                    counts["layered_lines_removed"] += dropped
            normalized.append(page_text)
            counts_per_page.append(counts)
            errors.append(page_errors)
            layout.append(signals)
    finally:
        if plumber is not None:
            plumber.close()
    cleaned, removed = strip_running_lines(normalized)
    holds = {int(page): note for page, note in options.get("review_hold_pages", {}).items()}

    out_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{doc_id}-", dir=out_root) as temporary:
        staging = Path(temporary)
        rows, ocr_done = [], 0
        for index, text in enumerate(cleaned):
            q = quality(text)
            status = page_status(q)
            signals = layout[index]
            review_note = None
            if status in ("ok", "ok_minor_issues") and signals["comparison_signs"] in ("unverified", "unavailable"):
                status = "degraded"  # underlined ≥/≤ may still read as >/<
            share = signals["image_share"] or 0
            # Image-only figure/flowchart: only its caption is in the text layer. A full-page background
            # image under real text (illustrated manuals) counts only when almost no text exists (covers).
            if status in ("ok", "ok_minor_issues") and (
                    (FIGURE_MIN_IMAGE_SHARE <= share < FIGURE_FULL_PAGE_SHARE and q["non_whitespace"] < FIGURE_MAX_TEXT)
                    or (share >= FIGURE_FULL_PAGE_SHARE and q["non_whitespace"] < FIGURE_FULL_PAGE_MAX_TEXT)):
                status = "figure_review"
            if index + 1 in holds:
                status, review_note = "review_hold", holds[index + 1]
            row = {"document_id": doc_id, "source_sha256": digest, "pdf_page": index + 1,
                   "pdf_page_label": labels[index] if index < len(labels) else None, "printed_page_number": None,
                   "text": text, "text_source": "pdf_text_repaired", "status": status, "pdf_text_status": status,
                   "review_note": review_note, "quality": q, "layout_checks": signals,
                   "normalization_counts": dict(sorted(counts_per_page[index].items())),
                   "removed_edge_lines": removed[index], "pre_normalization_text": extracted[index],
                   "ocr_text": None, "ocr_quality": None, "ocr_method": None, "errors": errors[index],
                   "human_review": None}
            if ocr and status in ("empty", "garbled", "figure_review") and ocr_done < max_ocr_pages:
                ocr_done += 1
                usage["ocr_attempts"] += 1
                try:
                    ocr_counts = collections.Counter()
                    ocr_text = normalize_text(ocr_page(data, index + 1, staging, dpi, ocr_languages,
                                                       renderer, tesseract), {}, ocr_counts)
                    oq = quality(ocr_text)
                    row.update(ocr_text=ocr_text, ocr_quality=oq, ocr_method=f"pdftoppm:{dpi}dpi+tesseract:{ocr_languages}")
                    # Thai OCR here splits words and drops tone marks, so it only fills pages without
                    # PDF text and with real Thai content (not just navigation bars). Garbled PDF text
                    # is kept; its OCR stays alongside for review. OCR is never treated as reviewed text.
                    if (status == "empty" and page_status(oq) not in ("empty", "garbled")
                            and oq["thai_letters"] >= OCR_MIN_THAI_LETTERS):
                        row.update(text=ocr_text, text_source="ocr", status="ocr_unreviewed")
                except (ExtractionError, OSError, UnicodeError) as exc:
                    row["errors"].append(f"ocr: {getattr(exc, 'code', 'ocr_failed')}: {exc}")
            rows.append(row)
        page_bytes = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode("utf-8")
        (staging / "pages.jsonl").write_bytes(page_bytes)
        status_pages = collections.defaultdict(list)
        for r in rows:
            status_pages[r["status"]].append(r["pdf_page"])
        totals = collections.Counter()
        for c in counts_per_page:
            totals.update(c)
        summary = {
            "document_id": doc_id, "title": record.get("title"), "source_sha256": digest,
            "pdf_pages": len(rows), "options": {k: v for k, v in options.items() if k != "evidence"},
            "font_repair": font_report, "normalization_totals": dict(sorted(totals.items())),
            "layout_totals": {
                "superscript_runs": sum(s["superscript_runs"] for s in layout),
                "underlined_signs_converted": sum(s["underlined_signs_converted"] for s in layout),
                "comparison_sign_pages": dict(sorted(collections.Counter(s["comparison_signs"] for s in layout).items())),
                "figure_pages": [r["pdf_page"] for r in rows if r["pdf_text_status"] == "figure_review"]},
            "review_hold_pages": {str(p): n for p, n in sorted(holds.items())},
            "status_counts": {k: len(v) for k, v in sorted(status_pages.items())},
            "status_pages": {k: v for k, v in sorted(status_pages.items()) if k != "ok"},
            "removed_edge_lines": sum(len(x) for x in removed), "ocr_pages": ocr_done,
            "configuration": {"tool_version": TOOL_VERSION, "pypdf_version": PYPDF_VERSION, "ocr": ocr,
                              "dpi": dpi if ocr else None, "ocr_languages": ocr_languages if ocr else None},
            "pages_jsonl_sha256": hashlib.sha256(page_bytes).hexdigest(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "clinical_or_layout_qa_performed": False, "human_approval": None,
            "notes": ["Font repairs and decoders are deterministic and were spot-checked against rendered pages;"
                      " they are not a page-by-page fidelity review.",
                      "Status is a heuristic retrieval gate, not clinical or source-content approval.",
                      "OCR text is unreviewed; tables, units and reading order still require visual QA."]}
        for leftover in ("_source_snapshot.pdf", "_ocr"):
            path = staging / leftover
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        (staging / "normalization.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                                    encoding="utf-8")
        staging.rename(destination)
    return {"document_id": doc_id, "outcome": "normalized", "summary": summary}


def main(argv=None) -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/documents.jsonl"))
    parser.add_argument("--cohort", type=Path, default=Path("data/manifests/corpus_50_candidates.csv"))
    parser.add_argument("--rights-review", type=Path, default=root / "data/manifests/rights_review_20261005.json")
    parser.add_argument("--config", type=Path, default=root / "configs/thai_normalization.json")
    parser.add_argument("--document-id", action="append", default=[])
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--out-dir", type=Path, default=Path("data/processed/normalized-v2"))
    parser.add_argument("--ocr", action="store_true", help="Opt-in local OCR for empty/garbled pages")
    parser.add_argument("--max-ocr-pages-per-document", type=int, default=60)
    parser.add_argument("--max-total-ocr-pages", type=int, default=400)
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--ocr-languages", default="tha+eng")
    parser.add_argument("--renderer", default="pdftoppm")
    parser.add_argument("--tesseract", default="tesseract")
    args = parser.parse_args(argv)
    if min(args.max_ocr_pages_per_document, args.max_total_ocr_pages) < 0 or not 72 <= args.dpi <= 400:
        parser.error("OCR limits must be nonnegative; DPI must be72..400")
    try:
        records = base.selected_records(args.manifest, args.cohort, args.document_id)
        rights = json.loads(args.rights_review.read_text(encoding="utf-8"))
        holds = {base.validate_id(r["document_id"]) for r in rights["records"] if r.get("automated_extraction_hold") is True}
        config = load_config(args.config)
    except (ExtractionError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"outcome": "selection_error", "error_code": getattr(exc, "code", "invalid_input"),
                          "message": str(exc)}, ensure_ascii=False))
        return 2
    results, failures, remaining_ocr = [], 0, args.max_total_ocr_pages
    page_attempts = 0
    for record in records:
        if record["document_id"] in holds:
            results.append({"document_id": record["document_id"], "outcome": "rights_hold"})
            continue
        usage = {"page_attempts": 0, "ocr_attempts": 0}
        try:
            result = normalize_document(record, args.raw_dir, args.out_dir, config.get(record["document_id"], {}),
                                        ocr=args.ocr, max_ocr_pages=min(args.max_ocr_pages_per_document, remaining_ocr),
                                        dpi=args.dpi, ocr_languages=args.ocr_languages, renderer=args.renderer,
                                        tesseract=args.tesseract, usage=usage)
        except Exception as exc:
            failures += 1
            result = {"document_id": record["document_id"], "outcome": "error",
                      "error_code": getattr(exc, "code", "local_io_error"), "message": str(exc)}
        remaining_ocr -= usage["ocr_attempts"]
        page_attempts += usage["page_attempts"]
        if "summary" in result:
            s = result.pop("summary")
            result.update(status_counts=s["status_counts"], font_repair=s["font_repair"]["font_actions"],
                          ocr_pages=s["ocr_pages"])
        results.append(result)
    print(json.dumps({"tool": "normalize_thai", "version": TOOL_VERSION, "results": results,
                      "document_failures": failures, "page_attempts": page_attempts,
                      "ocr_attempts": args.max_total_ocr_pages - remaining_ocr, "network_requests": 0,
                      "paid_api_calls": 0, "manifest_modified": False}, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
