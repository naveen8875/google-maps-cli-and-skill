"""Interactive request bootstrap helpers."""

from __future__ import annotations

import os
import re

from dataclasses import dataclass
from pathlib import Path

from gmaps_cli.config import save_job_to_path
from gmaps_cli.models import ScrapeJob, RunSummary, utc_now_iso


DEFAULT_REQUESTS_ROOT = Path("workspace/requests")


@dataclass
class RequestBootstrapResult:
    request_name: str
    request_slug: str
    request_dir: Path
    job_path: Path
    tracker_path: Path
    env_path: Path | None
    run_summary: RunSummary | None = None


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "request"


def build_request_job(
    *,
    request_slug: str,
    queries: list[str],
    proxy_mode: str,
    headless: bool,
    max_results: int,
    full_scroll: bool,
    continue_on_error: bool,
    request_dir: Path,
) -> ScrapeJob:
    seeds = [
        {
            "query": query,
            "full_scroll": full_scroll,
            "max_results": max_results,
        }
        for query in queries
    ]
    return ScrapeJob(
        name=request_slug,
        seeds=seeds,
        browser={"headless": headless},
        proxy={"mode": proxy_mode},
        output={
            "directory": request_dir / "runs",
            "filename": f"{request_slug}.csv",
            "checkpoint_filename": "checkpoint.json",
            "write_manifest": True,
        },
        options={"continue_on_error": continue_on_error},
    )


def render_env_script(values: dict[str, str]) -> str:
    lines = [
        "#!/usr/bin/env bash",
        "# Load proxy variables for this request.",
        "",
    ]
    for key, value in values.items():
        escaped = value.replace('"', '\\"')
        lines.append(f'export {key}="{escaped}"')
    lines.append("")
    return "\n".join(lines)


def render_tracker_markdown(
    *,
    request_name: str,
    request_slug: str,
    source_note: str | None,
    queries: list[str],
    proxy_mode: str,
    request_dir: Path,
    job_path: Path,
    env_path: Path | None,
    run_summary: RunSummary | None,
) -> str:
    command_lines = []
    if env_path:
        command_lines.append(f"source {env_path}")
    command_lines.extend(
        [
            "gmaps doctor",
            f"gmaps proxies resolve {job_path}",
            f"gmaps scrape run {job_path}",
        ]
    )
    if run_summary:
        command_lines.append(
            f"gmaps scrape run {job_path} --resume-from {run_summary.output_dir}"
        )

    latest_run = [
        "## Latest Run",
        "",
    ]
    if run_summary:
        latest_run.extend(
            [
                f"- Run ID: `{run_summary.run_id}`",
                f"- CSV: `{run_summary.csv_path}`",
                f"- Checkpoint: `{run_summary.checkpoint_path}`",
                f"- Records written: `{run_summary.records_written}`",
                f"- Seeds processed this run: `{run_summary.seeds_processed}`",
                f"- Seeds skipped from checkpoint: `{run_summary.seeds_skipped}`",
                f"- Seeds still failed: `{run_summary.seeds_failed}`",
                "",
            ]
        )
    else:
        latest_run.extend(
            [
                "- Status: `not started`",
                "",
            ]
        )

    lines = [
        f"# Request Tracker: {request_name}",
        "",
        f"- Created: `{utc_now_iso()}`",
        f"- Request slug: `{request_slug}`",
        f"- Workspace: `{request_dir}`",
        f"- Job file: `{job_path}`",
        f"- Proxy mode: `{proxy_mode}`",
    ]
    if source_note:
        lines.append(f"- Source: {source_note}")
    if env_path:
        lines.append(f"- Env helper: `{env_path}`")
    lines.extend(
        [
            "",
            "## Queries",
            "",
            *[f"- {query}" for query in queries],
            "",
            "## Suggested Workflow",
            "",
            "1. Load any request-specific env vars.",
            "2. Run `gmaps doctor` once on the machine.",
            "3. Resolve proxy settings before large runs.",
            "4. Start the scrape and keep the run directory for resumes.",
            "5. Update this tracker with outcomes, blockers, and delivery notes.",
            "",
            "## Commands",
            "",
            "```bash",
            *command_lines,
            "```",
            "",
            *latest_run,
            "## Delivery Notes",
            "",
            "- CSV delivered:",
            "- User-facing summary:",
            "- Follow-up needed:",
            "",
            "## Operator Notes",
            "",
            "-",
            "",
        ]
    )
    return "\n".join(lines)


def write_request_workspace(
    *,
    request_name: str,
    request_slug: str,
    request_dir: Path,
    source_note: str | None,
    queries: list[str],
    proxy_mode: str,
    job: ScrapeJob,
    env_values: dict[str, str] | None,
    run_summary: RunSummary | None = None,
) -> RequestBootstrapResult:
    request_dir.mkdir(parents=True, exist_ok=True)
    job_path = save_job_to_path(job, request_dir / "job.yaml")

    env_path: Path | None = None
    if env_values:
        env_path = request_dir / "env.sh"
        env_path.write_text(render_env_script(env_values), encoding="utf-8")
        env_path.chmod(0o755)

    tracker_path = request_dir / "REQUEST.md"
    tracker_path.write_text(
        render_tracker_markdown(
            request_name=request_name,
            request_slug=request_slug,
            source_note=source_note,
            queries=queries,
            proxy_mode=proxy_mode,
            request_dir=request_dir,
            job_path=job_path,
            env_path=env_path,
            run_summary=run_summary,
        ),
        encoding="utf-8",
    )

    return RequestBootstrapResult(
        request_name=request_name,
        request_slug=request_slug,
        request_dir=request_dir,
        job_path=job_path,
        tracker_path=tracker_path,
        env_path=env_path,
        run_summary=run_summary,
    )


def apply_env_values(values: dict[str, str] | None) -> None:
    if not values:
        return
    for key, value in values.items():
        os.environ[key] = value
