from pathlib import Path

import pytest

from catalog import CatalogItem, parse_feed
from matching import author_matches, is_match, matching_items, normalize_title, search_surname

FIXTURES = Path(__file__).parent / "fixtures"


def item(title, author="Rubin, Adam, 1983-"):
    return CatalogItem(title, author, "ent://SD_ILS/0/SD_ILS:1", "Books", "shelf")


def feed(name):
    return parse_feed((FIXTURES / name).read_text(encoding="utf-8"))


# --- titles ---

def test_exact_match():
    assert is_match("Dragons Love Tacos", "Adam Rubin", item("Dragons love tacos"))


def test_sequel_is_not_a_match():
    # The case CLAUDE.md calls out: a hit is not a match.
    assert not is_match("Dragons Love Tacos", "Adam Rubin", item("Dragons Love Tacos 2"))
    assert not is_match("Dragons Love Tacos", "Adam Rubin", item("Dragons love tacos 2 : the sequel"))


def test_sequel_matches_when_it_is_the_suggestion():
    assert is_match("Dragons Love Tacos 2", "Adam Rubin", item("Dragons Love Tacos 2"))
    assert is_match("Dragons Love Tacos 2", "Adam Rubin", item("DRAGONS LOVE TACOS 2: THE SEQUEL : The Sequel"))


def test_extra_word_after_title_is_a_different_book():
    assert not is_match("The Wild Robot", "Peter Brown", item("The wild robot escapes", "Brown, Peter"))
    assert not is_match("The Wild Robot", "Peter Brown", item("The wild robot protects", "Brown, Peter"))


def test_subtitle_after_colon_is_ignored():
    assert is_match("Dragons Love Tacos", "Adam Rubin", item("Dragons love tacos : a story"))
    assert is_match("Dragons Love Tacos: A Story", "Adam Rubin", item("Dragons love tacos"))


@pytest.mark.parametrize("suggested, catalog", [
    ("The Wild Robot", "Wild robot"),
    ("A Bad Case of Stripes", "Bad case of stripes"),
    ("An Egg Is Quiet", "Egg is quiet"),
    ("El gato con botas", "Gato con botas"),
    ("Los dragones aman los tacos", "Dragones aman los tacos"),
    ("Las tres preguntas", "Tres preguntas"),
    ("La oruga muy hambrienta", "Oruga muy hambrienta"),
])
def test_leading_articles_are_ignored(suggested, catalog):
    assert normalize_title(suggested) == normalize_title(catalog)


def test_article_only_title_is_kept():
    assert normalize_title("The") == "the"


def test_case_and_punctuation_are_ignored():
    assert normalize_title("DON'T LET THE PIGEON DRIVE THE BUS!") == normalize_title("Don’t let the pigeon drive the bus")
    assert normalize_title("Mr. Brown Can Moo! Can You?") == normalize_title("Mr Brown can moo can you")


def test_accents_are_ignored():
    assert normalize_title("Dragones y tacos 2: la continuación") == normalize_title("Dragones y tacos 2: la continuacion")
    assert is_match("Un día de nieve", "Ezra Jack Keats", item("Un dia de nieve", "Keats, Ezra Jack"))


def test_translated_title_is_not_the_same_book():
    assert not is_match("Dragons Love Tacos", "Adam Rubin", item("Dragones y tacos"))
    assert not is_match("Dragones y tacos", "Adam Rubin", item("Dragons love tacos"))


# --- authors ---

@pytest.mark.parametrize("suggested", ["Adam Rubin", "Rubin, Adam", "adam rubin", "Rubin"])
def test_author_name_orders(suggested):
    assert author_matches(suggested, "Rubin, Adam, 1983- author.")


def test_wrong_author_is_not_a_match():
    assert not is_match("Dragons Love Tacos", "Mo Willems", item("Dragons love tacos"))


def test_author_matches_any_person_in_multi_author_record():
    record = "Rubin, Adam/ Salmieri, Daniel (ILT)/ Rubin, Adam (NRT)"
    assert author_matches("Adam Rubin", record)
    assert author_matches("Daniel Salmieri", record)
    assert not author_matches("Mo Willems", record)


