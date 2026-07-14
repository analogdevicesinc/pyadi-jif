"""ADF4030 System Designer page for PyADI-JIF Tools Explorer."""

from typing import Optional

import streamlit as st

from adijif.plls.utils.adf4030_arch import ARCHITECTURES, Adf4030Architecture

from ..utils import Page, get_diagram_theme


class Adf4030SystemDesigner(Page):
    """ADF4030 architecture designer with partition + diagram output."""

    name = "ADF4030 System Designer"
    tagline = (
        "Plan an Aion (ADF4030) clock-distribution system: pick an "
        "architecture and the per-Unit-Board sizing, then view the "
        "partition summary and topology diagram."
    )
    help_text = (
        "The ADF4030 (Aion) is a 10-channel SYSREF synchronizer. "
        "Once a system needs more channels than one Aion provides, "
        "the Aions must be chained together; this page computes the "
        "partition (how many Aions per FPGA, how many Apollos per "
        "Aion, how many Unit Boards) for the chosen architecture and "
        "renders a topology diagram.\n\n"
        "Use the **Diagram scope** radio to switch between a single "
        "Unit Board view and the full system. At large N the system "
        "view can take a while to render."
    )

    def __init__(self, state: Optional[object]) -> None:
        """Initialize the page.

        Args:
            state: Application state object.
        """
        self.state = state

    def write(self) -> None:
        """Render the page."""
        self.header()

        col1, col2 = st.columns(2)
        with col1:
            N = st.number_input(
                "Total Apollo devices (N)", value=64, min_value=1,
                key="adf4030_N",
            )
            N_Apollo = st.number_input(
                "Apollos per Unit Board", value=8, min_value=1,
                key="adf4030_N_Apollo",
            )
            N_FPGA = st.number_input(
                "FPGAs per Unit Board", value=1, min_value=1,
                key="adf4030_N_FPGA",
            )
        with col2:
            architecture = st.selectbox(
                "Architecture", ARCHITECTURES,
                key="adf4030_architecture",
            )
            N_branch = None
            if architecture in ("tree", "hybrid", "hybrid2"):
                N_branch = st.number_input(
                    "Branches (N_branch)", value=2, min_value=1,
                    key="adf4030_N_branch",
                )
            scope = st.radio(
                "Diagram scope", ("ub", "system"),
                key="adf4030_scope",
            )

        try:
            arch = Adf4030Architecture(
                N=int(N),
                N_Apollo=int(N_Apollo),
                N_FPGA=int(N_FPGA),
                architecture=architecture,
                N_branch=int(N_branch) if N_branch is not None else None,
            )
        except ValueError as e:
            st.error(str(e))
            return

        self.section("Partition summary")
        st.text(arch.summary)
        self.section("Diagram")
        svg = arch.draw(scope=scope, theme=get_diagram_theme())
        st.components.v1.html(svg, height=600, scrolling=True)
