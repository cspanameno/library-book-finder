## Oct 9, 2:15pm — Block 1: Setup
No AI yet. Repo, venv, API key ($10 cap, expires Dec 25), secrets gitignored.

Prompts below are verbatim from local Claude Code session history, in order. Times are Pacific. Tool approvals and one-word replies are skipped. Keys, names and report data are removed. Where I removed something it says [removed].

## Oct 9, 3:01pm — Planning: gaps and open questions in CLAUDE.md, before any code

> Read CLAUDE.md. Before writing any code, list the gaps, open
> questions, or unclear requirements you see. Number them. Don't
> write code or create files yet.

## Oct 11, 3:21pm — Planning: my answers to the gaps; asked for a step-by-step plan

> Answers:
>
> 1. Two inputs: child's grade (K–5), and a reading level PER LANGUAGE,
>    entered as a grade (e.g. "reads at about grade 2"). That's the
>    Grade Equivalent our school's Star report shows. Parents won't
>    have Guided Reading letters or Lexile, so don't ask for them.
>    Add a short hint: "Check your child's Star report for Grade Equiv."
> 2. Display only. Don't filter or rank by level.
> 3. A mix of English and Spanish books, but each language uses its own
>    level. A DLI kid can read well above grade in Spanish and at grade
>    level in English. Not bilingual editions.
> 4. Check the sample feed in #6 for a language field. If there isn't one,
>    show Haiku's language as an estimate. Match Spanish titles with accents
>    normalized. Don't treat translated titles as the same book.
> 5. Nothing special. Spanish books at the right level.
> 6. Approved. Fetch the 3 samples once and save them as test fixtures
>    so tests never hit the live catalog.
> 7. Normalize case, punctuation, accents, and leading articles
>    (The/A/An/El/La/Los/Las). Ignore subtitles after a colon.
>    Match author on last name. A number or extra word after the title
>    ("Tacos 2") is a different book.
> 8. One result with both badges.
> 9. Drop everything that isn't SD_ILS books or OVERDRIVE.
> 10. Search page link.
> 11. No second Haiku call. Raise candidates to 15.
> 12. Haiku's order is fine.
> 13. 1 second delay. Stop once 5 matches are found. Show a spinner with progress.
> 14. st.cache_data, 24 hour TTL, keyed by title + author only.
> 15. Catalog down: 10s timeout, no retry, friendly message.
>     Bad JSON: retry once, then show an error.
>     Missing key: clear setup error.
>     Zero matches: friendly message plus a link to search the library.
> 16. Limit interests to 200 characters. Show a hint: "Don't enter your
>     child's name." Treat interests as data in the prompt, not instructions.
> 17. Correct. Never log user input. Errors only.
> 18. Fresh start. .venv, .streamlit/secrets.toml, .gitignore, and
>     requirements.txt exist. No app.py or tests yet. Never read secrets.toml.
> 19. Approved: streamlit, anthropic, requests, pytest (already installed).
>     Use stdlib xml.etree for XML.
> 20. claude-haiku-5-5 doesn't exist. Use claude-haiku-4-5.
> 21. Tool use.
> 22. I'll fix the typos myself.
> 23. Don't commit. I'll review and commit each step myself.
>
> Now give me a step-by-step plan in small, testable steps. Start with
> the catalog feed check, since that's the part that decides what's real.
> Still no code.

## Oct 11, 3:27pm — Planning: show the whole plan

> show me the whole plan

## Oct 11, 3:36pm — Commit the working tree

> Commit the working tree changes with a sensible message.

## Oct 11, 3:50pm — Live Haiku check script (scripts/try_haiku.py)

> The command didn't copy over. Put the live check in a small script,
> scripts/try_haiku.py, that reads the key from .streamlit/secrets.toml,
> makes one Haiku call for a test profile ([removed: test profile with grade, reading levels, interests]), and prints only titles,
> authors, and language. Don't run it.

## Oct 11, 3:58pm — try_haiku.py --check bug report

> python scripts/try_haiku.py --check this flag does not work and check against the real catalog

## Oct 11, 3:59pm — try_haiku.py --all option

