"""Name-keyed cache so the same spelling is never asked about twice.

Without it the 17,796 eligible postings would produce 375,677 candidate
occurrences, every one a separate call. Keyed by spelling the same work is
27,641 lookups, and inside the occurrence floor it is a few hundred.

The key carries the dictionary and prompt versions: when either changes an old
answer is no longer about the same question, so it is not reused.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .judgement import Judgement


def cache_key(name: str, dictionary_version: str, prompt_version: str) -> str:
    normalized = re.sub(r"\s+", " ", name.casefold()).strip()
    return f"{dictionary_version}|{prompt_version}|{normalized}"


class JudgementCache:
    def __init__(self, dictionary_version: str, prompt_version: str):
        self.dictionary_version = dictionary_version
        self.prompt_version = prompt_version
        self.entries: dict[str, dict] = {}
        self.hits = 0
        self.misses = 0

    @classmethod
    def load(cls, path: str | Path, dictionary_version: str, prompt_version: str) -> "JudgementCache":
        cache = cls(dictionary_version, prompt_version)
        file = Path(path)
        if file.is_file():
            payload = json.loads(file.read_text(encoding="utf-8"))
            cache.entries = dict(payload.get("entries", {}))
        return cache

    def get(self, name: str) -> Judgement | None:
        record = self.entries.get(cache_key(name, self.dictionary_version, self.prompt_version))
        if record is None:
            self.misses += 1
            return None
        self.hits += 1
        return Judgement(
            name=name,
            decision=record["decision"],
            canonical=record["canonical"],
            confidence=record["confidence"],
            reason=record["reason"],
            provider=record["provider"],
            is_mock=record["is_mock"],
        )

    def put(self, judgement: Judgement) -> None:
        key = cache_key(judgement.name, self.dictionary_version, self.prompt_version)
        self.entries[key] = judgement.as_record()

    def save(self, path: str | Path) -> None:
        file = Path(path)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps({
            "dictionary_version": self.dictionary_version,
            "prompt_version": self.prompt_version,
            "entry_count": len(self.entries),
            "entries": dict(sorted(self.entries.items())),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @property
    def statistics(self) -> dict:
        total = self.hits + self.misses
        return {
            "lookups": total,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 4) if total else 0.0,
        }


class NullCache(JudgementCache):
    """A cache that never hits, used to show the learned layer doing the work.

    With a real cache a second spelling that normalises to the same key is
    answered from the cache, so the learned memory layer never fires even
    though it is consulted. Disabling the cache makes that layer visible.
    """

    def get(self, name: str) -> Judgement | None:
        self.misses += 1
        return None

    def put(self, judgement: Judgement) -> None:
        return None

    def save(self, path: str | Path) -> None:
        return None
