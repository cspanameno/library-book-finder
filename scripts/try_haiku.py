"""Manual check: one real Haiku call for a test profile.

Run from the project root:
  python scripts/try_haiku.py           # print Haiku's suggestions
  python scripts/try_haiku.py --check   # also check them against the real catalog
  python scripts/try_haiku.py --check --all   # check all of them, not just until 5 are found

Reads the API key from .streamlit/secrets.toml and never prints it.
Prints only titles, authors, languages, and catalog results.

--check works like the app: one catalog request per book, a 1 second pause
between requests, and it stops once 5 books are found. --all is for testing
only: it checks every suggestion (up to 15 requests), which the app never does.
"""
import argparse
import logging
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
logging.disable(logging.WARNING)  # hide streamlit's "no runtime found" warning on import
from lookup import CatalogUnavailable, lookup_book  # noqa: E402
logging.disable(logging.NOTSET)
from suggest import Request, SuggestionError, api_key_from, make_client, suggest_books  # noqa: E402

SECRETS = ROOT / ".streamlit" / "secrets.toml"
WANTED = 5
TEST_PROFILE = Request(
    grade="1",
    levels={"English": 1.0, "Spanish": 3.0},
    interests="dragons and soccer",
)


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


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true",
                        help="check the suggestions against the real library catalog")
    parser.add_argument("--all", action="store_true",
                        help="with --check, check every suggestion instead of stopping at 5 (testing only)")
    args = parser.parse_args()
    if args.all and not args.check:
        parser.error("--all only works together with --check")

    try:
        with open(SECRETS, "rb") as f:
            secrets = tomllib.load(f)
    except FileNotFoundError:
        secrets = {}
    try:
        client = make_client(api_key_from(secrets))
        candidates = suggest_books(TEST_PROFILE, client)
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
