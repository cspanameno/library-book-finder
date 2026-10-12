"""Tidy catalog text for parents. The catalog files records the way a card
catalog did ("Rubin, Adam, 1983- author." and "Title = Parallel title"); parents
expect "Adam Rubin" and just the title."""
import re

SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}
TITLES = {"dr.", "mr.", "mrs.", "ms."}


def display_title(raw):
    """The title as a parent would say it: nothing after " = " (a parallel title
    in another language) or " / " (the statement of responsibility)."""
    title = raw
    for separator in (" = ", " / "):
        title = title.split(separator, 1)[0]
    title = re.sub(r"\s+:\s+", ": ", title)
    title = " ".join(title.split()).rstrip(" /=;:,.") or " ".join(raw.split())
    return title


def _given_name(text):
    words = text.split()
    if all(len(w.rstrip(".")) <= 1 for w in words):
        return text  # initials, "J. K."
    if words and words[-1].lower() in TITLES:
        return text  # "Dr."
    return text.rstrip(".")  # catalog punctuation: "Aurélie."


def _strip_dates_and_roles(part):
    """Remove birth/death years ("Christopher 1983-") and a role glued on after a
    period ("Jake. author") from one comma-separated piece."""
    part = re.sub(r"\s*\b\d{3,4}\s*-\s*(\d{3,4})?", "", part)
    part = re.sub(r"\.\s+[a-z].*$", ".", part)
    part = re.sub(r"\s+\.", ".", part)  # left behind when a "(...)" was removed
    return part.strip()


def display_author(raw):
    """"Last, First, dates role." becomes "First Last". Only the first person
    listed is shown. "Martin, Jr., Bill" becomes "Bill Martin Jr."."""
    first = " ".join(re.sub(r"\([^)]*\)", "", raw.split("/")[0]).split())
    parts = [_strip_dates_and_roles(part) for part in first.split(",")]
    parts = [part for part in parts if part]
    if not parts:
        return raw.strip()
    if len(parts) == 1:
        return parts[0]
    last, suffix, given = parts[0], "", ""
    for part in parts[1:]:
        if part.rstrip(".").lower() in SUFFIXES:
            suffix = suffix or part
        elif any(ch.isdigit() for ch in part) or part[0].islower():
            continue  # leftover numbers, and roles like "author" or "illustrator."
        elif not given:
            given = _given_name(part)
    return " ".join(piece for piece in (given, last, suffix) if piece)


def md_escape(text):
    """Make text safe to show inside Streamlit markdown (titles and reasons come
    from Claude and the catalog, and may contain * _ [ ] $ and the like)."""
    return re.sub(r"([\\`*_{}\[\]<>()#+!|~$:])", r"\\\1", text)


def level_text(level):
    """"2.5" becomes "grade 2.5"; anything else Haiku wrote is shown as it is."""
    level = " ".join((level or "").split())
    if re.fullmatch(r"\d+(\.\d+)?", level):
        return f"grade {level}"
    return level
