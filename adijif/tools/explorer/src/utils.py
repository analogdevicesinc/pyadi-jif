"""Utility functions and base classes for the explorer."""

from abc import ABC, abstractmethod

import streamlit as st

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
