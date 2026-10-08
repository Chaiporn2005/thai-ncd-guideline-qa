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
        pages, _ = build.scan_document(rows)
        self.assertEqual([p["suggest"] for p in pages], [None, "pediatric", "pediatric"])

    def test_name_list_page_suggests_exclusion(self):
        _, found = build.scan_document(ROWS)
        self.assertEqual({f["key"]: f["suggest"] for f in found}, {"d:p1": "redact", "d:p4": "exclude_page"})


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

    def test_value_not_on_page_fails(self):
        bad = json.loads(json.dumps(DECISIONS))
        bad["personal"][0]["redact"][0]["value"] = "02-000-0000"
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
