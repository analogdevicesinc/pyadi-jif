"""Utility functions and base classes for the explorer."""

import base64
import os
from abc import ABC, abstractmethod
from functools import lru_cache

import streamlit as st

_EXPLORER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# st.set_page_config(layout="wide")


def _slug(name: str) -> str:
    """Turn a page name into a key-safe slug.

    >>> _slug("ADF4030 System Designer")
    'adf4030_system_designer'
    """
    return "".join(c if c.isalnum() else "_" for c in name.lower()).strip("_")


class Page(ABC):
    """Base class for all explorer pages.

    Subclasses set ``name`` (page title), ``tagline`` (one-line
    intro), and ``help_text`` (body of the About dialog), then call
    ``self.header()`` at the top of ``write()`` and ``self.section()``
    between major content groups.
    """

    name: str = "Untitled"
    tagline: str = ""
    help_text: str = ""

    @abstractmethod
    def write(self) -> None:
        """Render the page content."""

    def header(self) -> None:
        """Render the standard page header: title + tagline + Help + rule."""
        cols = st.columns([0.85, 0.15])
        with cols[0]:
            st.title(self.name)
            if self.tagline:
                st.caption(self.tagline)
        with cols[1]:
            st.button(
                "Help",
                key=f"help_{_slug(self.name)}",
                on_click=self._show_help,
                use_container_width=True,
            )
        st.markdown("---")

    def section(self, label: str) -> None:
        """Render a section header inside the page."""
        st.subheader(label)

    @st.dialog("About")
    def _show_help(self) -> None:
        """Render the About dialog for this page."""
        st.markdown(self.help_text or "_No help text provided._")


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
