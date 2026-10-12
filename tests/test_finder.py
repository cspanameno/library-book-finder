from types import SimpleNamespace

import pytest

import finder
import spanish
import suggest
from catalog import CatalogItem
from finder import CATALOG_STOPPED, find_books
from lookup import Availability, CatalogUnavailable
from suggest import Request, SuggestionError


class FakeClient:
    def __init__(self, *queued):
        self.queued = list(queued)
        self.calls = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        item = self.queued.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def tool_reply(name, payload):
    return SimpleNamespace(content=[SimpleNamespace(type="tool_use", name=name, input=payload)], stop_reason="tool_use")


def suggestions(*titles, language="English"):
    books = [{"title": t, "author": f"Writer{i} Lastname{i}", "reason": f"Because {t}.",
              "estimated_level": "2.0", "language": language} for i, t in enumerate(titles)]
    return tool_reply(suggest.TOOL_NAME, {"books": books})


def words(*w):
    return tool_reply(spanish.WORDS_TOOL_NAME, {"words": list(w)})


def picks(*ids):
    return tool_reply(spanish.PICK_TOOL_NAME, {"picks": [{"id": i, "reason": f"Pick {i}.", "estimated_level": "2.5"} for i in ids]})


def catalog_book(n, title=None, author="Rubin, Adam, 1983- author."):
    return CatalogItem(title or f"Libro {n}", author, f"ent://SD_ILS/0/SD_ILS:{n}", "Books", "shelf", "J SPA", ("1",))


def spanish_search(by_word):
    def search(word):
        result = by_word[word]
        if isinstance(result, Exception):
            raise result
        return result
    return search


def lookup_by_title(found_titles, down_after=None):
    calls = []

    def lookup(title, author):
        calls.append(title)
        if down_after is not None and len(calls) > down_after:
            raise CatalogUnavailable("Timeout")
        on = title in found_titles
        return Availability(on, False, f"https://library/search?{title}")
    lookup.calls = calls
    return lookup


EN = Request("1", {"English": 1.5}, "dragons")
ES = Request("1", {"Spanish": 3.0}, "dragons")
BOTH = Request("1", {"English": 1.5, "Spanish": 3.0}, "dragons")


# --- English only ---

def test_english_keeps_the_first_five_found_in_haiku_order_and_stops_checking():
    titles = [f"Book {i}" for i in range(10)]
    client = FakeClient(suggestions(*titles))
    lookup = lookup_by_title(set(titles))
    result = find_books(EN, client, lookup=lookup)
    assert [b.title for b in result.books] == titles[:5]
    assert len(lookup.calls) == 5                    # stopped once 5 were found
    assert len(client.calls) == 1


def test_english_skips_books_the_catalog_does_not_have_and_never_pads():
    client = FakeClient(suggestions("A", "B", "C", "D"))
    result = find_books(EN, client, lookup=lookup_by_title({"B", "D"}))
    assert [b.title for b in result.books] == ["B", "D"]


def test_english_book_carries_haiku_text_and_catalog_badges():
    client = FakeClient(suggestions("A"))
    lookup = lambda title, author: Availability(True, True, "https://library/search?A")
    (book,) = find_books(EN, client, lookup=lookup).books
    assert (book.title, book.author, book.reason, book.estimated_level, book.language) == (
        "A", "Writer0 Lastname0", "Because A.", "2.0", "English")
    assert (book.on_shelf, book.on_libby, book.search_url) == (True, True, "https://library/search?A")


def test_english_request_to_haiku_mentions_only_the_english_level():
    client = FakeClient(suggestions("A"))
    find_books(Request("1", {"English": 1.5}, "dragons"), client, lookup=lookup_by_title({"A"}))
    prompt = client.calls[0]["messages"][0]["content"]
    assert "English" in prompt and "Spanish" not in prompt


def test_english_drops_suggestions_haiku_labels_spanish():
    client = FakeClient(tool_reply(suggest.TOOL_NAME, {"books": [
        {"title": "Uno", "author": "A B", "reason": "r", "estimated_level": "2", "language": "Spanish"},
        {"title": "Two", "author": "C D", "reason": "r", "estimated_level": "2", "language": "English"}]}))
    lookup = lookup_by_title({"Uno", "Two"})
    assert [b.title for b in find_books(EN, client, lookup=lookup).books] == ["Two"]
    assert lookup.calls == ["Two"]


def test_english_same_book_suggested_twice_is_shown_once():
    client = FakeClient(tool_reply(suggest.TOOL_NAME, {"books": [
        {"title": "The Wild Robot", "author": "Peter Brown", "reason": "r", "estimated_level": "3", "language": "English"},
        {"title": "Wild Robot", "author": "Brown, Peter", "reason": "r2", "estimated_level": "3", "language": "English"}]}))
    lookup = lambda title, author: Availability(True, False, "u")
    assert len(find_books(EN, client, lookup=lookup).books) == 1


