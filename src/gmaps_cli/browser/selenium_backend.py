"""Selenium-backed adapter around the package-local Google Maps scraper."""

from __future__ import annotations

from gmaps_cli.google_maps.selenium_scraper import GoogleMapsScraper
from gmaps_cli.jobs import materialize_seed
from gmaps_cli.models import LocationRecord, QuerySeed, ResolvedProxy, ScrapeJob


class SeleniumMapsBackend:
    def __init__(self, job: ScrapeJob, proxy: ResolvedProxy) -> None:
        self._scraper = GoogleMapsScraper(
            headless=job.browser.headless,
            proxy_server=proxy.browser_proxy if proxy.can_apply_in_browser else None,
        )

    def scrape_seed(self, seed: QuerySeed) -> list[LocationRecord]:
        hydrated_seed = materialize_seed(seed)
        items = self._scraper.get_maps_data(
            hydrated_seed.google_maps_url or "",
            hydrated_seed.full_scroll,
            hydrated_seed.max_results,
        )

        records = [
            LocationRecord(
                title=item.title,
                rating=item.rating,
                review_count=item.review_count,
                category=item.category,
                address=item.address,
                open_state=item.open_state,
                hours_text=item.hours_text,
                description=item.description,
                has_booking_link=item.has_booking_link,
                has_website_link=item.has_website_link,
                is_sponsored=item.is_sponsored,
                url=item.url,
                query=hydrated_seed.query,
                region=hydrated_seed.region,
                source_url=hydrated_seed.google_maps_url or "",
            )
            for item in items
        ]
        return records
