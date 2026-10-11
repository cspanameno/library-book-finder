"""Manual checks that call Haiku and/or the real library catalog.

Run from the project root:
  python scripts/try_haiku.py           # print Haiku's suggestions (English-style flow)
  python scripts/try_haiku.py --check   # also check them against the real catalog
  python scripts/try_haiku.py --check --all   # check all of them, not just until 5 are found
  python scripts/try_haiku.py --title "Brown Bear, Brown Bear, What Do You See?" --author "Bill Martin Jr."
                                        # skip Haiku: look up one book (no API key needed)
  python scripts/try_haiku.py --spanish # the catalog-first Spanish flow, start to finish
  python scripts/try_haiku.py --spanish --interests "dinosaurs and music" --spanish-level 2.5

Reads the API key from .streamlit/secrets.toml and never prints it.
Prints titles, authors, catalog results, and how many Haiku tokens were used.

--check works like the app: one catalog request per book, a 1 second pause
between requests, and it stops once 5 books are found. --all is for testing
only: it checks every suggestion (up to 15 requests), which the app never does.

--spanish makes 2 Haiku calls (search words, then picks) and 1 to 2 catalog
searches (each can take 15+ seconds). It uses the real code path the app will
use, except the 24-hour cache, so every run asks the library again.
"""
import argparse
import logging
import sys
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
logging.disable(logging.WARNING)  # hide streamlit's "no runtime found" warning on import
from lookup import CatalogUnavailable, feed_url, lookup_book, search_spanish_children  # noqa: E402
logging.disable(logging.NOTSET)
from spanish import PICK_TOOL_NAME, find_spanish_books  # noqa: E402
from suggest import Request, SuggestionError, api_key_from, make_client, suggest_books  # noqa: E402

SECRETS = ROOT / ".streamlit" / "secrets.toml"
WANTED = 5
TEST_PROFILE = Request(
    grade="1",
    levels={"English": 1.0, "Spanish": 3.0},
    interests="dragons and soccer",
)
# claude-haiku-4-5 list prices, dollars per million tokens (an estimate for this script only).
INPUT_PRICE, OUTPUT_PRICE = 1.0, 5.0


class RecordingClient:
    """Wraps the real client to keep each response, for token counts and diagnostics.
    Requests and responses pass through unchanged."""

    def __init__(self, client):
        self._client = client
        self.responses = []
        self.messages = self

    def create(self, **kwargs):
        response = self._client.messages.create(**kwargs)
        self.responses.append(response)
        return response


def print_usage(recorder):
    n = len(recorder.responses)
    tokens_in = sum(r.usage.input_tokens for r in recorder.responses)
    tokens_out = sum(r.usage.output_tokens for r in recorder.responses)
    cost = tokens_in * INPUT_PRICE / 1e6 + tokens_out * OUTPUT_PRICE / 1e6
    print(f"\nHaiku: {n} call{'s' if n != 1 else ''}, {tokens_in} input + {tokens_out} output tokens "
          f"(about ${cost:.4f})")


def badges(availability):
    names = []
    if availability.on_shelf:
        names.append("On the shelf")
    if availability.on_libby:
        names.append("On Libby")
    return " + ".join(names)


def check_catalog(candidates, check_all=False):
    found = 0
    checked = 0
    for c in candidates:
        checked += 1
        try:
            availability = lookup_book(c.title, c.author)
        except CatalogUnavailable:
            print(f"\nCatalog unavailable after {checked - 1} books checked. Stopping.")
            return
        label = f"{c.language} | {c.title} | {c.author}"
        if availability.found:
            found += 1
            print(f"FOUND   {label}\n        {badges(availability)}  {availability.search_url}")
        else:
            print(f"no      {label}")
        if found == WANTED and not check_all:
            break
    print(f"\n{found} found out of {checked} checked ({len(candidates)} suggested)")


def check_one(title, author):
    """One book straight through the library lookup. No Haiku, no API key."""
    print(f"Catalog request: {feed_url(title, author)}")
    try:
        availability = lookup_book(title, author)
    except CatalogUnavailable:
        print("Catalog unavailable.")
        return 1
    if availability.found:
        print(f"FOUND   {title} | {author}\n        {badges(availability)}  {availability.search_url}")
    else:
        print(f"no      {title} | {author}\n        {availability.search_url}")
    return 0


def timed_search(word):
    """The real catalog search for one word, with its timing printed."""
    started = time.monotonic()
    try:
        items = search_spanish_children(word)
    except CatalogUnavailable:
        print(f"  “{word}”: catalog unavailable after {time.monotonic() - started:.1f}s")
        raise
    print(f"  “{word}”: {len(items)} books in {time.monotonic() - started:.1f}s")
    return items


