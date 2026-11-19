"""Regenerate the week-14 segment summary and skill graph from the week-12 rule set.

The segment summary and the triple frequencies are computed on exactly the same
eligible posting set that week 12 mines rules from, so every number in the weekly
reports refers to one population. The run fails loudly if that set drifts away
from the count recorded in week12_rule_comparison.json.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from hashlib import sha256
from itertools import combinations
from pathlib import Path

from .graph import graph_from_rules


def _eligible_rows(records: list[dict], field: str, excluded_technologies: set[str] | None = None) -> list[dict]:
    """Apply the week-12 duplicate and empty-transaction policy, keeping whole rows."""
    seen_ids: set[tuple[str, str]] = set()
    seen_bodies: set[str] = set()
    rows: list[dict] = []
    excluded_technologies = excluded_technologies or set()
    for row in records:
        key = (str(row.get("source", "")), str(row.get("job_id", "")))
        if key in seen_ids:
            continue
        seen_ids.add(key)
        body = " ".join(str(row.get("raw_text", "")).casefold().split())
        body_hash = sha256(body.encode("utf-8")).hexdigest() if body else ""
        if body_hash and body_hash in seen_bodies:
            continue
        if body_hash:
            seen_bodies.add(body_hash)
        items = {str(item).strip() for item in row.get(field, []) if str(item).strip()} - excluded_technologies
        if items:
            filtered = dict(row)
            filtered[field] = sorted(items)
            rows.append(filtered)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/postings_normalized.jsonl"))
    parser.add_argument("--rules", type=Path, default=Path("artifacts/week12_all_rules.json"))
    parser.add_argument("--comparison", type=Path, default=Path("artifacts/week12_rule_comparison.json"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--field", default="normalized_techs")
    parser.add_argument("--top-triples", type=int, default=50)
    parser.add_argument("--categories", type=Path, default=Path("configs/tech_categories.json"))
    parser.add_argument("--exclude-category", action="append", default=["concept"])
    args = parser.parse_args()
    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    segment_path = args.artifact_dir / "week14_segment_comparison.json"
    graph_path = args.artifact_dir / "week14_skill_graph.json"
    if not args.input.is_file() or not args.rules.is_file():
        blocked = {"status": "blocked_missing_input", "expected_input_path": str(args.input), "expected_rules_path": str(args.rules)}
        segment_path.write_text(json.dumps(blocked, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        graph_path.write_text(json.dumps(blocked, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote blocked-input records: {segment_path} and {graph_path}")
        return 0

    with args.input.open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line.strip()]
    category_payload = json.loads(args.categories.read_text(encoding="utf-8"))
    excluded_technologies = {
        name for name, category in category_payload.get("categories", {}).items()
        if category in set(args.exclude_category)
    }
    rows = _eligible_rows(records, args.field, excluded_technologies)

    expected = json.loads(args.comparison.read_text(encoding="utf-8"))["normalized"]["transaction_count"]
    if len(rows) != expected:
        raise ValueError(
            f"eligible posting set ({len(rows)}) does not match the week-12 transaction count ({expected}); "
            "regenerate week 12 first so both artifacts describe the same population"
        )

    triples: Counter[tuple[str, ...]] = Counter()
    for row in rows:
        items = sorted({str(item).strip() for item in row.get(args.field, []) if str(item).strip()})
        for triple in combinations(items, 3):
            triples[triple] += 1

    segments = Counter(f"{row.get('job_role')}|{row.get('experience_segment')}" for row in rows)
    entry_eligible = sum(1 for row in rows if row.get("entry_eligible"))
    segment_path.write_text(json.dumps({
        "status": "complete",
        "basis": {
            "source_field": args.field,
            "excluded_categories": args.exclude_category,
            "excluded_technologies": sorted(excluded_technologies),
            "posting_set": "week-12 eligible transactions (first source + job_id occurrence, distinct raw_text body, non-empty technology list)",
            "posting_count": len(rows),
            "matches_week12_transaction_count": True,
        },
        "segments": dict(segments.most_common()),
        "entry_eligible_posting_count": entry_eligible,
        "top_triples": [{"items": list(items), "count": count} for items, count in triples.most_common(args.top_triples)],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rules = json.loads(args.rules.read_text(encoding="utf-8"))["normalized"]
    graph = graph_from_rules(rules)
    graph_path.write_text(json.dumps({
        "status": "complete",
        "basis": {"rules_artifact": args.rules.as_posix(), "rule_count": len(rules), "transaction_count": len(rows)},
        **graph,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {segment_path} ({len(rows)} postings, {len(segments)} segments) and {graph_path} ({len(graph['nodes'])} nodes, {len(graph['edges'])} edges)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
