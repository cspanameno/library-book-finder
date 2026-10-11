# Library Book Finder

## Purpose and users
Find a book for an elementary school student that matches their reading level from the local library. Most users are not technical. Some read in English or are part of the Dual-Language Immersion program in Spanish. I built this after struggling to find books that matched the kind of bbooks my 6 year old daughter can read at the San Leandro Public Library.
  
## Scope
A parent enters three things: reading level, interests, and language (English, Spanish or both). The app will return 5 books, that the San Leandro libraty actually has. 

How it works:
1. Claude (Haiku) suggests ~12 candidate books as structured JSON:
   title, author, one-line reason, estimated level, language.
2. The app checks each candidate against the library's catalog feed.
3. The app shows the first 5 that match, each with:
   - title and author
   - the one-line reason it fits this kid
   - a badge: "On the shelf" (physical book) or "On Libby" (ebook/audiobook)
   - a link to the library search for that book
4. If fewer than 5 match, show what we found. Never pad the list.

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
Link for parents (opens the normal catalog page):
https://sanle.ent.sirsi.net/client/en_US/default/search/results?qu=TITLE+AUTHOR

## Rules
- Show a book only if the catalog feed returned a matching title AND author.
  A wrong match is worse than showing fewer books.
- Never let Claude's output decide whether a book is at the library.
  Only the catalog feed decides that.
- Be polite to the library: one request per book, a short delay between
  requests, cache results. No bulk scraping.
- No child names or personal data in prompts, logs, or code.
- The API key lives only in .streamlit/secrets.toml. Never print or commit it.
- Make small changes, one step at a time. Explain what you changed.
- Ask me before adding any new dependency.
- Write tests for: parsing Claude's JSON, parsing the catalog feed, and
  title/author matching (including the sequel case).
- Use Claude Haiku for suggestions. Ask before switching models.
- Keep the UI plain. Show "Reading levels are estimates."

## How to run
source .venv/bin/activate
streamlit run app.py     # start the app
pytest                   # run tests
