"""Provider-independent language-model boundary; no network implementation."""

from .contracts import LLMProvider, LLMRequest, LLMResponse
from .fake_provider import FakeLLMProvider

__all__ = ["FakeLLMProvider", "LLMProvider", "LLMRequest", "LLMResponse"]
