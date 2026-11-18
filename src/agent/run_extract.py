"""Write the uncleaned candidate inventory for the week-12 eligible posting set.

The inventory is the input to dictionary building and to the before/after rule
comparison, so it is restricted to exactly the postings week 12 mines rules
from. The run aborts when that count drifts, for the same reason
src/analysis/run_week14.py does: two artifacts that describe different
populations cannot be compared.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

# Reused so the eligible posting set has one definition in the repository.
from src.analysis.run_week14 import _eligible_rows

from .extract import extract_candidates, load_stopwords


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/postings_normalized.jsonl"))
    parser.add_argument("--stopwords", type=Path, default=Path("configs/extract_stopwords.json"))
    parser.add_argument("--comparison", type=Path, default=Path("artifacts/week12_rule_comparison.json"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--field", default="normalized_techs")
    parser.add_argument("--limit", type=int, default=0, help="Stop after this many eligible postings (0 = all).")
    args = parser.parse_args()
    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.artifact_dir / "agent_candidates.json"
    if not args.input.is_file():
        output_path.write_text(json.dumps({
            "status": "blocked_missing_input",
            "expected_input_path": str(args.input),
            "next_action": "Run the week-11 command, then rerun this command.",
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote blocked-input record: {output_path}")
        return 0

    stopwords = load_stopwords(args.stopwords)
    with args.input.open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line.strip()]
    rows = _eligible_rows(records, args.field)
    if not args.limit:
        expected = json.loads(args.comparison.read_text(encoding="utf-8"))["normalized"]["transaction_count"]
        if len(rows) != expected:
            raise ValueError(
                f"eligible posting set ({len(rows)}) does not match the week-12 transaction count ({expected}); "
                "regenerate week 12 first so both artifacts describe the same population"
            )
    else:
        rows = rows[: args.limit]

    occurrences: Counter[str] = Counter()
    section_hits: Counter[str] = Counter()
    per_posting: list[int] = []
    for row in rows:
        candidates = extract_candidates(row.get("raw_text") or "", stopwords)
        per_posting.append(len(candidates))
        for candidate in candidates:
            occurrences[candidate.name] += 1
            if candidate.source == "section":
                section_hits[candidate.name] += 1

    total = sum(occurrences.values())
    output_path.write_text(json.dumps({
        "status": "complete",
        "basis": {
            "posting_set": "week-12 eligible transactions" if not args.limit else f"first {len(rows)} eligible transactions",
            "posting_count": len(rows),
            "source_field_for_eligibility": args.field,
            "stopwords_version": json.loads(args.stopwords.read_text(encoding="utf-8"))["version"],
            "minimum_subpart_length": 3,
        },
        "totals": {
            "candidate_occurrences": total,
            "distinct_candidates": len(occurrences),
            "candidates_per_posting": round(total / len(rows), 2) if rows else 0.0,
            "single_occurrence_candidates": sum(1 for count in occurrences.values() if count == 1),
        },
        "candidates": [
            {"name": name, "count": count, "section_count": section_hits.get(name, 0)}
            for name, count in occurrences.most_common()
        ],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output_path} ({len(rows)} postings, {total} occurrences, {len(occurrences)} distinct candidates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
