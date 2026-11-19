"""Real GLM provider. Not reached by the default run or by any test.

docs/llm_boundary.md requires that no API key, SDK dependency or HTTP request
is added until the integration is approved. This module respects that in three
ways: nothing here runs at import time, the credential is read from the
environment at call time and never from a file in the repository, and the agent
only constructs it when ``--provider glm`` is passed explicitly.

The credential comes from the ``GLM_API_KEY`` environment variable. A local
``.env`` may set it; ``.env`` is excluded from version control and only
``.env.example`` is committed. No third-party package is required: the request
is made with the standard library.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from .contracts import LLMRequest, LLMResponse

PROVIDER_NAME = "glm"
API_KEY_VARIABLE = "GLM_API_KEY"
BASE_URL_VARIABLE = "GLM_BASE_URL"
MODEL_VARIABLE = "GLM_MODEL"
DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
DEFAULT_MODEL = "glm-4-plus"
DEFAULT_TIMEOUT_SECONDS = 30


class MissingCredentialError(RuntimeError):
    """Raised when the provider is asked to run without a credential."""


def load_dotenv(path: str | Path = ".env") -> None:
    """Copy simple KEY=value lines from a local .env into the environment.

    Values already present in the environment win, so an explicitly exported
    variable is never overwritten by the file. Missing file is not an error.
    """
    dotenv = Path(path)
    if not dotenv.is_file():
        return
    for line in dotenv.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def read_api_key(dotenv_path: str | Path = ".env") -> str:
    load_dotenv(dotenv_path)
    key = os.environ.get(API_KEY_VARIABLE, "").strip()
    if not key:
        raise MissingCredentialError(
            f"{API_KEY_VARIABLE} is not set, so the GLM provider cannot run.\n"
            f"  Set it for this shell:  export {API_KEY_VARIABLE}=<your key>\n"
            f"  or copy .env.example to .env and fill in {API_KEY_VARIABLE}.\n"
            f"  .env is excluded from version control; never commit a key.\n"
            f"  To run without a model, use --provider fake."
        )
    return key


class GLMProvider:
    """Calls GLM over HTTPS. Constructed only when the caller asks for it."""

    provider_name = PROVIDER_NAME
    is_mock = False

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        dotenv_path: str | Path = ".env",
    ) -> None:
        # Reading the key here means constructing the provider is what fails
        # when the credential is missing, before any candidate is processed.
        self.api_key = api_key or read_api_key(dotenv_path)
        self.base_url = base_url or os.environ.get(BASE_URL_VARIABLE, DEFAULT_BASE_URL)
        self.model = model or os.environ.get(MODEL_VARIABLE, DEFAULT_MODEL)
        self.timeout = timeout

    def generate(self, request: LLMRequest) -> LLMResponse:
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": str(request.context.get("system", ""))},
                {"role": "user", "content": request.user_message},
            ],
            "temperature": float(request.context.get("temperature", 0.0)),
        }).encode("utf-8")
        http_request = urllib.request.Request(
            self.base_url,
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:  # pragma: no cover - needs a network
            raise RuntimeError(f"GLM request failed with HTTP {error.code}: {error.reason}") from error
        except urllib.error.URLError as error:  # pragma: no cover - needs a network
            raise RuntimeError(f"GLM request could not be sent: {error.reason}") from error
        try:
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:  # pragma: no cover - needs a network
            raise RuntimeError(f"GLM response had an unexpected shape: {body!r}") from error
        return LLMResponse(text=text, provider_name=self.provider_name, is_mock=False)
