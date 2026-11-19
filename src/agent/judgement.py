"""The four decisions the agent may reach about one candidate spelling.

The decision set is closed on purpose. ``needs_review`` is a designed outcome,
not a failure: deciding whether AI is a technology or a field is a judgement the
team makes, not one a model should make silently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Decision = Literal["canonical", "not_a_technology", "new_technology", "needs_review"]

DECISIONS: tuple[Decision, ...] = ("canonical", "not_a_technology", "new_technology", "needs_review")

#: What each decision means, written into the run artifact so a reader of the
#: log does not have to consult the source.
DECISION_MEANINGS = {
    "canonical": "the spelling denotes a technology already in the final_techs vocabulary",
    "not_a_technology": "the spelling is a business term, a role, a company name or an ordinary word",
    "new_technology": "the spelling denotes a real technology that the vocabulary does not contain",
    "needs_review": "undecided; the original spelling is preserved for a person to judge",
}


@dataclass(frozen=True)
class Judgement:
    """One decision about one candidate, with the evidence it was based on."""

    name: str
    decision: Decision
    canonical: str | None
    confidence: float
    reason: str
    provider: str
    is_mock: bool

    def __post_init__(self) -> None:
        if self.decision not in DECISIONS:
            raise ValueError(f"unknown decision {self.decision!r}; expected one of {DECISIONS}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence {self.confidence!r} is outside 0.0 - 1.0")
        if self.decision == "canonical" and not self.canonical:
            raise ValueError("a canonical decision must name the standard name it maps to")
        if self.decision != "canonical" and self.canonical:
            raise ValueError(f"a {self.decision} decision must not name a standard name")

    def as_record(self) -> dict:
        return {
            "name": self.name,
            "decision": self.decision,
            "canonical": self.canonical,
            "confidence": round(self.confidence, 4),
            "reason": self.reason,
            "provider": self.provider,
            "is_mock": self.is_mock,
        }
