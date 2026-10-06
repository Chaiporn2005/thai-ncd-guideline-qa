"""Thai normalization rules and font-map repairs on synthetic inputs; no publisher PDFs or network."""
import contextlib
import importlib.util
import io
import json
import struct
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject
from reportlab.pdfgen import canvas

spec = importlib.util.spec_from_file_location("normalize_thai", Path(__file__).resolve().parents[1] / "scripts/normalize_thai.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def stream(data: bytes) -> DecodedStreamObject:
    item = DecodedStreamObject()
    item.set_data(data)
    return item


def cmap(entries: dict[int, str], digits: int = 4) -> DecodedStreamObject:
    body = "\n".join(f"<{code:0{digits}X}> <{''.join(f'{ord(c):04X}' for c in value)}>" for code, value in entries.items())
    return stream(f"begincmap\n{len(entries)} beginbfchar\n{body}\nendbfchar\nendcmap".encode("ascii"))


def truetype_with_glyphs(count: int) -> bytes:
    # Offset table + one table record + maxp (version 0.5, numGlyphs).
    return (struct.pack(">IHHHH", 0x00010000, 1, 16, 0, 0) + struct.pack(">4sIII", b"maxp", 0, 28, 6)
            + struct.pack(">IH", 0x00005000, count))


def type0_font(name: str, glyphs: int, entries: dict[int, str] | None) -> DictionaryObject:
    descriptor = DictionaryObject({NameObject("/FontFile2"): stream(truetype_with_glyphs(glyphs))})
    descendant = DictionaryObject({NameObject("/CIDToGIDMap"): NameObject("/Identity"),
                                   NameObject("/FontDescriptor"): descriptor})
    font = DictionaryObject({NameObject("/Subtype"): NameObject("/Type0"), NameObject("/BaseFont"): NameObject(name),
                             NameObject("/DescendantFonts"): ArrayObject([descendant])})
    if entries is not None:
        font[NameObject("/ToUnicode")] = cmap(entries)
    return font


def simple_font(entries: dict[int, str]) -> DictionaryObject:
    return DictionaryObject({NameObject("/Subtype"): NameObject("/TrueType"), NameObject("/ToUnicode"): cmap(entries, 2)})


def current_map(font) -> dict[int, str]:
    return tool.parse_tounicode(font["/ToUnicode"].get_object().get_data())


class FontRepairTests(unittest.TestCase):
    def test_sarabun_glyph_order(self):
        self.assertEqual(tool.sarabun_char(0xD6), "ก")
        self.assertEqual(tool.sarabun_char(0x111), "เ")
        self.assertEqual(tool.sarabun_char(0x12), "1")
        self.assertEqual(tool.sarabun_char(0x153), "≥")
        self.assertEqual(tool.sarabun_char(0x160), "่")

    def test_broken_sarabun_tounicode_is_rebuilt_from_glyph_ids(self):
        broken = {0xD6: "ก", 0xD7: "ข", 0xD9: "ค", 0xDC: "ง", 0xE9: "ด", 0xEC: "ท", 0xEE: "น", 0xF8: "ร",
                  0x100: "หิ", 0x10A: "่", 0x119: "�", 0x107: "า"}
        font = type0_font("/ABCDEF+THSarabunNew", 511, broken)
        action, changed = tool.repair_sarabun_font(font)
        self.assertEqual(action, "repaired_tounicode")
        repaired = current_map(font)
        self.assertEqual((repaired[0x100], repaired[0x10A], repaired[0x119]), ("ห", "ี", "่"))
        self.assertEqual(changed, 3)

    def test_missing_sarabun_tounicode_is_added(self):
        font = type0_font("/ABCDEF+THSarabunNew-Bold", 511, None)
        self.assertEqual(tool.repair_sarabun_font(font)[0], "added_tounicode")
        repaired = current_map(font)
        self.assertEqual((repaired[0x12], repaired[0x13], repaired[0x17], repaired[0x153]), ("1", "2", "6", "≥"))

    def test_compact_subset_and_other_fonts_are_not_changed(self):
        compact = type0_font("/ABCDEF+THSarabunNew", 40, {0x03: "1"})
        self.assertEqual(tool.repair_sarabun_font(compact)[0], "skip_compact_subset")
        self.assertEqual(current_map(compact), {0x03: "1"})
        self.assertEqual(tool.repair_sarabun_font(type0_font("/X+Kanit", 511, {1: "a"}))[0], "not_applicable")

    def test_low_agreement_font_is_skipped(self):
        font = type0_font("/ABCDEF+THSarabunPSK", 511, {0xD6: "ข", 0xD7: "ค", 0xD9: "ง"})
        self.assertEqual(tool.repair_sarabun_font(font)[0], "skip_low_agreement")

    def test_sara_aa_labelled_as_sara_am(self):
        font = type0_font("/X+SukhumvitSet-Bold", 100, {0x10: "ำ", 0x11: "�", 0x12: "ต"})
        self.assertEqual(tool.repair_sara_aa_font(font)[0], "remapped_sara_aa")
        self.assertEqual(current_map(font)[0x10], "า")
        intact = type0_font("/X+Other", 100, {0x10: "ำ", 0x12: "า", 0x11: "�"})
        self.assertEqual(tool.repair_sara_aa_font(intact)[0], "not_applicable")

    def test_nikhahit_labelled_as_second_space_keeps_one_byte_codes(self):
        font = simple_font({0x03: " ", 0xCE: "์", 0xCF: " "})
        self.assertEqual(tool.repair_nikhahit_space_font(font)[0], "remapped_nikhahit_space")
        data = font["/ToUnicode"].get_object().get_data().decode("ascii")
        self.assertIn("<CF> <0E4D>", data)
        self.assertIn("<00> <FF>", data)

    def test_first_cluster_labels_are_reduced_only_when_marks_exist(self):
        font = type0_font("/X+9", 100, {0x86: "คื", 0x90: "ื", 0x91: "ฤๅ"})
        self.assertEqual(tool.repair_cluster_font(font), ("reduced_cluster_labels", 1))
        self.assertEqual(current_map(font), {0x86: "ค", 0x90: "ื", 0x91: "ฤๅ"})
        no_mark = type0_font("/X+9", 100, {0x86: "คื"})
        self.assertEqual(tool.repair_cluster_font(no_mark)[0], "not_applicable")

    def test_bfrange_arrays_parse_and_unsupported_ranges_are_rejected(self):
        data = b"beginbfrange\n<00CE> <00CF> [<0E4C> <0020>]\n<0010> <0011> <0E01>\nendbfrange"
        self.assertEqual(tool.parse_tounicode(data), {0xCE: "์", 0xCF: " ", 0x10: "ก", 0x11: "ข"})
        self.assertIsNone(tool.parse_tounicode(b"beginbfrange\n<01> <02> <0E2B0E34>\nendbfrange"))


class TextRuleTests(unittest.TestCase):
    def norm(self, text, **options):
        return tool.normalize_text(text, options)

    def test_positional_and_sara_am_repairs(self):
        self.assertEqual(self.norm("คุณคาอาหาร"), "คุณค่าอาหาร")
        self.assertEqual(self.norm("ส�าหรับ น�้า"), "สำหรับ น้ำ")
        self.assertEqual(self.norm("นํ้าหนัก นํ้ าตาล"), "น้ำหนัก น้ำตาล")
        self.assertEqual(self.norm("ขอนแก\x8bน ป\x86วย เป\x9aน"), "ขอนแก่น ป่วย เป็น")

    def test_spacing_artifacts(self):
        self.assertEqual(self.norm("อ ัลบูมิน ผู้ป ่ วย จังหว\nัด"), "อัลบูมิน ผู้ป่วย จังหวัด")
        self.assertEqual(self.norm("เนื่องจ าก อย่ าง"), "เนื่องจาก อย่าง")
        # Source PDFs keep a double space between letter-spaced words.
        self.assertEqual(self.norm("เ บ า ห ว า น  คื อ อ ะ ไ ร  ?"), "เบาหวาน คืออะไร ?")

    def test_dropped_sara_am_only_when_configured(self):
        self.assertEqual(self.norm("ส าหรับ น ้าตาล", dropped_sara_am=True), "สำหรับ น้ำตาล")
        self.assertEqual(self.norm("ส าหรับ"), "สาหรับ")

    def test_numbers_are_preserved_and_thai_digits_converted(self):
        self.assertEqual(self.norm("มีค่า ≥126 มก./ดล. หน้า ๒๐"), "มีค่า ≥126 มก./ดล. หน้า 20")

    def test_legacy_decoders(self):
        self.assertEqual(self.norm("°≈‡¡Á¥ \xa0—≠≠“≥", legacy_decoder="mac_thai"), "กลเม็ด สัญญาณ")
        self.assertEqual(self.norm("¤Ù‹Á×Í 2 ¼ แผ่น", legacy_decoder="cp1252_cp874_tokens"), "คู่มือ 2 ¼ แผ่น")
        self.assertEqual(self.norm("café", legacy_decoder="cp1252_cp874_tokens"), "café")
        self.assertEqual(self.norm("/ToTao/OAng/NoNu/ThoThahan/SaraIi/MaiEk2"), "ตอนที่")
        with self.assertRaises(tool.ExtractionError):
            self.norm("x", legacy_decoder="unknown")

    def test_quality_gate(self):
        self.assertEqual(tool.page_status(tool.quality("")), "empty")
        self.assertEqual(tool.page_status(tool.quality("ÖćøüĉîĉÝÞĆ÷ēøÙđïćĀüćî " * 5)), "garbled")
        self.assertEqual(tool.page_status(tool.quality("เวลาที\x00คุณไปตรวจ เชื\x00อ ที\x00")), "garbled")
        self.assertEqual(tool.page_status(tool.quality("การวินิจฉัยโรคเบาหวานใช้ผลการตรวจเลือดเป็นหลัก")), "ok")
        self.assertGreater(tool.quality("นÏ้าตาล")["garbled_characters"], 0)

    def test_running_headers_and_page_numbers_removed(self):
        topics = ["นิยาม", "วินิจฉัย", "รักษา", "ยา", "อาหาร", "ออกกำลังกาย", "ติดตาม", "แทรกซ้อน", "สูงอายุ", "สรุป"]
        pages = [f"{i + 10} แนวทางเวชปฏิบัติ 2567\n{topic}\nตารางที่ {i * 2}\n{i + 10}" for i, topic in enumerate(topics)]
        cleaned, removed = tool.strip_running_lines(pages)
        self.assertEqual(removed[3], ["13 แนวทางเวชปฏิบัติ 2567", "13"])
        # A numbered caption on every page edge is content when its number does not track the page.
        self.assertEqual(cleaned[3], "ยา\nตารางที่ 6")


class CommandLineTests(unittest.TestCase):
    def setUp(self):
        fixture_root = Path(__file__).resolve().parents[1] / "tmp/normalization-tests"
        fixture_root.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="งาน-", dir=fixture_root)
        self.root = Path(self.temporary.name)
        for doc_id in ("sample", "held"):
            folder = self.root / "raw" / doc_id
            folder.mkdir(parents=True)
            pdf = canvas.Canvas(str(folder / "source.pdf"), pagesize=(300, 200), invariant=True)
            pdf.drawString(20, 100, "FPG 126 mg/dL threshold text for retrieval checks")
            pdf.showPage()
            pdf.save()
        (self.root / "manifest.jsonl").write_text(
            "".join(json.dumps({"document_id": d}) + "\n" for d in ("sample", "held")), encoding="utf-8")
        (self.root / "cohort.csv").write_text("document_id\nsample\nheld\n", encoding="utf-8")
        (self.root / "rights.json").write_text(json.dumps(
            {"records": [{"document_id": "held", "automated_extraction_hold": True}]}), encoding="utf-8")
        (self.root / "config.json").write_text(json.dumps({"documents": {}}), encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def run_tool(self):
        args = ["--manifest", str(self.root / "manifest.jsonl"), "--cohort", str(self.root / "cohort.csv"),
                "--rights-review", str(self.root / "rights.json"), "--config", str(self.root / "config.json"),
                "--raw-dir", str(self.root / "raw"), "--out-dir", str(self.root / "out")]
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = tool.main(args)
        return code, json.loads(output.getvalue())

    def test_ocr_fills_only_empty_pages_with_thai_content(self):
        folder = self.root / "raw" / "scan"
        folder.mkdir(parents=True)
        pdf = canvas.Canvas(str(folder / "source.pdf"), pagesize=(300, 200), invariant=True)
        pdf.showPage()
        pdf.showPage()
        pdf.save()
        texts = iter(["Previous Page Contents Next Page", "การตรวจระดับพลาสมากลูโคสตอนเช้าหลังอดอาหารข้ามคืนมากกว่า 8 ชั่วโมง"])
        with unittest.mock.patch.object(tool.shutil, "which", return_value="tool"), \
                unittest.mock.patch.object(tool, "ocr_page", side_effect=lambda *a, **k: next(texts)):
            result = tool.normalize_document({"document_id": "scan"}, self.root / "raw", self.root / "out", {}, ocr=True,
                                             max_ocr_pages=5)
        rows = [json.loads(x) for x in (self.root / "out/scan/pages.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([r["status"] for r in rows], ["empty", "ocr_unreviewed"])
        self.assertEqual(rows[1]["text_source"], "ocr")
        self.assertEqual(rows[1]["pdf_text_status"], "empty")
        self.assertIsNotNone(rows[0]["ocr_text"])
        self.assertEqual(result["summary"]["ocr_pages"], 2)

    def test_outputs_rights_hold_and_no_overwrite(self):
        code, report = self.run_tool()
        self.assertEqual(code, 0)
        outcomes = {r["document_id"]: r["outcome"] for r in report["results"]}
        self.assertEqual(outcomes, {"sample": "normalized", "held": "rights_hold"})
        self.assertFalse((self.root / "out/held").exists())
        row = json.loads((self.root / "out/sample/pages.jsonl").read_text(encoding="utf-8").splitlines()[0])
        self.assertIn("126 mg/dL", row["text"])
        self.assertEqual(row["status"], "ok")
        summary = json.loads((self.root / "out/sample/normalization.json").read_text(encoding="utf-8"))
        self.assertIsNone(summary["human_approval"])
        self.assertNotIn("text", summary)
        code, report = self.run_tool()
        self.assertEqual(report["results"][0]["outcome"], "existing_output_preserved")


if __name__ == "__main__":
    unittest.main()
