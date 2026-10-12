import base64
import re
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import theme

ROOT = Path(__file__).parent.parent
SVG_FILES = sorted((ROOT / "assets" / "characters").glob("*.svg"))
ALLOWED_TAGS = {"svg", "g", "path", "circle", "ellipse", "rect", "polygon", "defs", "clipPath"}
EXPECTED_CHARACTERS = {"dragon", "dinosaur", "owl", "soccer-ball", "rocket", "books"}


def tag(element):
    return element.tag.split("}")[-1]


# --- the six drawings ---

def test_exactly_the_six_agreed_characters_exist():
    assert {f.stem for f in SVG_FILES} == EXPECTED_CHARACTERS


@pytest.mark.parametrize("path", SVG_FILES, ids=lambda p: p.stem)
def test_each_drawing_is_small_valid_xml_with_only_plain_shapes(path):
    assert path.stat().st_size < 4000
    root = ET.parse(path).getroot()
    assert tag(root) == "svg" and root.get("viewBox") == "0 0 200 200"
    tags = {tag(element) for element in root.iter()}
    assert tags <= ALLOWED_TAGS, tags - ALLOWED_TAGS      # no script, image, text, style, use, foreignObject


@pytest.mark.parametrize("path", SVG_FILES, ids=lambda p: p.stem)
def test_each_drawing_is_self_contained(path):
    text = path.read_text(encoding="utf-8")
    assert not re.search(r"https?://(?!www\.w3\.org/2000/svg)", text)    # only the SVG namespace
    assert "href" not in text and "@import" not in text and "font" not in text and "on" + "load" not in text
    assert all(ref.startswith("#") for ref in re.findall(r"url\(([^)]*)\)", text))   # only internal references


# --- the CSS built from them ---

def decode(uri):
    return base64.b64decode(uri.split(",", 1)[1]).decode("utf-8")


def tier_css(css, marker):
    start = css.index(marker)
    return css[start:css.index("@media", start + 1)] if "@media" in css[start + 1:] else css[start:]


def test_every_screen_size_has_its_own_set_of_characters():
    css = theme.background_css()
    assert "@media (min-width: 1100px)" in css
    assert "@media (min-width: 641px) and (max-width: 1099px)" in css
    assert "@media (max-width: 640px)" in css
    assert css.count("data:image/svg+xml;base64,") == len(theme.WIDE) + len(theme.MEDIUM) + len(theme.PHONE)


def test_wide_screens_get_all_six_medium_four_and_phones_two():
    assert {n for n, _, _ in theme.WIDE} == EXPECTED_CHARACTERS
    assert len(theme.MEDIUM) == 4 and len(theme.PHONE) == 2
    assert {n for n, _, _ in theme.MEDIUM} <= EXPECTED_CHARACTERS and {n for n, _, _ in theme.PHONE} <= EXPECTED_CHARACTERS


def test_characters_stay_small_and_at_the_edges():
    for placements, biggest in ((theme.WIDE, 190), (theme.MEDIUM, 110), (theme.PHONE, 80)):
        for _, position, size in placements:
            assert size <= biggest
            assert re.fullmatch(r"(left|right) \d+(%|px) (top|bottom) \d+(%|px)", position), position
            assert not re.search(r"\b(4\d|5\d|6\d)%", position.split(" ")[1]), position   # nothing near the center


def test_phones_get_the_smallest_characters():
    assert max(s for _, _, s in theme.PHONE) < min(s for _, _, s in theme.MEDIUM)


def test_each_embedded_picture_decodes_to_the_faded_original():
    css = theme.background_css()
    for uri in re.findall(r'url\("(data:image/svg\+xml;base64,[^"]+)"\)', css):
        svg = decode(uri)
        root = ET.fromstring(svg)
        assert tag(root) == "svg" and root.get("opacity") == str(theme.FADE)


def test_css_loads_nothing_from_outside_and_cannot_break_out_of_its_style_tag():
    css = theme.background_css()
    assert "http" not in css.replace("data:image/svg+xml;base64,", "")
    assert "<" not in css and "</style" not in css and "@import" not in css


def test_the_form_sits_on_a_mostly_opaque_white_panel():
    css = theme.background_css()
    assert '[data-testid="stMainBlockContainer"]' in css
    alpha = float(re.search(r"rgba\(255, 255, 255, ([0-9.]+)\)", css).group(1))
    assert alpha >= 0.9


def test_the_panel_leaves_room_for_the_characters_at_each_size():
    css = theme.background_css()
    medium = css[css.index("@media (min-width: 641px) and (max-width: 1099px) {\n  [data-testid"):]
    assert "calc(100% - 220px)" in medium.split("@media (max-width: 640px)")[0]
    phone = css[css.index("@media (max-width: 640px) {\n  [data-testid"):]
    assert "margin: 8.25rem auto" in phone                  # a strip above the panel for the two small characters


def test_the_page_has_no_animation():
    css = theme.background_css()
    assert "animation" not in css and "transition" not in css and "@keyframes" not in css


# --- the light theme ---

def luminance(hex_color):
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def config():
    return tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text())["theme"]


def test_config_forces_the_light_theme_and_holds_only_colors():
    parsed = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text())
    assert list(parsed) == ["theme"]                       # no other settings, nothing secret
    assert config()["base"] == "light"
    colors = {k: v for k, v in config().items() if k != "base"}
    assert set(colors) == {"primaryColor", "backgroundColor", "secondaryBackgroundColor", "textColor"}
    assert all(re.fullmatch(r"#[0-9A-Fa-f]{6}", v) for v in colors.values())


def test_page_colors_have_readable_contrast():
    theme_colors = config()
    assert theme.CREAM == theme_colors["backgroundColor"]
    assert contrast(theme_colors["textColor"], "#FFFFFF") >= 7          # text on the white panel
    assert contrast(theme_colors["textColor"], theme_colors["backgroundColor"]) >= 7
    assert contrast(theme_colors["textColor"], theme_colors["secondaryBackgroundColor"]) >= 7
    assert contrast("#FFFFFF", theme_colors["primaryColor"]) >= 4.5     # white text on the main button
