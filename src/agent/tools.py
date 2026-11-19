"""The tools the agent may call. None of them calls a model.

The split matters for cost and for the boundary in docs/llm_boundary.md: the
model chooses what to look at, every lookup happens locally, and no tool
recalculates a rule or a metric.

``get_context`` and ``get_cooccurrence`` are served from an index built in a
single pass over the postings. Scanning the corpus once per candidate would be
593 passes over 17,796 postings; one pass that records what each candidate
needs is cheap enough to run in seconds.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from .extract import Candidate


@dataclass
class ContextIndex:
    """Snippets and neighbours for the candidates the agent will ask about."""

    snippets: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    neighbours: dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))
    section_hits: Counter = field(default_factory=Counter)
    occurrences: Counter = field(default_factory=Counter)

    @classmethod
    def build(
        cls,
        postings: list[dict],
        extracted: list[tuple[Candidate, ...]],
        targets: set[str],
        snippets_per_candidate: int = 3,
        window: int = 120,
    ) -> "ContextIndex":
        index = cls()
        for posting, candidates in zip(postings, extracted):
            names = [candidate.name for candidate in candidates]
            wanted = [name for name in names if name in targets]
            if not wanted:
                continue
            text = posting.get("raw_text") or ""
            for candidate in candidates:
                if candidate.name not in targets:
                    continue
                index.occurrences[candidate.name] += 1
                if candidate.source == "section":
                    index.section_hits[candidate.name] += 1
            for name in wanted:
                index.neighbours[name].update(other for other in names if other != name)
                if len(index.snippets[name]) >= snippets_per_candidate:
                    continue
                position = text.find(name)
                if position < 0:
                    continue
                start = max(0, position - window // 2)
                snippet = re.sub(r"\s+", " ", text[start:position + len(name) + window // 2]).strip()
                index.snippets[name].append(snippet)
        return index


class AgentTools:
    """The callable surface the agent sees. Every call is recorded by the loop."""

    def __init__(self, memory, index: ContextIndex, neighbours_per_candidate: int = 10):
        self.memory = memory
        self.index = index
        self.neighbours_per_candidate = neighbours_per_candidate

    # --- memory lookups -------------------------------------------------
    def lookup_dictionary(self, name: str) -> dict:
        canonical = self.memory.lookup_confirmed(name)
        return {"canonical": canonical, "source": "confirmed"}

    def lookup_learned(self, name: str) -> dict:
        learned = self.memory.lookup_learned(name)
        if learned is None:
            return {"canonical": None, "confidence": 0.0, "source": "learned"}
        canonical, confidence = learned
        return {"canonical": canonical, "confidence": confidence, "source": "learned"}

    # --- corpus lookups -------------------------------------------------
    def get_context(self, name: str) -> dict:
        return {
            "snippets": list(self.index.snippets.get(name, [])),
            "section": self.index.section_hits.get(name, 0) > 0,
            "section_occurrences": self.index.section_hits.get(name, 0),
            "occurrences": self.index.occurrences.get(name, 0),
        }

    def get_cooccurrence(self, name: str) -> dict:
        counter = self.index.neighbours.get(name, Counter())
        return {
            "neighbours": [
                {"name": other, "count": count}
                for other, count in counter.most_common(self.neighbours_per_candidate)
            ]
        }

    # --- writes back into memory ---------------------------------------
    def propose_canonical(self, name: str, canonical: str, confidence: float, reason: str) -> dict:
        if canonical not in self.memory.standard_names:
            return {"accepted": False, "reason": f"{canonical!r} is not a standard name"}
        self.memory.learned[_key(name)] = (canonical, confidence)
        return {"accepted": True}

    def mark_not_a_technology(self, name: str, reason: str) -> dict:
        self.memory.rejected[_key(name)] = reason
        return {"accepted": True}

    def mark_needs_review(self, name: str, reason: str) -> dict:
        self.memory.undecided[_key(name)] = reason
        return {"accepted": True}


def _key(name: str) -> str:
    return re.sub(r"\s+", " ", name.casefold()).strip()
