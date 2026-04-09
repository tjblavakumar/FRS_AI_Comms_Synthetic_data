"""Base generator class for synthetic data generation."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from datagen.bedrock_client import BedrockClient
from datagen.config import AppConfig

logger = logging.getLogger(__name__)


class BaseGenerator(ABC):
    """Abstract base class for all data generators."""

    # Subclasses must set these
    category_name: str = ""
    id_prefix: str = ""

    def __init__(self, config: AppConfig, client: BedrockClient) -> None:
        self.config = config
        self.client = client
        self.date_start = config.data.date_range.start
        self.date_end = config.data.date_range.end
        self.context = config.data.context
        self.batch_size = config.bedrock.batch_size

    @abstractmethod
    def get_count(self) -> int:
        """Return the number of records to generate."""

    @abstractmethod
    def build_prompt(self, batch_index: int, batch_size: int, offset: int) -> str:
        """Build the prompt for generating a batch of records.

        Args:
            batch_index: The current batch number (0-indexed).
            batch_size: Number of records to generate in this batch.
            offset: The starting ID offset for this batch.

        Returns:
            The formatted prompt string.
        """

    def get_system_prompt(self) -> str:
        """Return the system prompt for this generator.

        Override in subclasses for category-specific system prompts.
        """
        return (
            "You are a synthetic data generator for a central bank communications AI system. "
            f"The context is the {self.context}. "
            "Generate realistic, diverse synthetic data that would be useful for training "
            "NLP models for text classification, sentiment analysis, and topic modeling. "
            "Always return valid JSON arrays. Each record must be complete and realistic."
        )

    def generate(self) -> list[dict[str, Any]]:
        """Generate all records for this category.

        Returns:
            List of all generated records.
        """
        total = self.get_count()
        if total <= 0:
            logger.info("Skipping %s (count=0)", self.category_name)
            return []

        logger.info(
            "Generating %d %s records (batch_size=%d)",
            total,
            self.category_name,
            self.batch_size,
        )

        all_records: list[dict[str, Any]] = []
        generated = 0
        batch_index = 0

        while generated < total:
            remaining = total - generated
            current_batch_size = min(self.batch_size, remaining)

            logger.info(
                "  Batch %d: generating %d records (offset=%d)",
                batch_index + 1,
                current_batch_size,
                generated,
            )

            prompt = self.build_prompt(batch_index, current_batch_size, generated)
            system_prompt = self.get_system_prompt()

            try:
                result = self.client.generate_json(prompt, system_prompt)

                if isinstance(result, dict):
                    # If model returned a wrapper object, try to extract the array
                    for key in result:
                        if isinstance(result[key], list):
                            result = result[key]
                            break
                    else:
                        result = [result]

                if not isinstance(result, list):
                    logger.warning("Unexpected response type: %s", type(result))
                    result = [result]

                # Assign IDs if not present
                for i, record in enumerate(result):
                    if "id" not in record:
                        record["id"] = f"{self.id_prefix}-{generated + i + 1:05d}"

                all_records.extend(result)
                generated += len(result)

                logger.info(
                    "  Batch %d complete: got %d records (total: %d/%d)",
                    batch_index + 1,
                    len(result),
                    generated,
                    total,
                )

            except (ValueError, KeyError) as e:
                logger.error("  Batch %d failed: %s. Retrying...", batch_index + 1, e)
                # Retry once on failure
                try:
                    result = self.client.generate_json(prompt, system_prompt)
                    if isinstance(result, dict):
                        for key in result:
                            if isinstance(result[key], list):
                                result = result[key]
                                break
                        else:
                            result = [result]
                    if not isinstance(result, list):
                        result = [result]
                    for i, record in enumerate(result):
                        if "id" not in record:
                            record["id"] = f"{self.id_prefix}-{generated + i + 1:05d}"
                    all_records.extend(result)
                    generated += len(result)
                except Exception as retry_err:
                    logger.error(
                        "  Batch %d retry also failed: %s. Skipping batch.",
                        batch_index + 1,
                        retry_err,
                    )

            batch_index += 1

        # Trim to exact count if we over-generated
        if len(all_records) > total:
            all_records = all_records[:total]

        logger.info(
            "Finished generating %d %s records", len(all_records), self.category_name
        )
        return all_records
