# Failure Modes

Read this file when a run exits non-zero, returns zero records, or produces a partial CSV.

## Common Cases

### Driver setup fails

- Run `gmaps doctor`.
- Confirm Chrome is installed locally.
- Confirm Python dependencies are installed.

### Empty CSV

- Inspect the generated `run.json` manifest.
- Re-run with a direct `google_maps_url` seed if a query-generated URL is suspicious.
- Check whether Google changed result card selectors in the selenium adapter.

### Partial results

- Set `full_scroll: true`.
- Increase `max_results`.
- Split very large batches into multiple job files for easier retries.
- Resume interrupted runs with `--resume-from runs/<run-id>` instead of restarting the full batch.

### Proxy confusion

- Run `gmaps proxies resolve job.yaml`.
- If `mode: env`, verify the shell session actually exports `HTTP_PROXY`, `HTTPS_PROXY`, or `ALL_PROXY`.
- If the proxy URL includes `user:pass@`, expect the CLI to reject it before browser startup.
- Confirm the resolved output says `Browser apply: yes` before long runs.
