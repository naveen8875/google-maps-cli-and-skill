"""Click CLI for Google Maps scrape jobs."""

from __future__ import annotations

import json
from pathlib import Path

import click

from gmaps_cli.config import load_job_from_path, save_job_to_path
from gmaps_cli.doctor import run_diagnostics
from gmaps_cli.jobs import build_job_template
from gmaps_cli.proxies.manager import resolve_proxy
from gmaps_cli.request_bootstrap import (
    DEFAULT_REQUESTS_ROOT,
    apply_env_values,
    build_request_job,
    slugify,
    write_request_workspace,
)
from gmaps_cli.runner import run_job


def emit_json(payload: dict[str, object]) -> None:
    click.echo(json.dumps(payload, indent=2, default=str))


@click.group()
def cli() -> None:
    """Run Google Maps scrape jobs from repeatable config files."""


@cli.group()
def job() -> None:
    """Create and inspect job files."""


@job.command("init")
@click.argument("output_path", type=click.Path(path_type=Path))
@click.option("--name", required=True, help="Job name used for run IDs and manifests.")
@click.option(
    "--query",
    "queries",
    multiple=True,
    required=True,
    help="Search query to include. Pass multiple times for batch jobs.",
)
@click.option(
    "--filename",
    default="results.csv",
    show_default=True,
    help="CSV filename to write inside each run directory.",
)
@click.option(
    "--max-results",
    default=50,
    show_default=True,
    type=click.IntRange(1, 1000),
    help="Soft cap per query seed.",
)
@click.option(
    "--full-scroll/--no-full-scroll",
    default=True,
    show_default=True,
    help="Scroll the full search results container before collecting records.",
)
def init_job(
    output_path: Path,
    name: str,
    queries: tuple[str, ...],
    filename: str,
    max_results: int,
    full_scroll: bool,
) -> None:
    """Create a starter job file in YAML or JSON format."""
    job = build_job_template(
        name=name,
        queries=list(queries),
        output_filename=filename,
        full_scroll=full_scroll,
        max_results=max_results,
    )
    saved_path = save_job_to_path(job, output_path)
    click.echo(f"Wrote starter job to {saved_path}")


@cli.group()
def scrape() -> None:
    """Run scrape jobs."""


@scrape.command("run")
@click.argument("job_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--resume-from",
    type=click.Path(path_type=Path),
    help="Resume from an existing run directory or checkpoint file.",
)
@click.option("--json-output", is_flag=True, help="Emit machine-readable JSON.")
def scrape_run(job_path: Path, resume_from: Path | None, json_output: bool) -> None:
    """Execute a scrape job and write run artifacts."""
    job = load_job_from_path(job_path)
    summary = run_job(job, job_path=str(job_path), resume_from=resume_from)
    payload = summary.model_dump(mode="json")

    if json_output:
        emit_json(payload)
        return

    click.echo(f"Run ID: {summary.run_id}")
    click.echo(f"CSV: {summary.csv_path}")
    if summary.manifest_path:
        click.echo(f"Manifest: {summary.manifest_path}")
    if summary.checkpoint_path:
        click.echo(f"Checkpoint: {summary.checkpoint_path}")
    click.echo(f"Records written: {summary.records_written}")
    click.echo(f"Seeds total: {summary.seeds_total}")
    click.echo(f"Seeds processed this run: {summary.seeds_processed}")
    click.echo(f"Seeds skipped from checkpoint: {summary.seeds_skipped}")
    click.echo(f"Seeds still failed: {summary.seeds_failed}")
    if summary.warnings:
        click.echo("Warnings:")
        for warning in summary.warnings:
            click.echo(f"- {warning}")


@cli.group()
def proxies() -> None:
    """Inspect proxy resolution for a job."""


@proxies.command("resolve")
@click.argument("job_path", type=click.Path(exists=True, path_type=Path))
@click.option("--json-output", is_flag=True, help="Emit machine-readable JSON.")
def resolve_proxies(job_path: Path, json_output: bool) -> None:
    """Show how proxy configuration resolves for a job file."""
    job = load_job_from_path(job_path)
    payload = resolve_proxy(job).model_dump(mode="json")
    if json_output:
        emit_json(payload)
        return

    click.echo(f"Proxy mode: {payload['mode']}")
    click.echo(f"Active proxy: {payload.get('active_proxy') or 'none'}")
    click.echo(f"Browser proxy: {payload.get('browser_proxy') or 'none'}")
    click.echo(
        "Browser apply: "
        + ("yes" if payload.get("can_apply_in_browser") else "no")
    )
    if payload.get("warnings"):
        click.echo("Warnings:")
        for warning in payload["warnings"]:
            click.echo(f"- {warning}")


@cli.group()
def request() -> None:
    """Create a tracked request workspace for an operator or agent."""


