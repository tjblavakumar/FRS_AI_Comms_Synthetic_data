"""CLI entrypoint for the synthetic data generator."""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import click

from datagen.bedrock_client import BedrockClient
from datagen.config import load_config
from datagen.generators.inquiries import InquiryGenerator
from datagen.generators.social_media import SocialMediaGenerator
from datagen.generators.news_articles import NewsArticleGenerator
from datagen.generators.response_templates import ResponseTemplateGenerator
from datagen.generators.insight_reports import InsightReportGenerator
from datagen.utils import save_json


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


GENERATOR_MAP = {
    "inquiries": InquiryGenerator,
    "social_media": SocialMediaGenerator,
    "news_articles": NewsArticleGenerator,
    "response_templates": ResponseTemplateGenerator,
    "insight_reports": InsightReportGenerator,
}


@click.group()
def cli() -> None:
    """Synthetic Data Generator for Central Bank Communications AI."""


@cli.command()
@click.option(
    "--config",
    "config_path",
    default="config.yaml",
    help="Path to the configuration YAML file.",
    type=click.Path(exists=True),
)
@click.option(
    "--category",
    "categories",
    multiple=True,
    type=click.Choice(list(GENERATOR_MAP.keys()) + ["all"]),
    default=["all"],
    help="Category to generate. Use 'all' for everything. Can specify multiple.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose/debug logging.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be generated without calling Bedrock.",
)
def generate(
    config_path: str,
    categories: tuple[str, ...],
    verbose: bool,
    dry_run: bool,
) -> None:
    """Generate synthetic data for specified categories."""
    setup_logging(verbose)
    logger = logging.getLogger(__name__)

    logger.info("Loading configuration from: %s", config_path)
    config = load_config(config_path)

    # Determine which categories to generate
    if "all" in categories:
        selected = list(GENERATOR_MAP.keys())
    else:
        selected = list(categories)

    # Filter by enabled flag in config
    enabled_categories = []
    for cat_name in selected:
        cat_config = getattr(config.categories, cat_name)
        if cat_config.enabled:
            enabled_categories.append(cat_name)
        else:
            logger.info("Skipping disabled category: %s", cat_name)

    if not enabled_categories:
        logger.warning("No categories enabled. Nothing to generate.")
        sys.exit(0)

    # Show plan
    logger.info("=" * 60)
    logger.info("Synthetic Data Generation Plan")
    logger.info("=" * 60)
    logger.info("Model: %s", config.bedrock.model_id)
    logger.info("Region: %s", config.bedrock.region)
    logger.info(
        "Date range: %s to %s", config.data.date_range.start, config.data.date_range.end
    )
    logger.info("Output directory: %s", config.output.directory)
    logger.info("-" * 60)

    total_records = 0
    for cat_name in enabled_categories:
        cat_config = getattr(config.categories, cat_name)
        count = cat_config.count
        total_records += count
        logger.info("  %-25s %d records", cat_name, count)

    logger.info("-" * 60)
    logger.info("  %-25s %d records", "TOTAL", total_records)
    logger.info("=" * 60)

    if dry_run:
        logger.info("DRY RUN: No data will be generated.")
        sys.exit(0)

    # Initialize Bedrock client
    logger.info("Initializing AWS Bedrock client...")
    client = BedrockClient(config.bedrock)

    # Generate each category
    start_time = time.time()
    results: dict[str, int] = {}

    for cat_name in enabled_categories:
        logger.info("")
        logger.info("=" * 60)
        logger.info("Generating: %s", cat_name.upper())
        logger.info("=" * 60)

        cat_start = time.time()
        generator_cls = GENERATOR_MAP[cat_name]
        generator = generator_cls(config, client)

        records = generator.generate()

        # Save to file
        output_path = save_json(
            records,
            config.output.directory,
            cat_name,
            config.output.pretty,
            config.output.add_timestamp,
        )

        cat_elapsed = time.time() - cat_start
        results[cat_name] = len(records)
        logger.info(
            "Completed %s: %d records in %.1fs -> %s",
            cat_name,
            len(records),
            cat_elapsed,
            output_path,
        )

    # Summary
    total_elapsed = time.time() - start_time
    logger.info("")
    logger.info("=" * 60)
    logger.info("Generation Complete!")
    logger.info("=" * 60)
    for cat_name, count in results.items():
        logger.info("  %-25s %d records", cat_name, count)
    logger.info("-" * 60)
    logger.info("  %-25s %d records", "TOTAL", sum(results.values()))
    logger.info("  Time elapsed: %.1fs", total_elapsed)
    logger.info("  Output directory: %s", Path(config.output.directory).resolve())
    logger.info("=" * 60)


@cli.command()
@click.option(
    "--config",
    "config_path",
    default="config.yaml",
    help="Path to the configuration YAML file.",
    type=click.Path(exists=True),
)
def validate(config_path: str) -> None:
    """Validate the configuration file without generating data."""
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        config = load_config(config_path)
        logger.info("Configuration is valid!")
        logger.info("Model: %s", config.bedrock.model_id)
        logger.info("Region: %s", config.bedrock.region)

        total = 0
        for cat_name in GENERATOR_MAP:
            cat_config = getattr(config.categories, cat_name)
            status = "enabled" if cat_config.enabled else "disabled"
            count = cat_config.count
            total += count if cat_config.enabled else 0
            logger.info("  %-25s %s (%d records)", cat_name, status, count)

        logger.info("Total records to generate: %d", total)

    except Exception as e:
        logger.error("Configuration validation failed: %s", e)
        sys.exit(1)


@cli.command()
@click.option(
    "--config",
    "config_path",
    default="config.yaml",
    help="Path to the configuration YAML file.",
    type=click.Path(exists=True),
)
def test_connection(config_path: str) -> None:
    """Test the AWS Bedrock connection with a simple prompt."""
    setup_logging()
    logger = logging.getLogger(__name__)

    config = load_config(config_path)
    logger.info("Testing connection to AWS Bedrock...")
    logger.info("Model: %s", config.bedrock.model_id)
    logger.info("Region: %s", config.bedrock.region)

    try:
        client = BedrockClient(config.bedrock)
        response = client.generate(
            "Say 'Connection successful!' in exactly those words."
        )
        logger.info("Response: %s", response.strip())
        logger.info("AWS Bedrock connection test PASSED!")
    except Exception as e:
        logger.error("Connection test FAILED: %s", e)
        logger.error(
            "Make sure your AWS credentials are configured and you have "
            "access to the specified Bedrock model."
        )
        sys.exit(1)


if __name__ == "__main__":
    cli()