def test_author_with_title_prefix_or_suffix():
    assert author_matches("Dr. Seuss", "Seuss, Dr.")
    assert author_matches("Martin Luther King Jr.", "King, Martin Luther, Jr.")


def test_two_word_last_name():
    assert author_matches("Gabriel García Márquez", "García Márquez, Gabriel")
    assert author_matches("García Márquez, Gabriel", "Garcia Marquez, Gabriel, 1927-")


def test_last_name_must_match_whole_word():
    assert not author_matches("Jason Reynolds", "Reynolds-Brown, Alex")
    assert not author_matches("Anna Son", "Mason, Anna")


def test_empty_author_never_matches():
    assert not author_matches("", "Rubin, Adam")
    assert not author_matches("Adam Rubin", "")


# --- against the saved feeds ---

def test_matching_items_in_physical_feed():
    items = feed("physical_dragons_love_tacos.xml")
    found = matching_items("Dragons Love Tacos", "Adam Rubin", items)
    assert [i.title for i in found] == ["Dragons love tacos"]
    assert found[0].kind == "shelf"


def test_sequel_suggestion_matches_only_sequel_items():
    items = feed("physical_dragons_love_tacos.xml")
    found = matching_items("Dragons Love Tacos 2", "Adam Rubin", items)
    assert {i.kind for i in found} == {"shelf", "libby"}
    assert all("2" in i.title for i in found)


def test_wild_robot_matches_original_in_every_format():
    items = feed("libby_wild_robot.xml")
    found = matching_items("The Wild Robot", "Peter Brown", items)
    assert sorted(i.kind for i in found) == ["libby", "libby", "shelf"]
    assert all(i.title.lower() == "the wild robot" for i in found)


def test_spanish_feed_does_not_match_english_title():
    items = feed("spanish_dragones_y_tacos.xml")
    assert matching_items("Dragons Love Tacos", "Adam Rubin", items) == []
    found = matching_items("Dragones y tacos", "Adam Rubin", items)
    assert [i.kind for i in found] == ["libby"]


def test_no_results_feed_matches_nothing():
    assert matching_items("Anything", "Anyone", feed("no_results.xml")) == []


# --- Brown Bear: "Bill Martin Jr." versus the catalog's "Martin, Bill, 1916-2004." ---

BROWN_BEAR = "Brown Bear, Brown Bear, What Do You See?"


@pytest.mark.parametrize("catalog_author", [
    "Martin, Bill, 1916-2004.",
    "Martin, Bill, 1916-2004, author.",
    "Martin, Jr., Bill",
])
def test_jr_in_suggested_author_still_matches_catalog_last_name(catalog_author):
    assert author_matches("Bill Martin Jr.", catalog_author)


def test_brown_bear_print_copy_is_found_in_the_real_feed():
    items = feed("brown_bear_query_without_jr.xml")
    found = matching_items(BROWN_BEAR, "Bill Martin Jr.", items)
    assert [(i.kind, i.item_id) for i in found] == [("shelf", "ent://SD_ILS/0/SD_ILS:336001")]


def test_brown_bear_translations_are_not_matches():
    items = feed("brown_bear_query_without_jr.xml")
    titles = {i.title for i in matching_items(BROWN_BEAR, "Bill Martin Jr.", items)}
    assert not any("Oso pardo" in t or "Zong" in t or "Gấu" in t for t in titles)


# --- Pete the Cat: ignoring subtitles must not merge different books in a series ---

PETE_SHOES = "Pete the Cat: I Love My White Shoes"
PETE_SCHOOL = item("Pete the cat : rocking in my school shoes", "Litwin, Eric.")
PETE_SHOES_RECORD = item("Pete the cat : I love my white shoes", "Litwin, Eric.")


def test_pete_the_cat_matches_its_own_record():
    assert is_match(PETE_SHOES, "Eric Litwin", PETE_SHOES_RECORD)