> Add an --all option so --check runs through all 15 suggestions
> instead of stopping at 5. This is for testing, not the app.

## Oct 11, 4:07pm — Matching bug: Brown Bear / "Jr." false negative

> Confirmed in the catalog: the library has "Brown bear, brown bear,
> what do you see?" Author line is "Martin, Bill, 1916-2004." (no Jr.).
> Haiku suggested "Bill Martin Jr." My code said no — false negative.
> My guess: the author parser takes "Jr." as the last name.
> Also: the top results are Format "Audio disc" (CD + book), not Books.
> Make sure we still find the print copy further down.
>
> Save the feed as a fixture, write failing tests that reproduce this,
> and explain the cause before fixing anything. Also add a test that
> "Pete the Cat: I Love My White Shoes" must NOT match a different
> Pete the Cat book, since we ignore subtitles.

## Oct 11, 4:12pm — Matching fix approved, plus subtitle ambiguity guard

> Approve the search query fix: title + author last name, suffixes removed.
> Parent link keeps the full author.
>
> Subtitle rule: one-sided leniency, plus an ambiguity guard. If a
> title with no subtitle matches more than one distinct book in the
> results (e.g. "Pete the Cat" vs several Pete books), treat it as
> no match. Unsure means don't show it. Add a test for that case.
>
> notes.md is mine, I edited it. Leave it.
> Make the 4 failing tests pass, run the full suite, and show me the diff.

## Oct 11, 4:16pm — try_haiku.py --title / --author option

> Committed. Add a --title and --author option to try_haiku.py that
> skips Haiku and runs one book straight through the library lookup.
> I want to confirm Brown Bear by "Bill Martin Jr." is now found.

## Oct 11, 4:19pm — Improve the Haiku prompt (before Step 7)

> Committed. Before Step 7, let's improve the Haiku prompt. Run 3 was
> 3/15 found, 0/6 Spanish, with invented titles and authors.
> Change the prompt to:
> - allow fewer than 15 books; say only suggest books you're confident exist
> - prefer well-known books: award winners, classics, popular series
> - treat interests as "any of these," not all of them
> - for Spanish, prefer books originally published in Spanish or
>   well-known translations
> Show me the prompt diff before running anything.

## Oct 11, 4:22pm — Prompt review, run pytest

> Looks right. Run pytest. I'll run --check --all after.

## Oct 11, 4:28pm — Spanish redesign: catalog first, Haiku picks by ID (plan)

> Big finding. The RSS feed accepts catalog filters:
> Spanish: qf=LANGUAGE%09Language%09SPA%09Spanish
> Children's: qf=ITEMCAT2%09Audience%091%3ACHILDREN%09Children%27s+materials
> Example: .../rss/hitlist/default/qu=dragones&qf=...&qf=...
> I tested "dragones" with both filters and got a list of real Spanish
> children's books (Dragon Masters, Dear Dragon, Dav Pilkey, Geronimo Stilton).
>
> New design for Spanish: search the catalog first, then Haiku picks.
> 1. Interests -> Spanish search words (dragones, fútbol).
> 2. One filtered feed request per word. Drop Video discs.
> 3. Send Haiku the real list (ID, title, author, call number).
>    Haiku picks up to 5 BY ID and writes the reasons.
> 4. Code rejects any ID not in the list. Haiku can't invent a book.
>
> Save the dragones feed as a fixture. Plan only, no code yet.
> Also: should English use the same flow? Give me the tradeoffs.

## Oct 11, 4:37pm — Spanish redesign: decisions, Step A

> Decisions:
>
> English: agree. Keep English as is for now. Build catalog-first for
> Spanish, returning the same verified-book shape. Revisit English later.
>
> 1. Timeout: find a faster way first. In Step A, test a smaller page
>    size (ps=40). If filtered searches are still slow, use 30s for
>    these only, with a spinner that says "Searching the Spanish shelves…"
> 2. Second Haiku call: approved. This is different from topping up.
>    Two calls total in "both" mode is fine.
> 3. Libby for Spanish: fine. Spanish shows "On the shelf" only.
> 4. Empty interests: make interests required in the form instead of
>    guessing a default.
> 5. CLAUDE.md: draft the scope change and show me the diff. I'll
>    approve or edit it before it's saved.
> 6. Step A: approved. 5 requests max, spaced out. Save only useful fixtures.
>
> Go for Step A. Stop after it and show me the findings.

