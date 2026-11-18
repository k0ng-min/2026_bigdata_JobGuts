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
    return "unknown", "needs_review" if matched else "unclassified"

def classify_experience(label: str | None) -> tuple[str, str]:
    value = (label or "").strip()
    if value in {"신입", "경력무관"}: return "entry", "source_label"
    if value in {"1~3년차", "3~5년차", "5년이상"}: return value, "source_label"
    return "unknown", "needs_review"
