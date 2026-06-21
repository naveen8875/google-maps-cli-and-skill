"""Checkpoint helpers for resumable scrape runs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from gmaps_cli.models import QuerySeed, RunCheckpoint, ScrapeJob, utc_now_iso


def job_fingerprint(job: ScrapeJob) -> str:
    payload = job.model_dump(mode="json")
    payload.pop("created_at", None)
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def seed_key(seed: QuerySeed) -> str:
    encoded = json.dumps(seed.model_dump(mode="json"), sort_keys=True).encode("utf-8")
    return hashlib.sha1(encoded).hexdigest()


def resolve_checkpoint_path(path: str | Path, checkpoint_filename: str) -> Path:
    candidate = Path(path)
    if candidate.is_dir():
        return candidate / checkpoint_filename
    return candidate


def create_checkpoint(
    *,
    job: ScrapeJob,
    run_id: str,
    output_dir: Path,
    csv_path: Path,
    checkpoint_path: Path,
    warnings: list[str],
) -> RunCheckpoint:
    return RunCheckpoint(
        job_name=job.name,
        job_fingerprint=job_fingerprint(job),
        run_id=run_id,
        output_dir=output_dir,
        csv_path=csv_path,
        checkpoint_path=checkpoint_path,
        warnings=list(warnings),
    )


def load_checkpoint(path: str | Path) -> RunCheckpoint:
    checkpoint_path = Path(path)
    payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    return RunCheckpoint.model_validate(payload)


def save_checkpoint(checkpoint: RunCheckpoint) -> Path:
    checkpoint.updated_at = utc_now_iso()
    checkpoint.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.checkpoint_path.write_text(
        json.dumps(checkpoint.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return checkpoint.checkpoint_path
