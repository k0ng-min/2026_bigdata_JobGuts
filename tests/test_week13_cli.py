import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.service.run_week13 import main


class Week13CliTests(unittest.TestCase):
    def test_scenarios_are_recorded_from_the_stored_rule_artifact(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        rules = root / "rules.json"
        rules.write_text(json.dumps({"normalized": [
            {"antecedent": ["TensorFlow"], "consequent": ["PyTorch"], "support": 0.5, "confidence": 0.9, "interest": 0.4},
            {"antecedent": [".NET"], "consequent": ["C#"], "support": 0.5, "confidence": 0.9, "interest": 0.3},
        ]}), encoding="utf-8")
        postings = root / "postings.jsonl"
        postings.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in [
            {"source": "s", "job_id": "1", "title": "ML", "normalized_techs": ["TensorFlow", "PyTorch"], "job_role": "other_tech", "experience_segment": "신입", "entry_eligible": True},
            {"source": "s", "job_id": "2", "title": "FE", "normalized_techs": ["TensorFlow", "PyTorch"], "job_role": "frontend", "experience_segment": "5년이상", "entry_eligible": False},
            {"source": "s", "job_id": "3", "title": "BE", "normalized_techs": [".NET", "C#"], "job_role": "backend", "experience_segment": "5년이상", "entry_eligible": False},
        ]), encoding="utf-8")
        dictionary = root / "dictionary.json"
        dictionary.write_text(json.dumps({"version": "test.v1", "canonical_technologies": {"TensorFlow": ["tensorflow"]}}), encoding="utf-8")
        artifacts = root / "artifacts"
        argv = ["run_week13", "--rules", str(rules), "--postings", str(postings), "--dictionary", str(dictionary), "--artifact-dir", str(artifacts)]
        with patch.object(sys, "argv", argv):
            self.assertEqual(main(), 0)

        record = json.loads((artifacts / "week13_service_scenarios.json").read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "complete")
        self.assertEqual(record["rule_count"], 2)
        self.assertEqual(record["scenarios"]["normal"]["response"]["status"], "ok")
        self.assertEqual(record["scenarios"]["no_rules"]["response"]["status"], "no_rules")
        self.assertEqual(record["scenarios"]["insufficient_sample"]["response"]["status"], "insufficient_sample")
        self.assertEqual(
            [posting["job_id"] for posting in record["scenarios"]["entry_eligible"]["response"]["evidence_postings"]],
            ["1"],
        )

    def test_missing_inputs_are_recorded_without_inventing_results(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        artifacts = root / "artifacts"
        argv = ["run_week13", "--rules", str(root / "missing.json"), "--postings", str(root / "missing.jsonl"), "--artifact-dir", str(artifacts)]
        with patch.object(sys, "argv", argv):
            self.assertEqual(main(), 0)

        record = json.loads((artifacts / "week13_service_scenarios.json").read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "blocked_missing_input")
        self.assertNotIn("scenarios", record)
