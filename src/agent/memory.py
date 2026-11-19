"""What the agent remembers: the confirmed dictionary plus what it has learned.

Two layers, deliberately kept apart. The confirmed layer is dictionary v2,
which a person approved and a model may not change. The learned layer holds the
decisions reached during this run; it is consulted before any model call, so a
spelling judged once steers the spellings that follow. That consultation is the
"result reflected back" element of the agent: without it each candidate would
be judged in isolation and the run would not accumulate anything.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .judgement import Judgement


def lookup_key(name: str) -> str:
    """Case-insensitive key that still tells C, C++ and C# apart."""
    return re.sub(r"\s+", " ", name.casefold()).strip()


class AgentMemory:
    def __init__(self, confirmed: dict[str, str], standard_names: set[str], version: str):
        #: spelling key -> standard name, approved by a person
        self.confirmed = confirmed
        #: the closed vocabulary a decision may point at
        self.standard_names = standard_names
        self.dictionary_version = version
        #: spelling key -> (standard name, confidence), learned during this run
        self.learned: dict[str, tuple[str, float]] = {}
        #: spelling key -> reason, judged not to be a technology
        self.rejected: dict[str, str] = {}
        #: spelling key -> reason, a real technology outside the vocabulary
        self.new_technologies: dict[str, str] = {}
        #: spelling key -> reason, left for a person
        self.undecided: dict[str, str] = {}

    @classmethod
    def from_dictionary(cls, path: str | Path) -> "AgentMemory":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        confirmed: dict[str, str] = {}
        for record in payload["technologies"]:
            for item in record["spellings"]:
                confirmed[lookup_key(item["spelling"])] = record["canonical"]
        standard = {record["canonical"] for record in payload["technologies"]}
        return cls(confirmed, standard, payload["version"])

    def lookup_confirmed(self, name: str) -> str | None:
        return self.confirmed.get(lookup_key(name))

    def lookup_learned(self, name: str) -> tuple[str, float] | None:
        return self.learned.get(lookup_key(name))

    def remember(self, judgement: Judgement) -> None:
        """Record a decision so later candidates in the same run can use it."""
        key = lookup_key(judgement.name)
        if judgement.decision == "canonical" and judgement.canonical:
            self.learned[key] = (judgement.canonical, judgement.confidence)
        elif judgement.decision == "not_a_technology":
            self.rejected[key] = judgement.reason
        elif judgement.decision == "new_technology":
            self.new_technologies[key] = judgement.reason
        else:
            self.undecided[key] = judgement.reason

    @property
    def statistics(self) -> dict:
        return {
            "confirmed_spellings": len(self.confirmed),
            "standard_names": len(self.standard_names),
            "learned_mappings": len(self.learned),
            "rejected": len(self.rejected),
            "new_technologies": len(self.new_technologies),
            "undecided": len(self.undecided),
        }
