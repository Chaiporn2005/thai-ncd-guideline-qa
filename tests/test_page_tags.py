"""Page tags: personal-data detection, population labels, redaction and exclusion."""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = load("build_page_tag_review")
tool = load("apply_page_tags")

ROWS = [
    {"document_id": "d", "pdf_page": 1, "status": "ok", "text": "คณะทำงาน นพ.สมชาย ใจดี โทร 081-234-5678",
     "removed_edge_lines": ["ติดต่อ 081-234-5678"], "human_review": None},
    {"document_id": "d", "pdf_page": 2, "status": "ok", "text": "บทที่ 16 เบาหวานในเด็กและวัยรุ่น", "human_review": None},
    {"document_id": "d", "pdf_page": 3, "status": "ok", "text": "อินซูลินในเด็ก", "human_review": None},
    {"document_id": "d", "pdf_page": 4, "status": "ok", "text": "รายนาม ศ.นพ.กมล ใจงาม ผศ.พญ.ขวัญ ดีมาก", "human_review": None},
]


class Detection(unittest.TestCase):
    def test_finds_personal_data_and_skips_isbn(self):
        row = {"document_id": "d", "pdf_page": 1, "status": "ok", "human_review": None,
               "text": "ISBN 9789241549028 อีเมล a.b@gmail.com เลข 1101700230708 ภายนอกการ"}
        types = {f["type"]: f["value"] for f in build.personal_findings(row)}
        self.assertEqual(types, {"email": "a.b@gmail.com", "citizen_id": "1101700230708"})

    def test_chapter_suggestion_ignores_cross_references(self):
        rows = [{"document_id": "d", "pdf_page": 1, "status": "ok", "human_review": None,
                 "text": "ผู้ป่วยตั้งครรภ์ (ดูบทที่ 18 เบาหวานในหญิงมีครรภ์)"}] + ROWS[1:3]
        pages, _, _ = build.scan_document(rows)
        self.assertEqual([p["suggest"] for p in pages], [None, "pediatric", "pediatric"])

    def test_name_list_page_suggests_exclusion(self):
        _, found, _ = build.scan_document(ROWS)
        self.assertEqual({f["key"]: f["suggest"] for f in found}, {"d:p1": "redact", "d:p4": "exclude_page"})


class Cases(unittest.TestCase):
    def row(self, text):
        return {"document_id": "d", "pdf_page": 1, "status": "ok", "human_review": None, "text": text}

    def test_case_narrative_suggests_exclusion_but_toc_does_not(self):
        narrative = self.row("กรณีศึกษาอายุ 67 ปี กรณีศึกษามีสามี กรณีศึกษาไม่เครียด")
        _, found, _ = build.scan_document([narrative])
        self.assertEqual((found[0]["suggest"], found[0]["findings"][0]["type"]), ("exclude_page", "case"))
        toc = self.row("สารบัญตาราง ผลตรวจของกรณีศึกษา แผนของกรณีศึกษา สรุปของกรณีศึกษา")
        self.assertEqual(build.scan_document([toc])[1], [])

    def test_worked_example_is_kept_for_review(self):
        _, found, _ = build.scan_document([self.row("ตัวอย่างการคำนวณ ผู้ป่วยชายอายุ 50 ปี น้ำหนัก 60 กก.")])
        self.assertEqual((found[0]["suggest"], found[0]["findings"][0]["type"]), ("keep", "case_example"))

    def test_elderly_cue_is_reported(self):
        pages, _, _ = build.scan_document([self.row("การดูแลผู้สูงอายุที่เป็นเบาหวาน")])
        self.assertIn("elderly", pages[0]["hits"])


