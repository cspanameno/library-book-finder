import unicodedata

import pytest

from topics import BY_KEY, MAX_TOPICS, TOPICS, english_phrase, spanish_words

EXPECTED = {
    "dragons": ("🐉", "dragones"), "soccer": ("⚽", "fútbol"), "dinosaurs": ("🦖", "dinosaurios"),
    "animals": ("🐶", "animal"), "trucks": ("🚒", "camiones"), "unicorns": ("🦄", "unicornios"),
    "fairies": ("🧚", "hadas"), "space": ("🚀", "espacio"), "ocean": ("🌊", "océano"),
    "princesses": ("🏰", "princesas"), "robots": ("🤖", "robots"), "bugs": ("🐛", "insectos"),
    "monsters": ("👻", "monstruos"), "funny": ("😂", "humor"),
}


def test_there_are_fourteen_topics_with_the_agreed_emoji_and_words_in_order():
    assert [t.key for t in TOPICS] == list(EXPECTED)
    assert {t.key: (t.emoji, t.spanish_word) for t in TOPICS} == EXPECTED


def test_animals_uses_the_singular_because_animales_takes_55_seconds():
    assert BY_KEY["animals"].spanish_word == "animal"


def test_every_spanish_word_is_one_lowercase_letters_only_word():
    for topic in TOPICS:
        word = topic.spanish_word
        assert word.isalpha() and word == word.lower() and len(word) >= 3, word


def test_keys_and_words_are_unique():
    assert len({t.key for t in TOPICS}) == len(TOPICS)
    plain = lambda w: "".join(c for c in unicodedata.normalize("NFKD", w) if not unicodedata.combining(c))
    assert len({plain(t.spanish_word) for t in TOPICS}) == len(TOPICS)


def test_labels_show_the_emoji_and_the_capitalized_english_name():
    assert BY_KEY["dragons"].label == "🐉 Dragons"
    assert BY_KEY["funny"].label == "😂 Funny"


def test_at_most_two_topics():
    assert MAX_TOPICS == 2


@pytest.mark.parametrize("keys, phrase, words", [
    (["dragons"], "dragons", ("dragones",)),
    (["dragons", "soccer"], "dragons and soccer", ("dragones", "fútbol")),
    (["soccer", "dragons"], "soccer and dragons", ("fútbol", "dragones")),
])
def test_phrase_and_words_follow_the_order_chosen(keys, phrase, words):
    assert english_phrase(keys) == phrase
    assert spanish_words(keys) == words
