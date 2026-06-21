"""Record models returned by the Google Maps selenium scraper."""

from pydantic import BaseModel


class Location(BaseModel):
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
