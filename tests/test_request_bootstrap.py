from pathlib import Path

from gmaps_cli.request_bootstrap import build_request_job, write_request_workspace


def test_write_request_workspace_creates_tracking_files(tmp_path: Path) -> None:
    request_dir = tmp_path / "workspace" / "requests" / "demo-request"
    job = build_request_job(
        request_slug="demo-request",
        queries=["coffee in Austin TX"],
        proxy_mode="env",
        headless=True,
        max_results=10,
        full_scroll=True,
        continue_on_error=True,
        request_dir=request_dir,
    )

    result = write_request_workspace(
        request_name="Demo Request",
        request_slug="demo-request",
        request_dir=request_dir,
        source_note="https://example.com/ticket/123",
        queries=["coffee in Austin TX"],
        proxy_mode="env",
        job=job,
        env_values={
            "HTTP_PROXY": "http://proxy-host:9000",
            "HTTPS_PROXY": "http://proxy-host:9000",
        },
    )

    assert result.job_path.exists()
    assert result.tracker_path.exists()
    assert result.env_path is not None and result.env_path.exists()
    tracker_text = result.tracker_path.read_text(encoding="utf-8")
    assert "Demo Request" in tracker_text
    assert "coffee in Austin TX" in tracker_text
    assert "gmaps scrape run" in tracker_text
