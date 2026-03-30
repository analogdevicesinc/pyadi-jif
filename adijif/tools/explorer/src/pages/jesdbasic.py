"""Basic JESD204 Calculator."""

from typing import Optional

import pandas as pd
import streamlit as st

from ..utils import Page


class JESDBasic(Page):
    """Basic JESD204 calculator page."""

    def __init__(self, state: Optional[object]) -> None:
        """Initialize basic JESD204 calculator page.

        Args:
            state: Application state object
        """
        self.state = state

    def write(self) -> None:
        """Render the basic JESD204 calculator page."""
        st.title("Basic JESD204 Calculator")

        # Horizontal line
        st.markdown("---")

        # Add int boxes for L, M, Np, JESD Class
        jesd_params, output_table = st.columns(2)
        with jesd_params:
            st.header("JESD204 Parameters")

            L_c, M_c = st.columns(2)

            with L_c:
                L = st.number_input(
                    "L (number of lanes)", min_value=1, step=1, value=4
                )
            with M_c:
                M = st.number_input(
                    "M (number of converters)", min_value=1, step=1, value=4
                )

            np_c, class_c = st.columns(2)
            with np_c:
                Np = st.number_input(
                    "Np (Bits per sample)", min_value=1, step=1, value=16
                )

            with class_c:
                jesd_class = st.selectbox(
                    "JESD204 Class", ["JESD204B", "JESD204C"]
                )

            label_c, value_c = st.columns(2)
            with label_c:
                clock_ref_source = st.selectbox(
                    "Clock Reference Source", ["Sample Rate", "Lane Rate"]
                )

            with value_c:
                if clock_ref_source == "Sample Rate":
                    sample_rate = st.number_input(
                        "Sample Rate (SPS)",
                        min_value=1.0,
                        step=1.0,
                        value=100e6,
                    )
                else:
                    lane_rate = st.number_input(
                        "Lane Rate (Gbps)", min_value=0.1, step=0.1, value=10.0
                    )

        if jesd_class == "JESD204B":
            encoding_factor = float(10) / float(
                8
            )  # Assuming 16-bit samples for simplicity
        else:
            encoding_factor = float(66) / float(
                64
            )  # Assuming 16-bit samples for simplicity

        # Lane rate = (M * Np * Sample Rate * encoding_factor) / L
        if clock_ref_source == "Sample Rate":
            rate = (
                (M * Np * sample_rate * encoding_factor) / L / 1e9
            )  # Convert to Gbps
            label = "Lane Rate (Gbps)"
            if jesd_class == "JESD204B":
                core_clock = rate / 40 * 1e3  # Convert to MHz
            else:
                core_clock = rate / 66 * 1e3  # Convert to MHz
        else:
            # lane_rate_gbps = lane_rate
            rate = (
                (lane_rate * 1e9 * L) / (M * Np * encoding_factor) / 1e6
            )  # Convert to MSPS
            label = "Sample Rate (MSPS)"
            if jesd_class == "JESD204B":
                core_clock = lane_rate / 40 * 1e3  # Convert to MHz
            else:
                core_clock = lane_rate / 66 * 1e3  # Convert to MHz

        with output_table:
            st.header("Derived Parameters")
            df = pd.DataFrame(
                {
                    "Parameter": [label, "Core Clock (MHz)"],
                    "Value": [rate, core_clock],
                }
            )
            st.table(df)
