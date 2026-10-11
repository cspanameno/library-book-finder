"""Parse the San Leandro library catalog feed (Atom XML) into plain items."""
import html
import xml.etree.ElementTree as ET
from dataclasses import dataclass

ATOM = "{http://www.w3.org/2005/Atom}"


class CatalogParseError(ValueError):
    """The feed could not be read as a catalog feed."""


@dataclass(frozen=True)
class CatalogItem:
    title: str
    author: str  # raw author text, e.g. "Rubin, Adam, 1983- author."
    item_id: str
    format: str  # e.g. "Books", "eBook", "eAudiobook"
    kind: str  # "shelf" (physical book) or "libby" (ebook/audiobook)


def _clean(text):
    # Titles and content are escaped twice, so unescape once more after XML
    # parsing. \xa0 is the non-breaking space the feed uses between words.
    return html.unescape(text).replace("\xa0", " ").strip()


def _kind(item_id, fmt):
    if "OVERDRIVE" in item_id:
        return "libby"
    if item_id.startswith("ent://SD_ILS/") and fmt == "Books":
        return "shelf"
    return None


def parse_feed(xml_text):
    """Return the shelf and Libby items in a feed. Everything else is dropped."""
    end = xml_text.find("</feed>")
    if end == -1:
        raise CatalogParseError("No </feed> found")
    try:
        root = ET.fromstring(xml_text[: end + len("</feed>")])
    except ET.ParseError as err:
        raise CatalogParseError(f"Feed is not valid XML: {err}") from err

    items = []
    for entry in root.findall(f"{ATOM}entry"):
        title = _clean(entry.findtext(f"{ATOM}title", ""))
        item_id = (entry.findtext(f"{ATOM}id") or "").strip()
        author, fmt = "", ""
        content = entry.findtext(f"{ATOM}content", "")
        for line in content.split("<br/>"):
            line = _clean(line)
            if line.startswith("by "):
                author = line[3:].strip()
            elif line.startswith("Format:"):
                fmt = line[len("Format:"):].strip()
        kind = _kind(item_id, fmt)
        if kind and title:
            items.append(CatalogItem(title, author, item_id, fmt, kind))
    return items
