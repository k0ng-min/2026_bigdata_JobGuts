import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from src.agent.cache import JudgementCache, NullCache, cache_key
from src.agent.judgement import Judgement
from src.agent.loop import LoopCounters, process_candidate
from src.agent.memory import AgentMemory
from src.agent.tools import AgentTools, ContextIndex

STANDARD = {"Java", "JavaScript", "Spring Boot"}


class _Judge:
    """Records every call so the tests can assert a model was not consulted."""

    provider_name = "stub"
    is_mock = True

    def __init__(self, answers: dict[str, Judgement]):
        self.answers = answers
        self.calls: list[str] = []

    def judge(self, name, context):
        self.calls.append(name)
        return self.answers.get(
            name,
            Judgement(name, "needs_review", None, 0.0, "no answer", self.provider_name, True),
        )


def _memory() -> AgentMemory:
    return AgentMemory({"java": "Java"}, set(STANDARD), "test.v1")


def _tools(memory, snippets=("Java 백엔드 개발",), neighbours=("Spring",)) -> AgentTools:
    index = ContextIndex()
    index.snippets["X"] = list(snippets)
    index.neighbours["X"] = Counter(neighbours)
    index.occurrences["X"] = 100
    index.section_hits["X"] = 7
    return AgentTools(memory, index)


def _run(name, tools, cache, judge, counters=None, remaining=10, apply_at=0.8, flag_at=0.5):
    return process_candidate(
        name, 100, tools, cache, judge, counters or LoopCounters(), apply_at, flag_at, remaining
    )


class MemoryBeforeModelTests(unittest.TestCase):
    def test_a_confirmed_dictionary_hit_never_reaches_the_model(self):
        memory = _memory()
        judge = _Judge({})
        counters = LoopCounters()
        judgement, log, called = _run("JAVA", _tools(memory), NullCache("d", "p"), judge, counters)

        self.assertEqual((judgement.decision, judgement.canonical), ("canonical", "Java"))
        self.assertEqual(judge.calls, [])
        self.assertFalse(called)
        self.assertEqual(counters.dictionary_hits, 1)
        self.assertEqual([step["tool"] for step in log.steps], ["cache", "lookup_dictionary"])

    def test_an_unknown_spelling_does_reach_the_model(self):
        memory = _memory()
        judge = _Judge({"Pytorch": Judgement("Pytorch", "needs_review", None, 0.2, "r", "stub", True)})
        counters = LoopCounters()
        _run("Pytorch", _tools(memory), NullCache("d", "p"), judge, counters)

        self.assertEqual(judge.calls, ["Pytorch"])
        self.assertEqual(counters.llm_calls, 1)

    def test_a_judgement_is_reflected_back_and_serves_a_later_candidate(self):
        # The fourth element of the agent: what was decided changes what happens
        # next. Without a cache the second spelling can only be answered by the
        # learned layer.
        memory = _memory()
        tools = _tools(memory)
        judge = _Judge({"SpringBoot": Judgement("SpringBoot", "canonical", "Spring Boot", 0.9, "r", "stub", True)})
        counters = LoopCounters()
        cache = NullCache("d", "p")

        _run("SpringBoot", tools, cache, judge, counters)
        self.assertEqual(memory.lookup_learned("springboot"), ("Spring Boot", 0.9))

        judgement, log, called = _run("springboot", tools, cache, judge, counters)

        self.assertEqual(judgement.canonical, "Spring Boot")
        self.assertEqual(judge.calls, ["SpringBoot"], "the model must not be asked a second time")
        self.assertFalse(called)
        self.assertEqual(counters.learned_hits, 1)
        self.assertIn("lookup_learned", [step["tool"] for step in log.steps])


class ConfidenceTests(unittest.TestCase):
    def _judgement(self, confidence):
        return Judgement("Vue3", "canonical", "Java", confidence, "r", "stub", True)

    def test_a_confident_mapping_is_applied(self):
        memory = _memory()
        judge = _Judge({"Vue3": self._judgement(0.95)})
        judgement, log, _ = _run("Vue3", _tools(memory), NullCache("d", "p"), judge)
        self.assertEqual(judgement.decision, "canonical")
        self.assertFalse(log.outcome["low_confidence"])

    def test_a_middling_mapping_is_applied_but_flagged(self):
        memory = _memory()
        judge = _Judge({"Vue3": self._judgement(0.6)})
        judgement, log, _ = _run("Vue3", _tools(memory), NullCache("d", "p"), judge)
        self.assertEqual(judgement.decision, "canonical")
        self.assertTrue(log.outcome["low_confidence"])

    def test_a_weak_mapping_becomes_needs_review(self):
        memory = _memory()
        judge = _Judge({"Vue3": self._judgement(0.2)})
        judgement, _, _ = _run("Vue3", _tools(memory), NullCache("d", "p"), judge)
        self.assertEqual(judgement.decision, "needs_review")
        self.assertIsNone(judgement.canonical)

    def test_a_standard_name_outside_the_vocabulary_is_refused_by_memory(self):
        memory = _memory()
        judge = _Judge({"Groovyish": Judgement("Groovyish", "canonical", "Groovy", 0.99, "r", "stub", True)})
        judgement, log, _ = _run("Groovyish", _tools(memory), NullCache("d", "p"), judge)

        self.assertEqual(judgement.decision, "needs_review")
        self.assertIn("rejected by memory", judgement.reason)
        self.assertFalse(next(s for s in log.steps if s["tool"] == "propose_canonical")["result"]["accepted"])


