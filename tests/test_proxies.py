from gmaps_cli.models import ProxyConfig, ScrapeJob, QuerySeed
from gmaps_cli.proxies.manager import resolve_proxy


def make_job(proxy: ProxyConfig) -> ScrapeJob:
    return ScrapeJob(
        name="proxy-test",
        seeds=[QuerySeed(query="coffee in Austin TX")],
        proxy=proxy,
    )


def test_resolve_direct_proxy() -> None:
    resolved = resolve_proxy(make_job(ProxyConfig(mode="direct")))

    assert resolved.mode == "direct"
    assert resolved.active_proxy is None
    assert resolved.can_apply_in_browser is False


def test_resolve_static_proxy_without_credentials() -> None:
    resolved = resolve_proxy(
        make_job(
            ProxyConfig(
                mode="static",
                https_url="http://proxy-host:9000",
            )
        )
    )

    assert resolved.active_proxy == "http://proxy-host:9000"
    assert resolved.browser_proxy == "http://proxy-host:9000"
    assert resolved.can_apply_in_browser is True


def test_resolve_static_proxy_with_credentials_is_redacted() -> None:
    resolved = resolve_proxy(
        make_job(
            ProxyConfig(
                mode="static",
                https_url="http://user:pass@proxy-host:9000",
            )
        )
    )

    assert resolved.active_proxy == "http://***:***@proxy-host:9000"
    assert resolved.browser_proxy == "http://proxy-host:9000"
    assert resolved.can_apply_in_browser is False
    assert resolved.has_credentials is True