class LowContent(unittest.TestCase):
    def kind(self, text, page=50, last=100):
        row = {"document_id": "d", "pdf_page": page, "status": "ok", "human_review": None, "text": text}
        found = build.low_content(row, last)
        return found and (found["kind"], found["suggest"])

    BODY = "แนวทางการรักษาโรคเบาหวานชนิดที่ 2 ในผู้ใหญ่ " * 8

    def test_kinds(self):
        self.assertEqual(self.kind("Contents Next Chapter HOME Next Page"), ("nav_only", "exclude"))
        self.assertEqual(self.kind("บทที่ 6 การดูแลรักษา"), ("divider", "exclude"))
        self.assertEqual(self.kind("แนวทางเวชปฏิบัติสำหรับโรคเบาหวาน สมาคมโรคเบาหวานแห่งประเทศไทย", page=1), ("cover", "exclude"))
        self.assertEqual(self.kind("ติดต่อกองโรคไม่ติดต่อ โทร 025903867 กรมควบคุมโรค", page=99), ("back", "exclude"))
        self.assertEqual(self.kind("รูปที่ 1 แนวทางการพิจารณาการฟอกไตในผู้ป่วยไตวายเฉียบพลัน", page=99), ("figure_caption", "keep"))
        self.assertEqual(self.kind("ตารางที่ 2 เป้าหมาย HbA1c น้อยกว่า 7 เปอร์เซ็นต์ในผู้ใหญ่ทั่วไป"), ("figure_caption", "keep"))
        self.assertEqual(self.kind("ข้อควรระวังการฉีดอินซูลินในผู้ใหญ่ที่เป็นเบาหวาน ควรหมุนตำแหน่งที่ฉีดทุกครั้ง"), ("short", "keep"))

    def test_normal_page_and_late_short_page_are_not_flagged(self):
        self.assertIsNone(self.kind(self.BODY))
        self.assertEqual(self.kind("ตารางสั้นกลางเล่ม HbA1c 7 ผู้ใหญ่ เป้าหมายน้ำตาลในเลือดที่เหมาะสมต่อการรักษา", page=98, last=100)[0], "back")

    def test_font_glyph_ids_are_garbage(self):
        self.assertEqual(self.kind("คำนำ " + "/g11/g46/g57/g40/g42/g52/g33/g42/g64/g263/g49/g63 " * 3), ("garbage_text_layer", "exclude"))


class Groups(unittest.TestCase):
    def test_spread_covers_documents_and_is_deterministic(self):
        items = [{"document_id": f"d{d}", "p": p} for d in range(5) for p in range(1, 21)]
        picked = build.spread(items, 6)
        self.assertEqual(len(picked), 6)
        self.assertGreaterEqual(len({i["document_id"] for i in picked}), 5)
        self.assertEqual(picked, build.spread(list(reversed(items)), 6))
        self.assertEqual(len(build.spread(items[:3], 6)), 3)

    def test_groups_split_cases_from_name_lists_and_skip_keep_suggestions(self):
        low = [{"key": "d:p1", "document_id": "d", "p": 1, "kind": "cover", "suggest": "exclude", "text": "ปก", "pdf": None},
               {"key": "d:p2", "document_id": "d", "p": 2, "kind": "short", "suggest": "keep", "text": "สั้น", "pdf": None}]
        pd = [{"key": "d:p3", "document_id": "d", "p": 3, "suggest": "exclude_page", "redact": [False],
               "findings": [{"type": "case"}], "preview": "เคส", "pdf": None},
              {"key": "d:p4", "document_id": "d", "p": 4, "suggest": "exclude_page", "redact": [False],
               "findings": [{"type": "name"}], "preview": "รายชื่อ", "pdf": None},
              {"key": "d:p5", "document_id": "d", "p": 5, "suggest": "keep", "redact": [], "findings": [], "preview": ""}]
        with tempfile.TemporaryDirectory() as t:
            groups = {g["id"]: g for g in build.build_groups(low, pd, Path(t) / "raw", Path(t) / "out")}
        self.assertEqual(set(groups), {"lc:cover", "pd:case", "pd:names"})
        self.assertEqual((groups["pd:case"]["keys"], groups["pd:names"]["keys"]), (["d:p3"], ["d:p4"]))
        self.assertIsNone(groups["lc:cover"]["samples"][0]["img"])  # no source PDF in the temp folder


