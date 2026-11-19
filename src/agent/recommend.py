"""Retry a recommendation by widening the filters, and say that it widened.

``no_rules`` and ``insufficient_sample`` are the observations the agent acts
on. The relaxation order releases the narrowest condition first: experience is
unknown for 64.3% of postings and 94.1% of job roles fall back to other_tech,
so those two filters starve a query long before the technology does.

Two things are never done silently. The technology the user asked about is
never swapped for another, and a response that came from a widened search
always carries the original request, the filters actually used, and the steps
taken. Metrics are global by construction — the rule table is mined over all
postings and filters only choose evidence — so every response says so.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Filters are released in this order, narrowest first.
RELAXATION_ORDER = ("experience_segment", "job_role")

METRICS_SCOPE_NOTE = (
    "support, confidence and interest are computed over the whole transaction set. "
    "Filters select evidence postings only and do not re-compute the metrics."
)


@dataclass(frozen=True)
class RelaxationStep:
    step: int
    released: str
    reason: str
    status_before: str

    def as_record(self) -> dict:
        return {
            "step": self.step,
            "released": self.released,
            "reason": self.reason,
            "status_before": self.status_before,
        }


def recommend_with_relaxation(
    repository,
    skills: list[str],
    job_role: str | None = None,
    experience_segment: str | None = None,
    entry_eligible: bool = False,
    dictionary=None,
    max_steps: int = 3,
) -> dict:
    """Search, widen on an empty result, and report what was widened."""
    requested = {
        "skills": list(skills),
        "job_role": job_role,
        "experience_segment": experience_segment,
        "entry_eligible": entry_eligible,
    }
    filters = {"job_role": job_role, "experience_segment": experience_segment, "entry_eligible": entry_eligible}
    steps: list[RelaxationStep] = []

    response = repository.recommend(skills, filters["job_role"], filters["experience_segment"], filters["entry_eligible"])

    if response["status"] == "no_rules":
        # Widening cannot help: no rule starts from these skills under any
        # filter. Try the spelling once, then stop rather than loop.
        normalized = [dictionary.canonicalize(skill) or skill for skill in skills] if dictionary else list(skills)
        if normalized != list(skills):
            retried = repository.recommend(normalized, filters["job_role"], filters["experience_segment"], filters["entry_eligible"])
            if retried["status"] != "no_rules":
                return _finish(retried, requested, filters, steps, normalized_skills=normalized)
        return _finish(
            {
                **response,
                "next_action": "No rule starts from these skills. Check the spelling or try a related skill.",
            },
            requested,
            filters,
            steps,
            normalized_skills=normalized,
        )

    for index, field in enumerate(RELAXATION_ORDER, start=1):
        if response["status"] != "insufficient_sample" or index > max_steps:
            break
        if not filters.get(field):
            continue
        steps.append(RelaxationStep(index, field, "insufficient_sample", response["status"]))
        filters[field] = None
        response = repository.recommend(skills, filters["job_role"], filters["experience_segment"], filters["entry_eligible"])

    if response["status"] == "insufficient_sample" and filters["entry_eligible"] and len(steps) < max_steps:
        steps.append(RelaxationStep(len(steps) + 1, "entry_eligible", "insufficient_sample", response["status"]))
        filters["entry_eligible"] = False
        response = repository.recommend(skills, filters["job_role"], filters["experience_segment"], False)

    return _finish(response, requested, filters, steps)


def _finish(response: dict, requested: dict, filters: dict, steps, normalized_skills=None) -> dict:
    widened = bool(steps)
    result = {
        **response,
        "requested_filters": requested,
        "applied_filters": {
            "job_role": filters["job_role"] or "all",
            "experience_segment": filters["experience_segment"] or "all",
            "entry_eligible_only": bool(filters["entry_eligible"]),
        },
        "relaxation_steps": [step.as_record() for step in steps],
        "search_was_widened": widened,
        "metrics_scope": "all_postings",
        "metrics_note": METRICS_SCOPE_NOTE,
    }
    if normalized_skills is not None:
        result["normalized_skills"] = normalized_skills
    if widened:
        released = ", ".join(step.released for step in steps)
        result["disclosure"] = (
            f"요청하신 조건에서는 근거 공고를 찾지 못해 {released} 조건을 풀고 검색한 결과입니다."
        )
    return result
