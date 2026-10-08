"""Page tags: which pages need a decision, low-content pages, groups, and applying the decisions."""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = load("build_page_tag_review")
tool = load("apply_page_tags")

ADULT = "ผู้ป่วยเบาหวานชนิดที่ 2 ควรควบคุมระดับน้ำตาลในเลือดและตรวจติดตามสม่ำเสมอ " * 6
NAME_LIST = "รายนามคณะทำงาน\n" + "\n".join(
    f"{i}. ศ.นพ.สมชาย{n} ใจดี{n} ประธาน\nคณะแพทยศาสตร์ มหาวิทยาลัยตัวอย่าง" for i, n in enumerate("กขคงจฉ", 1))

ROWS = [
    {"document_id": "d", "pdf_page": 1, "status": "ok", "text": "คณะทำงาน นพ.สมชาย ใจดี โทร 081-234-5678",
     "removed_edge_lines": ["ติดต่อ 081-234-5678"], "human_review": None},
    {"document_id": "d", "pdf_page": 2, "status": "ok", "text": "บทที่ 16 เบาหวานในเด็กและวัยรุ่น", "human_review": None},
    {"document_id": "d", "pdf_page": 3, "status": "ok", "text": "อินซูลินในเด็ก", "human_review": None},
    {"document_id": "d", "pdf_page": 4, "status": "ok", "text": "รายนาม ศ.นพ.กมล ใจงาม ผศ.พญ.ขวัญ ดีมาก", "human_review": None},
]


def row(text, page=10, doc="d"):
    return {"document_id": doc, "pdf_page": page, "status": "ok", "human_review": None, "text": text}


class NeedsDecision(unittest.TestCase):
    def decide(self, text, doc_type="clinical_guideline"):
        return build.decide_page(row(text), doc_type)[0]

    def test_name_list_page_is_separated_for_a_decision(self):
        found = self.decide(NAME_LIST)
        self.assertEqual((found["group"], found["suggest"]), ("name_list", "exclude_page"))

    def test_leaflet_credits_and_organisation_contacts_need_no_decision(self):
        credits = ADULT + "\nจัดทำโดย นพ.สมชาย ใจดี และ พญ.สมหญิง ดีใจ"
        self.assertIsNone(self.decide(credits, "patient_education"))
        office = ("สมาคมโรคไตแห่งประเทศไทย ถนนเพชรบุรี กรุงเทพมหานคร 10310 โทร 02-716-6091 "
                  "แฟ็กซ์ 02-718-1900 อีเมล kidney@loxinfo.co.th")
        self.assertIsNone(self.decide(ADULT + "\n" + office))

    def test_personal_mobile_is_suggested_for_redaction(self):
        found = self.decide(ADULT + "\nติดต่อ นพ.สมชาย ใจดี โทร 081-234-5678")
        self.assertEqual((found["group"], found["suggest"]), ("contact_personal", "redact"))
        flagged = [f["value"] for f, r in zip(found["findings"], found["redact"]) if r]
        self.assertEqual(flagged, ["081-234-5678"])

    def test_ambiguous_contact_goes_to_review_unticked(self):
        found = self.decide(ADULT + "\nข้อมูลเพิ่มเติม abc@gmail.com")
        self.assertEqual((found["group"], found["suggest"], any(found["redact"])), ("review", "keep", False))

    def test_finds_citizen_id_and_skips_isbn(self):
        text = ADULT + "\nISBN 9789241549028 เลข 1101700230708"
        types = {f["type"]: f["value"] for f in build.decide_page(row(text), "")[0]["findings"]}
        self.assertEqual(types, {"citizen_id": "1101700230708"})

    def test_case_narrative_suggests_exclusion_but_contents_page_does_not(self):
        found = self.decide("กรณีศึกษาอายุ 67 ปี กรณีศึกษามีสามี กรณีศึกษาไม่เครียด")
        self.assertEqual((found["group"], found["suggest"]), ("case", "exclude_page"))
        self.assertIsNone(self.decide("สารบัญตาราง ผลตรวจของกรณีศึกษา แผนของกรณีศึกษา สรุปของกรณีศึกษา"))

    def test_worked_example_patient_is_kept_for_a_look(self):
        found = self.decide("ตัวอย่างการคำนวณ ผู้ป่วยชายอายุ 50 ปี น้ำหนัก 60 กก. " + ADULT)
        self.assertEqual((found["group"], found["suggest"]), ("review", "keep"))

    def test_scan_document_suggests_population_from_the_chapter(self):
        rows = [row("บทที่ 16 การดูแลเบาหวานในเด็กและวัยรุ่น " + ADULT, 1), row("ตารางที่ 1 เป้าหมาย HbA1c", 2)]
        pages, _, _ = build.scan_document(rows)
        self.assertEqual([p["suggest"] for p in pages], ["pediatric", "pediatric"])

    def test_mention_only_page_is_not_suggested_but_is_reported(self):
        pages, _, _ = build.scan_document([row(ADULT + " ห้ามใช้ในหญิงตั้งครรภ์")])
        self.assertIsNone(pages[0]["suggest"])
        self.assertEqual(pages[0]["mention"], {"pregnancy": 1})