class BudgetAndCacheTests(unittest.TestCase):
    def test_the_model_is_not_called_once_the_budget_is_gone(self):
        memory = _memory()
        judge = _Judge({})
        counters = LoopCounters()
        judgement, _, _ = _run("Unknown", _tools(memory), NullCache("d", "p"), judge, counters, remaining=0)

        self.assertEqual(judgement.decision, "needs_review")
        self.assertIn("budget", judgement.reason)
        self.assertEqual(judge.calls, [])
        self.assertEqual(counters.llm_calls_skipped_by_budget, 1)

    def test_the_same_spelling_is_asked_about_once(self):
        memory = _memory()
        tools = _tools(memory)
        judge = _Judge({"Zed": Judgement("Zed", "new_technology", None, 0.9, "r", "stub", True)})
        cache = JudgementCache("d", "p")
        counters = LoopCounters()

        _run("Zed", tools, cache, judge, counters)
        _run("Zed", tools, cache, judge, counters)

        self.assertEqual(judge.calls, ["Zed"])
        self.assertEqual(counters.cache_hits, 1)
        self.assertEqual(cache.statistics["hits"], 1)

    def test_the_cache_key_changes_with_the_dictionary_and_prompt_version(self):
        self.assertNotEqual(cache_key("x", "d1", "p"), cache_key("x", "d2", "p"))
        self.assertNotEqual(cache_key("x", "d", "p1"), cache_key("x", "d", "p2"))
        self.assertEqual(cache_key("JAVA", "d", "p"), cache_key(" java ", "d", "p"))

    def test_a_saved_cache_is_reused_by_the_next_run(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "cache.json"
        first = JudgementCache("d", "p")
        first.put(Judgement("Zed", "new_technology", None, 0.9, "r", "stub", True))
        first.save(path)

        second = JudgementCache.load(path, "d", "p")
        self.assertIsNotNone(second.get("Zed"))
        self.assertIsNone(JudgementCache.load(path, "other", "p").get("Zed"))


class ToolLogTests(unittest.TestCase):
    def test_every_call_is_logged_with_its_arguments_and_result(self):
        memory = _memory()
        judge = _Judge({"Pytorch": Judgement("Pytorch", "canonical", "Java", 0.9, "r", "stub", True)})
        _, log, _ = _run("Pytorch", _tools(memory), NullCache("d", "p"), judge)

        tools_used = [step["tool"] for step in log.steps]
        self.assertEqual(
            tools_used,
            ["cache", "lookup_dictionary", "lookup_learned", "get_context", "get_cooccurrence",
             "judge", "propose_canonical"],
        )
        for step in log.steps:
            self.assertIn("arguments", step)
            self.assertIn("result", step)
        self.assertEqual(log.as_record()["candidate"], "Pytorch")
        self.assertEqual(log.outcome["route"], "model")

    def test_the_context_passed_to_the_model_is_recorded(self):
        memory = _memory()
        judge = _Judge({})
        index = ContextIndex()
        index.snippets["X"] = ["Java 백엔드 개발"]
        index.neighbours["X"] = Counter({"Spring": 4})
        index.occurrences["X"] = 100
        index.section_hits["X"] = 7
        _, log, _ = _run("X", AgentTools(memory, index), NullCache("d", "p"), judge)

        judged = next(step for step in log.steps if step["tool"] == "judge")
        self.assertEqual(judged["arguments"]["context"]["snippets"], ["Java 백엔드 개발"])
        self.assertEqual(judged["arguments"]["context"]["neighbours"], ["Spring"])
        self.assertEqual(judged["arguments"]["context"]["section_occurrences"], 7)


class ContextIndexTests(unittest.TestCase):
    def test_the_index_only_tracks_the_candidates_it_was_asked_about(self):
        from src.agent.extract import Candidate

        postings = [{"raw_text": "Java 와 Spring 을 씁니다"}]
        extracted = [(Candidate("Java", "section"), Candidate("Spring", "body"))]
        index = ContextIndex.build(postings, extracted, {"Java"})

        self.assertIn("Java", index.occurrences)
        self.assertNotIn("Spring", index.occurrences)
        self.assertEqual(index.section_hits["Java"], 1)
        self.assertEqual(index.neighbours["Java"].most_common(1), [("Spring", 1)])
        self.assertTrue(index.snippets["Java"][0].startswith("Java"))


class MemoryStateTests(unittest.TestCase):
    def test_decisions_are_filed_under_the_right_heading(self):
        memory = _memory()
        memory.remember(Judgement("A", "canonical", "Java", 0.9, "r", "s", True))
        memory.remember(Judgement("B", "not_a_technology", None, 0.9, "r", "s", True))
        memory.remember(Judgement("C", "new_technology", None, 0.9, "r", "s", True))
        memory.remember(Judgement("D", "needs_review", None, 0.1, "r", "s", True))

        self.assertEqual(memory.learned["a"], ("Java", 0.9))
        self.assertIn("b", memory.rejected)
        self.assertIn("c", memory.new_technologies)
        self.assertIn("d", memory.undecided)

    def test_memory_is_built_from_dictionary_v2(self):
        root = Path(__file__).resolve().parents[1]
        memory = AgentMemory.from_dictionary(root / "configs" / "tech_dictionary_v2.json")

        self.assertEqual(memory.lookup_confirmed("JAVA"), "Java")
        self.assertEqual(memory.lookup_confirmed("자바"), "Java")
        self.assertIsNone(memory.lookup_confirmed("SI"))
        self.assertIn("Java", memory.standard_names)
