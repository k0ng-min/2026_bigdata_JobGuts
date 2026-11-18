"""Load JSON, JSONL, or CSV job-posting exports without modifying raw input."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from .models import JobPosting


FIELD_ALIASES = {
    "source": ("source", "platform", "origin"),
    "job_id": ("job_id", "id", "posting_id"),
    "raw_text": ("raw_text", "text", "description", "job_description"),
    "final_techs": ("final_techs",),
    "hard_skills": ("hard_skills",),
    "job_role": ("job_role", "role", "category", "job_category"),
    "experience_level": ("experience_level", "experience", "career_level"),
}


def _first_value(row: dict[str, Any], field: str) -> Any:
    for name in FIELD_ALIASES[field]:
        if name in row:
            return row[name]
    return None


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _as_tech_list(value: Any) -> tuple[str, ...] | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = [part.strip() for part in value.split(",")]
        value = parsed
    if not isinstance(value, list):
        return None
    return tuple(str(item).strip() for item in value if str(item).strip())


def _read_rows(path: Path) -> Iterable[dict[str, Any]]:
    suffix = path.suffix.lower()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        if suffix == ".json":
            document = json.load(handle)
            if isinstance(document, dict):
                for key in ("data", "rows", "items"):
                    if isinstance(document.get(key), list):
                        document = document[key]
                        break
            if not isinstance(document, list):
                raise ValueError("JSON input must be a list or contain data, rows, or items list")
            yield from document
        elif suffix in {".jsonl", ".ndjson"}:
            for line in handle:
                if line.strip():
                    yield json.loads(line)
        elif suffix == ".csv":
            yield from csv.DictReader(handle)
        else:
            raise ValueError("supported input formats are .json, .jsonl, .ndjson, and .csv")


def load_postings(path: str | Path) -> list[JobPosting]:
    """Read a supported export; no source fields are discarded from ``raw``."""
    rows: list[JobPosting] = []
    for row_number, raw in enumerate(_read_rows(Path(path)), start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"row {row_number} is not an object")
        rows.append(
            JobPosting(
                row_number=row_number,
                source=_as_text(_first_value(raw, "source")),
                job_id=_as_text(_first_value(raw, "job_id")),
                raw_text=_as_text(_first_value(raw, "raw_text")),
                final_techs=_as_tech_list(_first_value(raw, "final_techs")),
                hard_skills=_as_tech_list(_first_value(raw, "hard_skills")),
                job_role=_as_text(_first_value(raw, "job_role")),
                experience_level=_as_text(_first_value(raw, "experience_level")),
                raw=raw,
            )
        )
    return rows
