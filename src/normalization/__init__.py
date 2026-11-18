"""Technology-name normalization while preserving source values and identifiers."""

from .dictionary import TechnologyDictionary
from .normalizer import NormalizationResult, normalize_technologies

__all__ = ["NormalizationResult", "TechnologyDictionary", "normalize_technologies"]
