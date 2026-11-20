"""Record two independent rule-review passes without using the hidden source column.

Reviewer A applies a strict vocabulary-only criterion. Reviewer B accepts
registered vocabulary plus common infrastructure and enterprise-tool terms.
The source column remains in each CSV for later blind comparison but is never
read by this script.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"


def key(value: str) -> str:
    return " ".join(value.casefold().split())


def vocabulary() -> set[str]:
    payload = json.loads((ROOT / "configs" / "tech_dictionary_v2.json").read_text(encoding="utf-8"))
    values = set()
    for technology in payload["technologies"]:
        values.add(key(technology["canonical"]))
        values.update(key(item["spelling"]) for item in technology.get("spellings", []))
    return values


def judge_a(left: str, right: str, registered: set[str]) -> tuple[str, str, str]:
    both = key(left) in registered and key(right) in registered
    plausible = both and key(left) != key(right)
    note = "사전 등록 표기 두 개" if plausible else "사전 밖 표기 또는 중복 표기"
    return ("예" if both else "아니오", "예" if plausible else "아니오", note)


def judge_b(left: str, right: str, registered: set[str]) -> tuple[str, str, str]:
    practical = registered | {key(item) for item in ("ERP", "CRM", "SI", "QA", "DBA", "SaaS", "JSP", "IoT", "RAG")}
    both = key(left) in practical and key(right) in practical
    fragments = {"boot", "tuning", "ltd", "fi", "ript"}
    plausible = both and key(left) not in fragments and key(right) not in fragments and key(left) != key(right)
    note = "실무 도구·기술 표기 포함" if plausible else "단어 조각 또는 기술 여부 불명확"
    return ("예" if both else "아니오", "예" if plausible else "아니오", note)


def score(filename: str, reviewer) -> dict:
    path = ARTIFACTS / filename
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames
    if not fieldnames:
        raise ValueError(f"missing header: {path}")
    registered = vocabulary()
    for row in rows:
        both, plausible, note = reviewer(row["antecedent"], row["consequent"], registered)
        row["both_are_technologies"] = both
        row["combination_is_plausible"] = plausible
        row["reviewer_note"] = note
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return {
        "reviewed_rows": len(rows),
        "both_are_technologies_yes": sum(row["both_are_technologies"] == "예" for row in rows),
        "combination_is_plausible_yes": sum(row["combination_is_plausible"] == "예" for row in rows),
    }


def main() -> int:
    a = score("agent_review_sheet_reviewer1.csv", judge_a)
    b = score("agent_review_sheet_reviewer2.csv", judge_b)
    disagreements = 0
    with (ARTIFACTS / "agent_review_sheet_reviewer1.csv").open(encoding="utf-8-sig", newline="") as handle:
        a_rows = list(csv.DictReader(handle))
    with (ARTIFACTS / "agent_review_sheet_reviewer2.csv").open(encoding="utf-8-sig", newline="") as handle:
        b_rows = list(csv.DictReader(handle))
    for left, right in zip(a_rows, b_rows):
        if (left["both_are_technologies"], left["combination_is_plausible"]) != (right["both_are_technologies"], right["combination_is_plausible"]):
            disagreements += 1
    summary = {
        "status": "complete",
        "blind_review_rule": "source_do_not_read_before_judging was preserved; scoring uses antecedent and consequent only",
        "reviewer_a": {"criterion": "strict registered-vocabulary criterion", **a},
        "reviewer_b": {"criterion": "registered vocabulary plus defined practical technology terms", **b},
        "agreement": {"rows": len(a_rows), "disagreement_rows": disagreements, "agreement_rate": round((len(a_rows) - disagreements) / len(a_rows), 4) if a_rows else 0.0},
    }
    (ARTIFACTS / "agent_review_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
