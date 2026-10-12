from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import finder
import suggest
from finder import CATALOG_DOWN, CATALOG_STOPPED, NO_RESULTS
from lookup import CatalogUnavailable
from test_finder import (FakeClient, catalog_book, lookup_by_title, picks, spanish_search, suggestions,
                         tool_reply, words)

APP = str(Path(__file__).parent.parent / "app.py")


@pytest.fixture(autouse=True)
def no_real_key(monkeypatch):
    # Never touch .streamlit/secrets.toml or the real API from tests.
    monkeypatch.setattr(suggest, "api_key_from", lambda secrets: "test-key")


def use_client(monkeypatch, client):
    monkeypatch.setattr(suggest, "make_client", lambda key: client)


def start():
    at = AppTest.from_file(APP, default_timeout=10)
    at.run()
    assert not at.exception
    return at


def texts(elements):
    return [e.value for e in elements]


def page_text(at):
    return "\n".join(texts(at.markdown))


def fill(at, language="English", grade="1", levels=None, interests="dragons"):
    levels = levels or {"English": 1.5, "Spanish": 3.0}
    at.radio[0].set_value(language).run()
    at.selectbox[0].set_value(grade).run()
    wanted = ("English", "Spanish") if language == "Both" else (language,)
    for lang in wanted:
        at.number_input(key=f"level_{lang}").set_value(levels[lang]).run()
    at.text_input[0].set_value(interests).run()
    return at


def search(at):
    at.button[0].click().run()
    assert not at.exception
    return at


# --- the form ---

def test_page_shows_the_hints_and_the_estimate_note():
    captions = texts(start().caption)
    assert "Check your child's Star report for Grade Equiv." in captions
    assert "Don't enter your child's name." in captions
    assert "Reading levels are estimates." in captions


def test_interests_box_has_example_placeholder_and_a_200_character_limit():
    box = start().text_input[0]
    assert box.placeholder == "e.g. dragons, soccer, animals"
    assert box.max_chars == 200


def test_english_is_the_default_and_shows_only_the_english_level():
    at = start()
    assert at.radio[0].value == "English"
    assert [n.key for n in at.number_input] == ["level_English"]


def test_choosing_spanish_or_both_changes_which_levels_show():
    at = start()
    at.radio[0].set_value("Spanish").run()
    assert [n.key for n in at.number_input] == ["level_Spanish"]
    at.radio[0].set_value("Both").run()
    assert [n.key for n in at.number_input] == ["level_English", "level_Spanish"]


def test_levels_start_empty_so_they_must_be_entered():
    assert all(n.value is None for n in start().number_input)


def test_submitting_an_empty_form_lists_what_is_missing_and_searches_nothing(monkeypatch):
    client = FakeClient()
    use_client(monkeypatch, client)
    at = search(start())
    messages = texts(at.error)
    assert "Please choose your child's grade." in messages
    assert "Please enter the reading level in English." in messages
    assert "Please tell us at least one thing your child likes." in messages
    assert client.calls == []


def test_both_languages_need_both_levels(monkeypatch):
    use_client(monkeypatch, FakeClient())
    at = start()
    at.radio[0].set_value("Both").run()
    at.selectbox[0].set_value("2").run()
    at.number_input(key="level_English").set_value(2.0).run()
    at.text_input[0].set_value("dragons").run()
    assert texts(search(at).error) == ["Please enter the reading level in Spanish."]


# --- results ---

def test_english_search_shows_books_with_reason_badge_level_and_link(monkeypatch):
    use_client(monkeypatch, FakeClient(suggestions("Dragons Love Tacos", "Wild Robot")))
    monkeypatch.setattr(finder, "cached_lookup", lookup_by_title({"Dragons Love Tacos", "Wild Robot"}))
    at = search(fill(start()))
    text = page_text(at)
    assert "**Dragons Love Tacos** by Writer0 Lastname0" in text
    assert "**Wild Robot** by Writer1 Lastname1" in text
    assert ":green-badge[On the shelf]" in text
    assert "English · Estimated level: grade 2.0" in text
    assert "[Find it at the library](https://library/search?Dragons Love Tacos)" in text
    assert not at.error
    assert texts(at.caption)[-1] == "Reading levels are estimates."


def test_both_badges_show_when_a_book_is_on_the_shelf_and_on_libby(monkeypatch):
    from lookup import Availability
    use_client(monkeypatch, FakeClient(suggestions("A")))
    monkeypatch.setattr(finder, "cached_lookup", lambda t, a: Availability(True, True, "u"))
    text = page_text(search(fill(start())))
    assert ":green-badge[On the shelf] :blue-badge[On Libby]" in text


def test_spanish_search_shows_tidy_titles_and_authors_with_shelf_badge_only(monkeypatch):
    item = catalog_book(1, "Ven a la escuela, querido dragón = Come to school, dear dragon", "Hillert, Margaret, author.")
    use_client(monkeypatch, FakeClient(words("dragones"), picks("B1")))
    monkeypatch.setattr(finder, "cached_spanish_search", spanish_search({"dragones": [item]}))
    text = page_text(search(fill(start(), language="Spanish")))
    assert "**Ven a la escuela, querido dragón** by Margaret Hillert" in text
    assert "Come to school" not in text
    assert ":green-badge[On the shelf]" in text and "Libby" not in text
    assert "Spanish · Estimated level: grade 2.5" in text


