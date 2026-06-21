# Startup

Use this file as the first operational checklist when a user gives you this repository or a GitHub link to it.

## Default User Prompt

Users should be able to say:

```text
Here’s the repo: <github-link>
Please clone it, read STARTUP.md, set it up locally, and help me run a scrape request.
```

## Mission

Set up this repository locally, verify the CLI works, bootstrap a tracked scrape request, and help the user get to a real CSV export or a clearly explained blocker.

## Operating Rules

1. Treat this repository as the source of truth.
2. Prefer the guided request workflow over ad hoc job creation.
3. Track active work inside `workspace/requests/<request-slug>/REQUEST.md`.
4. Report concrete artifact paths back to the user.
5. If network access, proxy values, or browser setup is required, handle what you can and then ask only for the missing piece.

## Fresh Clone Workflow

Use this path when the user provides a GitHub URL and the repo is not already present locally.

1. Clone the repository into the user’s chosen workspace.
2. Enter the repository root.
3. Read `README.md`.
4. Read `skills/google-maps-scrape/SKILL.md`.
5. Set up the local Python environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

6. Run the environment check:

```bash
gmaps doctor
```

7. Start the guided request workflow:

```bash
gmaps request start
```

## Already Cloned Workflow

Use this path when the repo is already open locally.

1. Read `README.md`.
2. Read `skills/google-maps-scrape/SKILL.md`.
3. Verify the environment with `gmaps doctor`.
4. Start or resume work from `workspace/requests/`.

## Request Workflow

After setup, prefer this sequence:

1. Run `gmaps request start`.
2. Let it generate:
   - `workspace/requests/<request-slug>/job.yaml`
   - `workspace/requests/<request-slug>/REQUEST.md`
   - `workspace/requests/<request-slug>/env.sh` when env-mode proxies are used
3. If a run starts successfully, note the CSV path, checkpoint path, and run manifest path.
4. If the run is interrupted, resume with:

```bash
gmaps scrape run workspace/requests/<request-slug>/job.yaml \
  --resume-from workspace/requests/<request-slug>/runs/<run-id>
```

## Tracking Expectations

Use `workspace/requests/<request-slug>/REQUEST.md` to track:

- request source or ticket link
- final query list
- proxy mode
- latest run ID
- CSV delivery path
- blockers, warnings, and follow-up notes

## Proxy Expectations

- `direct` mode is simplest when no proxy is needed.
- `env` mode is preferred when secrets should stay out of the job file.
- If `env` mode only has placeholder values, do not pretend the scrape is ready. Ask the user for real proxy values or tell them to update `env.sh`.
- Credentialed proxy URLs are not yet automated in Selenium.

## Deliverable Back To The User

When a scrape completes or pauses, return:

1. the request workspace path
2. the job file path
3. the CSV path if produced
4. the checkpoint path
5. any warnings or blockers

## If Skill Installation Comes Up

This repo already contains a local skill at `skills/google-maps-scrape/`.

- Prefer using the local skill from this repo first.
- Only install it permanently into the user’s skill system if they explicitly ask for that behavior.