def haiku_pick_ids(recorder):
    """The IDs Haiku returned in its pick call, before the code checked them."""
    ids = []
    for response in recorder.responses:
        for block in response.content:
            if block.type == "tool_use" and block.name == PICK_TOOL_NAME:
                ids += [str(entry.get("id")) for entry in block.input.get("picks", []) if isinstance(entry, dict)]
    return ids


def run_spanish(recorder, interests, level):
    request = Request(grade=TEST_PROFILE.grade, levels={"Spanish": level}, interests=interests)
    print(f"Profile: grade {request.grade}, Spanish level {level}, interests “{interests}”\n")
    try:
        result = find_spanish_books(request, recorder, search=timed_search,
                                    progress=lambda message: print(message))
    except SuggestionError as err:
        print(f"\n{err}")
        return 1
    except CatalogUnavailable:
        print("\nEvery catalog search failed. Nothing to choose from.")
        return 1
    finally:
        print_usage(recorder)

    per_word = ", ".join(f"{w} {sum(w in b.words for b in result.pool.books)}" for w in result.words
                         if w in result.found_per_word)
    print(f"\nPool: {len(result.pool)} books given to Haiku ({per_word})")
    if result.failed_words:
        print(f"Searches that failed and were skipped: {', '.join(result.failed_words)}")

    asked = haiku_pick_ids(recorder)
    kept = {p.book.pool_id for p in result.picks}
    rejected = [i for i in asked if i not in kept]
    print(f"Haiku returned {len(asked)} IDs; the code kept {len(result.picks)}"
          + (f" and rejected {len(rejected)}: {', '.join(rejected)}" if rejected else "")
          + "\n")

    if not result.picks:
        print("No books picked.")
    for n, pick in enumerate(result.picks, start=1):
        item = pick.book.item
        print(f"{n}. [{pick.book.pool_id}] {item.title}\n"
              f"   {item.author} | call number {item.call_number} | found by: {', '.join(pick.book.words)}\n"
              f"   level {pick.estimated_level or '?'} | {pick.reason}")
    print("\n(Titles and authors are raw catalog text. The display formatter comes in Step 8.)")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true",
                        help="check the suggestions against the real library catalog")
    parser.add_argument("--all", action="store_true",
                        help="with --check, check every suggestion instead of stopping at 5 (testing only)")
    parser.add_argument("--title", help="skip Haiku: look up this one book (needs --author)")
    parser.add_argument("--author", help="skip Haiku: author for --title, e.g. \"Bill Martin Jr.\"")
    parser.add_argument("--spanish", action="store_true",
                        help="run the catalog-first Spanish flow (2 Haiku calls, 1-2 catalog searches)")
    parser.add_argument("--interests", default=TEST_PROFILE.interests,
                        help="with --spanish: the child's interests (default: %(default)s)")
    parser.add_argument("--spanish-level", type=float, default=TEST_PROFILE.levels["Spanish"],
                        help="with --spanish: Spanish reading level as a grade equivalent (default: %(default)s)")
    args = parser.parse_args()
    if args.all and not args.check:
        parser.error("--all only works together with --check")
    if bool(args.title) != bool(args.author):
        parser.error("--title and --author go together")
    if args.title and (args.check or args.all or args.spanish):
        parser.error("--title/--author can't be combined with --check, --all or --spanish")
    if args.spanish and (args.check or args.all):
        parser.error("--spanish can't be combined with --check or --all")
    if not args.spanish and (args.interests != TEST_PROFILE.interests
                             or args.spanish_level != TEST_PROFILE.levels["Spanish"]):
        parser.error("--interests and --spanish-level only work with --spanish")
    if args.title:
        return check_one(args.title, args.author)

    try:
        with open(SECRETS, "rb") as f:
            secrets = tomllib.load(f)
    except FileNotFoundError:
        secrets = {}
    try:
        recorder = RecordingClient(make_client(api_key_from(secrets)))
    except SuggestionError as err:
        print(err)
        return 1

    if args.spanish:
        return run_spanish(recorder, args.interests, args.spanish_level)

    try:
        candidates = suggest_books(TEST_PROFILE, recorder)
    except SuggestionError as err:
        print(err)
        return 1

    if args.check:
        print(f"{len(candidates)} suggested. Checking the catalog...\n")
        check_catalog(candidates, check_all=args.all)
    else:
        for c in candidates:
            print(f"{c.language} | {c.title} | {c.author}")
        print(f"\n{len(candidates)} books")
    print_usage(recorder)
    return 0


if __name__ == "__main__":
    sys.exit(main())
