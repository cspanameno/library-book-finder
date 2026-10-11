"""The candidate pool: real catalog books that Haiku may choose from.

Each search word gives a list of books straight from the catalog. This module
merges those lists, drops repeats, caps the size, and gives every book a short
ID so Haiku can pick by ID. Anything not in the pool cannot be shown.
"""
from dataclasses import dataclass

from matching import normalize_subtitle, normalize_title, primary_last_name

PER_WORD_CAP = 40  # keeps the prompt small; the pool holds at most this many per search word


@dataclass(frozen=True)
class PoolBook:
    pool_id: str  # "B1", "B2", ... what Haiku picks by
    item: object  # the CatalogItem
    words: tuple  # search words whose results included this book


class Pool:
    def __init__(self, books):
        self.books = tuple(books)
        self._by_id = {b.pool_id: b for b in self.books}

    def get(self, pool_id):
        """The book with this ID, or None. Haiku cannot add books: unknown IDs return None."""
        return self._by_id.get(pool_id.strip()) if isinstance(pool_id, str) else None

    def __len__(self):
        return len(self.books)


def book_key(item):
    """Two catalog records with the same key are the same book (another edition or copy).
    The subtitle stays in the key: volume 1 and volume 2 are different books."""
    return (normalize_title(item.title), normalize_subtitle(item.title), primary_last_name(item.author))


def build_pool(results_by_word, per_word_cap=PER_WORD_CAP):
    """Merge {search word: [CatalogItem]} into a Pool.

    - Only shelf books with a title and an author are kept.
    - The same book found by several words, or listed in several editions, appears once.
    - Books found by more than one word come first (they fit more of the interests).
    - The rest alternate between the words, so one broad word can't crowd out another.
    - At most per_word_cap books for each search word.
    """
    words = list(results_by_word)
    unique = {}  # book key -> [item, [words]]
    for word in words:
        for item in results_by_word[word]:
            if item.kind != "shelf" or not item.title.strip() or not item.author.strip():
                continue
            entry = unique.setdefault(book_key(item), [item, []])
            if word not in entry[1]:
                entry[1].append(word)

    ordered = [(item, tuple(w)) for item, w in unique.values() if len(w) > 1]
    queues = [[(item, tuple(w)) for item, w in unique.values() if len(w) == 1 and w[0] == word]
              for word in words]
    while any(queues):
        for queue in queues:
            if queue:
                ordered.append(queue.pop(0))

    ordered = ordered[: per_word_cap * len(words)]
    return Pool(PoolBook(f"B{n}", item, w) for n, (item, w) in enumerate(ordered, start=1))
