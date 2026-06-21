"""Helpers for creating and normalizing scrape jobs."""

from __future__ import annotations

from urllib.parse import quote_plus

from gmaps_cli.models import QuerySeed, ScrapeJob


def build_google_maps_search_url(query: str) -> str:
    return f"https://www.google.com/maps/search/{quote_plus(query)}"


def materialize_seed(seed: QuerySeed) -> QuerySeed:
    if seed.google_maps_url:
        return seed

    return seed.model_copy(
        update={"google_maps_url": build_google_maps_search_url(seed.query or "")}
    )


def build_job_template(
    *,
    name: str,
    queries: list[str],
    output_filename: str,
    full_scroll: bool,
    max_results: int,
) -> ScrapeJob:
    seeds = [
        QuerySeed(
            query=query,
            full_scroll=full_scroll,
            max_results=max_results,
        )
        for query in queries
    ]
    return ScrapeJob(
        name=name,
        seeds=seeds,
        output={"filename": output_filename},
    )
