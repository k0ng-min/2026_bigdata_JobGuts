"""Versioned technology dictionary used by the normalization pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


def _key(value: str) -> str:
    return " ".join(value.casefold().split())


@dataclass(frozen=True)
class TechnologyDictionary:
    version: str
    aliases: dict[str, str]

    @classmethod
    def from_json(cls, path: str | Path) -> "TechnologyDictionary":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        aliases: dict[str, str] = {}
        for canonical, variants in payload["canonical_technologies"].items():
            for variant in [canonical, *variants]:
                normalized_variant = _key(variant)
                previous = aliases.get(normalized_variant)
                if previous and previous != canonical:
                    raise ValueError(f"alias {variant!r} maps to both {previous!r} and {canonical!r}")
                aliases[normalized_variant] = canonical
        return cls(version=payload["version"], aliases=aliases)

    def canonicalize(self, value: str) -> str | None:
        return self.aliases.get(_key(value))
