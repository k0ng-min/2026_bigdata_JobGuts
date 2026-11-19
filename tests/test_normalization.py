import json
import tempfile
import unittest
from pathlib import Path

from src.normalization.dictionary import TechnologyDictionary
from src.normalization.normalizer import normalize_technologies


class NormalizationTests(unittest.TestCase):
    def test_aliases_are_canonicalized_and_duplicates_are_removed(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        dictionary_path = Path(temp_dir.name) / "dictionary.json"
        dictionary_path.write_text(json.dumps({
            "version": "test.v1",
            "canonical_technologies": {"JavaScript": ["js", "javascript"]}
        }), encoding="utf-8")
        dictionary = TechnologyDictionary.from_json(dictionary_path)

        result = normalize_technologies(("JS", "JavaScript", "Rust"), dictionary)

        self.assertEqual(result.normalized_techs, ("JavaScript", "Rust"))
        self.assertEqual(result.transformed_count, 1)
        self.assertEqual(result.duplicate_count, 1)
        self.assertEqual(result.unknown_techs, ("Rust",))

    def test_v2_spelling_records_are_loaded_as_aliases(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        dictionary_path = Path(temp_dir.name) / "dictionary-v2.json"
        dictionary_path.write_text(json.dumps({
            "version": "test.v2",
            "technologies": [{
                "canonical": "Python",
                "spellings": [{"spelling": "Python"}, {"spelling": "파이썬"}],
            }],
        }, ensure_ascii=False), encoding="utf-8")

        dictionary = TechnologyDictionary.from_json(dictionary_path)

        self.assertEqual(dictionary.canonicalize("파이썬"), "Python")
