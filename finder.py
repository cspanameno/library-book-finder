"""Find up to 5 library books for a request.

English: Haiku suggests books and the catalog verifies each one.
Spanish: the catalog lists books and Haiku picks from that list.
Both: Spanish first, then English; the two lists alternate (English, Spanish,
English, Spanish, English). Only the catalog decides what the library has.
"""
from dataclasses import dataclass
from itertools import zip_longest

from display import display_author, display_title
from lookup import CatalogUnavailable, cached_lookup, cached_spanish_search, search_url
from matching import normalize_title, primary_last_name
from spanish import find_spanish_books
from suggest import Request, SuggestionError, suggest_books

BOOKS_WANTED = 5
MAX_SPANISH_IN_BOTH = 2  # in "both" mode English gets the other 3 (more if Spanish finds fewer)

CATALOG_DOWN = "The library catalog isn't responding right now. Please try again in a few minutes."
CATALOG_STOPPED = "The library catalog stopped responding partway through, so this list may be shorter than usual."
NO_RESULTS = "We couldn't find books for that. Try simple topics like dragons or soccer."


@dataclass(frozen=True)
class ShownBook:
    title: str
    author: str
    reason: str
    estimated_level: str
    language: str
    on_shelf: bool
    on_libby: bool
    search_url: str  # opens the library's normal catalog page


@dataclass(frozen=True)
class FindResult:
    books: tuple  # up to 5 ShownBooks
    notices: tuple = ()  # friendly notes to show above the list


def _only(request, language):
    """The same request, for one language."""
    return Request(request.grade, {language: request.levels[language]}, request.interests, request.spanish_words)


def _spanish_books(request, client, spanish_search, progress):
    result = find_spanish_books(_only(request, "Spanish"), client, search=spanish_search, progress=progress)
    books = []
    for pick in result.picks:
        title, author = display_title(pick.book.item.title), display_author(pick.book.item.author)
        books.append(ShownBook(title, author, pick.reason, pick.estimated_level, "Spanish",
                               on_shelf=True, on_libby=False, search_url=search_url(title, author)))
    return books, ()


def _english_books(request, client, target, lookup, progress):
    candidates = suggest_books(_only(request, "English"), client)
    candidates = [c for c in candidates if c.language == "English"]
    books, seen, notices = [], set(), ()
    for number, candidate in enumerate(candidates, start=1):
        if len(books) >= target:
            break
        progress(f"Checking the library catalog… ({number} of {len(candidates)})")
        try:
            availability = lookup(candidate.title, candidate.author)
        except CatalogUnavailable:
            if not books:
                raise
            return books, (CATALOG_STOPPED,)
        key = (normalize_title(candidate.title), primary_last_name(candidate.author))
        if availability.found and key not in seen:
            seen.add(key)
            books.append(ShownBook(candidate.title, candidate.author, candidate.reason,
                                   candidate.estimated_level, "English", availability.on_shelf,
                                   availability.on_libby, availability.search_url))
    return books, notices


def _alternate(english, spanish):
    merged = []
    for e, s in zip_longest(english, spanish):
        merged += [book for book in (e, s) if book is not None]
    return merged[:BOOKS_WANTED]


def find_books(request, client, progress=None, lookup=None, spanish_search=None):
    """Return a FindResult. Raises SuggestionError (Haiku trouble) or CatalogUnavailable
    when the search could not be done at all. An empty result is not an error."""
    progress = progress or (lambda message: None)
    lookup = lookup or cached_lookup
    spanish_search = spanish_search or cached_spanish_search
    wants_english, wants_spanish = "English" in request.levels, "Spanish" in request.levels

    if wants_spanish and not wants_english:
        books, notices = _spanish_books(request, client, spanish_search, progress)
        return FindResult(tuple(books[:BOOKS_WANTED]), notices)
    if wants_english and not wants_spanish:
        books, notices = _english_books(request, client, BOOKS_WANTED, lookup, progress)
        return FindResult(tuple(books), notices)

    # Both languages. A failure on one side leaves the other side's books, with a note.
    spanish, english, notices, errors = [], [], [], []
    try:
        spanish, _ = _spanish_books(request, client, spanish_search, progress)
    except (SuggestionError, CatalogUnavailable) as err:
        errors.append(err)
        notices.append("We couldn't search the Spanish shelves just now, so these are English books only.")
    english_target = BOOKS_WANTED - min(len(spanish), MAX_SPANISH_IN_BOTH)
    try:
        english, english_notices = _english_books(request, client, english_target, lookup, progress)
        notices += english_notices
    except (SuggestionError, CatalogUnavailable) as err:
        errors.append(err)
        notices.append("We couldn't search for English books just now, so these are Spanish books only.")
    if len(errors) == 2:
        raise errors[0]
    return FindResult(tuple(_alternate(english, spanish)), tuple(notices))