class LowContent(unittest.TestCase):
    def kind(self, text, page=50, last=100):
        found = build.low_content(row(text, page), last)
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

    def test_normal_page_and_late_short_page(self):
        self.assertIsNone(self.kind(self.BODY))
        late = "ตารางสั้นกลางเล่ม HbA1c 7 ผู้ใหญ่ เป้าหมายน้ำตาลในเลือดที่เหมาะสมต่อการรักษา"
        self.assertEqual(self.kind(late, page=98, last=100)[0], "back")

    def test_font_glyph_ids_are_garbage(self):
        text = "คำนำ " + "/g11/g46/g57/g40/g42/g52/g33/g42/g64/g263/g49/g63 " * 3
        self.assertEqual(self.kind(text), ("garbage_text_layer", "exclude"))


class Groups(unittest.TestCase):
    def test_spread_covers_documents_and_is_deterministic(self):
        items = [{"document_id": f"d{d}", "p": p} for d in range(5) for p in range(1, 21)]
        picked = build.spread(items, 6)
        self.assertEqual(len(picked), 6)
        self.assertGreaterEqual(len({i["document_id"] for i in picked}), 5)
        self.assertEqual(picked, build.spread(list(reversed(items)), 6))
        self.assertEqual(len(build.spread(items[:3], 6)), 3)

    def test_groups_carry_their_own_actions_and_skip_keep_suggestions(self):
        low = [{"key": "d:p1", "document_id": "d", "p": 1, "kind": "cover", "suggest": "exclude", "text": "ปก", "pdf": None},
               {"key": "d:p2", "document_id": "d", "p": 2, "kind": "short", "suggest": "keep", "text": "สั้น", "pdf": None},
               {"key": "d:p6", "document_id": "d", "p": 6, "kind": "garbage_text_layer", "suggest": "exclude",
                "text": "/g1/g2/g3", "pdf": None}]
        pd = [{"key": f"d:p{n}", "document_id": "d", "p": n, "group": g, "suggest": s, "redact": [False], "findings": [],
               "preview": "x", "pdf": None}
              for n, g, s in ((3, "case", "exclude_page"), (4, "name_list", "exclude_page"),
                              (5, "contact_personal", "redact"), (7, "review", "keep"))]
        with tempfile.TemporaryDirectory() as t:
            groups = {g["id"]: g for g in build.build_groups(low, pd, Path(t) / "raw", Path(t) / "out")}
        self.assertEqual(set(groups), {"lc:cover", "lc:garbage_text_layer", "pd:case", "pd:name_list", "pd:contact_personal"})
        self.assertEqual([a["id"] for a in groups["pd:name_list"]["actions"]], ["exclude", "tag", "keep"])
        self.assertEqual([a["id"] for a in groups["lc:garbage_text_layer"]["actions"]], ["exclude", "reocr", "keep"])
        self.assertEqual([a["id"] for a in groups["pd:contact_personal"]["actions"]], ["redact", "keep"])
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

    def test_name_list_can_be_tagged_and_kept_in_storage_but_not_indexed(self):
        decisions = json.loads(json.dumps(DECISIONS))
        decisions["personal"][1] = {"key": "d:p4", "action": "tag_name_list", "redact": []}
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            self.assertEqual(run(tmp, decisions), 0)
            r = rows(tmp)[3]
            self.assertEqual((r["pdpa_tag"], r["index_exclusion"]["reason"]), ("personal_name_list", "pdpa_tagged_name_list"))
            self.assertIn("กมล", r["text"])  # kept in storage, only excluded from search

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
            self.assertEqual((r[1]["status"], r[1]["index_exclusion"]["reason"]),
                             ("garbled", "low_content_garbage_text_layer"))
            self.assertEqual(r[0]["low_content_review"]["action"], "keep")
            self.assertNotIn("index_exclusion", r[0])
            self.assertEqual(r[3]["index_exclusion"]["reason"], "personal_data_minimisation")  # personal reason wins

    def test_garbled_text_layer_can_be_sent_to_reocr_but_not_kept(self):
        decisions = json.loads(json.dumps(DECISIONS))
        decisions["lowcontent"] = [{"key": "d:p2", "kind": "garbage_text_layer", "action": "reocr"}]
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            self.assertEqual(run(tmp, decisions), 0)
            r = rows(tmp)[1]
            self.assertEqual((r["status"], r["needs_ocr"], r["index_exclusion"]["reason"]),
                             ("garbled", True, "awaiting_reocr"))
        decisions["lowcontent"] = [{"key": "d:p2", "kind": "garbage_text_layer", "action": "keep"}]
        with tempfile.TemporaryDirectory() as t, self.assertRaises(tool.DecisionError):
            run(Path(t), decisions)

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
