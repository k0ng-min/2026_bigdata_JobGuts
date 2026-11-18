"""Association-rule analysis for JobGuts technology transactions."""

from .apriori import mine_pair_rules

__all__ = ["mine_pair_rules"]
