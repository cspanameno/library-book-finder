from pathlib import Path

import pytest

from catalog import CatalogItem, parse_feed
from pool import PER_WORD_CAP, Pool, build_pool, book_key

FIXTURES = Path(__file__).parent / "fixtures"


def feed(name):
    return parse_feed((FIXTURES / name).read_text(encoding="utf-8"))


def book(title, author="Rubin, Adam, 1983- author.", n=1, kind="shelf"):
    return CatalogItem(title, author, f"ent://SD_ILS/0/SD_ILS:{n}", "Books" if kind == "shelf" else "eBook", kind)


def many(prefix, count, start=1000):
    return [book(f"{prefix} {i}", f"Author{i}, A.", start + i) for i in range(count)]


# --- merging and repeats ---

def test_single_word_keeps_the_feed_order_and_numbers_the_books():
    pool = build_pool({"a": [book("Uno", n=1), book("Dos", n=2), book("Tres", n=3)]})
    assert [(b.pool_id, b.item.title) for b in pool.books] == [("B1", "Uno"), ("B2", "Dos"), ("B3", "Tres")]
    assert all(b.words == ("a",) for b in pool.books)


def test_same_book_in_two_editions_appears_once():
    pool = build_pool({"a": [book("Fútbol", "Smith, Jo.", 1), book("Futbol", "Smith, Jo, 1970-", 2)]})
    assert len(pool) == 1
    assert pool.books[0].item.item_id.endswith(":1")  # the first record is kept


def test_volume_one_and_two_with_different_subtitles_are_different_books():
    pool = build_pool({"a": [book("Cuentos : historias verdaderas", "Brooks, Ben.", 1),
                             book("Cuentos : más historias verdaderas. 2", "Brooks, Ben.", 2)]})
    assert len(pool) == 2


def test_same_title_by_a_different_author_is_a_different_book():
    pool = build_pool({"a": [book("Dragones", "Perez, A.", 1), book("Dragones", "Lopez, B.", 2)]})
    assert len(pool) == 2


def test_book_found_by_two_words_appears_once_with_both_words():
    shared = book("Dragones y fútbol", "Gomez, C.", 7)
    pool = build_pool({"dragones": [book("Solo dragon", "A, A.", 1), shared],
                       "fútbol": [shared, book("Solo balon", "B, B.", 2)]})
    assert len(pool) == 3
    assert pool.books[0].item.title == "Dragones y fútbol"          # multi-word books come first
    assert pool.books[0].words == ("dragones", "fútbol")


def test_items_without_title_or_author_and_non_shelf_items_are_skipped():
    pool = build_pool({"a": [book("Bueno", n=1), book("", n=2), book("Sin autor", author="", n=3),
                             book("Ebook", n=4, kind="libby")]})
    assert [b.item.title for b in pool.books] == ["Bueno"]


# --- the cap ---

def test_cap_is_per_search_word():
    one = build_pool({"a": many("x", 100)})
    two = build_pool({"a": many("x", 100), "b": many("y", 100, start=5000)})
    assert len(one) == PER_WORD_CAP == 40
    assert len(two) == 80


def test_words_alternate_so_a_broad_word_cannot_crowd_out_a_narrow_one():
    pool = build_pool({"broad": many("b", 100), "narrow": many("n", 100, start=5000)}, per_word_cap=5)
    assert [b.item.title for b in pool.books] == ["b 0", "n 0", "b 1", "n 1", "b 2", "n 2", "b 3", "n 3", "b 4", "n 4"]


def test_small_word_does_not_waste_the_cap():
    pool = build_pool({"broad": many("b", 100), "tiny": many("t", 2, start=5000)}, per_word_cap=5)
    titles = [b.item.title for b in pool.books]
    assert len(titles) == 10
    assert titles.count("t 0") == titles.count("t 1") == 1
    assert sum(t.startswith("b") for t in titles) == 8


def test_multi_word_books_count_toward_the_cap():
    shared = [book(f"Shared {i}", f"S{i}, A.", i) for i in range(10)]
    pool = build_pool({"a": shared + many("x", 20), "b": shared + many("y", 20, start=5000)}, per_word_cap=5)
    assert len(pool) == 10
    assert all(len(b.words) == 2 for b in pool.books)


def test_empty_results_give_an_empty_pool():
    assert len(build_pool({})) == 0
    assert len(build_pool({"a": [], "b": []})) == 0


# --- IDs: Haiku can only pick what is in the pool ---

def test_pool_ids_are_unique_and_found_by_get():
    pool = build_pool({"a": many("x", 10)})
    ids = [b.pool_id for b in pool.books]
    assert len(set(ids)) == 10
    assert pool.get("B3") is pool.books[2]


@pytest.mark.parametrize("bad", ["B99", "b3", "", "3", "B3; DROP", None, 3, ["B1"]])
def test_unknown_ids_return_none(bad):
    pool = build_pool({"a": many("x", 10)})
    assert pool.get(bad) is None


def test_get_ignores_surrounding_spaces():
    pool = build_pool({"a": many("x", 3)})
    assert pool.get(" B2 ") is pool.books[1]


# --- with the real Spanish feeds ---

def test_real_feeds_dragones_and_futbol():
    pool = build_pool({"dragones": feed("spanish_children_dragones.xml"),
                       "fútbol": feed("spanish_children_futbol.xml")})
    assert len(pool) == 80                                  # 40 per word
    assert {b.words for b in pool.books} == {("dragones",), ("fútbol",)}
    assert sum(b.words == ("dragones",) for b in pool.books) == 40
    keys = [book_key(b.item) for b in pool.books]
    assert len(keys) == len(set(keys))
    assert all(b.item.kind == "shelf" and b.item.call_number for b in pool.books)


def test_real_futbol_feed_drops_its_two_repeated_editions():
    items = feed("spanish_children_futbol.xml")
    assert len(items) == 48
    assert len(build_pool({"fútbol": items}, per_word_cap=100)) == 46


def test_real_dragones_volumes_one_and_two_are_both_kept():
    pool = build_pool({"dragones": feed("spanish_children_dragones.xml")}, per_word_cap=100)
    brooks = [b for b in pool.books if b.item.author.startswith("Brooks")]
    assert len(brooks) == 2


def test_same_feed_under_two_words_is_all_multi_word():
    items = feed("spanish_children_futbol.xml")
    pool = build_pool({"fútbol": items, "futbol": items}, per_word_cap=100)
    assert len(pool) == 46 and all(len(b.words) == 2 for b in pool.books)
