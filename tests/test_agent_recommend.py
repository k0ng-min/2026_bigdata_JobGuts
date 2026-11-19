import unittest

from src.agent.recommend import METRICS_SCOPE_NOTE, RELAXATION_ORDER, recommend_with_relaxation


class _Repository:
    """Answers ok only when the filters it was told to accept are in force."""

    def __init__(self, ok_when, rules_exist=True):
        self.ok_when = ok_when
        self.rules_exist = rules_exist
        self.calls = []

    def recommend(self, skills, job_role=None, experience_segment=None, entry_eligible=False):
        self.calls.append((tuple(skills), job_role, experience_segment, entry_eligible))
        if not self.rules_exist or tuple(skills) not in self.ok_when:
            return {"status": "no_rules", "recommendations": [], "next_action": "Add a known skill or broaden filters."}
        filters = self.ok_when[tuple(skills)]
        if (job_role, experience_segment, entry_eligible) == filters:
            return {"status": "ok", "recommendations": [{"antecedent": list(skills), "consequent": ["X"]}],
                    "evidence_postings": [{"source": "s", "job_id": "1", "title": "t"}]}
        return {"status": "insufficient_sample", "recommendations": [{"antecedent": list(skills), "consequent": ["X"]}],
                "evidence_postings": []}


class _Dictionary:
    def __init__(self, mapping):
        self.mapping = mapping

    def canonicalize(self, value):
        return self.mapping.get(value.casefold())


class RelaxationOrderTests(unittest.TestCase):
    def test_experience_is_released_before_job_role(self):
        self.assertEqual(RELAXATION_ORDER, ("experience_segment", "job_role"))

    def test_an_answerable_query_is_not_widened(self):
        repository = _Repository({("Java",): ("frontend", "신입", False)})
        result = recommend_with_relaxation(repository, ["Java"], "frontend", "신입")

        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["search_was_widened"])
        self.assertEqual(result["relaxation_steps"], [])
        self.assertNotIn("disclosure", result)

    def test_experience_is_released_first_and_reported(self):
        repository = _Repository({("Java",): ("frontend", None, False)})
        result = recommend_with_relaxation(repository, ["Java"], "frontend", "신입")

        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["search_was_widened"])
        self.assertEqual([step["released"] for step in result["relaxation_steps"]], ["experience_segment"])
        self.assertEqual(result["requested_filters"]["experience_segment"], "신입")
        self.assertEqual(result["applied_filters"]["experience_segment"], "all")
        self.assertEqual(result["applied_filters"]["job_role"], "frontend")
        self.assertIn("experience_segment", result["disclosure"])

    def test_job_role_is_released_next_when_experience_was_not_enough(self):
        repository = _Repository({("Java",): (None, None, False)})
        result = recommend_with_relaxation(repository, ["Java"], "frontend", "신입")

        self.assertEqual([step["released"] for step in result["relaxation_steps"]],
                         ["experience_segment", "job_role"])
        self.assertEqual(result["applied_filters"], {"job_role": "all", "experience_segment": "all",
                                                     "entry_eligible_only": False})

    def test_entry_eligibility_is_released_last(self):
        repository = _Repository({("Java",): (None, None, False)})
        result = recommend_with_relaxation(repository, ["Java"], "frontend", "신입", entry_eligible=True)

        self.assertEqual([step["released"] for step in result["relaxation_steps"]],
                         ["experience_segment", "job_role", "entry_eligible"])
        self.assertFalse(result["applied_filters"]["entry_eligible_only"])

    def test_widening_stops_at_the_configured_step_limit(self):
        repository = _Repository({("Java",): (None, None, False)})
        result = recommend_with_relaxation(repository, ["Java"], "frontend", "신입", max_steps=1)

        self.assertEqual(len(result["relaxation_steps"]), 1)
        self.assertEqual(result["status"], "insufficient_sample")


class NoRulesTests(unittest.TestCase):
    def test_no_rules_is_retried_once_with_the_normalised_spelling(self):
        repository = _Repository({("PyTorch",): (None, None, False)})
        dictionary = _Dictionary({"pytorch": "PyTorch"})
        result = recommend_with_relaxation(repository, ["Pytorch"], dictionary=dictionary)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["normalized_skills"], ["PyTorch"])
        self.assertEqual([call[0] for call in repository.calls], [("Pytorch",), ("PyTorch",)])

    def test_no_rules_is_not_widened_because_filters_are_not_the_cause(self):
        repository = _Repository({}, rules_exist=False)
        result = recommend_with_relaxation(repository, ["Nope"], "frontend", "신입",
                                           dictionary=_Dictionary({}))

        self.assertEqual(result["status"], "no_rules")
        self.assertEqual(result["relaxation_steps"], [])
        self.assertIn("Check the spelling", result["next_action"])

    def test_the_requested_technology_is_never_swapped_for_another(self):
        repository = _Repository({}, rules_exist=False)
        result = recommend_with_relaxation(repository, ["Nope"], dictionary=_Dictionary({}))

        self.assertEqual(result["requested_filters"]["skills"], ["Nope"])
        for call in repository.calls:
            self.assertEqual(call[0], ("Nope",))


class DisclosureTests(unittest.TestCase):
    def test_every_response_states_that_metrics_are_global(self):
        repository = _Repository({("Java",): (None, None, False)})
        for kwargs in ({}, {"job_role": "frontend", "experience_segment": "신입"}):
            result = recommend_with_relaxation(repository, ["Java"], **kwargs)
            self.assertEqual(result["metrics_scope"], "all_postings")
            self.assertEqual(result["metrics_note"], METRICS_SCOPE_NOTE)

    def test_the_original_request_is_always_preserved_alongside_what_was_used(self):
        repository = _Repository({("Java",): (None, None, False)})
        result = recommend_with_relaxation(repository, ["Java"], "frontend", "신입")

        self.assertEqual(result["requested_filters"],
                         {"skills": ["Java"], "job_role": "frontend", "experience_segment": "신입",
                          "entry_eligible": False})
        self.assertNotEqual(result["requested_filters"]["job_role"], result["applied_filters"]["job_role"])
