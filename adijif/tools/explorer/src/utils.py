"""Utility functions and base classes for the explorer."""

import base64
import os
from abc import ABC, abstractmethod
from functools import lru_cache

import streamlit as st

_EXPLORER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# st.set_page_config(layout="wide")


class Page(ABC):
    """Base class for all page types."""

    @abstractmethod
    def write(self) -> None:
        """Render the page content."""
        pass


def add_custom_css() -> None:
    """Add custom CSS styling to the Streamlit app."""
    st.html(
        """
        <style>
            .stMainBlockContainer {
                max-width:1200px;
            }
        </style>
        """,
    )
    # st .markdown(
    #     """
    #     <style>
    #         section.main > div {max-width:1000px;}
    #     </style>
    #     """,
    #     unsafe_allow_html=True,
    # )


@lru_cache(maxsize=2)
def _logo_data_uri(name: str) -> str:
    with open(os.path.join(_EXPLORER_DIR, name), "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_sidebar_logo() -> None:
    """Render the PyADI-JIF logo with theme-aware variants.

    On first paint Streamlit hasn't yet reported the active theme, so we
    emit a <picture> element whose <source> uses prefers-color-scheme.
    The browser picks the right variant before any rerun. Once
    st.context.theme.type is populated (after the frontend reports it),
    we render an explicit <img> for the chosen theme — this covers the
    case where the user manually overrode Streamlit's theme away from
    their OS preference.
    """
    light = _logo_data_uri("PyADI-JIF_logo.png")
    dark = _logo_data_uri("PyADI-JIF_logo_dark.png")
    theme_type = getattr(st.context.theme, "type", None)
    if theme_type == "dark":
        html = f'<img src="{dark}" style="width:100%">'
    elif theme_type == "light":
        html = f'<img src="{light}" style="width:100%">'
    else:
        html = (
            "<picture>"
            f'<source srcset="{dark}" '
            'media="(prefers-color-scheme: dark)">'
            f'<img src="{light}" style="width:100%">'
            "</picture>"
        )
    with st.sidebar:
        st.html(html)
