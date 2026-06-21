---
name: google-maps-scrape
description: Run repeatable Google Maps scraping jobs from Codex or Claude Code by authoring a job file, validating the local scraper environment, executing the `gmaps` CLI, and returning CSV artifacts. Use when an agent needs to collect business listings from Google Maps into CSV, batch multiple search queries, inspect proxy configuration, or recover from failed/empty scrape runs in this repo.
---

# Google Maps Scrape

## Overview

Use the local `gmaps` CLI as the execution surface. Convert ambiguous user requests into explicit job files, run the CLI, inspect the resulting artifact folder, and return the CSV path plus any important warnings.

## Workflow

1. Define the scrape target as a job file.
2. Validate the environment before long runs.
3. Execute the job with the CLI, not by improvising browser steps in the prompt.
4. Inspect the CSV and manifest before reporting success.

## Prepare The Job

- Read [references/job-spec.md](references/job-spec.md) when creating or repairing a job file.
- Prefer `query` seeds for normal search requests.
- Prefer `google_maps_url` seeds when the user already provides a concrete Maps URL.
- Keep the job file in the workspace so the run is reproducible.

Prefer the guided request bootstrap when starting from a fresh user request:

```bash
PYTHONPATH=src python3 -m gmaps_cli request start
```

Use the CLI to generate a starter file when it saves time:

```bash
PYTHONPATH=src python3 -m gmaps_cli job init workspace/requests/austin-dentists/job.yaml \
  --name austin-dentists \
  --query "dentists in Austin TX"
```

## Validate Before Running

- Run `PYTHONPATH=src python3 -m gmaps_cli doctor` before the first real scrape on a machine.
- Run `python3 skills/google-maps-scrape/scripts/validate_job.py <job-file>` after editing a job by hand.
- Read [references/proxy-config.md](references/proxy-config.md) when the job needs `env` or `static` proxy settings.
- Use `.env.example` and `examples/jobs/proxy-env.yaml` as the starting point for env-based proxy runs.

## Run The Scrape

Execute the job through the module path unless the package has already been installed:

```bash
PYTHONPATH=src python3 -m gmaps_cli scrape run workspace/requests/austin-dentists/job.yaml
```

Prefer the JSON form when another tool or agent needs to read the result:

```bash
PYTHONPATH=src python3 -m gmaps_cli scrape run workspace/requests/austin-dentists/job.yaml --json-output
```

Resume an interrupted batch from its checkpoint:

```bash
PYTHONPATH=src python3 -m gmaps_cli scrape run workspace/requests/austin-dentists/job.yaml \
  --resume-from runs/<run-id>
```

Expect each run to create a timestamped folder under `runs/` containing:

- the CSV export
- `checkpoint.json` with completed seeds, failed seeds, and accumulated records
- `run.json` manifest with the job definition and run summary
- warnings that should be relayed to the user

## Inspect Output

- Open the CSV path and confirm the file is non-empty.
- Open `run.json` when the scrape result looks suspicious.
- Report the artifact paths explicitly in the final answer.

## Recover From Problems

- Read [references/failure-modes.md](references/failure-modes.md) when the scrape fails, returns zero rows, or looks incomplete.
- Run `PYTHONPATH=src python3 -m gmaps_cli proxies resolve <job-file>` when the user expects proxy-backed execution.
- Treat credentialed proxy URLs as unsupported until the Selenium backend grows an auth layer.
