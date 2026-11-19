"""Compare three technology lists over one posting set and prepare human review.

The three are the uncleaned extraction, the agent's cleanup, and final_techs.
They are mined with the same parameters over the same 17,796 postings, because
a difference in the posting set would make the rule counts incomparable.

Two precision and recall figures are reported, not one. Dictionary v2 takes its
standard names from final_techs and final_techs is also the ground truth here,
so a single figure flatters the dictionary. Splitting candidates into those
inside and outside the vocabulary separates the part of the score that the
shared vocabulary guarantees from the part that is earned.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
from collections import Counter
from pathlib import Path

from src.analysis.apriori import mine_pair_rules
from src.analysis.run_week14 import _eligible_rows

from .extract import extract_candidates, load_korean_spellings, load_stopwords


def comparison_key(value: str) -> str:
    """Case-insensitive key that still tells C, C++ and C# apart.

    Hangul is kept. Stripping it collapsed every Korean spelling onto its Latin
    remnant, so 생성형 AI compared equal to AI and 딥러닝 compared equal to the
    empty string, which silently mixed Korean candidates into the wrong bucket.
    """
    return re.sub(r"[^a-z0-9+#./\-\u3131-\u318e\uac00-\ud7a3 ]", "", value.casefold()).strip()


def score(predicted: list[set[str]], truth: list[set[str]], vocabulary: set[str]) -> dict:
    """Precision and recall overall, and split by whether a name is in the vocabulary."""
    vocabulary_keys = {comparison_key(name) for name in vocabulary}
    buckets = {
        "overall": {"hit": 0, "predicted": 0, "expected": 0},
        "inside_vocabulary": {"hit": 0, "predicted": 0, "expected": 0},
        "outside_vocabulary": {"hit": 0, "predicted": 0, "expected": 0},
    }
    for guess, gold in zip(predicted, truth):
        guess_keys = {comparison_key(name) for name in guess}
        gold_keys = {comparison_key(name) for name in gold}
        for key in guess_keys:
            inside = key in vocabulary_keys
            for bucket in ("overall", "inside_vocabulary" if inside else "outside_vocabulary"):
                buckets[bucket]["predicted"] += 1
                if key in gold_keys:
                    buckets[bucket]["hit"] += 1
        for key in gold_keys:
            inside = key in vocabulary_keys
            for bucket in ("overall", "inside_vocabulary" if inside else "outside_vocabulary"):
                buckets[bucket]["expected"] += 1
    result = {}
    for name, counts in buckets.items():
        precision = counts["hit"] / counts["predicted"] if counts["predicted"] else 0.0
        recall = counts["hit"] / counts["expected"] if counts["expected"] else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        result[name] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            **counts,
        }
    return result


def bucket_migration(before: list[set[str]], after: list[set[str]], origins: list[dict], truth: list[set[str]], vocabulary: set[str]) -> dict:
    """Split the in-vocabulary errors the cleanup adds into two kinds.

    Cleanup moves a name from outside the vocabulary to inside it, so an error
    that was already being counted outside reappears inside. That is a property
    of the buckets, not a new mistake. An error whose source spelling was
    correct, or absent, before is a new mistake and is reported separately.
    """
    vocabulary_keys = {comparison_key(name) for name in vocabulary}
    migrated: Counter[str] = Counter()
    introduced: Counter[str] = Counter()
    lost: Counter[str] = Counter()
    for guess_before, guess_after, origin, gold in zip(before, after, origins, truth):
        gold_keys = {comparison_key(name) for name in gold}
        inside_before = {comparison_key(name) for name in guess_before} & vocabulary_keys
        inside_after = {comparison_key(name) for name in guess_after} & vocabulary_keys
        origin_by_key = {comparison_key(name): source for name, source in origin.items()}
        for key in (inside_after - inside_before) - gold_keys:
            source = origin_by_key.get(key, key)
            source_key = comparison_key(source)
            was_outside_error = source_key not in vocabulary_keys and source_key not in gold_keys
            (migrated if was_outside_error else introduced)[f"{key} <- {source}"] += 1
        for key in (inside_before - inside_after) & gold_keys:
            lost[key] += 1
    total = sum(migrated.values()) + sum(introduced.values())
    return {
        "new_in_vocabulary_errors": total,
        "migrated_from_outside_bucket": sum(migrated.values()),
        "newly_introduced": sum(introduced.values()),
        "migrated_share": round(sum(migrated.values()) / total, 4) if total else 0.0,
        "correct_names_lost": sum(lost.values()),
        "migrated_top": [{"mapping": name, "count": count} for name, count in migrated.most_common(15)],
        "newly_introduced_top": [{"mapping": name, "count": count} for name, count in introduced.most_common(15)],
        "note": (
            "A migrated error was already counted in the outside_vocabulary bucket before cleanup, "
            "where its precision is structurally near zero, so it lowers inside_vocabulary precision "
            "without the cleanup having made a new mistake."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/postings_normalized.jsonl"))
    parser.add_argument("--cleaned", type=Path, default=Path("data/processed/postings_agent_cleaned.jsonl"))
    parser.add_argument("--dictionary", type=Path, default=Path("configs/tech_dictionary_v2.json"))
    parser.add_argument("--stopwords", type=Path, default=Path("configs/extract_stopwords.json"))
    parser.add_argument("--korean", type=Path, default=Path("configs/tech_dictionary_korean.json"))
    parser.add_argument("--experiments", type=Path, default=Path("configs/experiments.json"))
    parser.add_argument("--summary", type=Path, default=Path("artifacts/agent_run_summary.json"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--review-rows", type=int, default=50)
    parser.add_argument("--reviewers", type=int, default=2,
                        help="How many independent copies of the review sheet to write.")
    parser.add_argument("--seed", type=int, default=31415)
    args = parser.parse_args()
    args.artifact_dir.mkdir(parents=True, exist_ok=True)

    parameters = json.loads(args.experiments.read_text(encoding="utf-8"))["week12_parameters"]
    support = parameters["minimum_support"]
    confidence = parameters["minimum_confidence"]
    vocabulary = {
        record["canonical"]
        for record in json.loads(args.dictionary.read_text(encoding="utf-8"))["technologies"]
    }

    with args.input.open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line.strip()]
    postings = _eligible_rows(records, "normalized_techs")
    stopwords = load_stopwords(args.stopwords)
    korean = load_korean_spellings(args.korean)

    with args.cleaned.open(encoding="utf-8") as handle:
        cleaned_rows = [json.loads(line) for line in handle if line.strip()]
    if len(cleaned_rows) != len(postings):
        raise ValueError(
            f"the cleaned file has {len(cleaned_rows)} postings but the eligible set has {len(postings)}; "
            "rerun src.agent.run_agent so both describe the same population"
        )

    before = [{candidate.name for candidate in extract_candidates(row.get("raw_text") or "", stopwords, korean)}
              for row in postings]
    after = [set(row["agent_techs"]) for row in cleaned_rows]
    origins = [row.get("agent_origin", {}) for row in cleaned_rows]
    truth = [{str(item).strip() for item in (row.get("final_techs") or []) if str(item).strip()} for row in postings]

    experiments = {}
    rule_sets = {}
    for label, transactions in (("before_cleanup", before), ("after_agent", after), ("final_techs", truth)):
        usable = [items or {"__EMPTY__"} for items in transactions]
        rules = mine_pair_rules(usable, support, confidence)
        rule_sets[label] = rules
        experiments[label] = {
            "transaction_count": len(usable),
            "distinct_items": len({item for items in usable for item in items}),
            "rule_count": len(rules),
            "distinct_antecedents": len({rule["antecedent"][0] for rule in rules}),
            "top_rules": [
                {"antecedent": rule["antecedent"][0], "consequent": rule["consequent"][0],
                 "support": round(rule["support"], 6), "confidence": round(rule["confidence"], 6),
                 "interest": round(rule["interest"], 6)}
                for rule in rules[:10]
            ],
        }

    def pair_set(label):
        return {(rule["antecedent"][0], rule["consequent"][0]) for rule in rule_sets[label]}

    overlaps = {}
    for left, right in (("before_cleanup", "after_agent"), ("after_agent", "final_techs"), ("before_cleanup", "final_techs")):
        a, b = pair_set(left), pair_set(right)
        overlaps[f"{left}__vs__{right}"] = {
            "shared": len(a & b),
            f"only_{left}": len(a - b),
            f"only_{right}": len(b - a),
            "jaccard": round(len(a & b) / len(a | b), 4) if a | b else 0.0,
            "top50_shared": len(
                {(rule["antecedent"][0], rule["consequent"][0]) for rule in rule_sets[left][:50]}
                & {(rule["antecedent"][0], rule["consequent"][0]) for rule in rule_sets[right][:50]}
            ),
        }

    run_summary = json.loads(args.summary.read_text(encoding="utf-8")) if args.summary.is_file() else {}
    is_mock = bool(run_summary.get("is_mock"))
    report = {
        "status": "complete",
        "is_mock": is_mock,
        "mock_warning": run_summary.get("mock_warning"),
        "basis": {
            "posting_count": len(postings),
            "minimum_support": support,
            "minimum_confidence": confidence,
            "vocabulary_size": len(vocabulary),
        },
        "experiments": experiments,
        "rule_overlap": overlaps,
        "quality_against_final_techs": {
            "before_cleanup": score(before, truth, vocabulary),
            "after_agent": score(after, truth, vocabulary),
        },
        "in_vocabulary_error_breakdown": bucket_migration(before, after, origins, truth, vocabulary),
        "evaluation_bias_note": (
            "Standard names come from final_techs and final_techs is the ground truth here, so the "
            "inside_vocabulary figures are structurally favourable. Read outside_vocabulary and the "
            "human review sheet alongside them."
        ),
    }
    (args.artifact_dir / "agent_comparison.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Review sheet: top rules from both sides, shuffled, with the source hidden
    # in a column the reviewers are asked not to read until they have judged.
    rows = []
    for label in ("before_cleanup", "after_agent"):
        for rank, rule in enumerate(rule_sets[label][: args.review_rows], start=1):
            rows.append({
                "rule_id": f"{label[:1].upper()}{rank:03d}",
                "antecedent": rule["antecedent"][0],
                "consequent": rule["consequent"][0],
                "support": round(rule["support"], 6),
                "confidence": round(rule["confidence"], 6),
                "interest": round(rule["interest"], 6),
                "support_count": rule["support_count"],
                "both_are_technologies": "",
                "combination_is_plausible": "",
                "reviewer_note": "",
                "source_do_not_read_before_judging": label,
            })
    random.Random(args.seed).shuffle(rows)
    # One master sheet plus a blank copy per reviewer, so two people can judge
    # the same rules in the same order without overwriting each other.
    review_path = args.artifact_dir / "agent_review_sheet.csv"
    review_paths = [review_path] + [
        args.artifact_dir / f"agent_review_sheet_reviewer{index}.csv"
        for index in range(1, args.reviewers + 1)
    ]
    for path in review_paths:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    print(
        f"Wrote {args.artifact_dir / 'agent_comparison.json'} and {len(review_paths)} review sheets "
        f"({len(rows)} rows each) | rules before={experiments['before_cleanup']['rule_count']} "
        f"after={experiments['after_agent']['rule_count']} final_techs={experiments['final_techs']['rule_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
