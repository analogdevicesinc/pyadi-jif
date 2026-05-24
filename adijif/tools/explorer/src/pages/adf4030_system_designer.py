"""ADF4030 System Designer page for PyADI-JIF Tools Explorer."""

from typing import Optional

import streamlit as st

from adijif.plls.utils.adf4030_arch import ARCHITECTURES, Adf4030Architecture

from ..utils import Page


class Adf4030SystemDesigner(Page):
    """ADF4030 architecture designer with partition + diagram output."""

    def __init__(self, state: Optional[object]) -> None:
        """Initialize the page.

        Args:
            state: Application state object.
        """
        self.state = state

    def write(self) -> None:
        """Render the page."""
        st.title("ADF4030 System Designer")
        st.write(
            "Plan an Aion (ADF4030) clock-distribution system: pick "
            "an architecture and the per-Unit-Board sizing, then view "
            "the partition summary and topology diagram."
        )

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

        st.subheader("Partition summary")
        st.text(arch.summary)
        st.subheader("Diagram")
        svg = arch.draw(scope=scope)
        st.components.v1.html(svg, height=600, scrolling=True)
