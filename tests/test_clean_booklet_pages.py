"""Booklet cleanup: furniture goes, body lines stay, every removed line is accounted for."""
import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("clean_booklet_pages", SCRIPTS / "clean_booklet_pages.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

BODY = "# ระดับไขมันในเลือด\n\nไขมันดี HDL มากกว่า 40 มก./ดล.\n\nไขมันไม่ดี LDL น้อยกว่า 100 มก./ดล.\n"
FOOTER = "\nDDC กรมควบคุมโรค Department of Disease Control\nกองโรคไม่ติดต่อ\nสายด่วน กรมควบคุมโรค 1422\nรอบรู้ สุขภาพ ด้านโรคไม่ติดต่อ @NCD_DDC\n\nHealth Literacy: Together Fight NCDs"
TABS = "\nโรคความดัน โลหิตสูง\nโรค เบาหวาน\nโรคไต\nโรคหัวใจ\nโรคหลอดเลือด สมอง (Stroke)\nโรคอ้วน\nการลดการบริโภค เกลือและโซเดียม\n"


class Clean(unittest.TestCase):
    def test_footer_and_tab_strip_are_removed_and_body_stays(self):
        cleaned, removed = tool.clean_page_text(BODY + TABS + FOOTER)
        self.assertEqual(cleaned, BODY.strip())
        self.assertEqual(len(removed["side_tabs"]), 7)
        self.assertEqual(len(removed["footer"]), 5)

    def test_a_single_disease_line_in_the_body_is_not_a_tab(self):
        text = "# 7 สิ่งมหัศจรรย์\n\n**โรคเบาหวาน**\n*   วัด: น้ำหนัก ควบคุมให้สมส่วน\n\n**โรคไต**\n*   ตรวจ: ระดับไขมัน"
        cleaned, removed = tool.clean_page_text(text)
        self.assertEqual((cleaned, removed), (text, {}))

    def test_second_copy_of_the_body_is_dropped_first_copy_kept(self):
        text = "หากมีอาการเหล่านี้ต้องรีบรับการรักษา\n\n*   เจ็บแน่นหน้าอก\n*   ใจสั่น\n\n**เจ็บแน่นหน้าอก**\n\n**หากมีอาการเหล่านี้ต้องรีบรับการรักษา**"
        cleaned, removed = tool.clean_page_text(text)
        self.assertEqual(cleaned.count("เจ็บแน่นหน้าอก"), 1)
        self.assertEqual(len(removed["duplicates"]), 2)

    def test_footer_is_found_at_the_end_even_after_a_long_second_copy(self):
        copy = "\n".join(f"ข้อแนะนำข้อที่ {n} ของโปสเตอร์" for n in range(1, 25))
        text = copy + "\n\nDDC กรมควบคุมโรค Department of Disease Control\nสายด่วน กรมควบคุมโรค 1422\n" + TABS + copy
        cleaned, removed = tool.clean_page_text(text)
        self.assertEqual(len(removed["footer"]), 2)
        self.assertNotIn("1422", cleaned)

    def test_logo_block_is_removed_only_on_poster_pages(self):
        body = "# หัวข้อ\n" + "\n".join(f"เนื้อหาบรรทัดที่ {n} ของโปสเตอร์" for n in range(1, 30))
        text = "กระทรวงสาธารณสุข MINISTRY OF PUBLIC HEALTH\nกรมควบคุมโรค\n\n" + body
        self.assertEqual(tool.clean_page_text(text, poster=True)[0], body)
        self.assertEqual(tool.clean_page_text(text, poster=False)[0], text)


class Category(unittest.TestCase):
    def test_active_tab_from_image_agrees_with_toc(self):
        info = {"tabs": 9, "active_from_image": 2}
        cat = tool.category_for(34, info)  # printed page 32 is in the diabetes range 30-39
        self.assertEqual((cat["tab"], cat["label"], cat["toc_agrees"]), (2, "โรคเบาหวาน", True))

    def test_all_pale_strip_in_the_intro_section_is_not_a_disease_category(self):
        cat = tool.category_for(13, {"tabs": 9, "active_from_image": None})
        self.assertEqual((cat["tab"], cat["source"]), (None, "image_all_tabs_pale"))

    def test_section_opener_without_a_strip_takes_its_category_from_the_toc(self):
        cat = tool.category_for(32, {"tabs": 0, "active_from_image": None})  # printed 30 starts diabetes
        self.assertEqual((cat["tab"], cat["source"]), (2, "toc_section_opener"))
        self.assertIsNone(tool.category_for(95, {"tabs": 0, "active_from_image": None}))  # back matter


class Opener(unittest.TestCase):
    def test_section_opener_waiting_for_ocr_becomes_a_title_only_page(self):
        import json
        import tempfile
        tabs = {"71": {"tabs": 0, "active_from_image": None}}
        row = {"document_id": tool.DOCUMENT, "source_sha256": "a" * 64, "pdf_page": 71, "text": "", "status": "garbled",
               "text_source": "pdf_text_repaired", "needs_ocr": True,
               "index_exclusion": {"reason": "awaiting_reocr"}}
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            src = root / "src" / tool.DOCUMENT
            src.mkdir(parents=True)
            (src / "pages.jsonl").write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
            (src / "normalization.json").write_text(json.dumps({"pages_jsonl_sha256": "x"}), encoding="utf-8")
            (root / "tabs.json").write_text(json.dumps(tabs), encoding="utf-8")
            code = tool.main(["--source", str(root / "src"), "--tabs", str(root / "tabs.json"), "--out", str(root / "out"),
                              "--manifest", str(root / "m.json")])
            out = json.loads((root / "out" / tool.DOCUMENT / "pages.jsonl").read_text(encoding="utf-8").split("\n")[0])
        self.assertEqual(code, 0)
        self.assertNotIn("needs_ocr", out)
        self.assertEqual((out["section_opener_title"], out["index_exclusion"]["reason"]), ("โรคไม่ติดต่อ กับวันสำคัญ", "section_opener_title_only"))
        self.assertEqual(out["text"], "")  # no text is invented for a page that has none


if __name__ == "__main__":
    unittest.main()
