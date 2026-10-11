"""Decide whether a catalog item is the book Claude suggested.

A hit is not a match: the catalog also returns sequels and related books, so a
book matches only when both the title and the author agree.
"""
import re
import unicodedata

ARTICLES = {"the", "a", "an", "el", "la", "los", "las"}
NAME_SUFFIXES = {"jr", "sr", "ii", "iii"}


def _fold(text):
    """Lowercase, drop accents, drop apostrophes, turn other punctuation into spaces."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"['’`]", "", text)
    text = re.sub(r"[^\w\s]|_", " ", text)
    return " ".join(text.split())


def normalize_title(title):
    # The main title: everything before the first colon, folded, with one
    # leading article dropped. "Tacos 2" stays different from "Tacos".
    main = title.split(":", 1)[0]
    words = _fold(main).split()
    if len(words) > 1 and words[0] in ARTICLES:
        words = words[1:]
    return " ".join(words)


def normalize_subtitle(title):
    """Everything after the first colon, folded. Empty if there is none."""
    return _fold(title.partition(":")[2])


def search_surname(author):
    """The author's last name for the catalog search, without Jr./Sr./III.

    The catalog files authors as "Martin, Bill, 1916-2004." so a "Jr." in the
    query can make it return almost nothing.
    """
    author = author.strip()
    if "," in author:
        return author.split(",", 1)[0].strip()
    words = [w for w in author.split() if _fold(w) not in NAME_SUFFIXES]
    return words[-1].strip(".,;") if words else ""


def _last_name(person):
    """Last name from "Last, First, dates role" or "First Last"."""
    if "," in person:
        return _fold(person.split(",", 1)[0])
    words = [w for w in _fold(person).split() if w not in NAME_SUFFIXES]
    return words[-1] if words else ""


def primary_last_name(author):
    """Folded last name of the first person listed, e.g. "rubin" for
    "Rubin, Adam/ Salmieri, Daniel (ILT)". Used to tell books apart."""
    return _last_name(author.split("/", 1)[0])


def author_matches(candidate_author, catalog_author):
    """True if the candidate's last name is one of the catalog's authors.

    The catalog lists people separated by "/", e.g. "Rubin, Adam/ Salmieri,
    Daniel (ILT)". Any listed person counts.
    """
    wanted = candidate_author.strip()
    if not wanted:
        return False
    if "," in wanted:
        wanted_last = _last_name(wanted)
        folded = None
    else:
        wanted_last = None
        folded = " ".join(w for w in _fold(wanted).split() if w not in NAME_SUFFIXES)
    for person in catalog_author.split("/"):
        last = _last_name(person)
        if not last:
            continue
        if wanted_last is not None:
            if last == wanted_last:
                return True
        elif folded == last or folded.endswith(" " + last):
            # endswith handles two-word last names: "Garcia Marquez, Gabriel".
            return True
    return False


def is_match(title, author, item):
    """Main titles must be equal. A subtitle is ignored only when one side
    has none: two different subtitles are two different books ("Pete the Cat:
    I Love My White Shoes" is not "Pete the Cat: Rocking in My School Shoes")."""
    wanted = normalize_title(title)
    if not wanted or wanted != normalize_title(item.title):
        return False
    wanted_sub, item_sub = normalize_subtitle(title), normalize_subtitle(item.title)
    if wanted_sub and item_sub and wanted_sub != item_sub:
        return False
    return author_matches(author, item.author)


def matching_items(title, author, items):
    """All items that are the suggested book.

    Ambiguity guard: a suggestion with no subtitle that matches two or more
    differently subtitled books ("Pete the Cat" vs. a list of Pete books) is
    unsure, so it matches nothing. An exact subtitle-less record is the one
    case that settles it. One subtitled book (in any formats) is not
    ambiguous: "Dragons Love Tacos 2" is "Dragons love tacos 2 : the sequel".
    """
    matches = [item for item in items if is_match(title, author, item)]
    if normalize_subtitle(title):
        return matches
    subtitles = {normalize_subtitle(m.title) for m in matches} - {""}
    if len(subtitles) <= 1:
        return matches
    return [m for m in matches if not normalize_subtitle(m.title)]
