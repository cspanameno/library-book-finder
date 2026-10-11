from pathlib import Path

import pytest
import requests

import lookup
from lookup import CatalogUnavailable, Availability, lookup_book

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_fetch(name):
    text = (FIXTURES / name).read_text(encoding="utf-8")
    return lambda title, author: text


# --- URLs ---

def test_urls_are_encoded():
    # The feed query uses the author's last name only; the parent link keeps the full name.
    assert lookup.feed_url("Dragons Love Tacos", "Adam Rubin") == (
        "https://sanle.ent.sirsi.net/client/rss/hitlist/default/qu=Dragons+Love+Tacos+Rubin"
    )
    assert lookup.search_url("Don't Let the Pigeon Drive the Bus!", "Mo Willems") == (
        "https://sanle.ent.sirsi.net/client/en_US/default/search/results"
        "?qu=Don%27t+Let+the+Pigeon+Drive+the+Bus%21+Mo+Willems"
    )
    assert "%C3%B3" in lookup.search_url("Dragones y tacos 2: la continuación", "Adam Rubin")


# --- badges ---

def test_shelf_only():
    result = lookup_book("Dragons Love Tacos", "Adam Rubin",
                         fetch=fixture_fetch("physical_dragons_love_tacos.xml"))
    assert (result.on_shelf, result.on_libby, result.found) == (True, False, True)


def test_both_badges_in_one_result():
    result = lookup_book("The Wild Robot", "Peter Brown", fetch=fixture_fetch("libby_wild_robot.xml"))
    assert (result.on_shelf, result.on_libby) == (True, True)


def test_libby_only():
    result = lookup_book("Dragones y tacos", "Adam Rubin",
                         fetch=fixture_fetch("spanish_dragones_y_tacos.xml"))
    assert (result.on_shelf, result.on_libby) == (False, True)


def test_sequel_hit_is_not_a_match():
    # Only the sequel is in this feed; the original must come back not found.
    result = lookup_book("Dragones y tacos", "Adam Rubin",
                         fetch=lambda t, a: (FIXTURES / "spanish_dragones_y_tacos.xml").read_text(encoding="utf-8")
                         .replace("Dragones y tacos</title>", "Something else</title>"))
    assert not result.found


def test_not_in_catalog():
    result = lookup_book("Zxqvbn", "Nobody", fetch=fixture_fetch("no_results.xml"))
    assert result == Availability(False, False, lookup.search_url("Zxqvbn", "Nobody"))
    assert not result.found


def test_result_carries_parent_search_link():
    result = lookup_book("Dragons Love Tacos", "Adam Rubin",
                         fetch=fixture_fetch("physical_dragons_love_tacos.xml"))
    assert result.search_url == lookup.search_url("Dragons Love Tacos", "Adam Rubin")


# --- failures ---

def test_unreadable_response_is_unavailable():
    with pytest.raises(CatalogUnavailable):
        lookup_book("Any", "One", fetch=lambda t, a: "<html>Just a moment...</html>")


class FakeResponse:
    def __init__(self, body=b"", error=None):
        self.content = body
        self._error = error

    def raise_for_status(self):
        if self._error:
            raise self._error


@pytest.fixture
def no_wait(monkeypatch):
    monkeypatch.setattr(lookup, "_last_request_at", None)
    monkeypatch.setattr(lookup.time, "sleep", lambda s: None)


def test_fetch_uses_timeout_and_decodes_utf8(monkeypatch, no_wait):
    seen = {}

    def fake_get(url, headers, timeout):
        seen.update(url=url, timeout=timeout, headers=headers)
        return FakeResponse("Dragones y tacos 2 : la continuación".encode("utf-8"))

    monkeypatch.setattr(lookup.requests, "get", fake_get)
    text = lookup.fetch_feed("Dragons Love Tacos", "Adam Rubin")
    assert text == "Dragones y tacos 2 : la continuación"
    assert seen["timeout"] == 10
    assert seen["url"] == lookup.feed_url("Dragons Love Tacos", "Adam Rubin")
    assert "User-Agent" in seen["headers"]


