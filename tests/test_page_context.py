"""Page context: population by page/chapter evidence, name lists vs credits, organisation vs personal contacts."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "page_context", Path(__file__).resolve().parents[1] / "scripts/page_context.py")
pc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pc)

ADULT = "ผู้ป่วยเบาหวานชนิดที่ 2 ควรควบคุมระดับน้ำตาลในเลือดและตรวจติดตามสม่ำเสมอ " * 12


def page(n, text):
    return {"document_id": "d", "pdf_page": n, "status": "ok", "text": text}


class Population(unittest.TestCase):
    def label(self, text):
        return pc.page_population(text)[0]

    def test_caution_inside_adult_content_is_not_a_population_page(self):
        text = ADULT + " ห้ามใช้ยานี้ในหญิงตั้งครรภ์ ห้ามใช้ในหญิงตั้งครรภ์ หลีกเลี่ยงในหญิงตั้งครรภ์ ข้อห้ามในการตั้งครรภ์"
        self.assertIsNone(self.label(text))

    def test_organisation_names_do_not_count(self):
        text = "สมาคมต่อมไร้ท่อเด็กและวัยรุ่นไทย ราชวิทยาลัยกุมารแพทย์ ภาควิชากุมารเวชศาสตร์ " * 3 + ADULT
        self.assertIsNone(self.label(text))

    def test_reference_list_is_not_a_population_page(self):
        refs = "\n".join(f"{i}. Smith J, Lee K. Diabetes in children and adolescents. Diabetes Care. 2020;43:12-9." for i in range(1, 6))
        self.assertIsNone(self.label(refs))

    def test_dense_body_text_is_tagged(self):
        text = "เบาหวานในเด็กและวัยรุ่น ผู้ป่วยเด็กควรได้รับอินซูลิน เด็กอายุน้อยกว่า 10 ปี วัยรุ่นต้องติดตามน้ำตาล เด็กเล็กเสี่ยงน้ำตาลต่ำ"
        self.assertEqual(self.label(text), "pediatric")

    def test_a_few_specific_parts_in_adult_text_are_mixed(self):
        text = ADULT + " หญิงตั้งครรภ์ควรตรวจ ก่อนตั้งครรภ์ควรปรึกษา การตั้งครรภ์ต้องติดตาม"
        scores = pc.page_population_scores(text)
        self.assertGreaterEqual(scores["pregnancy"]["hits"], 3)
        self.assertEqual(self.label(text), "mixed")

    def test_chapter_title_gives_its_pages_the_population(self):
        rows = [page(1, "บทที่ 16 การดูแลเบาหวานในเด็กและวัยรุ่น " + ADULT[:200]),
                page(2, "ตารางที่ 1 ค่าเป้าหมาย HbA1c ต่ำกว่า 7.5 เปอร์เซ็นต์"),
                page(3, "บทที่ 19 บทบาทหน้าที่ของสถานบริการ " + ADULT[:200]),
                page(4, "ตารางที่ 2 ตัวชี้วัดของสถานบริการ")]
        result = pc.population_for_document(rows)
        self.assertEqual([result[n]["label"] for n in (1, 2, 3, 4)], ["pediatric", "pediatric", None, None])
        self.assertEqual(result[2]["confidence"], "high")

    def test_plain_word_names_the_audience_only_in_a_title(self):
        self.assertEqual(pc.title_population("บทที่ 3 อาหารและโภชนาการสำหรับเด็กระดับประถมศึกษา"), "pediatric")
        self.assertIsNone(pc.title_population("บทที่ 5 อาหารสำหรับวัยทำงานและหญิงเจริญพันธุ์"))
        self.assertIsNone(pc.title_population("หมวด 4 เบาหวานในเด็กและหญิงมีครรภ์"))  # two populations: no single label

    def test_cross_references_in_body_text_do_not_start_a_chapter(self):
        text = "ผู้ป่วยที่ตั้งครรภ์ (ดูรายละเอียดในบทที่ 18 เบาหวานในหญิงมีครรภ์)"
        self.assertIsNone(pc.section_heading(text))


NAMES = "\n".join(f"{i}. ศ.นพ.สมชาย{n} ใจดี{n} ประธาน\nคณะแพทยศาสตร์ มหาวิทยาลัยตัวอย่าง" for i, n in enumerate("กขคงจฉ", 1))


class People(unittest.TestCase):
    def klass(self, text, doc_type="clinical_guideline"):
        return pc.name_page_class(text, doc_type)[0]

    def test_page_of_people_is_a_name_list(self):
        self.assertEqual(self.klass("รายนามคณะทำงาน\n" + NAMES), "name_list")

    def test_few_names_crediting_a_leaflet_are_credits(self):
        text = ADULT[:300] + "\nจัดทำโดย นพ.สมชาย ใจดี และ พญ.สมหญิง ดีใจ"
        self.assertEqual(self.klass(text, "patient_education"), "credits")

    def test_one_name_inside_content_is_a_mention(self):
        self.assertEqual(self.klass(ADULT + "\nตามที่ นพ.สมชาย ใจดี รายงานไว้"), "mention")

    def test_page_without_names(self):
        self.assertEqual(self.klass(ADULT), "none")

    def test_list_heading_without_titles_still_makes_a_name_list(self):
        text = "รายนามผู้ทรงคุณวุฒิ\n" + "\n".join(f"สมชาย{n} ใจดี โรงพยาบาลตัวอย่าง{n}" for n in "กขคงจ")
        self.assertEqual(self.klass(text), "name_list")

    def test_committee_as_an_organisation_name_is_not_a_list(self):
        text = "คณะกรรมการพัฒนาคุณภาพชีวิตระดับอำเภอ\n" + ADULT[:200] + "\nนพ.สมชาย ใจดี ประธาน"
        self.assertNotEqual(self.klass(text), "name_list")


class Contacts(unittest.TestCase):
    def test_office_phone_in_an_address_block_is_an_organisation(self):
        ctx = "สมาคมโรคไตแห่งประเทศไทย ถนนเพชรบุรีตัดใหม่ แขวงบางกะปิ กรุงเทพมหานคร 10310 โทร 02-716-6091 แฟ็กซ์ 02-718-1900"
        self.assertEqual(pc.classify_contact("phone", "02-716-6091", ctx)[0], "org")

    def test_mobile_next_to_a_person_is_personal(self):
        ctx = "ติดต่อ นพ.สมชาย ใจดี โทร 081-234-5678"
        self.assertEqual(pc.classify_contact("phone", "081-234-5678", ctx)[0], "personal")

    def test_organisation_mailbox_is_an_organisation(self):
        self.assertEqual(pc.classify_contact("email", "info@dmthai.org", "ติดต่อสอบถาม สมาคมโรคเบาหวาน info@dmthai.org")[0], "org")

    def test_free_mail_without_other_clues_is_ambiguous(self):
        self.assertEqual(pc.classify_contact("email", "abc@gmail.com", "ข้อมูลเพิ่มเติม abc@gmail.com")[0], "ambiguous")

    def test_free_mail_beside_a_person_is_personal(self):
        self.assertEqual(pc.classify_contact("email", "abc@gmail.com", "ผู้นิพนธ์ประสานงาน นพ.สมชาย ใจดี abc@gmail.com")[0], "personal")

    def test_chart_numbers_are_not_phones(self):
        self.assertFalse(pc.valid_phone("00110 120"))
        self.assertTrue(pc.valid_phone("081-234-5678"))


if __name__ == "__main__":
    unittest.main()
