"""Run scrape jobs and persist artifacts."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from gmaps_cli.browser.selenium_backend import SeleniumMapsBackend
from gmaps_cli.checkpoints import (
    create_checkpoint,
    job_fingerprint,
    load_checkpoint,
    resolve_checkpoint_path,
    save_checkpoint,
    seed_key,
)
from gmaps_cli.export.csv_exporter import export_records
from gmaps_cli.models import (
    LocationRecord,
    ResolvedProxy,
    RunCheckpoint,
    RunSummary,
    ScrapeJob,
)
from gmaps_cli.proxies.manager import resolve_proxy


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "job"


def build_run_id(job_name: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{slugify(job_name)}-{timestamp}"


def _validate_proxy_for_runtime(proxy: ResolvedProxy) -> None:
    if proxy.mode == "direct":
        return

    if not proxy.is_configured:
        raise ValueError("Proxy mode was requested, but no proxy value could be resolved.")

    if not proxy.can_apply_in_browser:
        warning_text = "; ".join(proxy.warnings) or "Unsupported proxy configuration."
        raise ValueError(f"Cannot apply proxy settings in the browser: {warning_text}")


def _make_backend(job: ScrapeJob, proxy: ResolvedProxy) -> SeleniumMapsBackend:
    _validate_proxy_for_runtime(proxy)
    if job.browser.backend == "selenium":
        return SeleniumMapsBackend(job, proxy)
    raise ValueError(f"Unsupported browser backend: {job.browser.backend}")


def _dedupe_records(records: list[LocationRecord], mode: str) -> list[LocationRecord]:
    if mode == "none":
        return records

    seen: set[str] = set()
    unique: list[LocationRecord] = []
    for record in records:
        key = record.url if mode == "url" else record.title
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique


def _write_manifest(
    job: ScrapeJob,
    summary: RunSummary,
    job_path: str | None,
    proxy_state: dict[str, object],
) -> Path:
    manifest_path = summary.output_dir / "run.json"
    summary.manifest_path = manifest_path
    payload = {
        "job_path": job_path,
        "job": job.model_dump(mode="json"),
        "summary": summary.model_dump(mode="json"),
        "proxy_state": proxy_state,
    }
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def _dedupe_warning_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _load_or_create_checkpoint(
    job: ScrapeJob,
    *,
    resume_from: str | Path | None,
    initial_warnings: list[str],
) -> tuple[RunCheckpoint, Path | None]:
    if resume_from:
        checkpoint_path = resolve_checkpoint_path(
            resume_from, job.output.checkpoint_filename
        )
        checkpoint = load_checkpoint(checkpoint_path)
        expected_fingerprint = job_fingerprint(job)
        if checkpoint.job_fingerprint != expected_fingerprint:
            raise ValueError(
                "Checkpoint job fingerprint does not match the current job file."
            )
        checkpoint.warnings = _dedupe_warning_list(
            [*checkpoint.warnings, *initial_warnings]
        )
        return checkpoint, checkpoint_path

    run_id = build_run_id(job.name)
    output_dir = Path(job.output.directory) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / job.output.filename
    checkpoint_path = output_dir / job.output.checkpoint_filename
    checkpoint = create_checkpoint(
        job=job,
        run_id=run_id,
        output_dir=output_dir,
        csv_path=csv_path,
        checkpoint_path=checkpoint_path,
        warnings=initial_warnings,
    )
    save_checkpoint(checkpoint)
    return checkpoint, None


def _update_checkpoint_snapshot(
    checkpoint: RunCheckpoint,
    *,
    records: list[LocationRecord],
    warnings: list[str],
) -> None:
    checkpoint.records = records
    checkpoint.warnings = _dedupe_warning_list(warnings)
    export_records(records, checkpoint.csv_path)
    save_checkpoint(checkpoint)


def run_job(
    job: ScrapeJob,
    job_path: str | None = None,
    *,
    resume_from: str | Path | None = None,
) -> RunSummary:
    proxy_state = resolve_proxy(job)
    backend = _make_backend(job, proxy_state)
    checkpoint, resumed_from = _load_or_create_checkpoint(
        job,
        resume_from=resume_from,
        initial_warnings=list(proxy_state.warnings),
    )

    warnings = list(checkpoint.warnings)
    records = list(checkpoint.records)
    processed_count = 0
    skipped_count = 0

    for seed in job.seeds:
        current_seed_key = seed_key(seed)
        if current_seed_key in checkpoint.completed_seed_keys:
            skipped_count += 1
            continue

        try:
            records.extend(backend.scrape_seed(seed))
            records = _dedupe_records(records, job.options.dedupe_by)
            checkpoint.completed_seed_keys.append(current_seed_key)
            checkpoint.completed_seed_keys = list(dict.fromkeys(checkpoint.completed_seed_keys))
            checkpoint.seed_errors.pop(current_seed_key, None)
            checkpoint.failed_seed_keys = [
                key for key in checkpoint.failed_seed_keys if key != current_seed_key
            ]
            processed_count += 1
            _update_checkpoint_snapshot(
                checkpoint,
                records=records,
                warnings=warnings,
            )
        except Exception as exc:
            checkpoint.seed_errors[current_seed_key] = str(exc)
            if current_seed_key not in checkpoint.failed_seed_keys:
                checkpoint.failed_seed_keys.append(current_seed_key)
            if job.options.continue_on_error:
                warnings.append(f"Seed failed and was skipped: {exc}")
                processed_count += 1
                _update_checkpoint_snapshot(
                    checkpoint,
                    records=_dedupe_records(records, job.options.dedupe_by),
                    warnings=warnings,
                )
                continue
            _update_checkpoint_snapshot(
                checkpoint,
                records=_dedupe_records(records, job.options.dedupe_by),
                warnings=warnings,
            )
            raise

    records = _dedupe_records(records, job.options.dedupe_by)
    _update_checkpoint_snapshot(checkpoint, records=records, warnings=warnings)

    summary = RunSummary(
        job_name=job.name,
        run_id=checkpoint.run_id,
        output_dir=checkpoint.output_dir,
        csv_path=checkpoint.csv_path,
        records_written=len(records),
        seeds_total=len(job.seeds),
        seeds_processed=processed_count,
        seeds_skipped=skipped_count,
        seeds_failed=len(checkpoint.failed_seed_keys),
        resumed_from=Path(resume_from) if resume_from else resumed_from,
        checkpoint_path=checkpoint.checkpoint_path,
        warnings=_dedupe_warning_list(warnings),
    )

    if job.output.write_manifest:
        summary.manifest_path = _write_manifest(
            job,
            summary,
            job_path,
            proxy_state.model_dump(mode="json"),
        )

    return summary
