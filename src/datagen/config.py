"""Configuration loading and validation using Pydantic."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class BedrockConfig(BaseModel):
    model_id: str = "us.anthropic.claude-sonnet-4-5-20250514"
    region: str = "us-west-2"
    max_tokens: int = 4096
    batch_size: int = 10


class DateRangeConfig(BaseModel):
    start: str = "2022-01-01"
    end: str = "2025-12-31"


class DataConfig(BaseModel):
    date_range: DateRangeConfig = Field(default_factory=DateRangeConfig)
    context: str = (
        "Federal Reserve System / Federal Reserve Bank of San Francisco (FRBSF)"
    )


class InquiriesConfig(BaseModel):
    enabled: bool = True
    count: int = 500
    sources: list[str] = Field(
        default_factory=lambda: ["media", "public", "stakeholder"]
    )
    channels: list[str] = Field(
        default_factory=lambda: ["email", "web_form", "letter", "phone"]
    )
    topics: list[str] = Field(
        default_factory=lambda: [
            "monetary_policy",
            "interest_rates",
            "inflation",
            "employment",
            "banking_regulation",
            "financial_stability",
        ]
    )
    priorities: list[str] = Field(default_factory=lambda: ["high", "medium", "low"])


class SocialMediaConfig(BaseModel):
    enabled: bool = True
    count: int = 1000
    platforms: list[str] = Field(
        default_factory=lambda: ["twitter", "reddit", "linkedin"]
    )
    author_types: list[str] = Field(
        default_factory=lambda: [
            "journalist",
            "financial_analyst",
            "economist",
            "public",
            "policy_commentator",
        ]
    )
    sentiments: list[str] = Field(
        default_factory=lambda: ["positive", "negative", "neutral"]
    )
    topics: list[str] = Field(
        default_factory=lambda: [
            "fed_rate_decision",
            "inflation_data",
            "employment_report",
            "fomc_meeting",
        ]
    )


class NewsArticlesConfig(BaseModel):
    enabled: bool = True
    count: int = 200
    sources: list[str] = Field(
        default_factory=lambda: [
            "reuters",
            "bloomberg",
            "wall_street_journal",
            "financial_times",
        ]
    )
    sentiments: list[str] = Field(
        default_factory=lambda: ["positive", "negative", "neutral"]
    )
    topics: list[str] = Field(
        default_factory=lambda: [
            "monetary_policy",
            "interest_rates",
            "inflation",
            "employment",
        ]
    )


class ResponseTemplatesConfig(BaseModel):
    enabled: bool = True
    count: int = 50
    inquiry_categories: list[str] = Field(
        default_factory=lambda: [
            "monetary_policy",
            "interest_rates",
            "inflation",
            "general_inquiry",
            "media_request",
        ]
    )
    tones: list[str] = Field(
        default_factory=lambda: ["formal", "empathetic", "informational", "technical"]
    )


class InsightReportsConfig(BaseModel):
    enabled: bool = True
    count: int = 30
    report_types: list[str] = Field(
        default_factory=lambda: [
            "daily_summary",
            "weekly_analysis",
            "monthly_trend",
            "incident_report",
            "risk_assessment",
        ]
    )


class CategoriesConfig(BaseModel):
    inquiries: InquiriesConfig = Field(default_factory=InquiriesConfig)
    social_media: SocialMediaConfig = Field(default_factory=SocialMediaConfig)
    news_articles: NewsArticlesConfig = Field(default_factory=NewsArticlesConfig)
    response_templates: ResponseTemplatesConfig = Field(
        default_factory=ResponseTemplatesConfig
    )
    insight_reports: InsightReportsConfig = Field(default_factory=InsightReportsConfig)


class OutputConfig(BaseModel):
    format: str = "json"
    directory: str = "./output"
    pretty: bool = True
    add_timestamp: bool = True  # Add timestamp to filenames for versioning


class AppConfig(BaseModel):
    bedrock: BedrockConfig = Field(default_factory=BedrockConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    categories: CategoriesConfig = Field(default_factory=CategoriesConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """Load configuration from a YAML file.

    Args:
        config_path: Path to the YAML config file. Defaults to 'config.yaml'.

    Returns:
        Validated AppConfig instance.
    """
    if config_path is None:
        config_path = "config.yaml"

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path) as f:
        raw = yaml.safe_load(f)

    return AppConfig(**raw)
