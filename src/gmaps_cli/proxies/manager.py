"""Resolve proxy configuration for scrape jobs."""

from __future__ import annotations

import os
from urllib.parse import SplitResult, urlsplit, urlunsplit

from gmaps_cli.models import ResolvedProxy, ScrapeJob


ENV_PROXY_KEYS = ["HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY"]
SUPPORTED_PROXY_SCHEMES = {"http", "https", "socks4", "socks5"}


def _get_env_proxy_values() -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    for key in ENV_PROXY_KEYS:
        raw = os.getenv(key) or os.getenv(key.lower())
        if raw:
            values.append((key, raw))
    return values


def _redact_proxy_url(url: str) -> str:
    parsed = urlsplit(url)
    if not parsed.username and not parsed.password:
        return url

    hostname = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    username = "***" if parsed.username else ""
    password = ":***" if parsed.password else ""
    auth = f"{username}{password}@"
    netloc = f"{auth}{hostname}{port}"
    return urlunsplit(
        SplitResult(
            scheme=parsed.scheme,
            netloc=netloc,
            path=parsed.path,
            query=parsed.query,
            fragment=parsed.fragment,
        )
    )


def _build_browser_proxy(parsed_url: SplitResult) -> str | None:
    if not parsed_url.scheme or not parsed_url.hostname:
        return None

    hostname = parsed_url.hostname
    port = f":{parsed_url.port}" if parsed_url.port else ""
    return urlunsplit(
        SplitResult(
            scheme=parsed_url.scheme,
            netloc=f"{hostname}{port}",
            path="",
            query="",
            fragment="",
        )
    )


def resolve_proxy(job: ScrapeJob) -> ResolvedProxy:
    if job.proxy.mode == "direct":
        return ResolvedProxy(mode="direct")

    if job.proxy.mode == "env":
        env_values = _get_env_proxy_values()
        if not env_values:
            return ResolvedProxy(
                mode="env",
                warnings=[
                    "Proxy mode is set to env, but no HTTP_PROXY, HTTPS_PROXY, or ALL_PROXY value is available."
                ],
            )
        source, raw_url = env_values[0]
    else:
        source = "static"
        raw_url = (
            job.proxy.https_url or job.proxy.http_url or job.proxy.socks_url or ""
        )

    warnings: list[str] = []
    parsed = urlsplit(raw_url)
    scheme = parsed.scheme.lower() if parsed.scheme else None
    has_credentials = bool(parsed.username or parsed.password)
    browser_proxy = _build_browser_proxy(parsed)
    can_apply_in_browser = browser_proxy is not None and not has_credentials

    if not scheme or scheme not in SUPPORTED_PROXY_SCHEMES:
        warnings.append(
            "Proxy URL must include a supported scheme: http, https, socks4, or socks5."
        )

    if has_credentials:
        warnings.append(
            "Authenticated proxy URLs are redacted in manifests, but automatic proxy auth is not wired into Selenium yet."
        )

    if browser_proxy is None:
        warnings.append("Proxy URL is missing a hostname or cannot be translated for Chrome.")

    return ResolvedProxy(
        mode=job.proxy.mode,
        source=source,
        active_proxy=_redact_proxy_url(raw_url),
        browser_proxy=browser_proxy,
        scheme=scheme,
        has_credentials=has_credentials,
        is_configured=bool(raw_url),
        can_apply_in_browser=can_apply_in_browser and not warnings,
        warnings=warnings,
    )
