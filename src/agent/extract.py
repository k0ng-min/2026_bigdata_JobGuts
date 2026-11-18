"""Build the uncleaned technology candidate list from raw posting text.

Candidates are deliberately not filtered against the project dictionary: this is
the "before cleanup" baseline the agent is measured against. Only mechanical
tokenizer defects are corrected, so the baseline reflects how postings are
written rather than how a regular expression happens to split them.

Three defects are corrected here:

* symbols that belong to a name are kept, so ``C++`` and ``C#`` stay distinct
  from ``C`` instead of collapsing into one item;
* a hyphenated or slashed name is not blindly split, so ``Wi-Fi`` does not
  become ``Wi`` plus ``Fi`` and ``CI/CD`` does not become ``CI`` plus ``CD``;
* a compound and its own fragments are never emitted together, because two
  strings that co-occur by construction produce association rules with
  interest near 1 that describe the tokenizer rather than the job market.

The third point is handled by one rule, applied to hyphen and slash compounds
alike and without consulting any vocabulary:

    every part is at least MINIMUM_PART_LENGTH characters  ->  emit the parts
    otherwise                                              ->  emit the compound

``HTML/CSS`` therefore yields ``HTML`` and ``CSS``, while ``Wi-Fi``, ``CI/CD``,
``TCP/IP`` and ``Objective-C`` stay whole. Keeping ``Objective-C`` whole also
stops it from inflating the count of ``C``.

Space-separated names such as ``Spring Boot`` are *not* assembled. Their
boundaries cannot be found without a vocabulary, and guessing them produced
three times as many tokenizer-artifact rules for two points of recall. Joining
them is left to the agent, which has the surrounding context and a dictionary.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

# A technology token: optional leading dot (.NET), then letters, digits and the
# symbols that belong to names. Internal dots and hyphens join the token instead
# of ending it; a trailing dot or hyphen is left out of the match.
_CORE = r"\.?[A-Za-z][A-Za-z0-9#+]*(?:[.\-][A-Za-z0-9#+]+)*"
_TOKEN_RE = re.compile(_CORE)
_SLASH_RE = re.compile(rf"{_CORE}(?:/{_CORE})+")

#: Shortest fragment that counts as a name on its own.
MINIMUM_PART_LENGTH = 3
#: Longest candidate kept; longer matches are prose, not names.
MAXIMUM_CANDIDATE_LENGTH = 30

SECTION_MARKERS = (
    "사용 기술", "사용기술", "기술 스택", "기술스택", "Tech Stack", "기술 환경",
    "개발 환경", "개발환경", "사용하는 기술", "활용 기술", "주요 기술", "스킬", "Skills",
)
#: How far past a section marker still counts as part of the technology list.
SECTION_WINDOW = 400

DEFAULT_STOPWORDS_PATH = Path("configs/extract_stopwords.json")


@dataclass(frozen=True)
class Candidate:
    """One extracted string plus where in the posting it came from."""

    name: str
    source: str  # "section" when inside a technology list, otherwise "body"


def load_stopwords(path: str | Path = DEFAULT_STOPWORDS_PATH) -> frozenset[str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return frozenset(word.casefold() for word in payload["stopwords"])


def section_spans(text: str) -> tuple[tuple[int, int], ...]:
    """Character ranges that follow a technology-list marker."""
    spans = []
    for marker in SECTION_MARKERS:
        start = text.find(marker)
        if start >= 0:
            spans.append((start + len(marker), start + len(marker) + SECTION_WINDOW))
    return tuple(sorted(spans))


def _in_section(position: int, spans: tuple[tuple[int, int], ...]) -> bool:
    return any(start <= position < end for start, end in spans)


def _acceptable(name: str, stopwords: frozenset[str]) -> bool:
    if not name or len(name) > MAXIMUM_CANDIDATE_LENGTH:
        return False
    if name.casefold() in stopwords:
        return False
    if not re.search(r"[A-Za-z]", name):
        return False
    # A single character is only a name when it is written as one (C, R, Q).
    if len(name) == 1:
        return name.isupper()
    return True


def split_compound(token: str) -> tuple[str, ...]:
    """Return either the parts of a compound or the compound itself, never both.

    Slashes are resolved before hyphens, and the rule is applied again to each
    slash part so that ``Java/Objective-C`` keeps ``Objective-C`` intact.
    """
    for separator in ("/", "-"):
        if separator not in token:
            continue
        parts = [part for part in token.split(separator) if part]
        if len(parts) < 2:
            continue
        if all(len(part) >= MINIMUM_PART_LENGTH for part in parts):
            resolved: list[str] = []
            for part in parts:
                resolved.extend(split_compound(part) if part != token else [part])
            return tuple(dict.fromkeys(resolved))
        return (token,)
    return (token,)


def extract_candidates(text: str, stopwords: frozenset[str]) -> tuple[Candidate, ...]:
    """Return the ordered, de-duplicated candidate strings found in one posting."""
    if not text:
        return ()
    spans = section_spans(text)
    found: dict[str, str] = {}

    def remember(name: str, position: int) -> None:
        name = name.strip()
        if not _acceptable(name, stopwords):
            return
        source = "section" if _in_section(position, spans) else "body"
        if name not in found or (source == "section" and found[name] == "body"):
            found[name] = source

    # Slash compounds first, then blank them out so the token pass does not also
    # emit their fragments and recreate the compound-plus-part pairing.
    masked = list(text)
    for match in _SLASH_RE.finditer(text):
        for name in split_compound(match.group(0)):
            remember(name, match.start())
        for index in range(match.start(), match.end()):
            masked[index] = " "

    for match in _TOKEN_RE.finditer("".join(masked)):
        for name in split_compound(match.group(0)):
            remember(name, match.start())

    return tuple(Candidate(name, source) for name, source in found.items())


def candidate_names(text: str, stopwords: frozenset[str]) -> tuple[str, ...]:
    """Candidate strings only, for callers that do not need the source label."""
    return tuple(candidate.name for candidate in extract_candidates(text, stopwords))
