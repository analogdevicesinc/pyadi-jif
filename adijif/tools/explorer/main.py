"""Main entry point for PyADI-JIF Tools Explorer Streamlit application."""

import logging
import os
from typing import Optional

import streamlit as st
from src.pages import PAGE_MAP
from src.pages.landing import NAV_KEY
from src.utils import add_custom_css, render_sidebar_logo

# from src.state import provide_state


DOCS_URL = "https://analogdevicesinc.github.io/pyadi-jif/"

# Global logging configuration
logging.basicConfig(level=logging.ERROR)

# Configure page settings - must be first Streamlit command
st.set_page_config(
    page_title="PyADI-JIF Tools Explorer",
    page_icon=os.path.join(
        os.path.dirname(__file__), "static", "favicon-32.png"
    ),
    initial_sidebar_state="expanded",
)

# Apply custom CSS to main page and sidebar
add_custom_css()


# @provide_state()
def main(state: Optional[object] = None) -> None:
    """Run the main Streamlit application."""
    render_sidebar_logo()
    st.sidebar.title("Tools Explorer")
    current_page = st.sidebar.radio(
        "Select a Tool", list(PAGE_MAP), label_visibility="hidden", key=NAV_KEY
    )
    # Pinned to the bottom of the sidebar by add_custom_css.
    with st.sidebar.container(key="sidebar_docs"):
        st.divider()
        st.link_button(
            "PyADI-JIF documentation",
            DOCS_URL,
            icon=":material/menu_book:",
            width="stretch",
        )
    PAGE_MAP[current_page](state=state).write()


# Call main() unconditionally - Streamlit will import this module to run it
main()
