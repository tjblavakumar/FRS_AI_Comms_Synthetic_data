"""AWS Bedrock client for invoking Claude models."""

from __future__ import annotations

import json
import logging
from typing import Any

import boto3
from botocore.config import Config as BotoConfig

from datagen.config import BedrockConfig

logger = logging.getLogger(__name__)


class BedrockClient:
    """Client for interacting with AWS Bedrock Claude models."""

    def __init__(self, config: BedrockConfig) -> None:
        self.config = config
        boto_config = BotoConfig(
            region_name=config.region,
            retries={"max_attempts": 5, "mode": "adaptive"},
            read_timeout=300,  # 5 minutes for long-running generations
            connect_timeout=10,
        )
        self.client = boto3.client("bedrock-runtime", config=boto_config)
        self.model_id = config.model_id
        self.max_tokens = config.max_tokens

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Send a prompt to Claude via Bedrock and return the response text.

        Args:
            prompt: The user prompt to send.
            system_prompt: Optional system prompt for context.

        Returns:
            The model's text response.
        """
        messages = [{"role": "user", "content": prompt}]

        body: dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_tokens,
            "messages": messages,
        }

        if system_prompt:
            body["system"] = system_prompt

        logger.debug("Invoking Bedrock model: %s", self.model_id)

        response = self.client.invoke_model(
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )

        response_body = json.loads(response["body"].read())
        text = response_body["content"][0]["text"]

        logger.debug("Received response (%d chars)", len(text))
        return text

    def generate_json(
        self, prompt: str, system_prompt: str | None = None
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Send a prompt and parse the response as JSON.

        The model is instructed to return valid JSON. The response is parsed
        and returned as a Python dict or list.

        Args:
            prompt: The user prompt to send.
            system_prompt: Optional system prompt for context.

        Returns:
            Parsed JSON response as a dict or list.

        Raises:
            ValueError: If the response cannot be parsed as JSON.
        """
        full_prompt = (
            f"{prompt}\n\n"
            "IMPORTANT: Return ONLY valid JSON. No markdown code fences, "
            "no explanatory text before or after. Just the raw JSON array or object."
        )

        text = self.generate(full_prompt, system_prompt)

        # Try to extract JSON from the response
        text = text.strip()

        # Remove markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line (```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON response: %s", e)
            logger.error("Raw response:\n%s", text[:500])
            raise ValueError(
                f"Model returned invalid JSON. First 200 chars: {text[:200]}"
            ) from e