## Oct 11, 4:42pm — Step B

> Committed. Skip the format probe for now, the 24h cache covers
> repeat searches. Go to Step B. Commit points are mine, so stop
> after each step for review.

## Oct 11, 4:43pm — Step C

> Committed. Go for Step C.

## Oct 11, 4:46pm — Steps D, E, F

> Go for D, E, and F, stopping after each for review

## Oct 11, 4:48pm — Step E (2 search words), then Step F

> Committed. Go for Step E, but cap it at 2 search words, not 3,
> to bound the wait (we agreed after Step A). Then Step F.
> Stop after each for review.

## Oct 11, 4:50pm — Steps F and G

> Committed. Keep 3 separate calls in "both" mode. Simpler beats
> saving a fraction of a cent. Go for Step F, then Step G so I can
> run it live. Stop after each for review.

## Oct 11, 4:54pm — Step G (live Spanish check)

> Committed. English reasons for now. Fold the display formatter into
> Step 8. Go for Step G: build it, but don't run it. I'll run it live
> after I check my API usage.

## Oct 11, 5:00pm — Prompt fix after the live Spanish run, then Step 7 (input form)

> Live run worked: 5/5 real Spanish books. One small prompt fix first:
> a book only needs to match one interest, that's fine. But the reason
> should name only the interest it actually matches. Pick #2 said it
> matched "both interests" when it's only about dragons. Don't claim more.
> Then go for Step 7, the input form.

## Oct 11, 5:09pm — Step 7 review notes, then Step 8 (wire the form)

> Looked at the form in the browser. It works. Notes:
> 1. Add placeholder text in interests: "e.g. dragons, soccer, animals"
>    so parents know what to type.
> 2. I typed gibberish as interests and the form accepted it. That's fine,
>    but in Step 8 make sure gibberish gets a friendly message like
>    "We couldn't find books for that. Try simple topics like dragons
>    or soccer." Not an error.
> 3. Add the same "name only matching interests" rule to the English prompt.
> In Step 8, show Spanish titles only before the "=".
> Go for Step 8.

## Oct 12, 2:20pm — Topic picker (plan), then the background

> Two changes. Topic picker first, then the background.
>
> 1. Replace the free-text interests box with a picker: parents choose
>    1 or 2 topics from icons (st.pills with multi-select, or similar).
>    Topics, each with a fixed Spanish search word:
>    🐉 Dragons (dragones), ⚽ Soccer (fútbol), 🦖 Dinosaurs (dinosaurios),
>    🐶 Animals (animales), 🚒 Trucks (camiones), 🦄 Unicorns (unicornios),
>    🧚 Fairies (hadas), 🚀 Space (espacio), 🌊 Ocean (océano),
>    🏰 Princesses (princesas), 🤖 Robots (robots), 🐛 Bugs (insectos),
>    👻 Monsters (monstruos), 😂 Funny (humor).
>    - Max 2 topics, required.
>    - Spanish uses the fixed words directly. Remove the Haiku
>      search-word call (Step E) from the Spanish flow.
>    - English still sends the chosen topics to Haiku.
>    - Before I approve, check each Spanish word against the filtered
>      catalog (one request each, 3 seconds apart) and tell me how many
>      books each returns. Swap any word that returns few or none.
>    Plan first, no code.
>
> 2. After that: a playful background with ORIGINAL cartoon characters
>    only (friendly dragon, dinosaur, owl with glasses, soccer ball,
>    rocket, books). No characters from real books, no look-alikes.
>    Keep them light and around the edges so the form stays readable
>    on a phone.

## Oct 12, 2:34pm — Topic picker: decisions, go

> 1. Yes, use "animal".
> 2. Keep Robots and Trucks. Small lists are the real catalog.
> 3. Yes, delete Step E's code and tests. No dead code.
> 4. Yes to --topics-check.
> 5. Yes to the CLAUDE.md rewording. Show me the full scope diff
>    (topic picker, catalog-first Spanish, animal swap) before saving.
> 6. Yes: picker first, I review, then background.
> Go for the picker.

