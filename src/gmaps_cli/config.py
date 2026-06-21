"""Load and save job files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from gmaps_cli.models import ScrapeJob


def _deserialize(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(raw)
    return yaml.safe_load(raw)


def load_job_from_path(path: str | Path) -> ScrapeJob:
    file_path = Path(path)
    data = _deserialize(file_path)
    return ScrapeJob.model_validate(data)


def save_job_to_path(job: ScrapeJob, path: str | Path) -> Path:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if file_path.suffix.lower() == ".json":
        file_path.write_text(
            json.dumps(job.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
    else:
        file_path.write_text(
            yaml.safe_dump(job.model_dump(mode="json"), sort_keys=False),
            encoding="utf-8",
        )
    return file_path
