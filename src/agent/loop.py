"""One candidate through the agent: remember, look, reason, reflect.

The order is what makes the run affordable as much as what makes it correct.
Cache and dictionary hits never reach a model, so the only candidates that cost
anything are the ones nothing already knows about. Every step is appended to a
log with the tool called, what was passed and what came back, which is the
evidence the week-13 "tool call log" requirement asks for.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .judgement import Judgement


@dataclass
class StepLog:
    """What happened to one candidate, in order."""

    name: str
    occurrences: int
    steps: list[dict] = field(default_factory=list)
    outcome: dict | None = None

    def record(self, tool: str, arguments: dict, result: dict) -> None:
        self.steps.append({"tool": tool, "arguments": arguments, "result": result})

    def as_record(self) -> dict:
        return {"candidate": self.name, "occurrences": self.occurrences, "steps": self.steps, "outcome": self.outcome}


@dataclass
class LoopCounters:
    cache_hits: int = 0
    dictionary_hits: int = 0
    learned_hits: int = 0
    llm_calls: int = 0
    llm_calls_skipped_by_budget: int = 0


def process_candidate(
    name: str,
    occurrences: int,
    tools,
    cache,
    judge,
    counters: LoopCounters,
    apply_threshold: float,
    flag_threshold: float,
    remaining_calls: int,
) -> tuple[Judgement, StepLog, bool]:
    """Return the decision, its log, and whether a model was actually called."""
    log = StepLog(name=name, occurrences=occurrences)

    cached = cache.get(name)
    if cached is not None:
        counters.cache_hits += 1
        log.record("cache", {"name": name}, {"hit": True, "decision": cached.decision})
        log.outcome = {**cached.as_record(), "route": "cache", "low_confidence": False}
        return cached, log, False
    log.record("cache", {"name": name}, {"hit": False})

    # Memory: the confirmed dictionary a person approved.
    confirmed = tools.lookup_dictionary(name)
    log.record("lookup_dictionary", {"name": name}, confirmed)
    if confirmed["canonical"]:
        counters.dictionary_hits += 1
        judgement = Judgement(name, "canonical", confirmed["canonical"], 1.0,
                              "confirmed dictionary entry", "dictionary", False)
        log.outcome = {**judgement.as_record(), "route": "dictionary", "low_confidence": False}
        cache.put(judgement)
        return judgement, log, False

    # Memory: what this run has already decided. This is where a judgement made
    # earlier changes the handling of a later candidate.
    learned = tools.lookup_learned(name)
    log.record("lookup_learned", {"name": name}, learned)
    if learned["canonical"]:
        counters.learned_hits += 1
        judgement = Judgement(name, "canonical", learned["canonical"], float(learned["confidence"]),
                              "learned earlier in this run", "learned", False)
        log.outcome = {**judgement.as_record(), "route": "learned", "low_confidence": False}
        cache.put(judgement)
        return judgement, log, False

    if remaining_calls <= 0:
        counters.llm_calls_skipped_by_budget += 1
        judgement = Judgement(name, "needs_review", None, 0.0,
                              "model call budget exhausted before this candidate", "budget", False)
        log.outcome = {**judgement.as_record(), "route": "budget", "low_confidence": False}
        tools.mark_needs_review(name, judgement.reason)
        return judgement, log, False

    # Tools: read the postings again before asking anything.
    context = tools.get_context(name)
    log.record("get_context", {"name": name}, context)
    cooccurrence = tools.get_cooccurrence(name)
    log.record("get_cooccurrence", {"name": name}, cooccurrence)

    # Reasoning.
    payload = {
        "snippets": context["snippets"],
        "neighbours": [item["name"] for item in cooccurrence["neighbours"]],
        "occurrences": context["occurrences"] or occurrences,
        "section_occurrences": context["section_occurrences"],
    }
    judgement = judge.judge(name, payload)
    counters.llm_calls += 1
    log.record("judge", {"name": name, "context": payload}, judgement.as_record())

    # A decision the model is unsure about is downgraded rather than applied.
    low_confidence = False
    if judgement.decision == "canonical":
        if judgement.confidence < flag_threshold:
            judgement = Judgement(name, "needs_review", None, judgement.confidence,
                                  f"confidence {judgement.confidence:.2f} below {flag_threshold}: {judgement.reason}",
                                  judgement.provider, judgement.is_mock)
        elif judgement.confidence < apply_threshold:
            low_confidence = True

    # Reflection: write the decision back so later candidates see it.
    if judgement.decision == "canonical" and judgement.canonical:
        result = tools.propose_canonical(name, judgement.canonical, judgement.confidence, judgement.reason)
        log.record("propose_canonical", {"name": name, "canonical": judgement.canonical,
                                         "confidence": judgement.confidence, "reason": judgement.reason}, result)
        if not result["accepted"]:
            judgement = Judgement(name, "needs_review", None, judgement.confidence,
                                  f"rejected by memory: {result['reason']}", judgement.provider, judgement.is_mock)
            low_confidence = False
    elif judgement.decision == "not_a_technology":
        log.record("mark_not_a_technology", {"name": name, "reason": judgement.reason},
                   tools.mark_not_a_technology(name, judgement.reason))
    elif judgement.decision == "new_technology":
        # Outside the vocabulary: kept as its own name, not mapped onto a
        # standard name, because inventing one is what dictionary v2 forbids.
        log.record("mark_needs_review", {"name": name, "reason": judgement.reason},
                   {"accepted": True, "kept_as": "new_technology"})
        tools.memory.new_technologies[name.casefold()] = judgement.reason
    else:
        log.record("mark_needs_review", {"name": name, "reason": judgement.reason},
                   tools.mark_needs_review(name, judgement.reason))

    log.outcome = {**judgement.as_record(), "route": "model", "low_confidence": low_confidence}
    cache.put(judgement)
    return judgement, log, True
