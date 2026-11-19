"""Check that GLM is reachable with one short request, then stop.

Run this once after filling in .env and before any sample run, so a
configuration mistake surfaces in a single call rather than part way through a
few hundred. It sends one tiny prompt, prints what it found, and exits.

The key is never printed. Only its length and last two characters are shown,
which is enough to tell two keys apart without putting one on screen or into a
terminal log.

Failures are reported by kind, because each kind has a different fix:
configuration, authentication, model name, network, or response shape.
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

from src.llm.contracts import LLMRequest
from src.llm.glm_provider import (
    API_KEY_VARIABLE,
    BASE_URL_VARIABLE,
    MODEL_VARIABLE,
    GLMProvider,
    MissingCredentialError,
    MissingSettingError,
)

PROBE_MESSAGE = "Reply with the single word: ok"


def redact(key: str) -> str:
    """Describe a key without revealing it."""
    return f"length {len(key)}, ends with ...{key[-2:]}" if len(key) >= 2 else "length under 2"


def classify(error: Exception) -> tuple[str, str]:
    """Return (kind, what to do about it)."""
    if isinstance(error, MissingCredentialError):
        return "configuration", f"{API_KEY_VARIABLE} is absent. Copy .env.example to .env and fill it in."
    if isinstance(error, MissingSettingError):
        return "configuration", f"Set {BASE_URL_VARIABLE} and {MODEL_VARIABLE} in .env. Neither has a default."
    if isinstance(error, urllib.error.HTTPError):
        if error.code in (401, 403):
            return "authentication", f"The server rejected the key ({error.code}). Check {API_KEY_VARIABLE}."
        if error.code == 404:
            return "address", (
                f"The endpoint was not found (404). Check {BASE_URL_VARIABLE}: it must be the API root, "
                "and the code appends /chat/completions itself."
            )
        if error.code == 429:
            return "rate limit", "The plan's rate or quota limit was hit. Wait, then retry."
        if error.code in (400, 422):
            return "model or request", f"The server rejected the request ({error.code}). Check {MODEL_VARIABLE}."
        return "server", f"HTTP {error.code} {error.reason}."
    if isinstance(error, urllib.error.URLError):
        return "network", f"The request could not be sent ({error.reason}). Check the network and the host name."
    return "response", str(error)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dotenv", default=".env")
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()

    print("GLM connection check — sends exactly one short request.")
    try:
        provider = GLMProvider(dotenv_path=args.dotenv, timeout=args.timeout)
    except (MissingCredentialError, MissingSettingError) as error:
        kind, advice = classify(error)
        print(f"\nFAILED ({kind})\n")
        print(error)
        print(f"\nWhat to do: {advice}")
        return 1

    print(f"  {API_KEY_VARIABLE}: set ({redact(provider.api_key)})")
    print(f"  {BASE_URL_VARIABLE}: {provider.base_url}")
    print(f"  endpoint: {provider.endpoint}")
    print(f"  {MODEL_VARIABLE}: {provider.model}")
    print(f"  timeout: {args.timeout}s")
    print("\nSending one request...")

    try:
        response = provider.generate(LLMRequest(user_message=PROBE_MESSAGE, context={"system": "", "temperature": 0.0}))
    except Exception as error:  # noqa: BLE001 - the point is to classify whatever comes back
        kind, advice = classify(error)
        print(f"\nFAILED ({kind})")
        print(f"  {error}")
        print(f"\nWhat to do: {advice}")
        print("  The fake provider still works: use --provider fake.")
        return 1

    text = (response.text or "").strip()
    print("\nOK")
    print(f"  provider: {response.provider_name}")
    print(f"  is_mock: {response.is_mock}")
    print(f"  reply: {text[:120]!r}")
    if not text:
        print("\n  The call succeeded but the reply was empty. Check the model name before a sample run.")
        return 1
    print("\nNext: a 1% sample run.")
    print("  python -m src.agent.run_agent --provider glm --limit 187 \\")
    print("    --artifact-dir artifacts/glm_sample --cleaned-output data/processed/postings_glm_sample.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
