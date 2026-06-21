"""Google Maps selenium scraper implementation."""

from __future__ import annotations

import logging
import os
import re
import time

from contextlib import suppress
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from gmaps_cli.google_maps.models import Location


logging.getLogger("WDM").setLevel(logging.ERROR)


class ConsentFormAcceptError(Exception):
    """Raised when Google consent handling fails."""


class DriverInitializationError(Exception):
    """Raised when ChromeDriver cannot be started."""


class DriverGetMapsDataError(Exception):
    """Raised when Google Maps listings cannot be collected."""


class GoogleMapsScraper:
    """Scrape Google Maps result cards with Selenium."""

    def __init__(
        self,
        logger: logging.Logger | None = None,
        *,
        headless: bool = True,
        proxy_server: str | None = None,
    ) -> None:
        self._logger = logger if logger else logging.getLogger(__name__)
        self._headless = headless
        self._proxy_server = proxy_server
        self._consent_button_xpath = (
            "/html/body/c-wiz/div/div/div/div[2]/div[1]/div[3]/div[1]/div[1]/form[2]/div/div/button/span"
        )

    def _resolve_chromedriver_binary(self, driver_path: str) -> str:
        candidate = Path(driver_path)
        if candidate.name == "chromedriver":
            return str(candidate)

        sibling = candidate.with_name("chromedriver")
        if sibling.exists():
            return str(sibling)

        for path in candidate.parent.iterdir():
            if path.is_file() and path.name == "chromedriver":
                return str(path)

        return driver_path

    def _init_chrome_driver(self) -> webdriver.Chrome:
        chrome_options = Options()
        if self._headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        if self._proxy_server:
            chrome_options.add_argument(f"--proxy-server={self._proxy_server}")
        driver_path = ChromeDriverManager().install()
        binary_path = self._resolve_chromedriver_binary(driver_path)
        os.chmod(binary_path, 0o755)
        service = Service(binary_path)
        return webdriver.Chrome(service=service, options=chrome_options)

    def _click_consent_button(self, driver: webdriver.Chrome, url: str) -> None:
        self._logger.info("Accepting consent form..")
        try:
            driver.get(url)
            consent_button = driver.find_element(
                By.XPATH,
                self._consent_button_xpath,
            )
            consent_button.click()
        except NoSuchElementException:
            self._logger.warning("Consent form button not found.")
        except Exception as exc:
            raise ConsentFormAcceptError from exc

        time.sleep(2)

    def _normalize_text(self, value: str) -> str:
        return " ".join(value.replace("\u202f", " ").split()).strip()

    def _clean_segments(self, value: str) -> list[str]:
        segments = [self._normalize_text(part) for part in value.split("·")]
        return [segment for segment in segments if any(char.isalnum() for char in segment)]

    def _parse_rating_value(self, value: str | None) -> str | None:
        if not value:
            return None

        match = re.search(r"([0-9]+(?:\.[0-9]+)?)", value)
        return match.group(1) if match else self._normalize_text(value)

    def _parse_review_count(self, lines: list[str]) -> int | None:
        for line in lines:
            match = re.search(r"\(([0-9][0-9,]*)\)", line)
            if match:
                return int(match.group(1).replace(",", ""))
        return None

    def _parse_category_and_address(self, lines: list[str]) -> tuple[str | None, str | None]:
        for line in lines:
            if "·" not in line:
                continue
            if "Open" in line or "Closed" in line or "Closes" in line or "Opens" in line:
                continue

            segments = self._clean_segments(line)
            if not segments:
                continue

            category = segments[0] if segments else None
            address = segments[-1] if len(segments) > 1 else None
            if category or address:
                return category, address

        return None, None

    def _parse_open_state(self, lines: list[str]) -> tuple[str | None, str | None]:
        for line in lines:
            normalized = self._normalize_text(line)
            if not normalized:
                continue

            if normalized.startswith(("Open", "Closed", "Temporarily closed")):
                segments = self._clean_segments(normalized)
                open_state = segments[0] if segments else normalized
                hours_text = " · ".join(segments[1:]) if len(segments) > 1 else None
                return open_state, hours_text

        return None, None

    def _parse_description(self, lines: list[str], title: str) -> str | None:
        action_lines = {"Visit site", "Book online", "Directions", "Call", "Website"}
        skip_prefixes = ("Open", "Closed", "Temporarily closed")
        for line in lines:
            normalized = self._normalize_text(line)
            if (
                not normalized
                or not any(char.isalnum() for char in normalized)
                or normalized == "Sponsored"
                or normalized == title
                or normalized in action_lines
                or normalized.startswith(skip_prefixes)
                or normalized.replace(".", "", 1).isdigit()
                or "·" in normalized
            ):
                continue
            return normalized
        return None

    def _collect_card_lines(self, div: webdriver.Chrome) -> list[str]:
        return [
            self._normalize_text(line)
            for line in div.text.splitlines()
            if self._normalize_text(line)
        ]

    def _scroll_results_container(
        self,
        driver: webdriver.Chrome,
        container: webdriver.Chrome,
        max_results: int | None = None,
        max_scroll_passes: int = 200,
    ) -> None:
        last_height = driver.execute_script(
            "return arguments[0].scrollHeight", container
        )

        for _ in range(max_scroll_passes):
            if max_results:
                current_count = len(driver.find_elements(By.CLASS_NAME, "Nv2PK"))
                if current_count >= max_results:
                    break

            driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight", container
            )
            time.sleep(2)
            new_height = driver.execute_script(
                "return arguments[0].scrollHeight", container
            )
            if new_height == last_height:
                break
            last_height = new_height

    def _get_data_from_location_div(self, div: webdriver.Chrome) -> Location:
        title_element = div.find_element(By.CLASS_NAME, "hfpxzc")
        title = title_element.get_attribute("aria-label")
        url = title_element.get_attribute("href")
        lines = self._collect_card_lines(div)

        rating_aria = None
        with suppress(NoSuchElementException):
            rating_aria = div.find_element(By.CLASS_NAME, "ZkP5Je").get_attribute(
                "aria-label"
            )

        category, address = self._parse_category_and_address(lines)
        open_state, hours_text = self._parse_open_state(lines)
        description = self._parse_description(lines, title)

        return Location(
            title=title,
            rating=self._parse_rating_value(rating_aria),
            review_count=self._parse_review_count(lines),
            category=category,
            address=address,
            open_state=open_state,
            hours_text=hours_text,
            description=description,
            has_booking_link="Book online" in lines,
            has_website_link="Visit site" in lines or "Website" in lines,
            is_sponsored=bool(lines and lines[0] == "Sponsored"),
            url=url,
        )

    def _get_locations_from_page(
        self,
        url: str,
        driver: webdriver.Chrome,
        full: bool | None = False,
        max_results: int | None = None,
    ) -> list[Location]:
        driver.get(url)
        time.sleep(2)

        if full:
            result_container_xpath = "//div[contains(@aria-label, 'Results for')]"
            results_container = driver.find_element(By.XPATH, result_container_xpath)
            self._scroll_results_container(driver, results_container, max_results)
            time.sleep(2)

        location_divs = driver.find_elements(By.CLASS_NAME, "Nv2PK")
        if max_results:
            location_divs = location_divs[:max_results]
        return [self._get_data_from_location_div(div) for div in location_divs]

    def get_maps_data(
        self,
        url: str,
        full: bool | None = False,
        max_results: int | None = None,
    ) -> list[Location]:
        self._logger.info("Retrieving data from Google Maps for query %s..", url)
        try:
            driver = self._init_chrome_driver()
        except Exception as exc:
            raise DriverInitializationError from exc

        try:
            self._click_consent_button(driver, url)
        except Exception as exc:
            with suppress(Exception):
                driver.quit()
            raise exc

        self._logger.info("Scraping Google Maps page..")
        try:
            return self._get_locations_from_page(url, driver, full, max_results)
        except Exception as exc:
            raise DriverGetMapsDataError from exc
        finally:
            with suppress(Exception):
                driver.quit()
