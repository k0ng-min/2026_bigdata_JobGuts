"""Conservative metadata derived from titles; ambiguous records remain reviewable."""
from __future__ import annotations

ROLE_TERMS = {
    "backend": ("backend", "back-end", "백엔드", "서버"),
    "frontend": ("frontend", "front-end", "프론트엔드", "퍼블리셔"),
    "fullstack": ("fullstack", "full-stack", "풀스택"),
}

def classify_role(title: str | None) -> tuple[str, str]:
    text = (title or "").casefold()
    matched = [role for role, terms in ROLE_TERMS.items() if any(term in text for term in terms)]
    if len(matched) == 1:
        return matched[0], "title_rule"
    return "other_tech", "fallback_title"

# "경력무관" means the posting does not require experience, which is not the same
# claim as "신입". Both are kept as their own segment and the overlap that matters
# for entry-level recommendation is exposed as a separate eligibility flag.
KNOWN_EXPERIENCE_LABELS = ("신입", "경력무관", "1~3년차", "3~5년차", "5년이상")
ENTRY_ELIGIBLE_LABELS = ("신입", "경력무관")

def classify_experience(label: str | None) -> tuple[str, str]:
    """Return the source label unchanged; never collapse distinct labels together."""
    value = (label or "").strip()
    if value in KNOWN_EXPERIENCE_LABELS: return value, "source_label"
    return "unknown", "missing_or_unrecognized_label"

def is_entry_eligible(label: str | None) -> bool:
    """True when the source label states that an entry-level applicant may apply."""
    return (label or "").strip() in ENTRY_ELIGIBLE_LABELS
