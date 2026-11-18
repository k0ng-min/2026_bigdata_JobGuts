import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.analysis.run_week14 import main


def _write_inputs(root: Path, transaction_count: int) -> tuple[Path, Path, Path]:
    rows = [
        {"source": "s", "job_id": "1", "raw_text": "a", "normalized_techs": ["Java", "Spring", "AWS"], "job_role": "backend", "experience_segment": "신입", "entry_eligible": True},
        {"source": "s", "job_id": "2", "raw_text": "b", "normalized_techs": ["Java", "Spring", "AWS"], "job_role": "backend", "experience_segment": "경력무관", "entry_eligible": True},
        {"source": "s", "job_id": "2", "raw_text": "c", "normalized_techs": ["Java"], "job_role": "backend", "experience_segment": "신입", "entry_eligible": True},
        {"source": "s", "job_id": "3", "raw_text": "a", "normalized_techs": ["Java"], "job_role": "frontend", "experience_segment": "5년이상", "entry_eligible": False},
        {"source": "s", "job_id": "4", "raw_text": "d", "normalized_techs": [], "job_role": "frontend", "experience_segment": "unknown", "entry_eligible": False},
    ]
    postings = root / "postings.jsonl"
    postings.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    rules = root / "rules.json"
    rules.write_text(json.dumps({"normalized": [
        {"antecedent": ["Java"], "consequent": ["Spring"], "support": 0.5, "confidence": 0.6, "interest": 0.1},
        {"antecedent": ["Spring"], "consequent": ["AWS"], "support": 0.5, "confidence": 0.7, "interest": 0.2},
    ]}), encoding="utf-8")
    comparison = root / "comparison.json"
    comparison.write_text(json.dumps({"normalized": {"transaction_count": transaction_count}}), encoding="utf-8")
    return postings, rules, comparison


class Week14CliTests(unittest.TestCase):
    def _run(self, root: Path, transaction_count: int) -> tuple[dict, dict]:
        postings, rules, comparison = _write_inputs(root, transaction_count)
        artifacts = root / "artifacts"
        argv = ["run_week14", "--input", str(postings), "--rules", str(rules), "--comparison", str(comparison), "--artifact-dir", str(artifacts)]
        with patch.object(sys, "argv", argv):
            self.assertEqual(main(), 0)
        return (
            json.loads((artifacts / "week14_segment_comparison.json").read_text(encoding="utf-8")),
            json.loads((artifacts / "week14_skill_graph.json").read_text(encoding="utf-8")),
        )

    def test_segments_and_triples_use_the_week12_eligible_posting_set(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        # Of the five rows: one is a source+job_id duplicate, one repeats an earlier
        # body, and one has no technologies, leaving two eligible postings.
        segments, _ = self._run(Path(temp_dir.name), transaction_count=2)

        self.assertEqual(segments["basis"]["posting_count"], 2)
        self.assertEqual(sum(segments["segments"].values()), 2)
        self.assertEqual(segments["segments"]["backend|신입"], 1)
        self.assertEqual(segments["segments"]["backend|경력무관"], 1)
        self.assertEqual(segments["entry_eligible_posting_count"], 2)
        self.assertEqual(segments["top_triples"], [{"items": ["AWS", "Java", "Spring"], "count": 2}])

    def test_graph_keeps_every_rule_as_an_edge(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        _, graph = self._run(Path(temp_dir.name), transaction_count=2)

        self.assertEqual(len(graph["edges"]), 2)
        self.assertEqual(graph["basis"]["rule_count"], 2)
        self.assertEqual({node["id"] for node in graph["nodes"]}, {"Java", "Spring", "AWS"})

    def test_run_fails_when_the_posting_set_drifts_from_week12(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        with self.assertRaises(ValueError) as caught:
            self._run(Path(temp_dir.name), transaction_count=9999)

        self.assertIn("does not match the week-12 transaction count", str(caught.exception))
