"""Deterministic two-item Apriori rules with segment-local interest."""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from math import ceil


def mine_pair_rules(transactions: list[set[str]], minimum_support: float, minimum_confidence: float) -> list[dict]:
    """Mine one-item antecedent/consequent rules from de-duplicated transactions."""
    if not transactions:
        return []
    total = len(transactions)
    minimum_count = ceil(total * minimum_support)
    item_counts = Counter(item for transaction in transactions for item in transaction)
    pair_counts = Counter(
        pair for transaction in transactions for pair in combinations(sorted(transaction), 2)
    )
    rules: list[dict] = []
    for (left, right), pair_count in pair_counts.items():
        if pair_count < minimum_count:
            continue
        for antecedent, consequent in ((left, right), (right, left)):
            confidence = pair_count / item_counts[antecedent]
            if confidence < minimum_confidence:
                continue
            consequent_probability = item_counts[consequent] / total
            rules.append({
                "antecedent": [antecedent],
                "consequent": [consequent],
                "support": pair_count / total,
                "support_count": pair_count,
                "confidence": confidence,
                "consequent_probability": consequent_probability,
                "interest": confidence - consequent_probability,
                "transaction_count": total,
            })
    return sorted(rules, key=lambda rule: (-rule["interest"], -rule["confidence"], rule["antecedent"], rule["consequent"]))
