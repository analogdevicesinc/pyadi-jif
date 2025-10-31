"""Main entry point for PyADI-JIF Tools Explorer Streamlit application."""

import logging
import os
from typing import Optional

import streamlit as st
from src.pages import PAGE_MAP
from src.utils import add_custom_css

# from src.state import provide_state


# Global logging configuration
logging.basicConfig(level=logging.ERROR)

# Configure page settings - must be first Streamlit command
st.set_page_config(
    page_title="PyADI-JIF Tools Explorer",
    page_icon=os.path.join(os.path.dirname(__file__), "PyADI-JIF_logo.png"),
    initial_sidebar_state="expanded",
)

# Apply custom CSS to main page and sidebar
add_custom_css()


# @provide_state()
def main(state: Optional[object] = None) -> None:
    """Run the main Streamlit application."""
    logo_image = os.path.join(os.path.dirname(__file__), "PyADI-JIF_logo.png")
    st.sidebar.image(logo_image)
    st.sidebar.title("Tools Explorer")
    current_page = st.sidebar.radio(
        "Select a Tool", list(PAGE_MAP), label_visibility="hidden"
    )
    PAGE_MAP[current_page](state=state).write()


if __name__ == "__main__":
    main()
