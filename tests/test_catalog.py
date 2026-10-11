from pathlib import Path

import pytest

from catalog import CatalogParseError, parse_feed

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return parse_feed((FIXTURES / name).read_text(encoding="utf-8"))


def by_title(items):
    return {item.title: item for item in items}


def test_physical_feed_keeps_books_and_libby_only():
    items = by_title(load("physical_dragons_love_tacos.xml"))
    # The "Electronic Resources" item has an SD_ILS id but is not a book.
    assert set(items) == {
        "Dragons love tacos",
        "Dragons Love Tacos 2",
        "Dragons love tacos 2 : the sequel",
        "Dragones y tacos 2 : la continuación",
    }


def test_shelf_item_fields():
    item = by_title(load("physical_dragons_love_tacos.xml"))["Dragons love tacos"]
    assert item.kind == "shelf"
    assert item.format == "Books"
    assert item.author == "Rubin, Adam, 1983-"
    assert item.item_id == "ent://SD_ILS/0/SD_ILS:215993"


def test_libby_item_in_physical_feed():
    item = by_title(load("physical_dragons_love_tacos.xml"))["Dragons Love Tacos 2"]
    assert item.kind == "libby"
    assert item.format == "eBook"
    assert item.author == "Rubin, Adam"


def test_double_encoded_accent_in_title():
    titles = [i.title for i in load("physical_dragons_love_tacos.xml")]
    assert "Dragones y tacos 2 : la continuación" in titles


def test_libby_feed_drops_video_discs():
    items = load("libby_wild_robot.xml")
    assert all(i.format != "Video disc" for i in items)
    assert {i.kind for i in items} == {"shelf", "libby"}


def test_libby_feed_formats():
    items = load("libby_wild_robot.xml")
    libby_formats = {i.format for i in items if i.kind == "libby"}
    assert libby_formats == {"eBook", "eAudiobook"}
    assert all(i.format == "Books" for i in items if i.kind == "shelf")


def test_every_kept_item_has_author():
    for name in ["physical_dragons_love_tacos.xml", "libby_wild_robot.xml",
                 "spanish_dragones_y_tacos.xml"]:
        assert all(i.author for i in load(name)), name


def test_spanish_feed():
    items = by_title(load("spanish_dragones_y_tacos.xml"))
    assert items["Dragones y tacos"].kind == "libby"
    assert items["Dragones y tacos 2 : la continuación"].kind == "shelf"


def test_no_results_feed_is_empty_list():
    assert load("no_results.xml") == []


def test_trailing_junk_after_feed_is_ignored():
    xml = '<feed xmlns="http://www.w3.org/2005/Atom"></feed><a href="x"><script>if (a < b) {}</script>'
    assert parse_feed(xml) == []


def test_malformed_xml_raises():
    with pytest.raises(CatalogParseError):
        parse_feed('<feed xmlns="http://www.w3.org/2005/Atom"><entry></feed>')


def test_non_feed_response_raises():
    with pytest.raises(CatalogParseError):
        parse_feed("<html>Service unavailable</html>")


# --- Brown Bear: print copy sits below an "Audio disc" (CD + book) entry ---

def test_audio_disc_is_dropped_but_print_copy_further_down_is_kept():
    items = load("brown_bear_query_without_jr.xml")
    brown_bears = [i for i in items if i.title.lower() == "brown bear, brown bear, what do you see?"]
    assert [(i.kind, i.format) for i in brown_bears] == [("shelf", "Books")]
    assert brown_bears[0].item_id == "ent://SD_ILS/0/SD_ILS:336001"
    assert all(i.format != "Audio disc" for i in items)
