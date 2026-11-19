"""Turn a provider's text answer into one of the four decisions.

The prompt is kept here rather than in the provider so that swapping GLM for
another model does not change what is asked. The parser never guesses: an
answer it cannot read becomes ``needs_review`` with the raw text recorded, so a
malformed response degrades into a review item instead of a wrong mapping.
"""

from __future__ import annotations

import json
import re

from src.llm.contracts import LLMProvider, LLMRequest

from .judgement import DECISIONS, Judgement

PROMPT_VERSION = "agent-judge.v1"

SYSTEM_PROMPT = (
    "You classify a single string taken from a Korean IT job posting. "
    "Answer with one JSON object and nothing else, using these keys: "
    '"decision" (one of canonical, not_a_technology, new_technology, needs_review), '
    '"canonical" (the standard name when decision is canonical, otherwise null), '
    '"confidence" (0.0 to 1.0), "reason" (one short sentence). '
    "Choose canonical only when the string denotes a technology in the provided standard name list, "
    "and copy that name exactly. Choose not_a_technology for business terms, roles, company names and "
    "ordinary words. Choose new_technology for a real technology that is absent from the list. "
    "Choose needs_review whenever the string is ambiguous or names more than one thing. "
    "Never invent a standard name that is not in the list."
)


def build_request(name: str, context: dict[str, object]) -> LLMRequest:
    snippets = context.get("snippets") or []
    neighbours = context.get("neighbours") or []
    allowed = context.get("standard_names") or []
    message = "\n".join([
        f"String: {name}",
        f"Occurrences in the corpus: {context.get('occurrences', 'unknown')}",
        f"Occurrences inside a technology list section: {context.get('section_occurrences', 'unknown')}",
        "Context lines from real postings:",
        *([f"  - {snippet}" for snippet in snippets] or ["  (none found)"]),
        f"Frequently co-occurring strings: {', '.join(str(item) for item in neighbours) or '(none)'}",
        f"Standard names you may use: {', '.join(str(item) for item in allowed)}",
    ])
    return LLMRequest(user_message=message, context={"system": SYSTEM_PROMPT, "temperature": 0.0})


def parse_response(name: str, text: str, provider_name: str, is_mock: bool, allowed: set[str]) -> Judgement:
    """Read a provider answer; anything unreadable becomes needs_review."""
    def undecided(reason: str) -> Judgement:
        return Judgement(name, "needs_review", None, 0.0, reason, provider_name, is_mock)

    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not match:
        return undecided(f"response contained no JSON object: {(text or '')[:120]!r}")
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError as error:
        return undecided(f"response JSON could not be parsed: {error}")
    if not isinstance(payload, dict):
        return undecided("response JSON was not an object")

    decision = str(payload.get("decision", "")).strip()
    if decision not in DECISIONS:
        return undecided(f"unknown decision {decision!r}")
    canonical = payload.get("canonical")
    canonical = str(canonical).strip() if canonical else None
    reason = str(payload.get("reason", "")).strip() or "no reason given"
    try:
        confidence = float(payload.get("confidence", 0.0))
    except (TypeError, ValueError):
        return undecided("confidence was not a number")
    confidence = min(max(confidence, 0.0), 1.0)

    if decision == "canonical":
        if not canonical:
            return undecided("canonical decision named no standard name")
        if canonical not in allowed:
            # The model invented a name. Refusing it here is what keeps the
            # vocabulary closed, which is the whole point of dictionary v2.
            return undecided(f"proposed standard name {canonical!r} is not in the vocabulary")
    else:
        canonical = None
    return Judgement(name, decision, canonical, confidence, reason, provider_name, is_mock)


class ModelJudge:
    """Adapts any LLMProvider to the judge interface the agent loop expects."""

    def __init__(self, provider: LLMProvider, allowed: set[str]):
        self.provider = provider
        self.allowed = allowed
        self.provider_name = getattr(provider, "provider_name", "unknown")
        self.is_mock = bool(getattr(provider, "is_mock", False))

    def judge(self, name: str, context: dict[str, object]) -> Judgement:
        request = build_request(name, {**context, "standard_names": sorted(self.allowed)})
        response = self.provider.generate(request)
        return parse_response(name, response.text, response.provider_name, response.is_mock, self.allowed)
