"""Pure normalization functions; unknown values are preserved, never fabricated."""

from __future__ import annotations

from dataclasses import dataclass

from .dictionary import TechnologyDictionary


@dataclass(frozen=True)
class NormalizationResult:
    normalized_techs: tuple[str, ...]
    transformed_count: int
    unknown_techs: tuple[str, ...]
    duplicate_count: int


def normalize_technologies(values: tuple[str, ...] | list[str] | None, dictionary: TechnologyDictionary) -> NormalizationResult:
    """Canonicalize known aliases and remove per-posting duplicates in source order."""
    result: list[str] = []
    unknown: list[str] = []
    transformed_count = 0
    duplicate_count = 0
    seen: set[str] = set()
    for raw_value in values or ():
        cleaned = str(raw_value).strip()
        if not cleaned:
            continue
        canonical = dictionary.canonicalize(cleaned)
        output = canonical or cleaned
        if canonical is None:
            unknown.append(cleaned)
        elif output != cleaned:
            transformed_count += 1
        comparison_key = output.casefold()
        if comparison_key in seen:
            duplicate_count += 1
            continue
        seen.add(comparison_key)
        result.append(output)
    return NormalizationResult(tuple(result), transformed_count, tuple(unknown), duplicate_count)
