"""Regenerate the week-13 service scenario record from the stored rule artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.normalization.dictionary import TechnologyDictionary
from src.retrieval import RuleRepository

# Each scenario documents one response path the service layer must keep working.
SCENARIOS: tuple[tuple[str, dict], ...] = (
    ("normal", {"skills": ["TensorFlow"]}),
    ("no_rules", {"skills": ["NotARealSkill"]}),
    ("role_filtered", {"skills": ["TensorFlow"], "job_role": "frontend"}),
    ("entry_eligible", {"skills": ["TensorFlow"], "entry_eligible": True}),
    ("insufficient_sample", {"skills": [".NET"], "job_role": "frontend", "experience_segment": "1~3년차"}),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rules", type=Path, default=Path("artifacts/week12_all_rules.json"))
    parser.add_argument("--postings", type=Path, default=Path("data/processed/postings_normalized.jsonl"))
    parser.add_argument("--dictionary", type=Path, default=Path("configs/tech_dictionary_v2.json"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts"))
    args = parser.parse_args()
    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.artifact_dir / "week13_service_scenarios.json"
    if not args.rules.is_file() or not args.postings.is_file():
        output_path.write_text(json.dumps({
            "status": "blocked_missing_input",
            "expected_rules_path": str(args.rules),
            "expected_postings_path": str(args.postings),
            "next_action": "Run the week-11 and week-12 commands, then rerun this command.",
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote blocked-input record: {output_path}")
        return 0

    dictionary = TechnologyDictionary.from_json(args.dictionary)
    repository = RuleRepository(args.rules, args.postings)
    scenarios = {}
    for name, query in SCENARIOS:
        skills = [dictionary.canonicalize(skill) or skill for skill in query["skills"]]
        scenarios[name] = {
            "query": {**query, "normalized_skills": skills},
            "response": repository.recommend(
                skills,
                query.get("job_role"),
                query.get("experience_segment"),
                query.get("entry_eligible", False),
            ),
        }
    output_path.write_text(json.dumps({
        "status": "complete",
        "rules_artifact": args.rules.as_posix(),
        "rule_count": len(repository.rules),
        "dictionary_version": dictionary.version,
        "scenarios": scenarios,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    statuses = ", ".join(f"{name}={payload['response']['status']}" for name, payload in scenarios.items())
    print(f"Wrote {output_path} ({statuses})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
