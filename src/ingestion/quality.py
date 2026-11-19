"""Week-10 quality metrics. These metrics intentionally do not normalize skills."""

from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Any

from .models import JobPosting


def _missing(value: object) -> bool:
    return value is None or value == ()


def _body_fingerprint(text: str | None) -> str | None:
    if not text:
        return None
    compact = " ".join(text.casefold().split())
    return sha256(compact.encode("utf-8")).hexdigest()


def _primary_key(posting: JobPosting) -> tuple[str, str] | None:
    if posting.source and posting.job_id:
        return (posting.source, posting.job_id)
    return None


def _duplicate_summary(postings: list[JobPosting]) -> dict[str, Any]:
    keyed: dict[tuple[str, str], list[int]] = defaultdict(list)
    bodies: dict[str, list[JobPosting]] = defaultdict(list)
    for posting in postings:
        key = _primary_key(posting)
        if key:
            keyed[key].append(posting.row_number)
        fingerprint = _body_fingerprint(posting.raw_text)
        if fingerprint:
            bodies[fingerprint].append(posting)

    primary_groups = [rows for rows in keyed.values() if len(rows) > 1]
    suspected_body_groups = []
    for fingerprint, group in bodies.items():
        keys = {_primary_key(item) for item in group}
        if len(group) > 1 and len(keys) > 1:
            suspected_body_groups.append(
                {"body_sha256": fingerprint, "row_numbers": [item.row_number for item in group]}
            )
    return {
        "missing_source_or_job_id_rows": sum(_primary_key(item) is None for item in postings),
        "source_job_id_duplicate_groups": len(primary_groups),
        "source_job_id_duplicate_rows_after_first": sum(len(group) - 1 for group in primary_groups),
        "suspected_same_body_distinct_id_groups": len(suspected_body_groups),
        "suspected_same_body_distinct_id_rows": sum(
            len(group["row_numbers"]) for group in suspected_body_groups
        ),
        "suspected_same_body_examples": suspected_body_groups[:10],
    }


def build_week10_report(postings: list[JobPosting], provenance: dict[str, Any]) -> dict[str, Any]:
    """Return a JSON-serializable report for one fixed input file."""
    final_missing = sum(_missing(item.final_techs) for item in postings)
    hard_missing = sum(_missing(item.hard_skills) for item in postings)
    both_present = [item for item in postings if item.final_techs is not None and item.hard_skills is not None]
    comparisons = [
        (set(item.final_techs or ()), set(item.hard_skills or ())) for item in both_present
    ]
    roles = Counter(item.job_role or "unknown" for item in postings)
    experiences = Counter(item.experience_level or "unknown" for item in postings)
    return {
        "report_schema_version": "week10.v1",
        "input": provenance,
        "row_count": len(postings),
        "required_field_missing_rows": {
            "raw_text": sum(_missing(item.raw_text) for item in postings),
            "final_techs": final_missing,
            "hard_skills": hard_missing,
            "job_role": sum(_missing(item.job_role) for item in postings),
            "experience_level": sum(_missing(item.experience_level) for item in postings),
        },
        "duplicate_check": _duplicate_summary(postings),
        "technology_field_comparison": {
            "both_fields_present_rows": len(both_present),
            "exact_same_set_rows": sum(final == hard for final, hard in comparisons),
            "different_set_rows": sum(final != hard for final, hard in comparisons),
            "final_techs_only_rows": sum(
                item.final_techs is not None and item.hard_skills is None for item in postings
            ),
            "hard_skills_only_rows": sum(
                item.final_techs is None and item.hard_skills is not None for item in postings
            ),
            "empty_both_rows": sum(
                item.final_techs in (None, ()) and item.hard_skills in (None, ()) for item in postings
            ),
        },
        "job_role_counts": dict(sorted(roles.items())),
        "experience_level_counts": dict(sorted(experiences.items())),
        "analysis_contract": {
            "transaction_unit": "one source posting after source + job_id duplicate review",
            "transaction_items": "selected raw technology field only; job role and experience are metadata filters",
            "selected_starting_technology_field": "final_techs",
            "empty_technology_policy": "exclude from Apriori transactions; retain in quality report",
            "ambiguous_experience_policy": "preserve unknown or needs_review; never infer entry-level",
        },
    }


def file_provenance(path: str | Path, config_version: str) -> dict[str, Any]:
    input_path = Path(path)
    content = input_path.read_bytes()
    return {
        "file_name": input_path.name,
        # as_posix keeps the recorded path identical on Windows and WSL. With
        # str() the same run produced data\\raw\\... on one and data/raw/... on
        # the other, so every teammate saw a spurious diff on this artifact.
        "path": input_path.as_posix(),
        "sha256": sha256(content).hexdigest(),
        "bytes": len(content),
        "data_scope_config_version": config_version,
    }
