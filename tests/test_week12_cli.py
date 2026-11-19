import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.analysis.run_week12 import main


class Week12CliTests(unittest.TestCase):
    def _run(self, root: Path, top_n: int) -> tuple[dict, dict]:
        postings = root / "postings.jsonl"
        rows = []
        for index in range(10):
            techs = ["Java", "Spring"] if index < 6 else ["Python", "Django"]
            rows.append({"source": "s", "job_id": str(index), "raw_text": f"body {index}", "final_techs": techs, "normalized_techs": techs})
        postings.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        config = root / "experiments.json"
        config.write_text(json.dumps({"week12_parameters": {"minimum_support": 0.1, "minimum_confidence": 0.1}}), encoding="utf-8")
        artifacts = root / "artifacts"
        argv = ["run_week12", "--input", str(postings), "--config", str(config), "--artifact-dir", str(artifacts), "--top-n", str(top_n)]
        with patch.object(sys, "argv", argv):
            self.assertEqual(main(), 0)
        return (
            json.loads((artifacts / "week12_all_rules.json").read_text(encoding="utf-8")),
            json.loads((artifacts / "week12_top_rules.json").read_text(encoding="utf-8")),
        )

    def test_all_rules_artifact_is_not_truncated_by_the_display_top_n(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        all_rules, top_rules = self._run(Path(temp_dir.name), top_n=1)

        self.assertEqual(len(all_rules["normalized"]), 4)
        self.assertEqual(all_rules["rule_count"]["normalized"], 4)
        self.assertEqual(len(top_rules["normalized"]), 1)
        self.assertEqual(top_rules["rule_count"]["normalized"], 4)

    def test_every_antecedent_stays_reachable_in_the_all_rules_artifact(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        all_rules, top_rules = self._run(Path(temp_dir.name), top_n=1)

        self.assertEqual(
            {rule["antecedent"][0] for rule in all_rules["normalized"]},
            {"Java", "Spring", "Python", "Django"},
        )
        self.assertEqual({rule["antecedent"][0] for rule in top_rules["normalized"]}, {"Django"})
