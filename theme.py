"""The page background: original cartoon characters around the edges, faded,
behind a white panel that holds the form and results.

The characters live in assets/characters/*.svg and are embedded in the page's CSS
as data, so there is nothing to host. They never sit in the middle: wide screens
get six around the sides, medium screens four small ones in the corners, phones two.
"""
import base64
from functools import lru_cache
from pathlib import Path

import streamlit as st

CHARACTERS = Path(__file__).parent / "assets" / "characters"
FADE = 0.55  # how strong the characters are (1 is full color)
CREAM = "#FFF8EC"

# (file, CSS position, size in px) for each screen size.
WIDE = (  # 1100px and wider: plenty of room beside the panel
    ("dragon", "left 3% top 12%", 170),
    ("owl", "right 3% top 10%", 160),
    ("books", "left 2% top 52%", 150),
    ("rocket", "right 3% top 50%", 150),
    ("dinosaur", "left 4% bottom 4%", 180),
    ("soccer-ball", "right 5% bottom 5%", 130),
)
MEDIUM = (  # 641 to 1099px: small, in the corners
    ("dragon", "left 8px top 64px", 92),
    ("rocket", "right 8px top 64px", 84),
    ("books", "left 8px bottom 8px", 100),
    ("soccer-ball", "right 8px bottom 8px", 84),
)
PHONE = (  # 640px and narrower: two small ones in the strip above the panel
    ("dragon", "left 8px top 62px", 64),
    ("rocket", "right 8px top 62px", 60),
)


def _data_uri(name):
    svg = (CHARACTERS / f"{name}.svg").read_text(encoding="utf-8")
    svg = svg.replace("<svg ", f'<svg opacity="{FADE}" ', 1)  # fade the whole picture
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def _layers(placements):
    return (
        "background-image:" + ",".join(f'url("{_data_uri(n)}")' for n, _, _ in placements) + ";"
        "background-position:" + ",".join(position for _, position, _ in placements) + ";"
        "background-size:" + ",".join(f"{size}px" for _, _, size in placements) + ";"
    )


@lru_cache(maxsize=1)
def background_css():
    return f"""
.stApp {{ background-color: {CREAM}; background-repeat: no-repeat; }}
@media (min-width: 1100px) {{ .stApp {{ {_layers(WIDE)} }} }}
@media (min-width: 641px) and (max-width: 1099px) {{ .stApp {{ {_layers(MEDIUM)} }} }}
@media (max-width: 640px) {{ .stApp {{ {_layers(PHONE)} }} }}
[data-testid="stMainBlockContainer"] {{
  background: rgba(255, 255, 255, 0.92);
  border-radius: 20px;
  box-shadow: 0 2px 16px rgba(53, 64, 90, 0.10);
  margin: 1rem auto 3rem;
  padding: 3.5rem 1.75rem 2.5rem;
}}
@media (min-width: 641px) and (max-width: 1099px) {{
  [data-testid="stMainBlockContainer"] {{ width: calc(100% - 220px); max-width: 46rem; }}
}}
@media (max-width: 640px) {{
  [data-testid="stMainBlockContainer"] {{
    width: calc(100% - 1rem); margin: 8.25rem auto 3rem; padding: 2rem 1rem 2rem; border-radius: 16px;
  }}
}}
"""


def apply_background():
    st.markdown(f"<style>{background_css()}</style>", unsafe_allow_html=True)
