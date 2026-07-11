"""JESD204 mode selector page."""

from typing import Optional

import pandas as pd
import streamlit as st

from adijif.converters import supported_parts as sp
from adijif.registry import get_component_class

from ..utils import Page
from .helpers.datapath import gen_datapath
from .helpers.drawers import draw_adc, draw_dac
from .helpers.jesd import get_jesd_controls, get_valid_jesd_modes

# options_to_skip = ["global_index", "decimations"]


class JESDModeSelector(Page):
    """JESD204 mode selector tool page."""

    name = "JESD204 Mode Selector"
    tagline = "Find a JESD204 mode that fits your sample rate and FPGA lane budget."
    help_text = (
        "This tool helps you select the appropriate JESD204 mode for "
        "your application. It supports ADCs, DACs, MxFEs, and "
        "Transceivers from the ADI portfolio, modeling their JESD204 "
        "mode tables and the clocking limitations of the individual "
        "devices.\n\n"
        "Select a part from the dropdown, configure the datapath "
        "(decimation/interpolation, converter sample rate), and the "
        "tool derives the necessary clocks. Filter on JESD204 "
        "parameters to find a mode that fits.\n\n"
        "JESD204 settings can be exported as CSV from the table."
    )

    def __init__(self, state: Optional[object]) -> None:
        """Initialize JESD mode selector page.

        Args:
            state: Application state object
        """
        self.state = state
        self.part_images = {}

    def write(self) -> None:
        """Render the JESD mode selector page."""
        # Get supported parts that have quick_configuration_modes
        supported_parts_filtered = []
        for part in sp:
            try:
                converter = get_component_class("converter", part)()
                qsm = converter.quick_configuration_modes  # noqa: F841
                supported_parts_filtered.append(part)
            except Exception:  # noqa: S110
                pass
        supported_parts = supported_parts_filtered

        self.header()

        sb = st.selectbox(
            label="Select a part",
            options=supported_parts,
            format_func=lambda x: x.upper(),
            key="converter_part_select",
        )

        converter = get_component_class("converter", sb)()

        # Show diagram
        self.section("Diagram")
        if sb not in self.part_images:
            try:
                if converter.converter_type.lower() == "adc":
                    self.part_images[sb] = draw_adc(converter)
                    # FIXME: State is not being saved
                else:
                    self.part_images[sb] = draw_dac(converter)
            except Exception:
                # Diagram generation requires a solver (e.g. CPLEX) that
                # may not be installed in all environments.
                self.part_images[sb] = None
        if self.part_images[sb]:
            st.image(self.part_images[sb], width="stretch")

        # Datapath Configuration
        self.section("Datapath configuration")
        decimation = gen_datapath(converter)

        scalar = st.selectbox(
            "Units",
            options=["Hz", "kHz", "MHz", "GHz"],
            index=3,
            key="jesd_units_select",
        )
        if scalar == "Hz":
            scalar_value = 1
            new_default = 1e9
            min_value = 1
            max_value = 28e9
        elif scalar == "kHz":
            scalar_value = 1e3
            new_default = 1e6
            min_value = 100
            max_value = 28e6
        elif scalar == "MHz":
            scalar_value = 1e6
            new_default = 1e3
            min_value = 1e3
            max_value = 28e3
        elif scalar == "GHz":
            scalar_value = 1e9
            new_default = 1
            min_value = 0.1
            max_value = 28

        min_value = float(min_value)
        max_value = float(max_value)
        new_default = float(new_default)

        converter_rate = st.number_input(
            f"Converter Rate ({scalar})",
            value=new_default,
            min_value=min_value,
            max_value=max_value,
            key="jesd_converter_rate_input",
        )
        converter_rate = scalar_value * converter_rate
        converter.sample_clock = converter_rate / decimation

        # Derived settings
        dict_data = {
            "Derived Setting": ["Sample Rate (MSPS)"],
            "Value": [converter.sample_clock / 1e6],
        }
        df = pd.DataFrame.from_dict(dict_data)
        st.dataframe(df, hide_index=True, width="stretch")

        cols = st.columns(2, border=True)

        # JESD204 Configuration Inputs
        options, all_modes = get_jesd_controls(converter)
        selections = {}

        with cols[0]:
            st.subheader("Configuration")

            for option in options:
                selections[option] = st.multiselect(
                    option,
                    options[option],
                    key=f"jesd_{option.lower().replace(' ', '_')}_multiselect",
                )  # noqa: S608

        # Output table of valid modes and calculate clocks
        selections = {k: v for k, v in selections.items() if v != []}
        modes_all_info, found_modes = get_valid_jesd_modes(
            converter, all_modes, selections
        )

        with cols[1]:
            st.subheader("JESD204 Modes")

            if found_modes:
                # Create formatted table of modes

                # Convert to DataFrame so we can change orientation
                df = pd.DataFrame(modes_all_info)

                show_valid = st.toggle("Show only valid modes", value=True)
                if show_valid:
                    df = df[df["Valid"] == "Yes"]
                    df = df.drop(columns=["Valid"])

                # Create new index column and move mode to separate column
                df["Mode"] = df.index
                df = df.reset_index(drop=True)
                # Make mode first column
                cols = df.columns.tolist()
                cols = cols[-1:] + cols[:-1]
                df = df[cols]

                # Change jesd_class column name to be JESD204 Class
                df = df.rename(columns={"jesd_class": "JESD204 Class"})
                df = df.rename(columns={"Mode": "Quickset Mode"})

                # Change data in jesd_class column to be more human readable
                df["JESD204 Class"] = df["JESD204 Class"].replace(
                    {"jesd204b": "204B", "jesd204c": "204C"}
                )

                # Remove any blank rows (rows where all values are NaN or empty)
                df = df.dropna(how="all")
                df = df[df.astype(str).ne("").any(axis=1)]

                to_disable = df.columns
                # Use fixed height with scrolling for consistent display
                # Calculate dynamic height but cap it for better UX
                min_height = 150
                max_height = 600
                row_height = 35
                calculated_height = min(
                    max(len(df) * row_height + 38, min_height), max_height
                )

                st.data_editor(  # noqa: F841
                    df,
                    width="stretch",
                    disabled=to_disable,
                    hide_index=True,
                    height=calculated_height,
                )

            else:
                st.write("No modes found")
