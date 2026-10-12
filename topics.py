"""The topics a parent can pick from, each with a fixed Spanish catalog search word.

The words were checked against the library's filtered catalog (Spanish, children's
materials; run `python scripts/try_haiku.py --topics-check` to repeat it). Notes
from that check: "animal" instead of "animales" because "animales" takes about 55
seconds to answer and "animal" takes 8; Robots and Trucks return the fewest books
(13 and 17), which is the real size of the catalog.
"""
from dataclasses import dataclass

MAX_TOPICS = 2  # each Spanish search can take 15+ seconds, so two topics bound the wait


@dataclass(frozen=True)
class Topic:
    key: str  # also the English name, lowercase
    emoji: str
    spanish_word: str  # one word, used as-is to search the catalog

    @property
    def label(self):
        return f"{self.emoji} {self.key.capitalize()}"


TOPICS = (
    Topic("dragons", "🐉", "dragones"),
    Topic("soccer", "⚽", "fútbol"),
    Topic("dinosaurs", "🦖", "dinosaurios"),
    Topic("animals", "🐶", "animal"),
    Topic("trucks", "🚒", "camiones"),
    Topic("unicorns", "🦄", "unicornios"),
    Topic("fairies", "🧚", "hadas"),
    Topic("space", "🚀", "espacio"),
    Topic("ocean", "🌊", "océano"),
    Topic("princesses", "🏰", "princesas"),
    Topic("robots", "🤖", "robots"),
    Topic("bugs", "🐛", "insectos"),
    Topic("monsters", "👻", "monstruos"),
    Topic("funny", "😂", "humor"),
)

BY_KEY = {topic.key: topic for topic in TOPICS}


def english_phrase(keys):
    """"dragons", "dragons and soccer": what English prompts get as the interests."""
    return " and ".join(keys)


def spanish_words(keys):
    return tuple(BY_KEY[key].spanish_word for key in keys)
