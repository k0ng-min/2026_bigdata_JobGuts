"""Lossless, analysis-ready representation of a source job posting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class JobPosting:
    """A row from a source file, retaining its original payload for audit."""

    row_number: int
    source: str | None
    job_id: str | None
    raw_text: str | None
    final_techs: tuple[str, ...] | None
    hard_skills: tuple[str, ...] | None
    job_role: str | None
    experience_level: str | None
    raw: dict[str, Any]
