"""Deterministic stand-in for a real model, used by tests and the default run.

It satisfies the same call shape as a real provider but reaches its decisions
from a small rule table rather than by reasoning, so every one of the four
decision paths can be exercised without a network call or an API key. Results
are marked ``is_mock`` so no artifact can be mistaken for model output.

The rule table is not an attempt to be correct. Unknown spellings fall through
to ``needs_review`` with confidence 0.0, which is the safe default: the original
spelling is preserved and a person decides.
"""

from __future__ import annotations

import re

from src.llm.contracts import LLMRequest, LLMResponse

from .judgement import Judgement

PROVIDER_NAME = "fake"

#: Spellings the table maps to a standard name.
_CANONICAL = {
    "javascript": ("JavaScript", 0.95),
    "java": ("Java", 0.95),
    "python": ("Python", 0.95),
    "pytorch": ("PyTorch", 0.93),
    "tensorflow": ("TensorFlow", 0.93),
    "kubernetes": ("Kubernetes", 0.93),
    "restful": ("REST API", 0.85),
    "springboot": ("Spring Boot", 0.88),
}
#: Spellings the table rejects, with the kind of term they are.
_NOT_TECHNOLOGY = {
    "si": ("system integration business term", 0.92),
    "sw": ("abbreviation of software, not a named technology", 0.9),
    "pm": ("project or product manager role", 0.93),
    "po": ("product owner role", 0.92),
    "erp": ("business application category", 0.85),
    "crm": ("business application category", 0.85),
    "dba": ("database administrator role", 0.9),
    "qa": ("quality assurance role", 0.9),
    "b2b": ("business model term", 0.95),
    "saas": ("delivery model term", 0.85),
    "md": ("merchandiser role", 0.88),
    "sk": ("company name", 0.95),
    "lg": ("company name", 0.95),
    "ms": ("company name abbreviation", 0.8),
    "kornic": ("company name", 0.95),
    "glory": ("company name fragment", 0.9),
    "top": ("ordinary word", 0.9),
    "d": ("single letter with no technology meaning here", 0.85),
    "k": ("single letter with no technology meaning here", 0.85),
    "b": ("single letter with no technology meaning here", 0.85),
}
#: Spellings the table accepts as real technologies that the vocabulary lacks.
_NEW_TECHNOLOGY = {
    "rag": ("retrieval augmented generation, a named technique", 0.88),
    "jsp": ("JavaServer Pages, a named technology", 0.9),
    "iot": ("internet of things stack", 0.75),
    "msa": ("microservice architecture", 0.72),
    "chatgpt": ("a named product", 0.9),
    "cursor": ("a named editor", 0.8),
    "confluence": ("a named collaboration tool", 0.85),
    "objective-c": ("a named language absent from the vocabulary", 0.92),
    "unix": ("a named operating system family", 0.88),
    "gpu": ("hardware class rather than a vocabulary entry", 0.6),
}
#: Spellings the table explicitly refuses to decide, with the reason.
_NEEDS_REVIEW = {
    "api": "too general: names an interface, not a specific technology",
    "db": "too general: names a category",
    "rest": "names an architectural style, not the REST API entry",
    "ai/ml": "names two concept labels at once",
    "c/c++": "names two languages at once",
    "ui/ux": "names two design concepts at once",
    "agent": "could be an LLM agent or an installed software agent",
    "data": "ordinary word",
    "cloud": "ordinary word in this context",
    "vision": "fragment of computer vision or an ordinary word",
    # Mapping a bare Boot to Spring Boot is exactly what
    # configs/tech_dictionary_curated.json refuses to do: it only means Spring
    # Boot when Spring is nearby, which is a context judgement. The table said
    # otherwise and produced 1,192 of the new in-vocabulary errors on its own.
    "boot": "only means Spring Boot when Spring is nearby; that is a context judgement",
}


def _key(name: str) -> str:
    return re.sub(r"\s+", " ", name.casefold()).strip()


class FakeJudgeProvider:
    """Looks like a provider to the agent; answers from a table."""

    provider_name = PROVIDER_NAME
    is_mock = True

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Kept so the class also satisfies the existing LLMProvider protocol."""
        return LLMResponse(
            text=f"Mock judgement for: {request.user_message}",
            provider_name=self.provider_name,
            is_mock=True,
        )

    def judge(self, name: str, context: dict[str, object]) -> Judgement:
        key = _key(name)
        if key in _CANONICAL:
            canonical, confidence = _CANONICAL[key]
            return Judgement(name, "canonical", canonical, confidence, "rule table: known spelling", PROVIDER_NAME, True)
        if key in _NOT_TECHNOLOGY:
            reason, confidence = _NOT_TECHNOLOGY[key]
            return Judgement(name, "not_a_technology", None, confidence, f"rule table: {reason}", PROVIDER_NAME, True)
        if key in _NEW_TECHNOLOGY:
            reason, confidence = _NEW_TECHNOLOGY[key]
            return Judgement(name, "new_technology", None, confidence, f"rule table: {reason}", PROVIDER_NAME, True)
        if key in _NEEDS_REVIEW:
            return Judgement(name, "needs_review", None, 0.3, f"rule table: {_NEEDS_REVIEW[key]}", PROVIDER_NAME, True)
        return Judgement(
            name,
            "needs_review",
            None,
            0.0,
            "rule table has no entry for this spelling; the fake judge never guesses",
            PROVIDER_NAME,
            True,
        )
