"""Deterministic implementation used for contract and integration tests."""

from __future__ import annotations

from .contracts import LLMRequest, LLMResponse


class FakeLLMProvider:
    provider_name = "fake"

    def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text=f"Mock explanation for: {request.user_message}",
            provider_name=self.provider_name,
            is_mock=True,
        )
