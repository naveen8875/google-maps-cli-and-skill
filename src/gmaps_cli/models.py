"""Pydantic models for job definitions and run outputs."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator


ProxyMode = Literal["direct", "env", "static"]
BrowserBackend = Literal["selenium"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class QuerySeed(BaseModel):
    query: str | None = None
    google_maps_url: str | None = None
    region: str | None = None
    full_scroll: bool = True
    max_results: int = Field(default=50, ge=1, le=1000)

    @model_validator(mode="after")
    def validate_query_source(self) -> "QuerySeed":
        if not self.query and not self.google_maps_url:
            raise ValueError("Each seed must include either query or google_maps_url.")
        return self


class BrowserSettings(BaseModel):
    backend: BrowserBackend = "selenium"
    headless: bool = True


class ProxyConfig(BaseModel):
    mode: ProxyMode = "direct"
    http_url: str | None = None
    https_url: str | None = None
    socks_url: str | None = None

    @model_validator(mode="after")
    def validate_static_proxy(self) -> "ProxyConfig":
        if self.mode == "static" and not any(
            [self.http_url, self.https_url, self.socks_url]
        ):
            raise ValueError(
                "Static proxy mode requires one of http_url, https_url, or socks_url."
            )
        return self


class OutputSettings(BaseModel):
    directory: Path = Path("runs")
    filename: str = "results.csv"
    checkpoint_filename: str = "checkpoint.json"
    write_manifest: bool = True


class RunOptions(BaseModel):
    dedupe_by: Literal["url", "title", "none"] = "url"
    continue_on_error: bool = False


class ScrapeJob(BaseModel):
    name: str = Field(min_length=3, max_length=80)
    seeds: list[QuerySeed]
    browser: BrowserSettings = BrowserSettings()
    proxy: ProxyConfig = ProxyConfig()
    output: OutputSettings = OutputSettings()
    options: RunOptions = RunOptions()
    created_at: str = Field(default_factory=utc_now_iso)

    @model_validator(mode="after")
    def validate_seeds(self) -> "ScrapeJob":
        if not self.seeds:
            raise ValueError("A job must define at least one seed.")
        return self


class LocationRecord(BaseModel):
    title: str
    rating: str | None = None
    review_count: int | None = None
    category: str | None = None
    address: str | None = None
    open_state: str | None = None
    hours_text: str | None = None
    description: str | None = None
    has_booking_link: bool = False
    has_website_link: bool = False
    is_sponsored: bool = False
    url: str
    query: str | None = None
    region: str | None = None
    source_url: str
    scraped_at: str = Field(default_factory=utc_now_iso)


class RunSummary(BaseModel):
    job_name: str
    run_id: str
    output_dir: Path
    csv_path: Path
    records_written: int
    seeds_total: int
    seeds_processed: int
    seeds_skipped: int = 0
    seeds_failed: int = 0
    resumed_from: Path | None = None
    checkpoint_path: Path | None = None
    warnings: list[str] = Field(default_factory=list)
    manifest_path: Path | None = None


class ResolvedProxy(BaseModel):
    mode: ProxyMode
    source: str | None = None
    active_proxy: str | None = None
    browser_proxy: str | None = None
    scheme: str | None = None
    has_credentials: bool = False
    is_configured: bool = False
    can_apply_in_browser: bool = False
    warnings: list[str] = Field(default_factory=list)


class RunCheckpoint(BaseModel):
    job_name: str
    job_fingerprint: str
    run_id: str
    output_dir: Path
    csv_path: Path
    checkpoint_path: Path
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    completed_seed_keys: list[str] = Field(default_factory=list)
    failed_seed_keys: list[str] = Field(default_factory=list)
    seed_errors: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    records: list[LocationRecord] = Field(default_factory=list)
