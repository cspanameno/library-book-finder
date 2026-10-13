# Library Book Finder

Find books at the **San Leandro Public Library** that fit an elementary school
reader. A parent picks their child's grade, reading level, language and a topic or two,
and the app suggests up to 5 books that the library really has, in English,
Spanish, or both.

Built by a parent who kept struggling to find books at the right level, including
for the Spanish side of a Dual-Language Immersion program. It is a personal
project and is not affiliated with the library.

## What a parent does

1. Choose the child's **grade** (K to 5).
2. Choose **English**, **Spanish**, or **Both**.
3. Enter a **reading level** for each language. Use the **Grade Equiv.** from your
   child's Star report (for example, 2.5 means reading at about the middle of grade 2).
   A child can read above grade in Spanish and at grade level in English, so each
   language has its own level.
4. Tap **1 or 2 topics** (🐉 Dragons, ⚽ Soccer, 🦖 Dinosaurs, 🚀 Space, and so on).
5. Press **Find books**.

Each result shows the title and author, a one-line reason it fits, a badge
(**On the shelf** for a physical book, **On Libby** for an ebook or audiobook),
and a link that opens the library's own catalog search for that book.

Reading levels are estimates. If fewer than 5 books are found, you see only the
books that were found. The list is never padded.

## How it works

The one rule that shapes everything: **only the library's catalog decides what the
library has.** Claude (Haiku) never gets to say a book is on the shelf.

- **English.** Claude suggests up to 15 books it is confident exist. The app checks
  each one against the catalog, requiring the title *and* the author to match, and
  keeps the first 5 that match. A sequel does not count as a match for the original.
- **Spanish.** Each topic has a fixed Spanish search word (for example, Dragons is
  *dragones*). The app asks the catalog for Spanish children's books for that word,
  then Claude picks up to 5 **by ID** from that real list and writes the reasons.
  Any ID that is not on the list is thrown away, so Claude cannot invent a book.
- **Both.** Spanish runs first, then English, and the results alternate.

The full design, the catalog quirks, and the rules for working on the code are in
[CLAUDE.md](CLAUDE.md).

## What it does not do

- No accounts, no saved searches, and no data about the child is stored.
- Parents never type free text, so a child's name cannot end up in a prompt or a log.
- It does not check whether a book is checked out.
- No buying or affiliate links.

## Set up and run

You need Python 3.14 (the version this project was built with) and an
[Anthropic API key](https://console.anthropic.com/).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Put your key in `.streamlit/secrets.toml`. That file is git-ignored. Never commit
it or paste it anywhere:

```toml
ANTHROPIC_API_KEY = "your-key-here"
```

Start the app:

```bash
streamlit run app.py
```

If the key is missing, the page shows a setup message instead of results.

## Tests

```bash
pytest
```

The suite (over 400 tests) runs offline. It uses saved library feeds in
`tests/fixtures/` and fake Claude answers, so it never calls the library or the API
and never reads your secrets file.

## Live checks

`scripts/try_haiku.py` is for trying the real thing from the command line.
Run `python scripts/try_haiku.py --help` for all options:

```bash
python scripts/try_haiku.py --check            # Haiku suggests, then check them in the real catalog
python scripts/try_haiku.py --spanish          # the whole Spanish flow, with token use and cost
python scripts/try_haiku.py --topics-check     # test every topic's Spanish word (no API key needed)
python scripts/try_haiku.py --title "Brown Bear, Brown Bear, What Do You See?" --author "Bill Martin Jr."
```

These make real requests, so they cost a little and ask the library, politely, for
real data.

## Project layout

| Path | What it does |
|---|---|
| `app.py` | The Streamlit page: form, results, messages |
| `form.py`, `topics.py` | Form checks, and the 14 topics with their Spanish words |
| `finder.py` | Runs the English and Spanish flows and merges them |
| `suggest.py` | English: asks Haiku for suggestions |
| `lookup.py`, `catalog.py`, `matching.py` | Catalog requests, feed parsing, title and author matching |
| `spanish.py`, `pool.py` | Spanish: the candidate list and Haiku's picks by ID |
| `display.py` | Tidies catalog text for parents ("Rubin, Adam, 1983-" becomes "Adam Rubin") |
| `theme.py`, `assets/characters/` | The background and its six original cartoon characters |
| `scripts/try_haiku.py` | Live checks (see above) |
| `tests/` | The tests and the saved catalog feeds |

## Good to know

- **Searches can be slow.** Some Spanish words take 15 seconds or more to come back
  from the catalog, and a search with two of them can take around 30 seconds. Results
  are cached for 24 hours, so repeat searches are fast.
- **Spanish results are shelf books only.** The catalog's Spanish and children's
  filters do not cover Libby items, so Spanish never shows "On Libby".
- **Some topics have short lists.** Robots and Trucks return the fewest Spanish books
  (13 and 17) because that is what the catalog has.
- **Being polite to the library.** One request per book (English) or per topic word
  (Spanish), at least a second apart, cached for 24 hours. No bulk scraping.
- **The topic words were checked against the live catalog** and can go stale. Re-run
  `--topics-check` now and then.
- **The model** is `claude-haiku-4-5`. Switching models is a deliberate decision, not a
  quiet change.

## Credits

- Book availability comes from the San Leandro Public Library catalog (SirsiDynix Enterprise).
- Ebooks and audiobooks are borrowed through Libby.
- The six cartoon characters in the background (a dragon, a dinosaur, an owl with
  glasses, a soccer ball, a rocket, and a stack of books) were drawn from scratch for
  this project. None comes from a real book or character.