def test_both_languages_show_a_mix(monkeypatch):
    use_client(monkeypatch, FakeClient(words("dragones"), picks("B1"), suggestions("Book 0")))
    monkeypatch.setattr(finder, "cached_spanish_search", spanish_search({"dragones": [catalog_book(1, "Libro 1")]}))
    monkeypatch.setattr(finder, "cached_lookup", lookup_by_title({"Book 0"}))
    text = page_text(search(fill(start(), language="Both")))
    assert text.index("Book 0") < text.index("Libro 1")
    assert "English ·" in text and "Spanish ·" in text


def test_fewer_than_five_says_how_many_were_found_without_padding(monkeypatch):
    use_client(monkeypatch, FakeClient(suggestions("A", "B", "C")))
    monkeypatch.setattr(finder, "cached_lookup", lookup_by_title({"A", "B"}))
    at = search(fill(start()))
    assert "We found 2 books at the library that fit." in texts(at.caption)
    assert page_text(at).count("Find it at the library") == 2


def test_one_book_found_uses_the_singular(monkeypatch):
    use_client(monkeypatch, FakeClient(suggestions("A")))
    monkeypatch.setattr(finder, "cached_lookup", lookup_by_title({"A"}))
    assert "We found 1 book at the library that fit." in texts(search(fill(start())).caption)


def test_five_books_have_no_count_note(monkeypatch):
    titles = [f"Book {i}" for i in range(6)]
    use_client(monkeypatch, FakeClient(suggestions(*titles)))
    monkeypatch.setattr(finder, "cached_lookup", lookup_by_title(set(titles)))
    at = search(fill(start()))
    assert page_text(at).count("Find it at the library") == 5
    assert not any(c.startswith("We found") for c in texts(at.caption))


def test_titles_with_markdown_characters_are_escaped(monkeypatch):
    use_client(monkeypatch, FakeClient(suggestions("Dragons *love* $5 [tacos]")))
    monkeypatch.setattr(finder, "cached_lookup", lookup_by_title({"Dragons *love* $5 [tacos]"}))
    assert r"**Dragons \*love\* \$5 \[tacos\]**" in page_text(search(fill(start())))


# --- gibberish and no results: a friendly note, not an error ---

def test_gibberish_interests_get_a_friendly_message_and_a_library_link(monkeypatch):
    use_client(monkeypatch, FakeClient(tool_reply(suggest.TOOL_NAME, {"books": []})))
    at = search(fill(start(), interests="asdf qwerty zxcv"))
    assert texts(at.info) == [NO_RESULTS]
    assert NO_RESULTS == "We couldn't find books for that. Try simple topics like dragons or soccer."
    assert not at.error and not at.warning
    assert "[Search the library catalog yourself](https://sanle.ent.sirsi.net/client/en_US/default/)" in page_text(at)


def test_books_suggested_but_none_in_the_library_is_also_the_friendly_message(monkeypatch):
    use_client(monkeypatch, FakeClient(suggestions("A", "B")))
    monkeypatch.setattr(finder, "cached_lookup", lookup_by_title(set()))
    at = search(fill(start()))
    assert texts(at.info) == [NO_RESULTS] and not at.error


def test_spanish_gibberish_with_no_search_words_is_the_friendly_message(monkeypatch):
    use_client(monkeypatch, FakeClient(words()))
    at = search(fill(start(), language="Spanish", interests="asdf qwerty"))
    assert texts(at.info) == [NO_RESULTS] and not at.error


def test_spanish_words_with_no_catalog_hits_is_the_friendly_message(monkeypatch):
    use_client(monkeypatch, FakeClient(words("zxcvb")))
    monkeypatch.setattr(finder, "cached_spanish_search", spanish_search({"zxcvb": []}))
    at = search(fill(start(), language="Spanish", interests="zxcvb"))
    assert texts(at.info) == [NO_RESULTS] and not at.error


# --- real failures are errors, in plain words ---

def test_catalog_down_shows_a_friendly_error(monkeypatch):
    use_client(monkeypatch, FakeClient(suggestions("A")))
    monkeypatch.setattr(finder, "cached_lookup", lookup_by_title({"A"}, down_after=0))
    at = search(fill(start()))
    assert texts(at.error) == [CATALOG_DOWN]


def test_catalog_stopping_midway_keeps_the_books_found_and_adds_a_note(monkeypatch):
    use_client(monkeypatch, FakeClient(suggestions("A", "B", "C")))
    monkeypatch.setattr(finder, "cached_lookup", lookup_by_title({"A", "B", "C"}, down_after=1))
    at = search(fill(start()))
    assert texts(at.info) == [CATALOG_STOPPED]
    assert "**A** by" in page_text(at) and not at.error


def test_bad_answers_from_haiku_show_the_friendly_error(monkeypatch):
    bad = tool_reply(suggest.TOOL_NAME, {"books": [{"title": "x"}]})
    use_client(monkeypatch, FakeClient(bad, bad))
    at = search(fill(start()))
    assert texts(at.error) == ["Couldn't understand the book ideas that came back. Please try again."]


def test_missing_api_key_shows_a_setup_message(monkeypatch):
    monkeypatch.setattr(suggest, "api_key_from", lambda secrets: None)
    at = search(fill(start()))
    assert len(at.error) == 1 and "secrets.toml" in at.error[0].value


def test_unexpected_errors_show_a_plain_message_and_never_the_input(monkeypatch):
    use_client(monkeypatch, FakeClient(suggestions("A")))

    def boom(title, author):
        raise RuntimeError("secretword in the traceback")

    monkeypatch.setattr(finder, "cached_lookup", boom)
    at = search(fill(start(), interests="secretword"))
    assert texts(at.error) == ["Something went wrong. Please try again."]
    assert "secretword" not in " ".join(texts(at.error)) and not at.exception
