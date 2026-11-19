"""Run comparable raw and normalized association-rule experiments."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

from .apriori import mine_pair_rules


def _records(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _deduplicated_transactions(
    records: list[dict], field: str, excluded_technologies: set[str] | None = None
) -> tuple[list[set[str]], dict]:
    seen_ids: set[tuple[str, str]] = set()
    seen_bodies: set[str] = set()
    transactions: list[set[str]] = []
    excluded_empty = excluded_duplicate = excluded_same_body = excluded_category_items = 0
    excluded_technologies = excluded_technologies or set()
    for row in records:
        key = (str(row.get("source", "")), str(row.get("job_id", "")))
        if key in seen_ids:
            excluded_duplicate += 1
            continue
        seen_ids.add(key)
        body = " ".join(str(row.get("raw_text", "")).casefold().split())
        body_hash = sha256(body.encode("utf-8")).hexdigest() if body else ""
        if body_hash and body_hash in seen_bodies:
            excluded_same_body += 1
            continue
        if body_hash:
            seen_bodies.add(body_hash)
        original = {str(item).strip() for item in row.get(field, []) if str(item).strip()}
        transaction = original - excluded_technologies
        excluded_category_items += len(original - transaction)
        if not transaction:
            excluded_empty += 1
            continue
        transactions.append(transaction)
    return transactions, {
        "excluded_source_job_id_duplicates": excluded_duplicate,
        "excluded_same_body_duplicates": excluded_same_body,
        "excluded_empty_transactions": excluded_empty,
        "excluded_category_item_count": excluded_category_items,
    }


def _excluded_technologies(path: Path, excluded_categories: list[str]) -> set[str]:
    if not excluded_categories:
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    categories = payload.get("categories", {})
    return {name for name, category in categories.items() if category in set(excluded_categories)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/postings_normalized.jsonl"))
    parser.add_argument("--config", type=Path, default=Path("configs/experiments.json"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--top-n", type=int, default=50, help="How many rules to keep in the display-only top-N artifact.")
    parser.add_argument("--categories", type=Path, default=Path("configs/tech_categories.json"))
    parser.add_argument("--exclude-category", action="append", default=["concept"], help="Category label to omit from Apriori itemsets; repeat to omit more categories.")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    comparison_path = args.artifact_dir / "week12_rule_comparison.json"
    all_rules_path = args.artifact_dir / "week12_all_rules.json"
    top_rules_path = args.artifact_dir / "week12_top_rules.json"
    if not args.input.is_file():
        comparison_path.write_text(json.dumps({"status": "blocked_missing_input", "expected_path": str(args.input)}, indent=2) + "\n", encoding="utf-8")
        blocked = {"status": "blocked_missing_input", "raw": [], "normalized": []}
        all_rules_path.write_text(json.dumps(blocked, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        top_rules_path.write_text(json.dumps(blocked, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0
    records = _records(args.input)
    parameters = config["week12_parameters"]
    excluded_technologies = _excluded_technologies(args.categories, args.exclude_category)
    raw_transactions, raw_exclusions = _deduplicated_transactions(records, "final_techs", excluded_technologies)
    normalized_transactions, normalized_exclusions = _deduplicated_transactions(records, "normalized_techs", excluded_technologies)
    if len(raw_transactions) != len(normalized_transactions):
        raise ValueError("raw and normalized experiments must use the same eligible posting set")
    raw_rules = mine_pair_rules(raw_transactions, parameters["minimum_support"], parameters["minimum_confidence"])
    normalized_rules = mine_pair_rules(normalized_transactions, parameters["minimum_support"], parameters["minimum_confidence"])
    common = {(tuple(rule["antecedent"]), tuple(rule["consequent"])) for rule in raw_rules} & {(tuple(rule["antecedent"]), tuple(rule["consequent"])) for rule in normalized_rules}
    comparison = {
        "status": "complete",
        "input_row_count": len(records),
        "segment": {"job_role": "all", "experience_level": "all"},
        "parameters": parameters,
        "excluded_categories": args.exclude_category,
        "excluded_technologies": sorted(excluded_technologies),
        "raw": {"transaction_count": len(raw_transactions), "rule_count": len(raw_rules), **raw_exclusions},
        "normalized": {"transaction_count": len(normalized_transactions), "rule_count": len(normalized_rules), **normalized_exclusions},
        "common_rule_count": len(common),
        "interest_formula": "confidence(A -> B) - P(B), calculated in the same segment",
    }
    comparison_path.write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    all_rules_path.write_text(json.dumps({
        "status": "complete",
        "scope": "every rule that passed the configured support and confidence thresholds",
        "parameters": parameters,
        "rule_count": {"raw": len(raw_rules), "normalized": len(normalized_rules)},
        "raw": raw_rules,
        "normalized": normalized_rules,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    top_rules_path.write_text(json.dumps({
        "status": "complete",
        "scope": f"display-only preview: highest-interest {args.top_n} rules per experiment",
        "selected_top_n": args.top_n,
        "rule_count": {"raw": len(raw_rules), "normalized": len(normalized_rules)},
        "source_artifact": all_rules_path.name,
        "raw": raw_rules[:args.top_n],
        "normalized": normalized_rules[:args.top_n],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {comparison_path}, {all_rules_path} ({len(normalized_rules)} rules) and {top_rules_path} (top {args.top_n})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
