import logging

import streamlit as st

from display import level_text, md_escape
from finder import CATALOG_DOWN, NO_RESULTS, find_books
from form import GRADES, LANGUAGE_CHOICES, validate_form
from lookup import CatalogUnavailable
from suggest import MAX_INTERESTS_CHARS, MissingApiKey, SuggestionError, api_key_from, make_client

LIBRARY_CATALOG = "https://sanle.ent.sirsi.net/client/en_US/default/"
SOMETHING_WENT_WRONG = "Something went wrong. Please try again."


def show_book(book):
    st.markdown(f"**{md_escape(book.title)}** by {md_escape(book.author)}")
    st.write(book.reason)
    badges = []
    if book.on_shelf:
        badges.append(":green-badge[On the shelf]")
    if book.on_libby:
        badges.append(":blue-badge[On Libby]")
    details = book.language
    if book.estimated_level:
        details += f" · Estimated level: {md_escape(level_text(book.estimated_level))}"
    st.markdown(" ".join(badges) + "  \n" + details)
    st.markdown(f"[Find it at the library]({book.search_url})")


def show_results(request):
    try:
        client = make_client(api_key_from(st.secrets))
    except MissingApiKey as err:
        st.error(str(err))
        return

    progress = st.empty()
    label = "Searching the Spanish shelves…" if "Spanish" in request.levels else "Looking for books…"
    try:
        with st.spinner(label):
            result = find_books(request, client, progress=progress.caption)
    except CatalogUnavailable:
        st.error(CATALOG_DOWN)
        return
    except SuggestionError as err:
        st.error(str(err))
        return
    except Exception as err:  # parents should never see a traceback; log the type only, never the input
        logging.getLogger(__name__).error("Search failed: %s", type(err).__name__)
        st.error(SOMETHING_WENT_WRONG)
        return
    finally:
        progress.empty()

    for notice in result.notices:
        st.info(notice)
    if not result.books:
        st.info(NO_RESULTS)
        st.markdown(f"[Search the library catalog yourself]({LIBRARY_CATALOG})")
        return
    for book in result.books:
        st.divider()
        show_book(book)
    if len(result.books) < 5:
        count = len(result.books)
        st.caption(f"We found {count} book{'s' if count != 1 else ''} at the library that fit.")


st.title("Library Book Finder")
st.write("Find books at the San Leandro Public Library that match your child's reading level.")

grade = st.selectbox("What grade is your child in?", GRADES, index=None, placeholder="Choose a grade")
language_choice = st.radio("What language should the books be in?", list(LANGUAGE_CHOICES), horizontal=True)

levels = {}
for language in LANGUAGE_CHOICES[language_choice]:
    levels[language] = st.number_input(
        f"Reading level in {language} (grade)",
        min_value=0.0, max_value=12.9, step=0.1, format="%.1f", value=None,
        placeholder="For example 2.5", key=f"level_{language}",
    )
st.caption("Check your child's Star report for Grade Equiv.")

interests = st.text_input(
    "What does your child like?", max_chars=MAX_INTERESTS_CHARS,
    placeholder="e.g. dragons, soccer, animals",
)
st.caption("Don't enter your child's name.")

if st.button("Find books", type="primary"):
    request, errors = validate_form(grade, language_choice, levels, interests)
    if errors:
        for message in errors:
            st.error(message)
    else:
        show_results(request)

st.caption("Reading levels are estimates.")
