# Library Book Finder

## Purpose and users
Find a book for an elementary school student that matches their reading level from the local library. Most users are not technical. Some read in English or are part of the Dual-Language Immersion program in Spanish. I built this after struggling to find books that matched the kind of bbooks my 6 year old daughter can read at the San Leandro Public Library.
  
## Scope
A parent enters four things: the child's grade (K-5), a reading level for each
language (the Star report's "Grade Equiv."), 1 or 2 topics picked from a fixed
list of icons, and language (English, Spanish or both). Parents never type free
text. The app will return up to 5 books that the San Leandro library actually has.

How it works, English (Haiku suggests, the catalog verifies):
1. Claude (Haiku) suggests up to 15 candidate books as structured JSON:
   title, author, one-line reason, estimated level, language. It is told to
   suggest only books it is confident exist, and to prefer well-known ones.
   The chosen topics are sent to it as the interests ("dragons and soccer").
2. The app checks each candidate against the library's catalog feed, one at a time.
3. The app shows the first 5 that match.

How it works, Spanish (the catalog lists, Haiku picks):
1. Each topic has a fixed Spanish search word (table below). No Claude call.
2. The app makes one filtered catalog request per word (Spanish, children's
   materials), drops DVDs and other non-book formats, merges and de-duplicates.
3. Claude (Haiku) gets that real list (ID, title, author, call number) and picks
   up to 5 BY ID, with a one-line reason and estimated level. The code rejects any
   ID that is not on the list, so Claude cannot invent a book.
4. Spanish books therefore come straight from the catalog; there is no title
   matching step, and the badge is always "On the shelf".

Both languages: Spanish runs first, then English, and the lists alternate
(English, Spanish, English, Spanish, English). If one side finds fewer, the
other fills in, never past 5.

Each book shows:
- title and author, tidied for parents ("Rubin, Adam, 1983- author." becomes
  "Adam Rubin"; Spanish titles stop before the " = " parallel title)
- the one-line reason it fits this kid
- a badge: "On the shelf" (physical book) and/or "On Libby" (ebook/audiobook)
- a link to the library search for that book
If fewer than 5 are found, show what we found. Never pad the list. If none are
found, show a friendly message and a link to the library catalog (not an error).

Topics and their Spanish search words (checked against the real catalog):
| Topic | Word | Topic | Word |
| Dragons | dragones | Princesses | princesas |
| Soccer | fútbol | Robots | robots |
| Dinosaurs | dinosaurios | Bugs | insectos |
| Animals | animal | Monsters | monstruos |
| Trucks | camiones | Funny | humor |
| Unicorns | unicornios | Space | espacio |
| Fairies | hadas | Ocean | océano |
- Animals uses "animal", not "animales": "animales" takes about 55 seconds to
  answer, "animal" about 8.
- Robots (13 books) and Trucks (17) are small because the catalog is small. Keep them.
- Re-check the words with `python scripts/try_haiku.py --topics-check`.

### Out of scope
- user accounts or saved searches
- storing any data about the child 
- buying or affiliate links 
- checking if the book is checked out 

## Library catalog feed
Search feed (RSS/XML):
https://sanle.ent.sirsi.net/client/rss/hitlist/default/qu=TITLE+AUTHOR
- Each item has a title, author, format, and sometimes an ISBN and call number.
- IDs starting with SD_ILS are library-owned items. Only those with "Format: Books" are physical books; SD_ILS also covers DVDs and "Electronic Resources", which we drop.
- IDs containing OVERDRIVE are Libby ebooks or audiobooks.
- The feed is Atom (not RSS). Author, format and ISBN are inside one escaped-HTML <content> field, and the response has junk after </feed> that must be stripped before parsing.
- Search returns related books too. "Dragons Love Tacos" also returns
  "Dragons Love Tacos 2". A hit is not a match.
- For title lookups the query is the title plus the author's last name only,
  never "Jr."/"Sr.": "Bill Martin Jr." in the query returns almost nothing.
Filtered search (used for Spanish) adds two filters to a search word:
https://sanle.ent.sirsi.net/client/rss/hitlist/default/qu=WORD&qf=LANGUAGE%09Language%09SPA%09Spanish&qf=ITEMCAT2%09Audience%091%3ACHILDREN%09Children%27s+materials
- Libby items do not carry these filters, so filtered results are shelf books only.
- A response holds at most 300 entries, and the page size cannot be changed.
  Some words take 15+ seconds, so filtered requests use a 30 second timeout
  (title lookups use 10). Accents in the word do not matter.
Link for parents (opens the normal catalog page):
https://sanle.ent.sirsi.net/client/en_US/default/search/results?qu=TITLE+AUTHOR

## Rules
- Show a book only if the catalog feed returned a matching title AND author.
  A wrong match is worse than showing fewer books. (Spanish books come from
  the catalog list itself.)
- Never let Claude's output decide whether a book is at the library.
  Only the catalog feed decides that. In the Spanish flow Claude only picks by
  ID from the catalog's list, and code rejects any ID that is not on it.
- Be polite to the library: one request per book (English) or per topic word
  (Spanish, at most 2 topics), at least 1 second between requests, cache
  results for 24 hours. No bulk scraping.
- No child names or personal data in prompts, logs, or code. Topics come from
  a fixed list, so no free text from a parent reaches a prompt.
- The API key lives only in .streamlit/secrets.toml. Never print or commit it.
- Make small changes, one step at a time. Explain what you changed.
- Ask me before adding any new dependency.
- Write tests for: parsing Claude's JSON, parsing the catalog feed, and
  title/author matching (including the sequel case), picks by ID (including
  invented IDs), the topic words, and form validation.
- Use Claude Haiku (claude-haiku-4-5) for suggestions and picks. Ask before
  switching models.
- Keep the UI simple and readable. A light background of original
  illustrations is fine (nothing from real books). Show "Reading levels are estimates."

## How to run
source .venv/bin/activate
streamlit run app.py     # start the app
pytest                   # run tests
python scripts/try_haiku.py --help   # live checks (they call Haiku and/or the real catalog)
