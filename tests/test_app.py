from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import finder
import suggest
from finder import CATALOG_DOWN, CATALOG_STOPPED, NO_RESULTS
from lookup import CatalogUnavailable
from test_finder import FakeClient, catalog_book, lookup_by_title, picks, spanish_search, suggestions, tool_reply

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


def fill(at, language="English", grade="1", levels=None, topics=("dragons",)):
    levels = levels or {"English": 1.5, "Spanish": 3.0}
    at.radio[0].set_value(language).run()
    at.selectbox[0].set_value(grade).run()
    wanted = ("English", "Spanish") if language == "Both" else (language,)
    for lang in wanted:
        at.number_input(key=f"level_{lang}").set_value(levels[lang]).run()
    at.pills[0].set_value(list(topics)).run()
    return at


def search(at):
    at.button[0].click().run()
    assert not at.exception
    return at


# --- the form ---

def test_page_shows_the_hints_and_the_estimate_note():
    captions = texts(start().caption)
    assert "Check your child's Star report for Grade Equiv." in captions
    assert "Reading levels are estimates." in captions


def test_topics_are_a_picker_of_fourteen_with_nothing_chosen_to_start():
    at = start()
    assert len(at.pills) == 1 and len(at.text_input) == 0       # the free-text box is gone
    assert at.pills[0].label == "What does your child like? Pick 1 or 2."
    assert at.pills[0].options == ["Dragons", "Soccer", "Dinosaurs", "Animals", "Trucks", "Unicorns", "Fairies",
                                   "Space", "Ocean", "Princesses", "Robots", "Bugs", "Monsters", "Funny"]
    assert at.pills[0].value == []


def test_picking_three_topics_shows_a_red_note_and_an_error_on_submit(monkeypatch):
    client = FakeClient()
    use_client(monkeypatch, client)
    at = fill(start(), topics=("dragons", "soccer", "space"))
    assert ":red[Please pick up to 2 topics.]" in texts(at.caption)
    assert "Please pick up to 2 topics." in texts(search(at).error)
    assert client.calls == []


def test_picking_two_topics_shows_no_note():
    at = fill(start(), topics=("dragons", "soccer"))
    assert not any("Please pick up to" in c for c in texts(at.caption))


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
    assert "Please pick at least one thing your child likes." in messages
    assert client.calls == []


def test_both_languages_need_both_levels(monkeypatch):
    use_client(monkeypatch, FakeClient())
    at = start()
    at.radio[0].set_value("Both").run()
    at.selectbox[0].set_value("2").run()
    at.number_input(key="level_English").set_value(2.0).run()
    at.pills[0].set_value(["dragons"]).run()
    assert texts(search(at).error) == ["Please enter the reading level in Spanish."]


# --- results ---

def test_english_search_shows_books_with_reason_badge_level_and_link(monkeypatch):
    use_client(monkeypatch, FakeClient(suggestions("Dragons Love Tacos", "Wild Robot")))
    monkeypatch.setattr(finder, "cached_lookup", lookup_by_title({"Dragons Love Tacos", "Wild Robot"}))
    at = search(fill(start()))
    text = page_text(at)
    assert "### Dragons Love Tacos" in text and "by Writer0 Lastname0" in text
    assert "### Wild Robot" in text and "by Writer1 Lastname1" in text
    assert ":green-badge[On the shelf]" in text
    assert "English · Estimated level: grade 2.0" in text
    assert "[Find Dragons Love Tacos at the library](https://library/search?Dragons Love Tacos)" in text
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
    client = FakeClient(picks("B1"))
    use_client(monkeypatch, client)
    monkeypatch.setattr(finder, "cached_spanish_search", spanish_search({"dragones": [item]}))
    text = page_text(search(fill(start(), language="Spanish")))
    assert len(client.calls) == 1                       # Spanish needs one Haiku call, the pick
    assert '### <span lang="es">Ven a la escuela, querido dragón</span>' in text
    assert 'by <span lang="es">Margaret Hillert</span>' in text
    assert '[Find <span lang="es">Ven a la escuela, querido dragón</span> at the library]' in text
    assert "Come to school" not in text
    assert ":green-badge[On the shelf]" in text and "Libby" not in text
    assert "Spanish · Estimated level: grade 2.5" in text


def test_both_languages_show_a_mix(monkeypatch):
    client = FakeClient(picks("B1"), suggestions("Book 0"))
    use_client(monkeypatch, client)
    monkeypatch.setattr(finder, "cached_spanish_search", spanish_search({"dragones": [catalog_book(1, "Libro 1")]}))
    monkeypatch.setattr(finder, "cached_lookup", lookup_by_title({"Book 0"}))
    text = page_text(search(fill(start(), language="Both")))
    assert len(client.calls) == 2                       # "both" needs two: the pick and the English suggestions
    assert text.index("Book 0") < text.index("Libro 1")
    assert "English ·" in text and "Spanish ·" in text


def test_fewer_than_five_says_how_many_were_found_without_padding(monkeypatch):
    use_client(monkeypatch, FakeClient(suggestions("A", "B", "C")))
    monkeypatch.setattr(finder, "cached_lookup", lookup_by_title({"A", "B"}))
    at = search(fill(start()))
    assert "We found 2 books at the library that fit." in texts(at.caption)
    assert page_text(at).count("at the library](") == 2


