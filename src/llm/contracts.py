"""Contracts for the future explanation layer, independent of any vendor SDK."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMRequest:
    user_message: str
    context: dict[str, object]


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider_name: str
    is_mock: bool


class LLMProvider(Protocol):
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Return an explanation response without changing recommendation evidence."""
