#!/usr/bin/env python3
"""Validate a scrape job file using the local CLI models."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_job.py <job-file>")
        return 1

    repo_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo_root / "src"))

    from gmaps_cli.config import load_job_from_path  # noqa: PLC0415

    job = load_job_from_path(sys.argv[1])
    payload = {
        "name": job.name,
        "seeds": len(job.seeds),
        "backend": job.browser.backend,
        "proxy_mode": job.proxy.mode,
        "output_directory": str(job.output.directory),
        "output_filename": job.output.filename,
        "checkpoint_filename": job.output.checkpoint_filename,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
