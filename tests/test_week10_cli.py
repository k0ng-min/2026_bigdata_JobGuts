import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.ingestion.run_week10 import main


class Week10CliTests(unittest.TestCase):
    def test_cli_records_missing_input_without_inventing_results(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        config = root / "scope.json"
        config.write_text('{"version":"test", "input_file_contract":{"expected_path":"data/raw/missing.json"}}', encoding="utf-8")
        output = root / "artifacts"
        with patch.object(sys, "argv", ["run_week10", "--config", str(config), "--output-dir", str(output)]):
            self.assertEqual(main(), 0)

        summary = json.loads((output / "week10_data_quality_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["status"], "blocked_missing_input")
        self.assertEqual(len((output / "week10_raw_text_samples.csv").read_text(encoding="utf-8").strip().splitlines()), 1)
