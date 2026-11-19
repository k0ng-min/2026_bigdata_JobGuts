import json
import unittest
from pathlib import Path

from src.agent.build_dictionary import canonical_key, punctuation_key
from src.normalization.dictionary import TechnologyDictionary

ROOT = Path(__file__).resolve().parents[1]
DICTIONARY_PATH = ROOT / "configs" / "tech_dictionary_v2.json"
CATEGORIES_PATH = ROOT / "configs" / "tech_categories.json"
CURATED_PATH = ROOT / "configs" / "tech_dictionary_curated.json"


class ComparisonKeyTests(unittest.TestCase):
    """The v1 key dropped + and #, which merged C, C++ and C# into one name."""

    def test_plus_and_hash_are_preserved_so_the_c_family_stays_apart(self):
        keys = {canonical_key(name) for name in ("C", "C++", "C#")}
        self.assertEqual(len(keys), 3)

        keys = {punctuation_key(name) for name in ("C", "C++", "C#")}
        self.assertEqual(keys, {"c", "c++", "c#"})

    def test_case_differences_collapse_but_symbol_differences_do_not(self):
        self.assertEqual(canonical_key("JAVA"), canonical_key("java"))
        self.assertNotEqual(canonical_key("C++"), canonical_key("C"))

    def test_punctuation_key_ignores_dots_spaces_and_hyphens_only(self):
        self.assertEqual(punctuation_key("Node.js"), punctuation_key("NodeJS"))
        self.assertEqual(punctuation_key("MS-SQL"), punctuation_key("MSSQL"))
        self.assertEqual(punctuation_key("Spring Boot"), punctuation_key("SpringBoot"))
        self.assertNotEqual(punctuation_key("C#"), punctuation_key("C++"))


class DictionaryV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(DICTIONARY_PATH.read_text(encoding="utf-8"))
        cls.entries = {record["canonical"]: record for record in cls.payload["technologies"]}
        cls.categories = json.loads(CATEGORIES_PATH.read_text(encoding="utf-8"))

    def test_every_standard_name_is_a_category_we_declared(self):
        labels = set(self.categories["labels"])
        for record in self.payload["technologies"]:
            self.assertIn(record["category"], labels, record["canonical"])

    def test_no_spelling_points_at_two_standard_names(self):
        seen: dict[str, str] = {}
        for record in self.payload["technologies"]:
            for item in record["spellings"]:
                key = canonical_key(item["spelling"])
                previous = seen.get(key)
                self.assertIn(previous, (None, record["canonical"]), f"{item['spelling']!r} is ambiguous")
                seen[key] = record["canonical"]

    def test_every_spelling_records_the_rule_that_admitted_it(self):
        allowed = {"exact", "case", "punctuation", "curated", "korean"}
        for record in self.payload["technologies"]:
            for item in record["spellings"]:
                self.assertIn(item["rule"], allowed)
                self.assertIn("occurrences", item)

    def test_the_c_family_keeps_three_separate_entries(self):
        for name in ("C", "C++", "C#"):
            self.assertIn(name, self.entries, f"{name} should be its own standard name")
        self.assertNotEqual(self.entries["C"]["spellings"], self.entries["C++"]["spellings"])

    def test_ajax_uses_the_spelling_that_the_data_actually_contains(self):
        # Dictionary v1 declared AJAX as the standard name, but final_techs only
        # ever contains Ajax, so v1's single working alias moved values away
        # from the vocabulary it was supposed to normalise towards.
        self.assertIn("Ajax", self.entries)
        self.assertNotIn("AJAX", self.entries)

    def test_concept_labels_are_marked_so_they_can_be_excluded_later(self):
        for name in ("AI", "ML", "Deep Learning", "CI/CD", "DevOps", "RDBMS"):
            self.assertEqual(self.entries[name]["category"], "concept", name)

    def test_curated_targets_all_exist_as_standard_names(self):
        curated = json.loads(CURATED_PATH.read_text(encoding="utf-8"))
        for target in curated["aliases"]:
            self.assertIn(target, self.entries, f"curated target {target!r} is not in the dictionary")


class DictionaryV2LoadsWithTheExistingLoaderTests(unittest.TestCase):
    """v2 must stay usable by the pipeline's own dictionary loader."""

    def test_v2_can_be_flattened_into_the_v1_loader_shape(self):
        payload = json.loads(DICTIONARY_PATH.read_text(encoding="utf-8"))
        flattened = {
            "version": payload["version"],
            "canonical_technologies": {
                record["canonical"]: [item["spelling"] for item in record["spellings"]]
                for record in payload["technologies"]
            },
        }
        path = Path(self._out()) / "flat.json"
        path.write_text(json.dumps(flattened, ensure_ascii=False), encoding="utf-8")
        dictionary = TechnologyDictionary.from_json(path)

        self.assertEqual(dictionary.canonicalize("JAVA"), "Java")
        self.assertEqual(dictionary.canonicalize("Javascript"), "JavaScript")
        self.assertEqual(dictionary.canonicalize("k8s"), "Kubernetes")
        self.assertEqual(dictionary.canonicalize("C++"), "C++")
        self.assertEqual(dictionary.canonicalize("C#"), "C#")
        self.assertIsNone(dictionary.canonicalize("SI"))

    def _out(self) -> str:
        import tempfile

        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return temp_dir.name


class KoreanDictionaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(DICTIONARY_PATH.read_text(encoding="utf-8"))
        cls.entries = {record["canonical"]: record for record in cls.payload["technologies"]}
        cls.korean = json.loads((ROOT / "configs" / "tech_dictionary_korean.json").read_text(encoding="utf-8"))

    def test_every_korean_target_is_a_standard_name(self):
        for target in self.korean["spellings"]:
            self.assertIn(target, self.entries, f"korean target {target!r} is not in the dictionary")

    def test_korean_spellings_carry_the_korean_rule_and_their_evidence(self):
        registered = {s for v in self.korean["spellings"].values() for s in v}
        recorded = {
            item["spelling"]: item
            for record in self.payload["technologies"]
            for item in record["spellings"]
            if item["rule"] == "korean"
        }
        self.assertEqual(set(recorded), registered)
        for item in recorded.values():
            self.assertIn("occurrences", item)
            self.assertIn("section_occurrences", item)

    def test_ambiguous_korean_words_are_excluded_with_a_reason(self):
        excluded = self.korean["excluded_on_purpose"]
        for word in ("뷰", "노드", "루비", "깃", "러스트", "펄", "레스트", "몽고"):
            self.assertIn(word, excluded)
            self.assertTrue(excluded[word].strip())
        registered = {s for v in self.korean["spellings"].values() for s in v}
        self.assertFalse(registered & set(excluded))

    def test_korean_spelling_maps_to_exactly_one_standard_name(self):
        seen: dict[str, str] = {}
        for target, spellings in self.korean["spellings"].items():
            for spelling in spellings:
                self.assertNotIn(spelling, seen, f"{spelling!r} is registered twice")
                seen[spelling] = target
