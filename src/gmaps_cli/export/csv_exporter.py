"""CSV export helpers."""

from __future__ import annotations

import csv
from pathlib import Path

from gmaps_cli.models import LocationRecord


CSV_COLUMNS = [
    "title",
    "rating",
    "review_count",
    "category",
    "address",
    "open_state",
    "hours_text",
    "description",
    "has_booking_link",
    "has_website_link",
    "is_sponsored",
    "url",
    "query",
    "region",
    "source_url",
    "scraped_at",
]


def export_records(records: list[LocationRecord], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow(record.model_dump())

    return path
