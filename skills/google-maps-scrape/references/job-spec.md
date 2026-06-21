# Job Spec

Use a job file as the source of truth for every scrape. Prefer YAML for hand-authored jobs and JSON only when another tool is generating the file.

## Required Shape

```yaml
name: dentists-austin
seeds:
  - query: dentists in Austin TX
    region: Austin, Texas
    full_scroll: true
    max_results: 100
browser:
  backend: selenium
  headless: true
proxy:
  mode: direct
output:
  directory: runs
  filename: dentists-austin.csv
  checkpoint_filename: checkpoint.json
  write_manifest: true
options:
  dedupe_by: url
  continue_on_error: false
```

## Seed Rules

- Provide `query` when the CLI should build a Google Maps search URL.
- Provide `google_maps_url` when the user already has a canonical Maps URL.
- Keep `max_results` realistic. The selenium adapter now stops scrolling when it has collected enough cards, but broad queries can still take time.
- Use `full_scroll: true` when coverage matters more than speed.

## Output Rules

- Treat `output.directory` as the parent folder for timestamped run directories.
- Expect each run to create `results.csv` or the configured filename.
- Expect each run to create `checkpoint.json` or the configured checkpoint filename.
- Expect `run.json` when `write_manifest: true`.

## Resume Workflow

- Start a batch normally:

```bash
PYTHONPATH=src python3 -m gmaps_cli scrape run examples/jobs/batch-resume.yaml
```

- Resume a partial run from the run directory:

```bash
PYTHONPATH=src python3 -m gmaps_cli scrape run examples/jobs/batch-resume.yaml \
  --resume-from runs/<run-id>
```

- Resume from a specific checkpoint file:

```bash
PYTHONPATH=src python3 -m gmaps_cli scrape run examples/jobs/batch-resume.yaml \
  --resume-from runs/<run-id>/checkpoint.json
```

- Keep the job file unchanged when resuming. The checkpoint stores a fingerprint of the original job and rejects mismatched jobs.

## Current Limitations

- Browser backend support is scaffolded, but only `selenium` is implemented.
- Unauthenticated `http`, `https`, `socks4`, and `socks5` proxy URLs can be injected into the browser session.
- Authenticated proxy URLs with embedded credentials are redacted in manifests but are not yet supported by Selenium automation in this scaffold.
- The checkpoint file currently stores the accumulated records JSON as well as progress metadata. That is simple and durable, but it is not yet optimized for huge multi-million-row runs.
- Batch jobs are supported by multiple seeds in one file, not by parallel browser workers yet.