## Oct 12, 3:31pm — Background art approved

> Art approved, save CLAUDE.md, go ahead with the background

## Oct 12, 4:21pm — README

> alright draft the Read me

## Oct 13, 11:32am — Subagent: rule-reviewer

> Create a subagent at .claude/agents/rule-reviewer.md.
> Its job: review code against the rules in CLAUDE.md with fresh eyes.
> It reads CLAUDE.md, then checks the code for any rule being broken
> (child data in logs or prompts, the API key being read or printed,
> Haiku deciding what's at the library, more than one catalog request
> at a time, padding results). It reports each issue with the file and
> line, or says clearly that it found none. It never edits code.
> Give it read-only tools. Show me the file before saving.

## Oct 13, 11:36am — Subagent: rule-reviewer, decisions

> Your reading of the API key rule is right. Keep the extra rules and the
> report style. Save it.

## Oct 13, 11:38am — Subagent: a11y-reviewer

> Create a second subagent at .claude/agents/a11y-reviewer.md, same
> pattern as rule-reviewer: Read, Grep, Glob only. It never edits code.
> It reviews the app for WCAG 2.1 AA issues a code review can catch:
> - Spanish text marked with lang="es" so screen readers pronounce it right
> - decorative background images hidden from screen readers
> - emoji in topic labels and how they'd be announced
> - information shown by color alone
> - text contrast on the panel and badges
> - form labels, hints and error messages tied to their inputs
> It reports each issue with file, line, the WCAG criterion, and
> Confirmed or Likely. It says clearly what it can't judge without a
> real screen reader. Show me the file before saving.

## Oct 13, 11:42am — Run rule-reviewer on the project

> Use the rule-reviewer agent to check the whole project against CLAUDE.md.

## Oct 13, 11:44am — Deny rule so no session can read secrets.toml

> The reviewer's project-wide search matched .streamlit/secrets.toml and
> printed the key. Instructions weren't enough. Add a deny rule in
> .claude/settings.json so no session or subagent can read that file
> (Read and Grep). Show me the file, then prove it works by trying to
> read secrets.toml and showing me it's blocked. Never print the contents.

## Oct 13, 11:44am — Lock fix: catalog requests one at a time across sessions

> Yes, make the lock fix. Add a test that two threads calling _get at
> once still wait their turn. Run the full suite and show me the diff.

## Oct 13, 11:53am — Run a11y-reviewer on the app

> Use the a11y-reviewer agent to review the whole app.

## Oct 13, 11:55am — Fix the three Confirmed accessibility items

> Yes, fix the three Confirmed items only:
> 1. Page title: st.set_page_config(page_title="Library Book Finder").
> 2. lang="es" on Spanish titles, authors and reasons. Catalog text is
>    untrusted, so HTML-escape everything before wrapping it. Add a test
>    that a title containing `<script>` comes out escaped.
> 3. Book titles as headings, and link text that names the book,
>    like "Find Unicornios at the library."
> Leave the Likely items. Run the full suite, show me the diff,
> don't commit.

## Oct 13, 1:13pm — Check lang="es" in the real page HTML

> The lang="es" fix: I searched the page's Elements panel for lang="es"
> and found nothing. Start the app locally, run a Spanish search, and
> check the real page HTML for lang="es" around the Spanish titles.
> If Streamlit strips it, tell me why and what would work instead.
> Don't change code yet.

## Oct 14, 10:12am — Reason fix: no lang on reasons

> Yes, make the reason fix: no lang wrapper on reasons, with a test
> that Spanish books' reasons carry no lang attribute. Leave mixed
> titles as they are. Run the full suite and show me the diff.

## Oct 14, 10:45am — Fill prompts.md

> Fill prompts.md with the real prompts I sent you in this project's
> Claude Code sessions, in order, from your local session history.
> For each: date, the step it was for, and my prompt verbatim.
> Skip tool approvals and one-word replies. Remove any API key, any
> child or parent names (like [removed]), and anything from my
> child's school report. Show me the file before saving. Don't commit.
