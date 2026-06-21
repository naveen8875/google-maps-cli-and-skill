# Proxy Config

The CLI can now inject unauthenticated proxy URLs into the Selenium Chrome session. Proxy values are redacted in manifests and `gmaps proxies resolve` output when credentials are embedded.

## Modes

### `direct`

Use no proxy.

```yaml
proxy:
  mode: direct
```

### `env`

Resolve the proxy from environment variables at runtime.

Supported variables:

- `HTTP_PROXY`
- `HTTPS_PROXY`
- `ALL_PROXY`
- `NO_PROXY`

```yaml
proxy:
  mode: env
```

Use `gmaps proxies resolve job.yaml` to confirm what the CLI sees.
If no proxy environment variables are present, the scrape run fails fast instead of silently falling back to direct traffic.

Example shell usage:

```bash
cp .env.example .env
export HTTP_PROXY=http://proxy-host:9000
export HTTPS_PROXY=http://proxy-host:9000
PYTHONPATH=src python3 -m gmaps_cli scrape run examples/jobs/proxy-env.yaml
```

### `static`

Store explicit proxy URLs in the job file.

```yaml
proxy:
  mode: static
  https_url: http://proxy-host:9000
```

## Operator Guidance

- Prefer `env` mode for local development so secrets stay out of the repo.
- Prefer `static` mode only for generated ephemeral job files or secret-managed workspaces.
- Prefer proxy URLs without embedded credentials for now. Example: `http://proxy-host:9000` or `socks5://proxy-host:1080`.
- Treat embedded `user:pass@host:port` proxy URLs as unsupported in Selenium until a browser auth layer is added.
- Use `gmaps proxies resolve job.yaml` before running large jobs to confirm the browser-usable proxy value.
