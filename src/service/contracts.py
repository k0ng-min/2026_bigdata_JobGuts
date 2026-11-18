"""Week-10 query/response contract, including explicit empty-result behavior."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class RecommendationQuery:
    skills: tuple[str, ...]
    job_role: str | None = None
    experience_level: str | None = None


@dataclass(frozen=True)
class EvidencePosting:
    source: str
    job_id: str
    excerpt: str


@dataclass(frozen=True)
class RecommendationResponse:
    status: Literal["ok", "no_rules", "insufficient_sample", "unknown_skill"]
    recommendations: tuple[dict, ...] = ()
    evidence_postings: tuple[EvidencePosting, ...] = ()
    applied_filters: dict[str, str] = field(default_factory=dict)
    next_action: str | None = None