def test_english_progress_counts_the_books_being_checked():
    messages = []
    client = FakeClient(suggestions("A", "B", "C"))
    find_books(EN, client, progress=messages.append, lookup=lookup_by_title({"A", "B", "C"}))
    assert messages == ["Checking the library catalog… (1 of 3)", "Checking the library catalog… (2 of 3)",
                        "Checking the library catalog… (3 of 3)"]


def test_english_catalog_down_at_the_start_raises():
    client = FakeClient(suggestions("A", "B"))
    with pytest.raises(CatalogUnavailable):
        find_books(EN, client, lookup=lookup_by_title({"A", "B"}, down_after=0))


def test_english_catalog_going_down_midway_keeps_what_was_found_with_a_note():
    client = FakeClient(suggestions("A", "B", "C"))
    result = find_books(EN, client, lookup=lookup_by_title({"A", "B", "C"}, down_after=2))
    assert [b.title for b in result.books] == ["A", "B"]
    assert result.notices == (CATALOG_STOPPED,)


def test_english_nothing_to_suggest_means_no_books_and_no_catalog_requests():
    client = FakeClient(tool_reply(suggest.TOOL_NAME, {"books": []}))
    lookup = lookup_by_title(set())
    result = find_books(EN, client, lookup=lookup)
    assert result.books == () and result.notices == () and lookup.calls == []


def test_english_haiku_trouble_raises_a_suggestion_error():
    client = FakeClient(tool_reply(suggest.TOOL_NAME, {"books": [{"title": "x"}]}),
                        tool_reply(suggest.TOOL_NAME, {"books": [{"title": "x"}]}))
    with pytest.raises(SuggestionError):
        find_books(EN, client, lookup=lookup_by_title(set()))


# --- Spanish only ---

def test_spanish_books_are_tidied_for_display_and_marked_on_the_shelf():
    item = catalog_book(1, "Ven a la escuela, querido dragón = Come to school, dear dragon", "Hillert, Margaret, author.")
    client = FakeClient(words("dragones"), picks("B1"))
    result = find_books(ES, client, spanish_search=spanish_search({"dragones": [item]}))
    (book,) = result.books
    assert book.title == "Ven a la escuela, querido dragón"
    assert book.author == "Margaret Hillert"
    assert (book.language, book.on_shelf, book.on_libby) == ("Spanish", True, False)
    assert (book.reason, book.estimated_level) == ("Pick B1.", "2.5")
    assert book.search_url == ("https://sanle.ent.sirsi.net/client/en_US/default/search/results"
                               "?qu=Ven+a+la+escuela%2C+querido+drag%C3%B3n+Margaret+Hillert")


def test_spanish_request_to_haiku_mentions_only_the_spanish_level():
    client = FakeClient(words("dragones"), picks("B1"))
    find_books(ES, client, spanish_search=spanish_search({"dragones": [catalog_book(1)]}))
    assert "Spanish reading level: grade equivalent 3.0" in client.calls[1]["messages"][0]["content"]


def test_spanish_shows_at_most_five():
    client = FakeClient(words("dragones"), picks(*[f"B{i}" for i in range(1, 7)]))
    result = find_books(ES, client, spanish_search=spanish_search({"dragones": [catalog_book(i) for i in range(1, 9)]}))
    assert len(result.books) == 5


def test_spanish_nothing_found_in_the_catalog_is_an_empty_result_not_an_error():
    client = FakeClient(words("zzzz"))
    result = find_books(ES, client, spanish_search=spanish_search({"zzzz": []}))
    assert result.books == () and len(client.calls) == 1


def test_spanish_catalog_down_raises():
    client = FakeClient(words("dragones"))
    with pytest.raises(CatalogUnavailable):
        find_books(ES, client, spanish_search=spanish_search({"dragones": CatalogUnavailable("Timeout")}))


# --- both languages ---

def both_client(spanish_ids, english_titles):
    return FakeClient(words("dragones"), picks(*spanish_ids), suggestions(*english_titles))


def test_both_alternates_english_and_spanish_three_and_two():
    search = spanish_search({"dragones": [catalog_book(i, f"Libro {i}") for i in range(1, 6)]})
    client = both_client(["B1", "B2", "B3", "B4", "B5"], [f"Book {i}" for i in range(6)])
    result = find_books(BOTH, client, lookup=lookup_by_title({f"Book {i}" for i in range(6)}), spanish_search=search)
    assert [(b.language, b.title) for b in result.books] == [
        ("English", "Book 0"), ("Spanish", "Libro 1"), ("English", "Book 1"), ("Spanish", "Libro 2"), ("English", "Book 2")]


