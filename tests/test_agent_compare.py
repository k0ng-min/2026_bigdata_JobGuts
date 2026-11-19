import csv
import json
import unittest
from pathlib import Path

from src.agent.run_compare import bucket_migration, comparison_key, score

ROOT = Path(__file__).resolve().parents[1]
COMPARISON_PATH = ROOT / "artifacts" / "agent_comparison.json"
SHEET_PATH = ROOT / "artifacts" / "agent_review_sheet.csv"


class ComparisonKeyTests(unittest.TestCase):
    def test_hangul_is_kept_so_korean_spellings_do_not_collapse(self):
        # Stripping Hangul made 생성형 AI compare equal to AI and 딥러닝 equal to
        # the empty string, which put Korean candidates in the wrong bucket.
        self.assertNotEqual(comparison_key("생성형 AI"), comparison_key("AI"))
        self.assertNotEqual(comparison_key("딥러닝"), "")
        self.assertEqual(len({comparison_key(name) for name in ("자바", "파이썬", "딥러닝", "")}), 4)

    def test_the_key_keeps_the_symbols_that_distinguish_names(self):
        self.assertNotEqual(comparison_key("C++"), comparison_key("C#"))
        self.assertNotEqual(comparison_key("C"), comparison_key("C++"))
        self.assertEqual(comparison_key("JAVA"), comparison_key("java"))
        self.assertEqual(comparison_key("Node.js"), comparison_key("node.js"))


class ScoreTests(unittest.TestCase):
    VOCABULARY = {"Java", "Python"}

    def test_a_perfect_prediction_scores_one(self):
        result = score([{"Java"}], [{"Java"}], self.VOCABULARY)
        self.assertEqual(result["overall"]["precision"], 1.0)
        self.assertEqual(result["overall"]["recall"], 1.0)
        self.assertEqual(result["overall"]["f1"], 1.0)

    def test_names_are_split_by_whether_the_vocabulary_contains_them(self):
        result = score([{"Java", "RAG"}], [{"Java", "RAG"}], self.VOCABULARY)

        self.assertEqual(result["inside_vocabulary"]["predicted"], 1)
        self.assertEqual(result["outside_vocabulary"]["predicted"], 1)
        self.assertEqual(result["overall"]["predicted"], 2)

    def test_the_split_separates_a_guaranteed_hit_from_an_earned_one(self):
        # Java is in the vocabulary and in the truth; RAG is in neither the
        # vocabulary nor the truth, which is the structural bias the split
        # exists to expose.
        result = score([{"Java", "RAG"}], [{"Java"}], self.VOCABULARY)

        self.assertEqual(result["inside_vocabulary"]["precision"], 1.0)
        self.assertEqual(result["outside_vocabulary"]["precision"], 0.0)
        self.assertEqual(result["overall"]["precision"], 0.5)

    def test_an_empty_prediction_scores_zero_without_dividing_by_zero(self):
        result = score([set()], [{"Java"}], self.VOCABULARY)
        self.assertEqual(result["overall"]["precision"], 0.0)
        self.assertEqual(result["overall"]["recall"], 0.0)
        self.assertEqual(result["overall"]["f1"], 0.0)

    def test_case_differences_do_not_cost_a_point(self):
        self.assertEqual(score([{"JAVA"}], [{"Java"}], self.VOCABULARY)["overall"]["recall"], 1.0)


class BucketMigrationTests(unittest.TestCase):
    """Tell an error that only changed bucket from one the cleanup created."""

    VOCABULARY = {"Generative AI", "Java"}

    def test_a_correct_mapping_of_an_absent_name_counts_as_migration(self):
        # The posting says 생성형 AI and the cleanup maps it to Generative AI,
        # which the ground truth omits. The error existed before, outside the
        # vocabulary, so inside precision falls without a new mistake.
        result = bucket_migration(
            before=[{"생성형 AI"}],
            after=[{"Generative AI"}],
            origins=[{"Generative AI": "생성형 AI"}],
            truth=[{"Java"}],
            vocabulary=self.VOCABULARY,
        )
        self.assertEqual(result["new_in_vocabulary_errors"], 1)
        self.assertEqual(result["migrated_from_outside_bucket"], 1)
        self.assertEqual(result["newly_introduced"], 0)
        self.assertEqual(result["migrated_share"], 1.0)

    def test_mapping_a_name_that_was_already_right_counts_as_a_new_error(self):
        result = bucket_migration(
            before=[{"Java"}],
            after=[{"Generative AI"}],
            origins=[{"Generative AI": "Java"}],
            truth=[{"Java"}],
            vocabulary=self.VOCABULARY,
        )
        self.assertEqual(result["newly_introduced"], 1)
        self.assertEqual(result["migrated_from_outside_bucket"], 0)

    def test_losing_a_correct_name_is_counted(self):
        result = bucket_migration(
            before=[{"Java"}],
            after=[set()],
            origins=[{}],
            truth=[{"Java"}],
            vocabulary=self.VOCABULARY,
        )
        self.assertEqual(result["correct_names_lost"], 1)

    def test_an_unchanged_posting_produces_no_findings(self):
        result = bucket_migration([{"Java"}], [{"Java"}], [{"Java": "Java"}], [{"Java"}], self.VOCABULARY)
        self.assertEqual(result["new_in_vocabulary_errors"], 0)
        self.assertEqual(result["correct_names_lost"], 0)


class ComparisonArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(COMPARISON_PATH.read_text(encoding="utf-8"))

    def test_all_three_experiments_use_the_same_posting_set(self):
        counts = {name: payload["transaction_count"] for name, payload in self.report["experiments"].items()}
        self.assertEqual(set(counts), {"before_cleanup", "after_agent", "final_techs"})
        self.assertEqual(len(set(counts.values())), 1, counts)
        self.assertEqual(self.report["basis"]["posting_count"], min(counts.values()))

    def test_quality_is_reported_inside_and_outside_the_vocabulary(self):
        for side in ("before_cleanup", "after_agent"):
            buckets = self.report["quality_against_final_techs"][side]
            self.assertEqual(set(buckets), {"overall", "inside_vocabulary", "outside_vocabulary"})

    def test_the_in_vocabulary_error_breakdown_is_present(self):
        breakdown = self.report["in_vocabulary_error_breakdown"]
        self.assertEqual(
            breakdown["new_in_vocabulary_errors"],
            breakdown["migrated_from_outside_bucket"] + breakdown["newly_introduced"],
        )
        self.assertIn("structurally near zero", breakdown["note"])

    def test_the_bias_is_stated_in_the_artifact(self):
        self.assertIn("structurally favourable", self.report["evaluation_bias_note"])

    def test_a_mock_run_is_labelled_as_one(self):
        if self.report["is_mock"]:
            self.assertIn("not model performance", self.report["mock_warning"])


class ReviewSheetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with SHEET_PATH.open(encoding="utf-8-sig", newline="") as handle:
            cls.rows = list(csv.DictReader(handle))

    def test_both_sides_are_present_in_equal_numbers(self):
        sources = [row["source_do_not_read_before_judging"] for row in self.rows]
        self.assertEqual(sources.count("before_cleanup"), sources.count("after_agent"))

    def test_the_two_sides_are_shuffled_together(self):
        sources = [row["source_do_not_read_before_judging"] for row in self.rows]
        self.assertNotEqual(sources, sorted(sources), "an unshuffled sheet tells the reviewer which side is which")

    def test_the_judgement_columns_are_left_empty(self):
        for row in self.rows:
            self.assertEqual(row["both_are_technologies"], "")
            self.assertEqual(row["combination_is_plausible"], "")
            self.assertEqual(row["reviewer_note"], "")

    def test_each_reviewer_gets_an_identical_blank_copy(self):
        for index in (1, 2):
            path = SHEET_PATH.parent / f"agent_review_sheet_reviewer{index}.csv"
            self.assertTrue(path.is_file(), path)
            with path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([row["rule_id"] for row in rows], [row["rule_id"] for row in self.rows])


class RecordedPathsAreOsIndependentTests(unittest.TestCase):
    """A path written into an artifact must read the same on Windows and WSL."""

    ARTIFACTS = {
        "week10_data_quality_summary.json": ("input", "path"),
        "week11_normalization_summary.json": ("output_path",),
        "week13_service_scenarios.json": ("rules_artifact",),
        "week14_skill_graph.json": ("basis", "rules_artifact"),
        "agent_run_summary.json": ("cleaned_output",),
    }

    def test_no_artifact_records_a_backslash_path(self):
        for name, keys in self.ARTIFACTS.items():
            path = ROOT / "artifacts" / name
            if not path.is_file():
                continue
            value = json.loads(path.read_text(encoding="utf-8"))
            for key in keys:
                value = value[key]
            self.assertNotIn("\\", str(value), f"{name} -> {'.'.join(keys)}")
            self.assertIn("/", str(value), f"{name} -> {'.'.join(keys)}")
