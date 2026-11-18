import unittest

from src.analysis.apriori import mine_pair_rules


class AprioriTests(unittest.TestCase):
    def test_interest_uses_consequent_probability_in_same_transactions(self):
        rules = mine_pair_rules(
            [{"Java", "Spring"}, {"Java", "Spring"}, {"Java"}, {"Python"}],
            minimum_support=0.25,
            minimum_confidence=0.5,
        )
        java_to_spring = next(rule for rule in rules if rule["antecedent"] == ["Java"] and rule["consequent"] == ["Spring"])

        self.assertEqual(java_to_spring["support_count"], 2)
        self.assertAlmostEqual(java_to_spring["confidence"], 2 / 3)
        self.assertAlmostEqual(java_to_spring["consequent_probability"], 1 / 2)
        self.assertAlmostEqual(java_to_spring["interest"], (2 / 3) - (1 / 2))