def test_both_runs_spanish_first_and_makes_three_haiku_calls():
    client = both_client(["B1"], ["Book 0"])
    find_books(BOTH, client, lookup=lookup_by_title({"Book 0"}),
               spanish_search=spanish_search({"dragones": [catalog_book(1)]}))
    assert [c["tools"][0]["name"] for c in client.calls] == ["spanish_search_words", "pick_books", "suggest_books"]


def test_both_asks_for_only_as_many_english_as_it_needs():
    lookup = lookup_by_title({f"Book {i}" for i in range(10)})
    search = spanish_search({"dragones": [catalog_book(i) for i in range(1, 6)]})
    find_books(BOTH, both_client(["B1", "B2", "B3"], [f"Book {i}" for i in range(10)]), lookup=lookup, spanish_search=search)
    assert len(lookup.calls) == 3                     # English needs 3 when Spanish found 2 or more


def test_both_english_fills_in_when_spanish_finds_fewer():
    lookup = lookup_by_title({f"Book {i}" for i in range(10)})
    search = spanish_search({"dragones": [catalog_book(1)]})
    result = find_books(BOTH, both_client(["B1"], [f"Book {i}" for i in range(10)]), lookup=lookup, spanish_search=search)
    assert [b.language for b in result.books] == ["English", "Spanish", "English", "English", "English"]


def test_both_spanish_fills_in_when_english_finds_fewer():
    search = spanish_search({"dragones": [catalog_book(i) for i in range(1, 6)]})
    result = find_books(BOTH, both_client(["B1", "B2", "B3", "B4", "B5"], ["Book 0"]),
                        lookup=lookup_by_title({"Book 0"}), spanish_search=search)
    assert [b.language for b in result.books] == ["English", "Spanish", "Spanish", "Spanish", "Spanish"]


def test_both_never_pads_past_what_was_found():
    search = spanish_search({"dragones": [catalog_book(1)]})
    result = find_books(BOTH, both_client(["B1"], ["Book 0"]), lookup=lookup_by_title({"Book 0"}), spanish_search=search)
    assert len(result.books) == 2


def test_both_with_the_spanish_side_down_still_shows_english_with_a_note():
    client = FakeClient(words("dragones"), suggestions("Book 0", "Book 1"))
    result = find_books(BOTH, client, lookup=lookup_by_title({"Book 0", "Book 1"}),
                        spanish_search=spanish_search({"dragones": CatalogUnavailable("Timeout")}))
    assert [b.language for b in result.books] == ["English", "English"]
    assert result.notices == ("We couldn't search the Spanish shelves just now, so these are English books only.",)


def test_both_with_the_english_side_failing_still_shows_spanish_with_a_note():
    bad = tool_reply(suggest.TOOL_NAME, {"books": [{"title": "x"}]})
    client = FakeClient(words("dragones"), picks("B1"), bad, bad)
    result = find_books(BOTH, client, lookup=lookup_by_title(set()),
                        spanish_search=spanish_search({"dragones": [catalog_book(1)]}))
    assert [b.language for b in result.books] == ["Spanish"]
    assert result.notices == ("We couldn't search for English books just now, so these are Spanish books only.",)


def test_both_sides_failing_raises():
    client = FakeClient(words("dragones"))
    bad = tool_reply(suggest.TOOL_NAME, {"books": [{"title": "x"}]})
    client.queued += [bad, bad]
    with pytest.raises(CatalogUnavailable):
        find_books(BOTH, client, lookup=lookup_by_title(set()),
                   spanish_search=spanish_search({"dragones": CatalogUnavailable("Timeout")}))


def test_both_with_nothing_found_is_an_empty_result():
    client = FakeClient(words("zzzz"), tool_reply(suggest.TOOL_NAME, {"books": []}))
    result = find_books(BOTH, client, spanish_search=spanish_search({"zzzz": []}))
    assert result.books == () and result.notices == ()


def test_each_side_gets_a_request_with_only_its_own_level():
    client = both_client(["B1"], ["Book 0"])
    find_books(BOTH, client, lookup=lookup_by_title({"Book 0"}),
               spanish_search=spanish_search({"dragones": [catalog_book(1)]}))
    spanish_prompt = client.calls[1]["messages"][0]["content"]
    english_prompt = client.calls[2]["messages"][0]["content"]
    assert "Spanish reading level: grade equivalent 3.0" in spanish_prompt and "1.5" not in spanish_prompt
    assert "Reading level in English: grade equivalent 1.5" in english_prompt and "Spanish" not in english_prompt
