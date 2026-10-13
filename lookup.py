"""Ask the library catalog whether it has a suggested book.

Only the catalog feed decides what the library has. One request per book, a
pause between live requests, and results cached for 24 hours.
"""
import threading
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
FILTERED_TIMEOUT_SECONDS = 30  # filtered searches return whole lists and can take 15s+
MIN_SECONDS_BETWEEN_REQUESTS = 1.0
CACHE_TTL_SECONDS = 24 * 60 * 60
USER_AGENT = "library-book-finder (personal project)"

_last_request_at = None
# Streamlit runs each parent's session in its own thread; one lock keeps
# catalog requests to one at a time across all of them.
_request_lock = threading.Lock()


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


# Catalog filters (the feed's qf parameter): language Spanish, audience children's.
# Libby items carry neither, so filtered searches only return shelf books.
SPANISH_CHILDREN_FILTERS = (
    ("LANGUAGE", "Language", "SPA", "Spanish"),
    ("ITEMCAT2", "Audience", "1:CHILDREN", "Children's materials"),
)


def clean_search_word(word):
    return " ".join(word.lower().split())


def filtered_feed_url(word, filters=SPANISH_CHILDREN_FILTERS):
    qf = "".join(f"&qf={quote_plus(chr(9).join(parts))}" for parts in filters)
    return FEED_URL.format(query=quote_plus(clean_search_word(word))) + qf


def _wait_for_turn():
    global _last_request_at
    if _last_request_at is not None:
        wait = MIN_SECONDS_BETWEEN_REQUESTS - (time.monotonic() - _last_request_at)
        if wait > 0:
            time.sleep(wait)
    _last_request_at = time.monotonic()


def _get(url, timeout):
    """One live request to the catalog. No retry. Shared politeness delay.

    The lock covers the wait and the request, so only one request is in flight
    across all sessions, and the gap is measured from the end of the last one.
    """
    global _last_request_at
    with _request_lock:
        _wait_for_turn()
        try:
            response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
            response.raise_for_status()
        except requests.RequestException as err:
            # Don't include the URL: it contains what we searched for.
            raise CatalogUnavailable(type(err).__name__) from None
        finally:
            _last_request_at = time.monotonic()
    return response.content.decode("utf-8", errors="replace")


def fetch_feed(title, author):
    return _get(feed_url(title, author), TIMEOUT_SECONDS)


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


def search_spanish_children(word):
    """Spanish children's books on the shelf whose catalog record matches one search word.

    One live request. Returns CatalogItems, shelf books only (the parser drops
    DVDs and other formats; Libby items are dropped here). Raises
    CatalogUnavailable if the catalog fails.
    """
    if not clean_search_word(word):
        raise ValueError("Search word is empty")
    try:
        items = parse_feed(_get(filtered_feed_url(word), FILTERED_TIMEOUT_SECONDS))
    except CatalogParseError:
        raise CatalogUnavailable("CatalogParseError") from None
    return [item for item in items if item.kind == "shelf"]


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _cached_spanish_search(word):
    return tuple(search_spanish_children(word))


def cached_spanish_search(word):
    """Cached by the cleaned search word only. Failures raise, so they are not cached."""
    return list(_cached_spanish_search(clean_search_word(word)))