@pytest.mark.parametrize("error", [
    requests.Timeout("slow"),
    requests.ConnectionError("down"),
    requests.HTTPError("503"),
])
def test_fetch_errors_become_catalog_unavailable_without_retry(monkeypatch, no_wait, error):
    calls = []

    def fake_get(url, headers, timeout):
        calls.append(url)
        if isinstance(error, requests.HTTPError):
            return FakeResponse(error=error)
        raise error

    monkeypatch.setattr(lookup.requests, "get", fake_get)
    with pytest.raises(CatalogUnavailable) as raised:
        lookup.fetch_feed("Secret Title", "Secret Author")
    assert len(calls) == 1
    assert "Secret" not in str(raised.value)


# --- politeness ---

def test_pause_between_live_requests(monkeypatch):
    clock = [100.0]
    sleeps = []
    monkeypatch.setattr(lookup, "_last_request_at", None)
    monkeypatch.setattr(lookup.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(lookup.time, "sleep", lambda s: (sleeps.append(s), clock.__setitem__(0, clock[0] + s)))

    lookup._wait_for_turn()          # first request: no wait
    clock[0] += 0.25
    lookup._wait_for_turn()          # 0.25s later: wait the remaining 0.75s
    clock[0] += 5
    lookup._wait_for_turn()          # long enough ago: no wait

    assert sleeps == [pytest.approx(0.75)]


# --- caching ---

def test_cached_lookup_makes_one_request_per_book(monkeypatch):
    calls = []

    def fake_fetch(title, author):
        calls.append((title, author))
        return (FIXTURES / "physical_dragons_love_tacos.xml").read_text(encoding="utf-8")

    monkeypatch.setattr(lookup, "fetch_feed", fake_fetch)
    monkeypatch.setattr(lookup, "lookup_book", lambda t, a: lookup_book(t, a, fetch=fake_fetch))
    lookup.cached_lookup.clear()

    first = lookup.cached_lookup("Dragons Love Tacos", "Adam Rubin")
    second = lookup.cached_lookup("Dragons Love Tacos", "Adam Rubin")
    assert first == second
    assert len(calls) == 1
    lookup.cached_lookup.clear()


def test_failures_are_not_cached(monkeypatch):
    calls = []

    def failing_fetch(title, author):
        calls.append(1)
        raise CatalogUnavailable("Timeout")

    monkeypatch.setattr(lookup, "lookup_book", lambda t, a: lookup_book(t, a, fetch=failing_fetch))
    lookup.cached_lookup.clear()

    for _ in range(2):
        with pytest.raises(CatalogUnavailable):
            lookup.cached_lookup("Any", "One")
    assert len(calls) == 2
    lookup.cached_lookup.clear()


# --- Brown Bear: the search itself must find the book for "Bill Martin Jr." ---

BROWN_BEAR = "Brown Bear, Brown Bear, What Do You See?"


def test_search_query_does_not_include_name_suffix():
    # The catalog's author index is "Martin, Bill, 1916-2004." - a "Jr." in the
    # query makes it return almost nothing.
    url = lookup.feed_url(BROWN_BEAR, "Bill Martin Jr.")
    assert "jr" not in url.lower()
    assert "Martin" in url


def test_brown_bear_is_found_when_haiku_says_bill_martin_jr(monkeypatch, no_wait):
    # A catalog stand-in that answers like the real one did: a query containing
    # "Jr" gets one unrelated hit; without it, the full result list.
    with_jr = (FIXTURES / "brown_bear_query_with_jr.xml").read_bytes()
    without_jr = (FIXTURES / "brown_bear_query_without_jr.xml").read_bytes()

    def fake_get(url, headers, timeout):
        return FakeResponse(with_jr if "jr" in url.lower() else without_jr)

    monkeypatch.setattr(lookup.requests, "get", fake_get)
    result = lookup.lookup_book(BROWN_BEAR, "Bill Martin Jr.")
    assert result.on_shelf


def test_parent_link_keeps_the_full_author_including_suffix():
    url = lookup.search_url(BROWN_BEAR, "Bill Martin Jr.")
    assert url.endswith("Bill+Martin+Jr.")
    assert url == lookup.lookup_book(BROWN_BEAR, "Bill Martin Jr.",
                                     fetch=fixture_fetch("no_results.xml")).search_url


@pytest.mark.parametrize("author, query_end", [
    ("Bill Martin Jr.", "+Martin"),
    ("Martin, Bill, 1916-2004.", "+Martin"),
    ("Martin Luther King Jr.", "+King"),
    ("Dr. Seuss", "+Seuss"),
    ("Gabriel García Márquez", "+M%C3%A1rquez"),
    ("Rubin", "+Rubin"),
])
def test_feed_query_ends_with_last_name_only(author, query_end):
    assert lookup.feed_url("Some Title", author).endswith(query_end)


# --- filtered Spanish children's search (Step C) ---

def serve(monkeypatch, fixtures_by_word, calls=None):
    """Replace requests.get with a catalog stand-in that answers by search word."""
    def fake_get(url, headers, timeout):
        if calls is not None:
            calls.append((url, timeout))
        for word, name in fixtures_by_word.items():
            if f"qu={word}&" in url:
                return FakeResponse((FIXTURES / name).read_bytes())
        raise AssertionError(f"unexpected request: {url}")

    monkeypatch.setattr(lookup.requests, "get", fake_get)


def test_filtered_url_matches_the_url_that_worked_live():
    assert lookup.filtered_feed_url("dragones") == (
        "https://sanle.ent.sirsi.net/client/rss/hitlist/default/qu=dragones"
        "&qf=LANGUAGE%09Language%09SPA%09Spanish"
        "&qf=ITEMCAT2%09Audience%091%3ACHILDREN%09Children%27s+materials"
    )


def test_filtered_url_encodes_accents_and_spaces():
    url = lookup.filtered_feed_url("  Fútbol   Americano ")
    assert "qu=f%C3%BAtbol+americano&qf=" in url


def test_search_word_is_cleaned():
    assert lookup.clean_search_word("  Dragones ") == "dragones"
    assert lookup.clean_search_word("Ciencia   Ficción") == "ciencia ficción"


@pytest.mark.parametrize("word", ["", "   "])
def test_empty_search_word_is_rejected_without_a_request(monkeypatch, word):
    calls = []
    serve(monkeypatch, {}, calls)
    with pytest.raises(ValueError):
        lookup.search_spanish_children(word)
    assert calls == []


def test_search_returns_the_shelf_books_from_the_feed(monkeypatch, no_wait):
    serve(monkeypatch, {"dragones": "spanish_children_dragones.xml"})
    items = lookup.search_spanish_children("dragones")
    assert len(items) == 58
    assert {i.kind for i in items} == {"shelf"}
    assert "Los dragones adoran los calzoncillos" in {i.title for i in items}


def test_search_uses_the_long_timeout_but_title_lookup_keeps_the_short_one(monkeypatch, no_wait):
    calls = []
    serve(monkeypatch, {"dragones": "spanish_children_dragones.xml"}, calls)
    lookup.search_spanish_children("dragones")
    assert calls[0][1] == 30
    assert lookup.TIMEOUT_SECONDS == 10


def test_search_makes_exactly_one_request(monkeypatch, no_wait):
    calls = []
    serve(monkeypatch, {"fútbol".replace("ú", "%C3%BA"): "spanish_children_futbol.xml"}, calls)
    assert len(lookup.search_spanish_children("fútbol")) == 48
    assert len(calls) == 1


def test_libby_items_in_a_response_are_dropped(monkeypatch, no_wait):
    # The real filtered feeds have none; the function guarantees shelf-only anyway.
    monkeypatch.setattr(lookup.requests, "get",
                        lambda url, headers, timeout: FakeResponse((FIXTURES / "libby_wild_robot.xml").read_bytes()))
    items = lookup.search_spanish_children("robot")
    assert items and {i.kind for i in items} == {"shelf"}


@pytest.mark.parametrize("error", [requests.Timeout("slow"), requests.ConnectionError("down"), requests.HTTPError("503")])
def test_search_errors_become_catalog_unavailable_without_retry_or_leaks(monkeypatch, no_wait, error):
    calls = []

    def fake_get(url, headers, timeout):
        calls.append(url)
        if isinstance(error, requests.HTTPError):
            return FakeResponse(error=error)
        raise error

    monkeypatch.setattr(lookup.requests, "get", fake_get)
    with pytest.raises(CatalogUnavailable) as raised:
        lookup.search_spanish_children("secretword")
    assert len(calls) == 1
    assert "secretword" not in str(raised.value)


def test_non_feed_response_is_unavailable(monkeypatch, no_wait):
    monkeypatch.setattr(lookup.requests, "get",
                        lambda url, headers, timeout: FakeResponse(b"<html>Just a moment...</html>"))
    with pytest.raises(CatalogUnavailable):
        lookup.search_spanish_children("dragones")


def test_title_lookups_and_word_searches_share_one_politeness_delay(monkeypatch):
    clock = [50.0]
    sleeps = []
    monkeypatch.setattr(lookup, "_last_request_at", None)
    monkeypatch.setattr(lookup.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(lookup.time, "sleep", lambda s: (sleeps.append(s), clock.__setitem__(0, clock[0] + s)))
    monkeypatch.setattr(lookup.requests, "get",
                        lambda url, headers, timeout: FakeResponse((FIXTURES / "no_results.xml").read_bytes()))
    lookup.fetch_feed("Some Title", "Some Author")
    lookup.search_spanish_children("dragones")
    assert sleeps == [pytest.approx(1.0)]


# --- caching of word searches ---

@pytest.fixture
def clean_word_cache():
    lookup._cached_spanish_search.clear()
    yield
    lookup._cached_spanish_search.clear()


def test_repeat_word_search_makes_one_request(monkeypatch, no_wait, clean_word_cache):
    calls = []
    serve(monkeypatch, {"dragones": "spanish_children_dragones.xml"}, calls)
    first = lookup.cached_spanish_search("dragones")
    second = lookup.cached_spanish_search("dragones")
    assert first == second and len(first) == 58
    assert len(calls) == 1


def test_cache_key_is_the_cleaned_word(monkeypatch, no_wait, clean_word_cache):
    calls = []
    serve(monkeypatch, {"dragones": "spanish_children_dragones.xml"}, calls)
    lookup.cached_spanish_search("dragones")
    lookup.cached_spanish_search("  Dragones ")
    assert len(calls) == 1


def test_different_words_are_cached_separately(monkeypatch, no_wait, clean_word_cache):
    calls = []
    serve(monkeypatch, {"dragones": "spanish_children_dragones.xml",
                        "f%C3%BAtbol": "spanish_children_futbol.xml"}, calls)
    assert len(lookup.cached_spanish_search("dragones")) == 58
    assert len(lookup.cached_spanish_search("fútbol")) == 48
    assert len(calls) == 2


def test_failed_word_search_is_not_cached(monkeypatch, no_wait, clean_word_cache):
    calls = []

    def failing_get(url, headers, timeout):
        calls.append(url)
        raise requests.Timeout("slow")

    monkeypatch.setattr(lookup.requests, "get", failing_get)
    for _ in range(2):
        with pytest.raises(CatalogUnavailable):
            lookup.cached_spanish_search("dragones")
    assert len(calls) == 2
