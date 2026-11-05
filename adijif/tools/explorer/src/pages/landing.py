"""Basic JESD204 Calculator."""

from typing import Optional

import pandas as pd
import streamlit as st

from ..utils import Page


class Landing(Page):
    """Basic landing page to explain use."""

    name = "Table of Contents"
    tagline = (
        "Quick reference of JIF Tools."
    )
    help_text = (
        "Developed by [ADI](https://analogdevicesinc.github.io)."
    )

    def __init__(self, state: Optional[object]) -> None:
        """Initialize basic landing page.

        Args:
            state: Application state object
        """
        self.state = state

    def write(self) -> None:
        """Render the basic landing page."""
        self.header()

        cols0 = st.columns(3, border=True)
        gen_info = cols0[0]
        jesd_mode_select = cols0[1]
        clock_config = cols0[2]

        with gen_info:
            st.subheader("General Information", divider="gray")
            st.text("Click on the radio buttons on the left to select a tool.")
            st.text("Use the help button on each page to see more information about that page.")
            st.markdown("See [github documentation](https://analogdevicesinc.github.io/pyadi-jif/) for information beyond this page.")

        with jesd_mode_select:
            st.subheader("JESD204 Mode Selector", divider="gray")
            st.text("JESD204 Mode Selector is used to help select the JESD Mode for a given product.")
            st.text("To use: \n"
                    "1. Select a part. \n"
                    "2. Select decimation/interpolation settings. \n"
                    "3. Type in converter rate. \n"
                    "4. If desired, start limiting jesd configuration parameters.")
            st.text("By default the table of valid modes will auto-update based on selections. If no valid modes are found the table will display 'empty'.")

        with clock_config:
            st.subheader("Clock Configurator", divider="gray")
            st.text("Clock Configurator is used to validate a configuration of a clock chip and generate a divider tree.")
            st.text("To use: \n"
                    "1. Select a part. \n"
                    "2. Type in a desired reference clock. \n"
                    "3. Set the number of outputs. \n"
                    "4. For each output enter the desired frequency and optionally put in a clock name.")
            st.text("Outputs of the tool are a divider tree and diagram of the clock structure.")


        cols1 = st.columns(3, border=True, )
        sys_config = cols1[0]
        adf4030_des = cols1[1]
        jesd204_calc = cols1[2]
        cols1[2].empty()

        with sys_config:
            st.subheader("System Configurator", divider="gray")
            st.text("System Configurator is used to validate a full jesd204 system (converter+fpga+clock).")
            st.text("To use: \n"
                    "1. Select a converter part. \n"
                    "2. Select a clock part. \n"
                    "3. Select an FPGA development kit. \n"
                    "4. Enter the VCXO reference frequency. \n"
                    "5. Set the converter settings. Use the JESD204 Mode Selector to help find desired configurations. \n"
                    "6. Set FPGA settings. \n"
                    "7. Choose or configure the converter clock source. Use the Clock Configurator to validate any clock solutions. \n")
            st.text("Outputs of the tool are config trees for the various parts and a diagram of the full system.")

        with adf4030_des:
            st.subheader("ADF4030 System Designer", divider="gray")
            st.text("ADF4030 System Designer is used to plan Aion+Apollo (ADF4030+AD9084/88) based designs.")

        with jesd204_calc:
            st.subheader("JESD204 Calculator", divider="gray")
            st.text("JESD204 calculator is used to calculate clock rates based on input parameters.")
            st.text("To use: \n"
                    "1.) Enter the desired number of lanes (L). \n"
                    "2.) Enter the desired number of converters (M). \n"
                    "3.) Enter the desired number of packed bits per sample (Np). \n"
                    "4.) Select the JESD204 class (204B or 204C). \n"
                    "5.) Select the reference source ('Lane Rate' or 'Sample Rate'). \n"
                    "6.) Enter the reference clock rate.")
            st.text("Outputs of the tool is a table of derived clock rates. If 'Lane Rate' is selected as the reference source the table will output sample and core clock rates. If 'Sample Rate' is selected the table will output lane and core clock rates.")
