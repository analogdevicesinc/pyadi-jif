"""Landing page: one card per tool, each a button that opens it."""

from contextlib import contextmanager
from typing import Any, Generator, Optional

import streamlit as st

from ..utils import Page

# Material Symbols icon for each tool card, shown before its title.
CARD_ICONS = {
    "General Information": "info",
    "JESD204 Mode Selector": "tune",
    "Clock Configurator": "schedule",
    "System Configurator": "developer_board",
    "ADF4030 System Designer": "sync",
    "JESD204 Calculator": "calculate",
    "Frequency Planner": "graphic_eq",
}


# Sidebar radio key in main.py; the cards set it to switch pages.
NAV_KEY = "nav_page"

# Card title -> page name in PAGE_MAP. Cards without a page aren't buttons.
CARD_PAGES = {
    "JESD204 Mode Selector": "JESD204 Mode Selector",
    "Clock Configurator": "Clock Configurator",
    "System Configurator": "System Configurator",
    "ADF4030 System Designer": "ADF4030 System Designer",
    "JESD204 Calculator": "Basic JESD204 Calculator",
    "Frequency Planner": "Frequency Planner",
}

# Each tool card is one big button: a transparent st.button stretched over
# the whole bordered container, which highlights on hover.
_CARD_CSS = """
<style>
div[class*="st-key-card_"] { position: relative; transition: border-color .15s, background-color .15s; }
div[class*="st-key-card_"]:has(button):hover {
    border-color: var(--primary-color, #F58220);
    background-color: color-mix(in srgb, var(--primary-color, #F58220) 6%, transparent);
}
div[class*="st-key-card_"] div[class*="st-key-open_"] {
    position: absolute; inset: 0; z-index: 1; margin: 0;
    width: 100% !important; height: 100% !important;
}
div[class*="st-key-card_"] div[class*="st-key-open_"] div,
div[class*="st-key-card_"] div[class*="st-key-open_"] button {
    width: 100% !important; height: 100% !important;
}
div[class*="st-key-card_"] div[class*="st-key-open_"] button { opacity: 0; cursor: pointer; }
div[class*="st-key-card_"] div[class*="st-key-open_"] button:focus-visible { opacity: .08; }
</style>
"""


def _slug(title: str) -> str:
    """Return a widget-key-safe slug for a card title.

    Args:
        title: Card title.

    Returns:
        Lowercase title with non-alphanumerics replaced by underscores.
    """
    return "".join(c if c.isalnum() else "_" for c in title.lower())


def _go(page: str) -> None:
    """Switch the sidebar selection to a page.

    Args:
        page: Page name in PAGE_MAP.
    """
    st.session_state[NAV_KEY] = page


@contextmanager
def _card(col: Any, title: str) -> Generator[None, None, None]:
    """Render a bordered card; tool cards open their page when clicked.

    Args:
        col: Column to place the card in.
        title: Card title, a key of CARD_ICONS.

    Yields:
        None, with the card as the active container.
    """
    box = col.container(
        border=True, height="stretch", key=f"card_{_slug(title)}"
    )
    with box:
        page = CARD_PAGES.get(title)
        if page:
            st.button(
                f"Open {page}",
                key=f"open_{_slug(title)}",
                on_click=_go,
                args=(page,),
            )
        st.subheader(f":material/{CARD_ICONS[title]}: {title}", divider="gray")
        yield


