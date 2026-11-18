import unittest

from src.llm import FakeLLMProvider, LLMRequest


class LLMContractTests(unittest.TestCase):
    def test_fake_provider_is_explicitly_marked_as_mock(self):
        response = FakeLLMProvider().generate(LLMRequest("Explain this rule", {"rule_id": "r1"}))

        self.assertTrue(response.is_mock)
        self.assertEqual(response.provider_name, "fake")
