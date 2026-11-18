"""Create normalized JSONL and a summary from the approved week-10 input export."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.ingestion.loader import load_postings

from .dictionary import TechnologyDictionary
from .normalizer import normalize_technologies


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/raw/korean_it_recruit_postings.json"))
    parser.add_argument("--dictionary", type=Path, default=Path("configs/tech_dictionary.json"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/postings_normalized.jsonl"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts"))
    args = parser.parse_args()
    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.artifact_dir / "week11_normalization_summary.json"
    dictionary = TechnologyDictionary.from_json(args.dictionary)
    if not args.input.is_file():
        summary_path.write_text(json.dumps({
            "status": "blocked_missing_input",
            "input": {"expected_path": str(args.input)},
            "dictionary_version": dictionary.version,
            "next_action": "Create the approved week-10 input export, then rerun this command."
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote blocked-input record: {summary_path}")
        return 0

    postings = load_postings(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    transformed = duplicates = 0
    unknown_values: set[str] = set()
    with args.output.open("w", encoding="utf-8") as handle:
        for posting in postings:
            normalized = normalize_technologies(posting.final_techs, dictionary)
            row = dict(posting.raw)
            row["normalized_techs"] = list(normalized.normalized_techs)
            row["normalization_dictionary_version"] = dictionary.version
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            transformed += normalized.transformed_count
            duplicates += normalized.duplicate_count
            unknown_values.update(normalized.unknown_techs)
    summary_path.write_text(json.dumps({
        "status": "complete",
        "input_row_count": len(postings),
        "dictionary_version": dictionary.version,
        "starting_field": "final_techs",
        "output_field": "normalized_techs",
        "transformed_alias_count": transformed,
        "removed_per_posting_duplicate_count": duplicates,
        "unknown_technology_count": len(unknown_values),
        "unknown_technologies": sorted(unknown_values),
        "output_path": str(args.output)
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output} and {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
