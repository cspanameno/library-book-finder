"""Ask the library catalog whether it has a suggested book.

Only the catalog feed decides what the library has. One request per book, a
pause between live requests, and results cached for 24 hours.
"""
import time
from dataclasses import dataclass
from urllib.parse import quote_plus

import requests
import streamlit as st

from catalog import CatalogParseError, parse_feed
from matching import matching_items, search_surname

BASE = "https://sanle.ent.sirsi.net/client"
FEED_URL = BASE + "/rss/hitlist/default/qu={query}"
SEARCH_URL = BASE + "/en_US/default/search/results?qu={query}"
TIMEOUT_SECONDS = 10
MIN_SECONDS_BETWEEN_REQUESTS = 1.0
CACHE_TTL_SECONDS = 24 * 60 * 60
USER_AGENT = "library-book-finder (personal project)"

_last_request_at = None


class CatalogUnavailable(Exception):
    """The catalog could not be reached or did not return a usable feed."""


@dataclass(frozen=True)
class Availability:
    on_shelf: bool
    on_libby: bool
    search_url: str  # normal catalog page for parents

    @property
    def found(self):
        return self.on_shelf or self.on_libby


def search_url(title, author):
    return SEARCH_URL.format(query=quote_plus(f"{title} {author}"))


def feed_url(title, author):
    # Title + last name only: "Bill Martin Jr." finds almost nothing, "Martin" finds the book.
    return FEED_URL.format(query=quote_plus(f"{title} {search_surname(author)}"))


def _wait_for_turn():
    global _last_request_at
    if _last_request_at is not None:
        wait = MIN_SECONDS_BETWEEN_REQUESTS - (time.monotonic() - _last_request_at)
        if wait > 0:
            time.sleep(wait)
    _last_request_at = time.monotonic()


def fetch_feed(title, author):
    """One live request to the catalog. No retry."""
    _wait_for_turn()
    try:
        response = requests.get(
            feed_url(title, author),
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as err:
        # Don't include the URL: it contains the title and author we searched.
        raise CatalogUnavailable(type(err).__name__) from None
    return response.content.decode("utf-8", errors="replace")


def lookup_book(title, author, fetch=fetch_feed):
    """Check one suggested book against the catalog."""
    try:
        items = parse_feed(fetch(title, author))
    except CatalogParseError:
        raise CatalogUnavailable("CatalogParseError") from None
    found = matching_items(title, author, items)
    return Availability(
        on_shelf=any(i.kind == "shelf" for i in found),
        on_libby=any(i.kind == "libby" for i in found),
        search_url=search_url(title, author),
    )


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def cached_lookup(title, author):
    """Cached by title and author only. Failures raise, so they are not cached."""
    return lookup_book(title, author)
