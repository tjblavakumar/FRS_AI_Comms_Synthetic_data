"""Utility functions for synthetic data generation."""

from __future__ import annotations

import json
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


def random_date(start: str, end: str) -> str:
    """Generate a random ISO-format date string between start and end.

    Args:
        start: Start date in YYYY-MM-DD format.
        end: End date in YYYY-MM-DD format.

    Returns:
        Random date string in ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ).
    """
    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")
    delta = end_dt - start_dt
    random_days = random.randint(0, delta.days)
    random_seconds = random.randint(0, 86399)
    dt = start_dt + timedelta(days=random_days, seconds=random_seconds)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def get_timestamp() -> str:
    """Generate a timestamp string for file versioning.

    Returns:
        Timestamp string in format YYYYMMDD_HHMMSS.
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def save_json(
    data: list[dict], output_dir: str, filename: str, pretty: bool = True, add_timestamp: bool = True
) -> Path:
    """Save data to a JSON file.

    Args:
        data: List of records to save.
        output_dir: Directory to save the file in.
        filename: Name of the output file (without extension).
        pretty: Whether to pretty-print the JSON.
        add_timestamp: Whether to add timestamp to filename for versioning.

    Returns:
        Path to the saved file.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    if add_timestamp:
        timestamp = get_timestamp()
        file_path = out_path / f"{filename}_{timestamp}.json"
    else:
        file_path = out_path / f"{filename}.json"
    
    indent = 2 if pretty else None

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)

    logger.info("Saved %d records to %s", len(data), file_path)
    return file_path


def chunk_list(items: list, chunk_size: int) -> list[list]:
    """Split a list into chunks of a given size.

    Args:
        items: The list to split.
        chunk_size: Maximum size of each chunk.

    Returns:
        List of chunks.
    """
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def generate_id(prefix: str, index: int) -> str:
    """Generate a formatted ID string.

    Args:
        prefix: ID prefix (e.g., 'INQ', 'SM', 'NEWS').
        index: Sequential index number.

    Returns:
        Formatted ID string like 'INQ-00001'.
    """
    return f"{prefix}-{index:05d}"