def run(tmp: Path, decisions: dict, *extra: str) -> int:
    src = tmp / "src" / "d"
    src.mkdir(parents=True)
    (src / "pages.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in ROWS), encoding="utf-8")
    (src / "normalization.json").write_text(json.dumps({"pages_jsonl_sha256": "x"}), encoding="utf-8")
    (tmp / "dec.json").write_text(json.dumps(decisions, ensure_ascii=False), encoding="utf-8")
    with contextlib.redirect_stdout(io.StringIO()):
        return tool.main(["--source", str(tmp / "src"), "--decisions", str(tmp / "dec.json"), "--out",
                          str(tmp / "out"), "--manifest", str(tmp / "m.json"), *extra])


def rows(tmp: Path):
    return [json.loads(x) for x in (tmp / "out/d/pages.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()]


DECISIONS = {"reviewer": "tester", "personal_undecided": 0, "population_docs_not_reviewed": [],
             "population": [{"document_id": "d", "reviewed": True, "ranges": [[2, 3, "pediatric"]]}],
             "personal": [{"key": "d:p1", "action": "redact", "redact": [{"type": "phone", "value": "081-234-5678"}]},
                          {"key": "d:p4", "action": "exclude_page", "redact": []}]}


class Apply(unittest.TestCase):
    def test_labels_redaction_and_exclusion(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            self.assertEqual(run(tmp, DECISIONS), 0)
            r = rows(tmp)
            self.assertEqual([x["population"] for x in r], ["general", "pediatric", "pediatric", "general"])
            self.assertNotIn("081-234-5678", json.dumps(r[0], ensure_ascii=False))
            self.assertEqual(r[0]["personal_data"]["redacted"], {"phone": 2})
            self.assertEqual((r[3]["text"], r[3]["index_exclusion"]["reason"]), ("", "personal_data_minimisation"))
            manifest = (tmp / "m.json").read_text(encoding="utf-8")
            self.assertNotIn("081", manifest)
            self.assertNotIn("สมชาย", manifest)

    def test_low_content_exclusion_and_garbled_status(self):
        decisions = json.loads(json.dumps(DECISIONS))
        decisions["lowcontent"] = [{"key": "d:p3", "kind": "cover", "action": "exclude"},
                                   {"key": "d:p2", "kind": "garbage_text_layer", "action": "exclude"},
                                   {"key": "d:p1", "kind": "short", "action": "keep"}]
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            self.assertEqual(run(tmp, decisions), 0)
            r = rows(tmp)
            self.assertEqual(r[2]["index_exclusion"]["reason"], "low_content_cover")
            self.assertEqual((r[1]["status"], r[1]["index_exclusion"]["reason"]), ("garbled", "low_content_garbage_text_layer"))
            self.assertEqual(r[0]["low_content_review"]["action"], "keep")
            self.assertNotIn("index_exclusion", r[0])
            self.assertEqual(r[3]["index_exclusion"]["reason"], "personal_data_minimisation")  # personal reason wins

    def test_value_not_on_page_fails(self):
        bad = json.loads(json.dumps(DECISIONS))
        bad["personal"][0]["redact"][0]["value"] = "02-000-0000"
        with tempfile.TemporaryDirectory() as t, self.assertRaises(tool.DecisionError):
            run(Path(t), bad)

    def test_case_cannot_be_redacted_by_value(self):
        bad = json.loads(json.dumps(DECISIONS))
        bad["personal"][0]["redact"] = [{"type": "case", "value": "กรณีศึกษา ×3"}]
        with tempfile.TemporaryDirectory() as t, self.assertRaises(tool.DecisionError):
            run(Path(t), bad)

    def test_incomplete_review_needs_flag(self):
        partial = dict(DECISIONS, personal_undecided=3)
        with tempfile.TemporaryDirectory() as t, self.assertRaises(tool.DecisionError):
            run(Path(t), partial)
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(run(Path(t), partial, "--allow-incomplete"), 0)


if __name__ == "__main__":
    unittest.main()
