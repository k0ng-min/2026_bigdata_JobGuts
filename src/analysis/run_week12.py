"""Run comparable raw and normalized association-rule experiments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .apriori import mine_pair_rules


def _records(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _deduplicated_transactions(records: list[dict], field: str) -> tuple[list[set[str]], dict]:
    seen_ids: set[tuple[str, str]] = set()
    transactions: list[set[str]] = []
    excluded_empty = excluded_duplicate = 0
    for row in records:
        key = (str(row.get("source", "")), str(row.get("job_id", "")))
        if key in seen_ids:
            excluded_duplicate += 1
            continue
        seen_ids.add(key)
        transaction = {str(item).strip() for item in row.get(field, []) if str(item).strip()}
        if not transaction:
            excluded_empty += 1
            continue
        transactions.append(transaction)
    return transactions, {"excluded_source_job_id_duplicates": excluded_duplicate, "excluded_empty_transactions": excluded_empty}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/postings_normalized.jsonl"))
    parser.add_argument("--config", type=Path, default=Path("configs/experiments.json"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts"))
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    comparison_path = args.artifact_dir / "week12_rule_comparison.json"
    top_rules_path = args.artifact_dir / "week12_top_rules.json"
    if not args.input.is_file():
        comparison_path.write_text(json.dumps({"status": "blocked_missing_input", "expected_path": str(args.input)}, indent=2) + "\n", encoding="utf-8")
        top_rules_path.write_text("[]\n", encoding="utf-8")
        return 0
    records = _records(args.input)
    parameters = config["week12_parameters"]
    raw_transactions, raw_exclusions = _deduplicated_transactions(records, "final_techs")
    normalized_transactions, normalized_exclusions = _deduplicated_transactions(records, "normalized_techs")
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
        "raw": {"transaction_count": len(raw_transactions), "rule_count": len(raw_rules), **raw_exclusions},
        "normalized": {"transaction_count": len(normalized_transactions), "rule_count": len(normalized_rules), **normalized_exclusions},
        "common_rule_count": len(common),
        "interest_formula": "confidence(A -> B) - P(B), calculated in the same segment",
    }
    comparison_path.write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    top_rules_path.write_text(json.dumps({"raw": raw_rules[:50], "normalized": normalized_rules[:50]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {comparison_path} and {top_rules_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