def test_pete_the_cat_does_not_match_a_different_pete_the_cat_book():
    assert not is_match(PETE_SHOES, "Eric Litwin", PETE_SCHOOL)


def test_only_the_right_pete_the_cat_book_is_returned():
    found = matching_items(PETE_SHOES, "Eric Litwin", [PETE_SCHOOL, PETE_SHOES_RECORD])
    assert found == [PETE_SHOES_RECORD]


# --- search_surname: what goes into the catalog query ---

@pytest.mark.parametrize("author, surname", [
    ("Adam Rubin", "Rubin"),
    ("Bill Martin Jr.", "Martin"),
    ("Martin Luther King Jr.", "King"),
    ("Martin, Bill, 1916-2004.", "Martin"),
    ("Martin, Jr., Bill", "Martin"),
    ("Dr. Seuss", "Seuss"),
    ("Rubin", "Rubin"),
    ("  Mo Willems ", "Willems"),
    ("", ""),
])
def test_search_surname(author, surname):
    assert search_surname(author) == surname


# --- ambiguity guard: a title with no subtitle that fits several books matches none ---

def pete(subtitle, kind="shelf", item_id="ent://SD_ILS/0/SD_ILS:1"):
    title = f"Pete the cat : {subtitle}" if subtitle else "Pete the cat"
    return CatalogItem(title, "Litwin, Eric.", item_id, "Books" if kind == "shelf" else "eBook", kind)


WHITE_SHOES = pete("I love my white shoes")
SCHOOL_SHOES = pete("rocking in my school shoes")
GROOVY = pete("Pete's big lunch")


def test_bare_series_title_matching_several_books_is_no_match():
    assert matching_items("Pete the Cat", "Eric Litwin", [WHITE_SHOES, SCHOOL_SHOES, GROOVY]) == []


def test_bare_title_matching_two_books_is_no_match():
    assert matching_items("Pete the Cat", "Eric Litwin", [WHITE_SHOES, SCHOOL_SHOES]) == []


def test_bare_title_matching_one_book_is_a_match():
    assert matching_items("Pete the Cat", "Eric Litwin", [WHITE_SHOES]) == [WHITE_SHOES]


def test_bare_title_matching_one_book_in_two_formats_keeps_both():
    libby = pete("I love my white shoes", kind="libby", item_id="ent://X/OVERDRIVE:abc")
    found = matching_items("Pete the Cat", "Eric Litwin", [WHITE_SHOES, libby, SCHOOL_SHOES][:2])
    assert found == [WHITE_SHOES, libby]


def test_exact_subtitle_less_record_settles_the_ambiguity():
    exact = pete("")
    assert matching_items("Pete the Cat", "Eric Litwin", [WHITE_SHOES, exact, SCHOOL_SHOES]) == [exact]


def test_bare_title_with_one_subtitled_book_and_a_bare_record_is_the_same_book():
    # "Dragons Love Tacos 2" (ebook) and "Dragons love tacos 2 : the sequel" (print).
    ebook = pete("", kind="libby", item_id="ent://X/OVERDRIVE:abc")
    assert matching_items("Pete the Cat", "Eric Litwin", [ebook, WHITE_SHOES]) == [ebook, WHITE_SHOES]


def test_suggestion_with_subtitle_is_not_affected_by_other_books():
    assert matching_items("Pete the Cat: I Love My White Shoes", "Eric Litwin",
                          [WHITE_SHOES, SCHOOL_SHOES, GROOVY]) == [WHITE_SHOES]


def test_other_authors_books_do_not_make_a_title_ambiguous():
    other = CatalogItem("Pete the cat : not my book", "Someone, Else.", "ent://SD_ILS/0/SD_ILS:9", "Books", "shelf")
    assert matching_items("Pete the Cat", "Eric Litwin", [WHITE_SHOES, other]) == [WHITE_SHOES]


def test_one_sided_subtitle_still_matches():
    assert is_match("Pete the Cat", "Eric Litwin", WHITE_SHOES)
    assert is_match("Pete the Cat: I Love My White Shoes", "Eric Litwin", pete(""))