def test_one_book_found_uses_the_singular(monkeypatch):
    use_client(monkeypatch, FakeClient(suggestions("A")))
    monkeypatch.setattr(finder, "cached_lookup", lookup_by_title({"A"}))
    assert "We found 1 book at the library that fit." in texts(search(fill(start())).caption)


def test_five_books_have_no_count_note(monkeypatch):
    titles = [f"Book {i}" for i in range(6)]
    use_client(monkeypatch, FakeClient(suggestions(*titles)))
    monkeypatch.setattr(finder, "cached_lookup", lookup_by_title(set(titles)))
    at = search(fill(start()))
    assert page_text(at).count("at the library](") == 5
    assert not any(c.startswith("We found") for c in texts(at.caption))


def test_titles_with_markdown_characters_are_escaped(monkeypatch):
    use_client(monkeypatch, FakeClient(suggestions("Dragons *love* $5 [tacos]")))
    monkeypatch.setattr(finder, "cached_lookup", lookup_by_title({"Dragons *love* $5 [tacos]"}))
    assert r"### Dragons \*love\* \$5 \[tacos\]" in page_text(search(fill(start())))


def test_english_books_are_not_marked_as_spanish(monkeypatch):
    use_client(monkeypatch, FakeClient(suggestions("A")))
    monkeypatch.setattr(finder, "cached_lookup", lookup_by_title({"A"}))
    assert 'lang="es"' not in page_text(search(fill(start())))


def test_spanish_books_reasons_carry_no_lang_attribute(monkeypatch):
    item = catalog_book(1, "Ven a la escuela, querido dragón", "Hillert, Margaret, author.")
    use_client(monkeypatch, FakeClient(picks("B1")))
    monkeypatch.setattr(finder, "cached_spanish_search", spanish_search({"dragones": [item]}))
    text = page_text(search(fill(start(), language="Spanish")))
    assert 'lang="es"' in text                           # titles and authors are still marked
    assert "\nPick B1.\n" in text                        # the reason, plain
    assert "Pick B1.</span>" not in text and ">Pick B1." not in text


def test_a_script_tag_in_a_spanish_title_comes_out_escaped(monkeypatch):
    evil = "<script>alert(1)</script>"
    item = catalog_book(1, evil, "Hillert, <b>Margaret</b>, author.")
    use_client(monkeypatch, FakeClient(picks("B1")))
    monkeypatch.setattr(finder, "cached_spanish_search", spanish_search({"dragones": [item]}))
    text = page_text(search(fill(start(), language="Spanish")))
    assert "<script" not in text and "</script" not in text
    assert "<b>" not in text
    assert '<span lang="es">&lt;script&gt;' in text


def test_the_page_has_a_title(monkeypatch):
    assert Path(APP).read_text().count('page_title="Library Book Finder"') == 1


def test_spanish_searches_use_the_chosen_topics_fixed_words_in_the_order_picked(monkeypatch):
    seen = []

    def record(word):
        seen.append(word)
        return [catalog_book(len(seen), f"Libro {word}")]

    use_client(monkeypatch, FakeClient(picks("B1")))
    monkeypatch.setattr(finder, "cached_spanish_search", record)
    search(fill(start(), language="Spanish", topics=("soccer", "animals")))
    assert seen == ["fútbol", "animal"]


def test_english_hands_haiku_the_topic_names(monkeypatch):
    client = FakeClient(suggestions("A"))
    use_client(monkeypatch, client)
    monkeypatch.setattr(finder, "cached_lookup", lookup_by_title({"A"}))
    search(fill(start(), topics=("dragons", "soccer")))
    assert "<interests>dragons and soccer</interests>" in client.calls[0]["messages"][0]["content"]


# --- no results: a friendly note, not an error ---

def test_nothing_to_suggest_gets_a_friendly_message_and_a_library_link(monkeypatch):
    use_client(monkeypatch, FakeClient(tool_reply(suggest.TOOL_NAME, {"books": []})))
    at = search(fill(start()))
    assert texts(at.info) == [NO_RESULTS]
    assert NO_RESULTS == "We couldn't find books for that. Try simple topics like dragons or soccer."
    assert not at.error and not at.warning
    assert "[Search the library catalog yourself](https://sanle.ent.sirsi.net/client/en_US/default/)" in page_text(at)


def test_books_suggested_but_none_in_the_library_is_also_the_friendly_message(monkeypatch):
    use_client(monkeypatch, FakeClient(suggestions("A", "B")))
    monkeypatch.setattr(finder, "cached_lookup", lookup_by_title(set()))
    at = search(fill(start()))
    assert texts(at.info) == [NO_RESULTS] and not at.error


def test_spanish_words_with_no_catalog_hits_is_the_friendly_message(monkeypatch):
    client = FakeClient()
    use_client(monkeypatch, client)
    monkeypatch.setattr(finder, "cached_spanish_search", spanish_search({"dragones": []}))
    at = search(fill(start(), language="Spanish"))
    assert texts(at.info) == [NO_RESULTS] and not at.error
    assert client.calls == []                          # nothing to choose from, so no Haiku call


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
    assert "### A" in page_text(at) and not at.error


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
    at = search(fill(start()))
    assert texts(at.error) == ["Something went wrong. Please try again."]
    assert "secretword" not in " ".join(texts(at.error)) and not at.exception


# --- the background ---

def test_the_page_carries_the_background_styles_but_no_visible_clutter():
    at = start()
    style = [m.value for m in at.markdown if "<style>" in m.value]
    assert len(style) == 1 and "data:image/svg+xml;base64," in style[0]
    assert "stMainBlockContainer" in style[0]
