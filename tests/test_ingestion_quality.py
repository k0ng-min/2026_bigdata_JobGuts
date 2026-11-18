import tempfile
import unittest
from pathlib import Path

from src.ingestion.loader import load_postings
from src.ingestion.quality import build_week10_report


class IngestionQualityTests(unittest.TestCase):
    def test_report_separates_key_duplicates_from_suspected_body_duplicates(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        source = Path(temp_dir.name) / "postings.json"
        source.write_text(
        """[
          {"source":"a","job_id":"1","raw_text":"Java role","final_techs":["Java"],"hard_skills":["Java"],"job_role":"backend","experience_level":"new"},
          {"source":"a","job_id":"1","raw_text":"Java role","final_techs":["Java"],"hard_skills":["JVM"],"job_role":"backend","experience_level":"new"},
          {"source":"b","job_id":"2","raw_text":"Java role","final_techs":[],"hard_skills":null,"job_role":"frontend","experience_level":null}
        ]""",
        encoding="utf-8",
    )
        report = build_week10_report(load_postings(source), {"file_name": "postings.json"})

        self.assertEqual(report["row_count"], 3)
        self.assertEqual(report["duplicate_check"]["source_job_id_duplicate_rows_after_first"], 1)
        self.assertEqual(report["duplicate_check"]["suspected_same_body_distinct_id_groups"], 1)
        self.assertEqual(report["technology_field_comparison"]["different_set_rows"], 1)
        self.assertEqual(report["required_field_missing_rows"]["experience_level"], 1)


    def test_csv_list_fields_accept_json_or_comma_separated_values(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        source = Path(temp_dir.name) / "postings.csv"
        source.write_text(
        'source,job_id,raw_text,final_techs,hard_skills\na,1,text,"[""Java"", ""Python""]","Java, Python"\n',
        encoding="utf-8",
    )
        posting = load_postings(source)[0]
        self.assertEqual(posting.final_techs, ("Java", "Python"))
        self.assertEqual(posting.hard_skills, ("Java", "Python"))

    def test_title_is_not_treated_as_a_job_role(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        source = Path(temp_dir.name) / "postings.json"
        source.write_text('[{"source":"a","job_id":"1","title":"Backend Engineer"}]', encoding="utf-8")

        self.assertIsNone(load_postings(source)[0].job_role)
