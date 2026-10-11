# Build Plan

Each step is small and ends with a check I review before moving on.

## Step 1: Catalog feed check (only step that touches the live library)
- Fetch 3 feeds, one request each with a pause between, and save raw XML
  as fixtures in tests/fixtures/:
  - a physical book: "Dragons Love Tacos" by Adam Rubin (should also
    show the "Tacos 2" sequel hit)
  - a book on Libby
  - a query with no results
  - a Spanish title with an accent (4th fixture, my pick)
- Report what each feed contains: field names, how ID, format, ISBN and
  call number appear, any language field, what an empty result looks like.
- Check: I read the findings before any parser exists. If the feed isn't
  what CLAUDE.md assumes, adjust the spec first.

## Step 2: Project skeleton
- app.py with a placeholder page, tests/ folder, pytest config if needed.
- Confirm .gitignore covers secrets.toml and .venv (by name only).
- Check: streamlit run app.py loads, pytest runs with zero tests.

## Step 3: Catalog feed parser
- Pure function: feed XML -> list of items (title, author, ID, format,
  ISBN if present). Uses xml.etree. Keeps only SD_ILS and OVERDRIVE.
- Tests against fixtures: physical, Libby, empty, malformed XML.
- Check: pytest passes, no test touches the network.

## Step 4: Title and author matching
- Pure function: candidate (title, author) + feed item -> match or not.
- Title: normalize case, punctuation, accents, leading articles; ignore
  subtitle after a colon. A number or extra trailing word = different book.
- Author: match on last name, handles "Last, First" and "First Last".
- Tests: exact match, "Tacos" vs "Tacos 2" (no match), articles, accents,
  wrong author, translated title (no match), multi-author record.
- Check: sequel case fails to match.

## Step 5: Library lookup with badges
- For one candidate: build feed URL and parent search link; one request,
  10s timeout, no retry; parse, keep matches, combine into one result
  with badges (shelf, Libby, or both).
- Cache with st.cache_data, 24h TTL, keyed by title + author only.
- 1 second delay on live requests only, not cache hits.
- Tests: HTTP mocked with fixtures, plus timeout and HTTP error.
- Check: logic works mocked; one real call from the command line succeeds.

## Step 6: Haiku suggestions
- Call claude-haiku-4-5 with tool use for 15 candidates: title, author,
  reason, estimated level, language.
- Prompt gets grade and per-language levels. Interests wrapped as data,
  not instructions. No input logging.
- Both languages: rough 50/50 split.
- Bad response: one retry, then error. Missing key: clear setup message.
- Tests (mocked client): valid JSON, malformed, missing fields, retry.
- Check: one real Haiku call from the command line, key never printed.

## Step 7: Input form
- Grade (K-5) and language (English, Spanish, or both).
- Reading level per selected language as Grade Equivalent, hint:
  "Check your child's Star report for Grade Equiv."
- Interests, 200 characters max, hint: "Don't enter your child's name."
- Check: form validates inputs.

## Step 8: Wire it together
- Haiku, then check candidates in order until 5 match, spinner with progress.
- Show title, author, reason, badge, link, estimated level and language,
  and "Reading levels are estimates."
- Friendly messages: zero matches (with search link), catalog down, bad JSON.
- Check: I run the app in the browser and check it myself.

## Step 9: Final pass
- Full test suite. Re-check rules against code: no input logging, no key
  printing, one request per book, no padding.

## Assumptions
- Both languages: ~50/50 split, results in Haiku's order.
- No language field in feed: show Haiku's language as an estimate.
- Model ID kept as one constant so it's easy to change.
- I review every step and commit myself.
