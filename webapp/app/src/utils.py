import streamlit as st
from abc import ABC, abstractmethod


class Page(ABC):
    @abstractmethod
    def write(self):
        pass


def add_custom_css():
    st.markdown(
        """
        <style>
            section.main > div {max-width:75rem}
        </style>
        """,
        unsafe_allow_html=True,
    )
