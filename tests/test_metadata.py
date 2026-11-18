import json
import tempfile
import unittest
from pathlib import Path

from src.normalization.metadata import classify_experience, is_entry_eligible
from src.retrieval import RuleRepository


class ExperienceMetadataTests(unittest.TestCase):
    def test_experience_labels_are_kept_as_they_appear_in_the_source(self):
        for label in ("신입", "경력무관", "1~3년차", "3~5년차", "5년이상"):
            segment, status = classify_experience(label)
            self.assertEqual(segment, label)
            self.assertEqual(status, "source_label")

    def test_no_experience_label_is_never_inferred_as_entry_level(self):
        for label in (None, "", "   ", "무관", "알 수 없음"):
            segment, status = classify_experience(label)
            self.assertEqual(segment, "unknown")
            self.assertEqual(status, "missing_or_unrecognized_label")
            self.assertFalse(is_entry_eligible(label))

    def test_entry_eligibility_covers_both_신입_and_경력무관(self):
        self.assertTrue(is_entry_eligible("신입"))
        self.assertTrue(is_entry_eligible("경력무관"))
        self.assertFalse(is_entry_eligible("1~3년차"))
        self.assertFalse(is_entry_eligible("5년이상"))

    def test_경력무관_is_not_collapsed_into_the_신입_segment(self):
        self.assertNotEqual(classify_experience("경력무관")[0], classify_experience("신입")[0])


class EntryEligibleFilterTests(unittest.TestCase):
    def test_entry_eligible_filter_keeps_신입_and_경력무관_evidence_only(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        (root / "rules.json").write_text(json.dumps({"normalized": [
            {"antecedent": ["Java"], "consequent": ["Spring"], "interest": 0.3, "confidence": 0.5}
        ]}), encoding="utf-8")
        rows = [
            {"source": "s", "job_id": "veteran", "title": "t", "normalized_techs": ["Java", "Spring"], "experience_segment": "5년이상", "entry_eligible": False},
            {"source": "s", "job_id": "open", "title": "t", "normalized_techs": ["Java", "Spring"], "experience_segment": "경력무관", "entry_eligible": True},
            {"source": "s", "job_id": "fresh", "title": "t", "normalized_techs": ["Java", "Spring"], "experience_segment": "신입", "entry_eligible": True},
        ]
        (root / "postings.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
        repository = RuleRepository(root / "rules.json", root / "postings.jsonl")

        unfiltered = repository.recommend(["Java"])
        self.assertEqual([posting["job_id"] for posting in unfiltered["evidence_postings"]], ["veteran", "open", "fresh"])

        entry_only = repository.recommend(["Java"], entry_eligible=True)
        self.assertEqual([posting["job_id"] for posting in entry_only["evidence_postings"]], ["open", "fresh"])
        self.assertTrue(entry_only["applied_filters"]["entry_eligible_only"])
