import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.agent.fake_judge import FakeJudgeProvider
from src.agent.judge import ModelJudge, build_request, parse_response
from src.agent.judgement import DECISIONS, Judgement
from src.llm.contracts import LLMResponse
from src.llm.glm_provider import API_KEY_VARIABLE, GLMProvider, MissingCredentialError, load_dotenv

ALLOWED = {"JavaScript", "Java", "Python", "REST API", "Spring Boot"}


class JudgementTests(unittest.TestCase):
    def test_a_canonical_decision_must_name_a_standard_name(self):
        with self.assertRaises(ValueError):
            Judgement("js", "canonical", None, 0.9, "r", "fake", True)

    def test_a_non_canonical_decision_must_not_name_one(self):
        with self.assertRaises(ValueError):
            Judgement("SI", "not_a_technology", "Java", 0.9, "r", "fake", True)

    def test_confidence_outside_the_range_is_rejected(self):
        with self.assertRaises(ValueError):
            Judgement("x", "needs_review", None, 1.5, "r", "fake", True)

    def test_unknown_decisions_are_rejected(self):
        with self.assertRaises(ValueError):
            Judgement("x", "maybe", None, 0.5, "r", "fake", True)


class FakeJudgeTests(unittest.TestCase):
    def setUp(self):
        self.judge = FakeJudgeProvider()

    def test_all_four_decision_paths_are_reachable(self):
        reached = {self.judge.judge(name, {}).decision for name in ("Javascript", "SI", "RAG", "API")}
        self.assertEqual(reached, set(DECISIONS))

    def test_an_unknown_spelling_is_never_guessed(self):
        result = self.judge.judge("전혀 모르는 이름", {})
        self.assertEqual(result.decision, "needs_review")
        self.assertEqual(result.confidence, 0.0)

    def test_results_are_marked_as_mock(self):
        self.assertTrue(self.judge.judge("Javascript", {}).is_mock)

    def test_the_same_input_always_gives_the_same_answer(self):
        first = self.judge.judge("Javascript", {}).as_record()
        second = FakeJudgeProvider().judge("Javascript", {}).as_record()
        self.assertEqual(first, second)


class ResponseParsingTests(unittest.TestCase):
    def _parse(self, text):
        return parse_response("x", text, "glm", False, ALLOWED)

    def test_a_well_formed_answer_is_read(self):
        result = self._parse('{"decision":"canonical","canonical":"Java","confidence":0.9,"reason":"ok"}')
        self.assertEqual((result.decision, result.canonical), ("canonical", "Java"))

    def test_an_invented_standard_name_is_refused(self):
        result = self._parse('{"decision":"canonical","canonical":"Groovy","confidence":0.99,"reason":"ok"}')
        self.assertEqual(result.decision, "needs_review")
        self.assertIn("not in the vocabulary", result.reason)

    def test_unreadable_answers_become_needs_review_rather_than_an_error(self):
        for text in ("", "I think it is Java", '{"decision":', '{"decision":"banana"}', "null"):
            result = self._parse(text)
            self.assertEqual(result.decision, "needs_review", text)
            self.assertEqual(result.canonical, None)

    def test_a_non_numeric_confidence_becomes_needs_review(self):
        result = self._parse('{"decision":"canonical","canonical":"Java","confidence":"high","reason":"r"}')
        self.assertEqual(result.decision, "needs_review")

    def test_confidence_is_clamped_into_range(self):
        result = self._parse('{"decision":"new_technology","canonical":null,"confidence":4,"reason":"r"}')
        self.assertEqual(result.confidence, 1.0)

    def test_surrounding_prose_around_the_json_is_tolerated(self):
        result = self._parse('Sure!\n{"decision":"not_a_technology","canonical":null,"confidence":0.8,"reason":"role"}\nDone.')
        self.assertEqual(result.decision, "not_a_technology")

    def test_the_prompt_lists_only_the_allowed_standard_names(self):
        request = build_request("x", {"standard_names": ["Java", "Python"], "snippets": ["line"]})
        self.assertIn("Java, Python", request.user_message)
        self.assertIn("Never invent a standard name", str(request.context["system"]))


class ModelJudgeTests(unittest.TestCase):
    class _Provider:
        provider_name = "stub"
        is_mock = False

        def __init__(self, text):
            self.text = text
            self.calls = 0

        def generate(self, request):
            self.calls += 1
            return LLMResponse(text=self.text, provider_name=self.provider_name, is_mock=False)

    def test_a_provider_answer_becomes_a_judgement(self):
        provider = self._Provider('{"decision":"canonical","canonical":"Python","confidence":0.8,"reason":"r"}')
        result = ModelJudge(provider, ALLOWED).judge("python", {})
        self.assertEqual((result.decision, result.canonical, result.is_mock), ("canonical", "Python", False))
        self.assertEqual(provider.calls, 1)


class GLMCredentialTests(unittest.TestCase):
    def test_constructing_without_a_key_fails_with_an_actionable_message(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(API_KEY_VARIABLE, None)
            with self.assertRaises(MissingCredentialError) as caught:
                GLMProvider(dotenv_path=Path(temp_dir.name) / "absent.env")

        message = str(caught.exception)
        self.assertIn(API_KEY_VARIABLE, message)
        self.assertIn("--provider fake", message)
        self.assertIn(".env is excluded from version control", message)

    def test_a_dotenv_value_is_used_but_never_overrides_the_environment(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        dotenv = Path(temp_dir.name) / ".env"
        dotenv.write_text(f'# comment\n{API_KEY_VARIABLE}="from-file"\n', encoding="utf-8")

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(API_KEY_VARIABLE, None)
            provider = GLMProvider(dotenv_path=dotenv)
            self.assertEqual(provider.api_key, "from-file")

        with patch.dict(os.environ, {API_KEY_VARIABLE: "from-shell"}, clear=False):
            load_dotenv(dotenv)
            self.assertEqual(os.environ[API_KEY_VARIABLE], "from-shell")

    def test_the_repository_ships_an_example_but_no_real_env_file(self):
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root / ".env.example").is_file())
        example = (root / ".env.example").read_text(encoding="utf-8")
        self.assertIn(f"{API_KEY_VARIABLE}=", example)
        for line in example.splitlines():
            if line.startswith(f"{API_KEY_VARIABLE}="):
                self.assertEqual(line.strip(), f"{API_KEY_VARIABLE}=", "the example must not carry a value")

    def test_gitignore_excludes_env(self):
        root = Path(__file__).resolve().parents[1]
        self.assertIn(".env", (root / ".gitignore").read_text(encoding="utf-8").split())


class FakeJudgeAgreesWithTheCuratedExclusionsTests(unittest.TestCase):
    """The rule table must not assert what the dictionary refuses to assert."""

    def setUp(self):
        self.judge = FakeJudgeProvider()
        root = Path(__file__).resolve().parents[1]
        self.curated = json.loads((root / "configs" / "tech_dictionary_curated.json").read_text(encoding="utf-8"))

    def test_boot_is_not_mapped_to_spring_boot(self):
        # configs/tech_dictionary_curated.json excludes Boot because it only
        # means Spring Boot when Spring is nearby. The table once mapped it
        # anyway and produced 1,192 in-vocabulary errors on its own.
        result = self.judge.judge("Boot", {})
        self.assertEqual(result.decision, "needs_review")
        self.assertIsNone(result.canonical)

    def test_no_curated_exclusion_is_mapped_by_the_rule_table(self):
        for spelling in self.curated["excluded_on_purpose"]:
            result = self.judge.judge(spelling, {})
            self.assertNotEqual(result.decision, "canonical", f"{spelling!r} is excluded on purpose")
