"""CLI for the recommendation flow that widens filters and says that it did."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.retrieval import RuleRepository

from .memory import as_technology_dictionary

from .recommend import recommend_with_relaxation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills", nargs="+", required=True)
    parser.add_argument("--role")
    parser.add_argument("--experience")
    parser.add_argument("--entry-eligible", action="store_true")
    parser.add_argument("--rules", default="artifacts/week12_all_rules.json")
    parser.add_argument("--postings", default="data/processed/postings_normalized.jsonl")
    parser.add_argument("--dictionary", default="configs/tech_dictionary_v2.json")
    parser.add_argument("--config", type=Path, default=Path("configs/agent.json"))
    args = parser.parse_args()

    max_steps = json.loads(args.config.read_text(encoding="utf-8"))["max_relaxation_steps"]
    dictionary = as_technology_dictionary(args.dictionary)
    # Raw spellings are passed through: normalising them is one of the retry
    # steps, so doing it here would hide that the step happened.
    repository = RuleRepository(args.rules, args.postings)
    response = recommend_with_relaxation(
        repository, list(args.skills), args.role, args.experience, args.entry_eligible,
        dictionary=dictionary, max_steps=max_steps,
    )
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
