"""Build dictionary v2 from the data's own vocabulary, plus the agent review list.

Every standard name comes from the ``final_techs`` vocabulary; no standard name
is invented here. A candidate spelling joins the dictionary only through one of
four auditable rules, and each entry records which rule admitted it and how
often the spelling occurs, so any entry can be traced back to the data.

    exact        the spelling is already a standard name
    case         it differs from a standard name only in letter case
    punctuation  it differs only in dots, spaces or hyphens
    curated      a hand-checked entry in configs/tech_dictionary_curated.json

Anything else is left out and written to the review list, including spellings
that are plainly technologies but absent from the vocabulary: adding them would
mean inventing a standard name.

Comparison keys keep ``+`` and ``#`` so that C, C++ and C# stay three names.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

#: Occurrence count below which a candidate cannot reach the Apriori support
#: floor, so it is not worth a dictionary entry or an LLM call.
DEFAULT_MINIMUM_OCCURRENCES = 89


def canonical_key(value: str) -> str:
    """Case-insensitive key that still tells C, C++ and C# apart."""
    return re.sub(r"\s+", " ", value.casefold()).strip()


def punctuation_key(value: str) -> str:
    """Key that also ignores dots, spaces and hyphens, but never + or #."""
    return re.sub(r"[^a-z0-9+#]", "", value.casefold())


def vocabulary(records: list[dict]) -> Counter[str]:
    """Standard names and their posting counts, taken from final_techs."""
    counts: Counter[str] = Counter()
    for row in records:
        for item in row.get("final_techs") or []:
            name = str(item).strip()
            if name:
                counts[name] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/postings_normalized.jsonl"))
    parser.add_argument("--candidates", type=Path, default=Path("artifacts/agent_candidates.json"))
    parser.add_argument("--categories", type=Path, default=Path("configs/tech_categories.json"))
    parser.add_argument("--curated", type=Path, default=Path("configs/tech_dictionary_curated.json"))
    parser.add_argument("--output", type=Path, default=Path("configs/tech_dictionary_v2.json"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--minimum-occurrences", type=int, default=DEFAULT_MINIMUM_OCCURRENCES)
    args = parser.parse_args()
    args.artifact_dir.mkdir(parents=True, exist_ok=True)

    with args.input.open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line.strip()]
    standard = vocabulary(records)
    categories = json.loads(args.categories.read_text(encoding="utf-8"))
    curated = json.loads(args.curated.read_text(encoding="utf-8"))
    candidate_payload = json.loads(args.candidates.read_text(encoding="utf-8"))
    candidates = {entry["name"]: entry for entry in candidate_payload["candidates"]}

    missing_category = sorted(set(standard) - set(categories["categories"]))
    if missing_category:
        raise ValueError(f"configs/tech_categories.json is missing {len(missing_category)} name(s): {missing_category}")
    unknown_category = sorted(set(categories["categories"]) - set(standard))
    if unknown_category:
        raise ValueError(f"configs/tech_categories.json names {len(unknown_category)} value(s) absent from final_techs: {unknown_category}")

    by_case = {canonical_key(name): name for name in standard}
    by_punctuation: dict[str, str] = {}
    for name in sorted(standard):
        by_punctuation.setdefault(punctuation_key(name), name)

    curated_target: dict[str, str] = {}
    for target, spellings in curated["aliases"].items():
        if target not in standard:
            raise ValueError(f"curated alias target {target!r} is not a final_techs standard name")
        for spelling in spellings:
            key = canonical_key(spelling)
            previous = curated_target.get(key)
            if previous and previous != target:
                raise ValueError(f"curated spelling {spelling!r} points at both {previous!r} and {target!r}")
            curated_target[key] = target

    def classify(name: str) -> tuple[str, str] | None:
        """Return (standard name, rule) or None when the spelling is undecided."""
        if name in standard:
            return name, "exact"
        key = canonical_key(name)
        if key in by_case:
            return by_case[key], "case"
        # Mechanical rules are preferred over hand-checked ones so that as few
        # entries as possible rest on judgement.
        punctuation = punctuation_key(name)
        if punctuation in by_punctuation:
            return by_punctuation[punctuation], "punctuation"
        if key in curated_target:
            return curated_target[key], "curated"
        return None

    considered = {name: entry for name, entry in candidates.items() if entry["count"] >= args.minimum_occurrences}
    entries: dict[str, dict] = {}
    review: list[dict] = []
    resolved_occurrences = 0
    rule_counts: Counter[str] = Counter()
    for name, entry in sorted(considered.items(), key=lambda item: -item[1]["count"]):
        decision = classify(name)
        if decision is None:
            review.append({
                "name": name,
                "count": entry["count"],
                "section_count": entry["section_count"],
                "reason": "no standard name in the final_techs vocabulary matches this spelling",
            })
            continue
        target, rule = decision
        resolved_occurrences += entry["count"]
        rule_counts[rule] += 1
        record = entries.setdefault(target, {
            "canonical": target,
            "category": categories["categories"][target],
            "standard_name_posting_count": standard[target],
            "spellings": [],
        })
        record["spellings"].append({
            "spelling": name,
            "rule": rule,
            "occurrences": entry["count"],
            "section_occurrences": entry["section_count"],
        })

    # Curated spellings that the data has not shown yet are still worth keeping,
    # but they are marked so the evidence columns are not mistaken for data.
    for key, target in sorted(curated_target.items()):
        record = entries.setdefault(target, {
            "canonical": target,
            "category": categories["categories"][target],
            "standard_name_posting_count": standard[target],
            "spellings": [],
        })
        if any(canonical_key(item["spelling"]) == key for item in record["spellings"]):
            continue
        record["spellings"].append({
            "spelling": key,
            "rule": "curated",
            "occurrences": candidates.get(key, {}).get("count", 0),
            "section_occurrences": candidates.get(key, {}).get("section_count", 0),
        })

    for record in entries.values():
        record["spellings"].sort(key=lambda item: (-item["occurrences"], item["spelling"]))

    total_occurrences = sum(entry["count"] for entry in considered.values())
    review.sort(key=lambda item: -item["count"])
    args.output.write_text(json.dumps({
        "version": "tech-dictionary.v2",
        "matching": "case-insensitive exact spellings; comparison keys preserve + and #",
        "standard_name_source": "final_techs vocabulary of the input export; no standard name is invented",
        "standard_name_count": len(standard),
        "minimum_occurrences_considered": args.minimum_occurrences,
        "category_labels": categories["labels"],
        "rule_counts": dict(rule_counts),
        "technologies": [entries[name] for name in sorted(entries)],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    review_path = args.artifact_dir / "agent_review_candidates.json"
    review_path.write_text(json.dumps({
        "status": "complete",
        "basis": {
            "posting_count": candidate_payload["basis"]["posting_count"],
            "minimum_occurrences": args.minimum_occurrences,
            "candidates_considered": len(considered),
        },
        "totals": {
            "resolved_by_dictionary": len(considered) - len(review),
            "needs_agent_judgement": len(review),
            "resolved_occurrence_share": round(resolved_occurrences / total_occurrences, 4) if total_occurrences else 0.0,
            "review_occurrence_share": round(1 - resolved_occurrences / total_occurrences, 4) if total_occurrences else 0.0,
        },
        "candidates": review,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"Wrote {args.output} ({len(entries)} standard names, "
        f"{sum(len(record['spellings']) for record in entries.values())} spellings) "
        f"and {review_path} ({len(review)} candidates needing judgement)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
