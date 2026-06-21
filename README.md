<div align="center">

# Google Maps CLI

**Agent-ready Google Maps scraping with tracked request workspaces, resumable runs, proxy-aware execution, and structured CSV exports.**

[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](#install)
[![CLI](https://img.shields.io/badge/interface-CLI-111111)](#cli-commands)
[![Status](https://img.shields.io/badge/status-working%20prototype-0A7F5A)](#what-you-get)
[![Tests](https://img.shields.io/badge/tests-7%20passing-1F6FEB)](#testing)

</div>

---

## Start With An Agent

If you want Codex or Claude Code to handle setup and execution, give it the repo link and this prompt:

```text
Here’s the repo: https://github.com/naveen8875/google-maps-cli-and-skill.git
Please clone it, read STARTUP.md, set it up locally, and help me run a scrape request.
```

That onboarding flow is documented in [STARTUP.md](STARTUP.md).

It tells the agent how to:

- clone the repo if needed
- install dependencies locally
- validate the environment
- bootstrap a tracked request workspace
- run or resume a scrape
- return the CSV, checkpoint, and manifest paths

If the repo is already open locally, this shorter prompt works too:

```text
Read STARTUP.md and follow it. Help me set up this repo and run a Google Maps scrape request.
```

## What This Repo Does

`google-maps-cli` turns ad hoc Google Maps scraping requests into a repeatable workflow:

**Prompt -> Request -> Job -> Run -> CSV**

Instead of asking an agent to improvise browser steps every time, this repo gives it a stable execution surface:

- guided request intake with `gmaps request start`
- reproducible YAML job files
- resumable batch runs with checkpoints
- proxy-aware execution
- richer CSV exports with business metadata
- a repo-local Codex skill in `skills/google-maps-scrape/`

## What You Get

| Area | Included |
| --- | --- |
| Intake | Interactive request bootstrap that asks for queries, proxy mode, and run behavior |
| Tracking | Per-request workspace with `REQUEST.md`, `job.yaml`, optional `env.sh`, and run artifacts |
| Execution | `gmaps scrape run` with checkpoint/resume support |
| Output | CSV rows with title, rating, category, address, hours, sponsorship, and source URL |
| Agent Support | Codex skill docs for setup, recovery, and artifact inspection |

## Quick Start

### 1. Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Validate The Machine

```bash
gmaps doctor
```

### 3. Start A Tracked Request

```bash
gmaps request start
```

That guided flow will:

1. ask for the request name and source note
2. ask for one or more search queries
3. ask how proxy handling should work
4. create a private request workspace
5. optionally start the scrape immediately

> [!TIP]
> If you are using an AI agent, prefer the `STARTUP.md` flow instead of jumping straight to manual commands.

## Request Workspace

Every guided request gets its own local operator folder:

```text
workspace/requests/<request-slug>/
├── REQUEST.md        # tracking note, commands, delivery notes
├── job.yaml          # scrape job config
├── env.sh            # optional proxy env helper
└── runs/
    └── <run-id>/
        ├── results.csv
        ├── checkpoint.json
        └── run.json
```

`REQUEST.md` is where the operator or agent should track:

- where the request came from
- which queries were used
- which run produced the final CSV
- what still needs follow-up
- what was delivered back to the user

The generated workspace is intentionally private and local. `workspace/` is ignored by git.

## Core Workflow

### Guided Intake

```bash
gmaps request start
```

### Validate Proxy Resolution

```bash
gmaps proxies resolve workspace/requests/<request-slug>/job.yaml
```

### Run

```bash
gmaps scrape run workspace/requests/<request-slug>/job.yaml
```

### Resume

```bash
gmaps scrape run workspace/requests/<request-slug>/job.yaml \
  --resume-from workspace/requests/<request-slug>/runs/<run-id>
```

## CLI Commands

| Command | Purpose |
| --- | --- |
| `gmaps request start` | Guided request intake and workspace bootstrap |
| `gmaps job init ...` | Create a job file directly without the guided flow |
| `gmaps scrape run ...` | Execute a job and write CSV/checkpoint/manifest artifacts |
| `gmaps proxies resolve ...` | Show how proxy configuration resolves for a job |
| `gmaps doctor` | Check local runtime dependencies and proxy env visibility |

## Proxy Modes

Use env mode when you want the request workspace to carry a local env helper.

Start from the root template:

```bash
cp .env.example .env
```

Use the shipped env-mode example:

```bash
gmaps scrape run examples/jobs/proxy-env.yaml
```

### Supported Today

- `direct`
- `env` via `HTTP_PROXY`, `HTTPS_PROXY`, or `ALL_PROXY`
- static unauthenticated `http`, `https`, `socks4`, and `socks5` proxy URLs

### Current Limits

- no automatic browser auth for `http://user:pass@host:port`
- no parallel workers yet
- no detail-page click-through extraction for phone, website URL, or full review counts

## Output Schema

Current CSV rows can include:

- `title`
- `rating`
- `review_count`
- `category`
- `address`
- `open_state`
- `hours_text`
- `description`
- `has_booking_link`
- `has_website_link`
- `is_sponsored`
- `url`
- `source_url`

## Examples

| Example | Use it for |
| --- | --- |
| [examples/jobs/basic-smoke.yaml](examples/jobs/basic-smoke.yaml) | Small sanity check run |
| [examples/jobs/batch-resume.yaml](examples/jobs/batch-resume.yaml) | Multi-query resumable batch |
| [examples/jobs/proxy-env.yaml](examples/jobs/proxy-env.yaml) | Env-backed proxy setup |

<details>
<summary><strong>Manual Job Mode</strong></summary>

If you want to skip the guided request flow and create a job directly:

```bash
gmaps job init workspace/requests/demo/job.yaml \
  --name demo \
  --query "dentists in Austin TX" \
  --query "orthodontists in Austin TX"
```

Then run it:

```bash
gmaps scrape run workspace/requests/demo/job.yaml
```

</details>

## Repo Layout

```text
.
├── STARTUP.md                   # agent onboarding entrypoint
├── src/gmaps_cli/               # installable Python package
│   ├── browser/                 # backend adapters
│   ├── google_maps/             # selenium scraper internals
│   ├── proxies/                 # proxy resolution
│   ├── export/                  # CSV export helpers
│   ├── request_bootstrap.py     # guided request workspace generator
│   └── checkpoints.py           # resumable run helpers
├── examples/jobs/               # shipped example job files
├── skills/google-maps-scrape/   # Codex skill for this CLI
├── tests/                       # offline tests
└── .env.example                 # proxy env template
```

## Codex Skill

The included skill at `skills/google-maps-scrape/` teaches an agent how to:

- bootstrap a request workspace
- validate job files
- run scrapes and resumes
- inspect checkpoints and manifests
- recover from proxy and scrape failures

For most users, the best v1 setup is:

1. give the agent the repo link
2. tell it to read `STARTUP.md`
3. let it use the repo-local skill from `skills/google-maps-scrape/`

## Testing

Run the offline suite:

```bash
PYTHONPATH=src python3 -m pytest
```

## Before Publishing

Choose and add the license you want to ship under. That is still intentionally open because it has real downstream implications for a public repo.