class Landing(Page):
    """Basic landing page to explain use."""

    name = "PyADI-JIF Tools"
    tagline = "Quick reference of JIF Tools."
    help_text = "Developed by [ADI](https://analogdevicesinc.github.io)."

    def __init__(self, state: Optional[object]) -> None:
        """Initialize basic landing page.

        Args:
            state: Application state object
        """
        self.state = state

    def write(self) -> None:
        """Render the basic landing page."""
        self.header()

        st.html(_CARD_CSS)
        cols0 = st.columns(3)
        cols1 = st.columns(3)
        cols2 = st.columns(3)

        with _card(cols0[0], "General Information"):
            st.text(
                "Click a tool's card to open it, or pick it from the list on the left."
            )
            st.text(
                "Use the help button on each page to see more information about that page."
            )
            st.markdown(
                "See [github documentation](https://analogdevicesinc.github.io/pyadi-jif/) for information beyond this page."
            )

        with _card(cols0[1], "JESD204 Mode Selector"):
            st.text(
                "JESD204 Mode Selector is used to help select the JESD Mode for a given product."
            )
            st.text(
                "To use: \n"
                "1. Select a part. \n"
                "2. Select decimation/interpolation settings. \n"
                "3. Type in converter rate. \n"
                "4. If desired, start limiting jesd configuration parameters."
            )
            st.text(
                "By default the table of valid modes will auto-update based on selections. If no valid modes are found the table will display 'empty'."
            )

        with _card(cols0[2], "Clock Configurator"):
            st.text(
                "Clock Configurator is used to validate a configuration of a clock chip and generate a divider tree."
            )
            st.text(
                "To use: \n"
                "1. Select a part. \n"
                "2. Type in a desired reference clock. \n"
                "3. Set the number of outputs. \n"
                "4. For each output enter the desired frequency and optionally put in a clock name."
            )
            st.text(
                "Outputs of the tool are a divider tree and diagram of the clock structure."
            )

        with _card(cols1[0], "System Configurator"):
            st.text(
                "System Configurator is used to validate a full jesd204 system (converter+fpga+clock)."
            )
            st.text(
                "To use: \n"
                "1. Select a converter part. \n"
                "2. Select a clock part. \n"
                "3. Select an FPGA development kit. \n"
                "4. Enter the VCXO reference frequency. \n"
                "5. Set the converter settings. Use the JESD204 Mode Selector to help find desired configurations. \n"
                "6. Set FPGA settings. \n"
                "7. Choose or configure the converter clock source. Use the Clock Configurator to validate any clock solutions. \n"
            )
            st.text(
                "Outputs of the tool are config trees for the various parts and a diagram of the full system."
            )

        with _card(cols1[1], "ADF4030 System Designer"):
            st.text(
                "ADF4030 System Designer is used to plan Aion+Apollo (ADF4030+AD9084/88) based designs."
            )

        with _card(cols1[2], "JESD204 Calculator"):
            st.text(
                "JESD204 calculator is used to calculate clock rates based on input parameters."
            )
            st.text(
                "To use: \n"
                "1.) Enter the desired number of lanes (L). \n"
                "2.) Enter the desired number of converters (M). \n"
                "3.) Enter the desired number of packed bits per sample (Np). \n"
                "4.) Select the JESD204 class (204B or 204C). \n"
                "5.) Select the reference source ('Lane Rate' or 'Sample Rate'). \n"
                "6.) Enter the reference clock rate."
            )
            st.text(
                "Outputs of the tool is a table of derived clock rates. If 'Lane Rate' is selected as the reference source the table will output sample and core clock rates. If 'Sample Rate' is selected the table will output lane and core clock rates."
            )

        with _card(cols2[0], "Frequency Planner"):
            st.text(
                "Frequency Planner places signals through a converter's DDC/DUC chains (NCOs, decimation/interpolation) and checks what each output captures and which JESD204 modes the plan needs."
            )
            st.text(
                "To use: \n"
                "1. Select a part and, optionally, an FPGA. \n"
                "2. Click a block in the datapath diagram to edit its NCO, decimation/interpolation or routing. \n"
                "3. Click an ADC (or FDUC on Tx) to add the signals on that input. \n"
                "4. Pick an output path to see its spectra and verdict. \n"
                "5. Check the JESD204 link line for M, the link rate and the modes that fit."
            )
            st.text(
                "Outputs of the tool are per-output capture verdicts, the fitting JESD204 modes and an exportable JSON config of the NCO, decimation and JESD204 settings."
            )
