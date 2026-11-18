"""Read stored analysis results; do not recalculate rules in the service layer."""
from __future__ import annotations
import json
from pathlib import Path

class RuleRepository:
    def __init__(self, rules_path: str | Path, postings_path: str | Path):
        self.rules = json.loads(Path(rules_path).read_text(encoding="utf-8"))["normalized"]
        with Path(postings_path).open(encoding="utf-8") as handle:
            self.postings = [json.loads(line) for line in handle if line.strip()]
    def recommend(self, skills: list[str], job_role: str | None = None, experience_segment: str | None = None) -> dict:
        owned = set(skills)
        candidates = [r for r in self.rules if set(r["antecedent"]).issubset(owned) and r["consequent"][0] not in owned]
        candidates.sort(key=lambda r: (-r["interest"], -r["confidence"]))
        if not candidates:
            return {"status": "no_rules", "recommendations": [], "next_action": "Add a known skill or broaden filters."}
        evidence = []
        for row in self.postings:
            if job_role and row.get("job_role") != job_role: continue
            if experience_segment and row.get("experience_segment") != experience_segment: continue
            if set(candidates[0]["antecedent"] + candidates[0]["consequent"]).issubset(set(row.get("normalized_techs", []))):
                evidence.append({"source": row.get("source"), "job_id": row.get("job_id"), "title": row.get("title")})
            if len(evidence) == 3: break
        return {"status": "ok" if evidence else "insufficient_sample", "recommendations": candidates[:10], "evidence_postings": evidence, "applied_filters": {"job_role": job_role or "all", "experience_segment": experience_segment or "all"}}