@request.command("start")
@click.option(
    "--workspace-root",
    type=click.Path(path_type=Path),
    default=DEFAULT_REQUESTS_ROOT,
    show_default=True,
    help="Parent folder for generated request workspaces.",
)
def request_start(workspace_root: Path) -> None:
    """Ask setup questions, write env/job/tracker files, and optionally start the scrape."""
    click.echo("Request Setup")
    request_name = click.prompt("Request name")
    source_note = click.prompt(
        "Source note or ticket URL",
        default="",
        show_default=False,
    ).strip() or None

    queries: list[str] = []
    click.echo("Enter search queries. Submit an empty value when you are done.")
    while True:
        prompt_label = f"Query {len(queries) + 1}"
        raw_query = click.prompt(
            prompt_label,
            default="",
            show_default=False,
        ).strip()
        if not raw_query:
            if queries:
                break
            click.echo("Add at least one query.")
            continue
        queries.append(raw_query)

    proxy_mode = click.prompt(
        "Proxy mode",
        type=click.Choice(["direct", "env", "static"], case_sensitive=False),
        default="direct",
        show_default=True,
    )
    headless = click.confirm("Run headless Chrome?", default=True, show_default=True)
    full_scroll = click.confirm(
        "Scroll the full results pane?",
        default=True,
        show_default=True,
    )
    max_results = click.prompt(
        "Max results per query",
        type=click.IntRange(1, 1000),
        default=25,
        show_default=True,
    )
    continue_on_error = click.confirm(
        "Continue on seed errors?",
        default=True,
        show_default=True,
    )

    request_slug = slugify(request_name)
    request_dir = workspace_root / request_slug
    if request_dir.exists():
        overwrite = click.confirm(
            f"{request_dir} already exists. Overwrite the request files?",
            default=False,
            show_default=True,
        )
        if not overwrite:
            raise click.ClickException("Aborted to avoid overwriting an existing request workspace.")
    env_values: dict[str, str] | None = None
    runtime_env_values: dict[str, str] | None = None

    if proxy_mode == "env":
        click.echo(
            "Enter env-backed proxy values. Leave blanks if you only want placeholders."
        )
        http_proxy = click.prompt(
            "HTTP_PROXY",
            default="",
            show_default=False,
        ).strip()
        https_proxy = click.prompt(
            "HTTPS_PROXY",
            default=http_proxy,
            show_default=bool(http_proxy),
        ).strip()
        all_proxy = click.prompt(
            "ALL_PROXY",
            default="",
            show_default=False,
        ).strip()
        no_proxy = click.prompt(
            "NO_PROXY",
            default="localhost,127.0.0.1",
            show_default=True,
        ).strip()
        runtime_env_values = {
            key: value
            for key, value in {
                "HTTP_PROXY": http_proxy,
                "HTTPS_PROXY": https_proxy,
                "ALL_PROXY": all_proxy,
                "NO_PROXY": no_proxy,
            }.items()
            if value
        }
        env_values = runtime_env_values or {
            "HTTP_PROXY": "http://proxy-host:9000",
            "HTTPS_PROXY": "http://proxy-host:9000",
            "NO_PROXY": "localhost,127.0.0.1",
        }

    if proxy_mode == "static":
        click.echo("Static proxy URLs must be unauthenticated for Selenium.")
        static_proxy = click.prompt(
            "Proxy URL",
            default="http://proxy-host:9000",
            show_default=True,
        ).strip()
    else:
        static_proxy = None

    job = build_request_job(
        request_slug=request_slug,
        queries=queries,
        proxy_mode=proxy_mode,
        headless=headless,
        max_results=max_results,
        full_scroll=full_scroll,
        continue_on_error=continue_on_error,
        request_dir=request_dir,
    )
    if static_proxy:
        job.proxy.https_url = static_proxy

    result = write_request_workspace(
        request_name=request_name,
        request_slug=request_slug,
        request_dir=request_dir,
        source_note=source_note,
        queries=queries,
        proxy_mode=proxy_mode,
        job=job,
        env_values=env_values,
    )

    click.echo(f"Workspace: {result.request_dir}")
    click.echo(f"Job: {result.job_path}")
    click.echo(f"Tracker: {result.tracker_path}")
    if result.env_path:
        click.echo(f"Env helper: {result.env_path}")

    start_now = click.confirm(
        "Start the scrape now?",
        default=False,
        show_default=True,
    )
    if not start_now:
        click.echo("Next steps")
        if result.env_path:
            click.echo(f"- source {result.env_path}")
        click.echo("- gmaps doctor")
        click.echo(f"- gmaps proxies resolve {result.job_path}")
        click.echo(f"- gmaps scrape run {result.job_path}")
        return

    if proxy_mode == "env" and not runtime_env_values:
        raise click.ClickException(
            "Cannot start env-mode scraping immediately because only placeholder env values were written. "
            f"Edit and source {result.env_path} first, then run the scrape command."
        )

    apply_env_values(runtime_env_values)
    job_path = result.job_path
    summary = run_job(job, job_path=str(job_path))
    result = write_request_workspace(
        request_name=request_name,
        request_slug=request_slug,
        request_dir=request_dir,
        source_note=source_note,
        queries=queries,
        proxy_mode=proxy_mode,
        job=job,
        env_values=env_values,
        run_summary=summary,
    )
    click.echo(f"Run ID: {summary.run_id}")
    click.echo(f"CSV: {summary.csv_path}")
    click.echo(f"Checkpoint: {summary.checkpoint_path}")
    click.echo(f"Updated tracker: {result.tracker_path}")


@cli.command()
@click.option("--json-output", is_flag=True, help="Emit machine-readable JSON.")
def doctor(json_output: bool) -> None:
    """Print environment diagnostics for the scraper stack."""
    payload = run_diagnostics()
    if json_output:
        emit_json(payload)
        return

    click.echo("Environment")
    click.echo(f"- Python: {payload['python_version']}")
    click.echo(f"- Platform: {payload['platform']}")
    click.echo("Modules")
    for name, present in payload["modules"].items():
        click.echo(f"- {name}: {'ok' if present else 'missing'}")
