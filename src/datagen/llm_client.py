"""Unified LLM client with auto-detection: Ollama → OpenAI → AWS Bedrock."""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared JSON extraction helper
# ---------------------------------------------------------------------------

def _parse_json_response(text: str) -> list[dict] | dict:
    """Strip markdown fences and parse JSON from model text output."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # drop ```json or ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON response: %s", e)
        logger.error("Raw response (first 500 chars):\n%s", text[:500])
        raise ValueError(
            f"Model returned invalid JSON. First 200 chars: {text[:200]}"
        ) from e


# ---------------------------------------------------------------------------
# Ollama client (network or localhost)
# ---------------------------------------------------------------------------

class OllamaClient:
    """Client for Ollama running on local network or localhost."""

    def __init__(self, host: str, model: str, max_tokens: int = 4096) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Send a prompt to Ollama /api/chat and return the response text."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": self.max_tokens,
            },
        }

        logger.debug("Ollama: POST %s/api/chat model=%s", self.host, self.model)

        response = requests.post(
            f"{self.host}/api/chat",
            json=payload,
            timeout=300,
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]

    def generate_json(
        self, prompt: str, system_prompt: str | None = None
    ) -> list[dict] | dict:
        """Send a prompt with JSON mode enabled and parse the response."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Reinforce JSON-only output in the user prompt
        json_prompt = (
            f"{prompt}\n\n"
            "IMPORTANT: Return ONLY valid JSON. No markdown code fences, "
            "no explanatory text before or after. Just the raw JSON array or object."
        )
        messages.append({"role": "user", "content": json_prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": "json",  # Forces Ollama to produce valid JSON output
            "options": {
                "num_predict": self.max_tokens,
            },
        }

        logger.debug("Ollama: POST %s/api/chat model=%s [json mode]", self.host, self.model)

        response = requests.post(
            f"{self.host}/api/chat",
            json=payload,
            timeout=300,
        )
        response.raise_for_status()
        data = response.json()
        text = data["message"]["content"]
        return _parse_json_response(text)


# ---------------------------------------------------------------------------
# OpenAI client
# ---------------------------------------------------------------------------

class OpenAIClient:
    """Client for the OpenAI API."""

    def __init__(self, api_key: str, model: str = "gpt-4o", max_tokens: int = 4096) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "openai package is not installed. Run: pip install openai>=1.0"
            ) from exc
        self._openai = OpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Send a prompt to OpenAI chat completions and return the response text."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        logger.debug("OpenAI: chat completion model=%s", self.model)

        response = self._openai.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content or ""

    def generate_json(
        self, prompt: str, system_prompt: str | None = None
    ) -> list[dict] | dict:
        """Send a prompt using json_object response format and parse the result."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        json_prompt = (
            f"{prompt}\n\n"
            "IMPORTANT: Return ONLY valid JSON. No markdown code fences, "
            "no explanatory text before or after. Just the raw JSON array or object."
        )
        messages.append({"role": "user", "content": json_prompt})

        logger.debug("OpenAI: chat completion model=%s [json mode]", self.model)

        response = self._openai.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content or ""
        return _parse_json_response(text)


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------

def detect_ollama(host: str) -> list[str] | None:
    """Ping Ollama and return installed model names, or None if unreachable.

    Args:
        host: Ollama base URL, e.g. "http://192.168.68.96:11434"

    Returns:
        List of model name strings if reachable, None otherwise.
    """
    try:
        response = requests.get(
            f"{host.rstrip('/')}/api/tags",
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        models = [m["name"] for m in data.get("models", [])]
        return models
    except Exception:
        return None


def validate_openai_key(api_key: str) -> bool:
    """Return True if the OpenAI API key is valid (makes a lightweight models call)."""
    try:
        from openai import OpenAI, AuthenticationError
        client = OpenAI(api_key=api_key)
        client.models.list()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Auto-detection entry point
# ---------------------------------------------------------------------------

def auto_detect_client(
    ollama_host: str = "http://localhost:11434",
    ollama_model: str | None = None,
    openai_api_key: str | None = None,
    openai_model: str = "gpt-4o",
    bedrock_config: Any | None = None,
    max_tokens: int = 4096,
) -> tuple[Any, str, str]:
    """Auto-detect which LLM backend to use in priority order: Ollama → OpenAI → AWS Bedrock.

    Args:
        ollama_host: Base URL of the Ollama server.
        ollama_model: Specific Ollama model to use. If None, uses the first available model.
        openai_api_key: OpenAI API key. Skipped if None or empty.
        openai_model: OpenAI model name.
        bedrock_config: BedrockConfig instance. Skipped if None.
        max_tokens: Maximum tokens for generation.

    Returns:
        Tuple of (client_instance, backend_label, detail_string).

    Raises:
        RuntimeError: If no backend is available.
    """
    # 1. Try Ollama
    logger.info("Checking Ollama at %s ...", ollama_host)
    models = detect_ollama(ollama_host)
    if models is not None:
        selected_model = ollama_model if ollama_model else (models[0] if models else "gemma4")
        client = OllamaClient(host=ollama_host, model=selected_model, max_tokens=max_tokens)
        detail = f"{selected_model} @ {ollama_host}"
        logger.info("Connected to Local Ollama: %s", detail)
        return client, "Local Ollama", detail

    logger.info("Ollama not available. Trying OpenAI ...")

    # 2. Try OpenAI
    if openai_api_key and openai_api_key.strip():
        logger.info("Validating OpenAI API key ...")
        if validate_openai_key(openai_api_key.strip()):
            client = OpenAIClient(
                api_key=openai_api_key.strip(),
                model=openai_model,
                max_tokens=max_tokens,
            )
            logger.info("Connected to OpenAI: %s", openai_model)
            return client, "OpenAI", openai_model
        else:
            logger.warning("OpenAI API key validation failed.")

    logger.info("OpenAI not available. Trying AWS Bedrock ...")

    # 3. Fall back to AWS Bedrock
    if bedrock_config is not None:
        try:
            from datagen.bedrock_client import BedrockClient
            client = BedrockClient(config=bedrock_config)
            detail = f"{bedrock_config.model_id} ({bedrock_config.region})"
            logger.info("Connected to AWS Bedrock: %s", detail)
            return client, "AWS Bedrock", detail
        except Exception as e:
            logger.warning("AWS Bedrock connection failed: %s", e)

    raise RuntimeError(
        "No LLM backend available. "
        "Start Ollama, provide an OpenAI API key, or configure AWS credentials."
    )
