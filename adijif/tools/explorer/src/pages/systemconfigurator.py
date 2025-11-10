"""System configurator page."""

from typing import Optional

import pandas as pd
import streamlit as st

import adijif
from adijif.clocks import supported_parts as csp
from adijif.converters import supported_parts as xsp

# from adijif.utils import get_jesd_mode_from_params
from ..utils import Page
from .helpers.datapath import gen_datapath

# Clocks
options_to_skip = ["list_references_available", "d_syspulse"]
parts_to_ignore = ["ad9545", "ad9523_1"]
sp = [p for p in csp if p not in parts_to_ignore]
# Put HMC7044 at the front
sp = [p for p in sp if p != "hmc7044"]
sp.insert(0, "hmc7044")

# Converters


class SystemConfigurator(Page):
    """System configurator tool page."""

    def __init__(self, state: Optional[object]) -> None:
        """Initialize system configurator page.

        Args:
            state: Application state object
        """
        self.state = state

    def write(self) -> None:
        """Render the system configurator page."""
        st.title("System Configurator")

        with st.expander("System Settings", expanded=True):
            hsx = st.selectbox(
                label="Select a converter part",
                options=xsp,
                format_func=lambda x: x.upper(),
                key="converter_part_select",
            )

            clock = st.selectbox(
                label="Select a clock part",
                options=sp,
                format_func=lambda x: x.upper(),
                key="clock_part_select",
            )

            fpga_kit = st.selectbox(
                label="Select an FPGA development kit",
                options=adijif.xilinx._available_dev_kit_names,
                format_func=lambda x: x.upper(),
                key="fpga_dev_kit_select",
            )

            reference_rate = st.number_input(
                f"Reference Rate (VCXO) for {clock.upper()} (Hz)",
                value=125000000,
                min_value=int(100e6),
                max_value=int(400e6),
            )

        sys = adijif.system(hsx.lower(), clock.lower(), "xilinx", reference_rate)

        # Get Converter clocking requirements
        sys.Debug_Solver = False

        # Get FPGA clocking requirements
        sys.fpga.setup_by_dev_kit_name(fpga_kit.lower())

        converter_c, fpga_c = st.columns(2)

        with converter_c:
            # st.header("Converter Configuration")
            with st.expander("Converter Settings", expanded=True):

                # Units GHz, MHz, kHz
                units = st.selectbox(
                    label="Select units for Converter Clock",
                    options=["Hz", "kHz", "MHz", "GHz"],
                    index=2,
                )
                if units == "Hz":
                    multiplier = 1
                elif units == "kHz":
                    multiplier = 1e3
                elif units == "MHz":
                    multiplier = 1e6
                elif units == "GHz":
                    multiplier = 1e9

                # Converter Clock
                converter_clock = st.number_input(
                    f"Converter Clock ({units})",
                    value=1e9 / multiplier,
                    format="%f",
                    min_value=1e6 / multiplier,
                    max_value=20e9 / multiplier,
                )
                # sys.converter.decimation = 1

                decimation = gen_datapath(sys.converter)
                sys.converter.sample_clock = converter_clock * multiplier / decimation

                # JESD modes
                qsm = sys.converter.quick_configuration_modes

                # Flatten dict for display as a list
                qsm_flat = {}
                for jesdclasses in qsm:
                    for mode in qsm[jesdclasses]:
                        settings = qsm[jesdclasses][mode]
                        other_settings = (
                            f" (M={settings['M']}, "
                            + f"F={settings['F']},"
                            + f"Np={settings['Np']}, "
                            + f"L={settings['L']}, S={settings['S']})"
                        )
                        qsm_flat[
                            f"{jesdclasses.upper()} Mode: {mode} {other_settings}"
                        ] = {
                            "mode": mode,
                            "jesdclass": jesdclasses,
                        }

                # Sort by mode
                qsm_flat = dict(
                    sorted(qsm_flat.items(), key=lambda item: item[1]["mode"])
                )

                mode = st.selectbox(
                    label="Select JESD Configuration Mode",
                    options=list(qsm_flat.keys()),
                    # options=list(qsm_flat.keys()),
                    # format_func=lambda x: f"{x} : {qsm_flat[x]}",
                )
                sys.converter.set_quick_configuration_mode(
                    qsm_flat[mode]["mode"], qsm_flat[mode]["jesdclass"]
                )

        # with clock_c:
        #     st.header("Clock Configuration")

        #     with st.container(border=True):
        #         st.markdown(cfg["clock"])

        with fpga_c:
            with st.expander("FPGA Settings", expanded=True):

                # sys.fpga.ref_clock_constraint = "Unconstrained"
                ref_clock_constraint = st.selectbox(
                    options=adijif.xilinx._ref_clock_constraint_options,
                    label="FPGA Reference Clock Constraint",
                    index=adijif.xilinx._ref_clock_constraint_options.index(
                        "Unconstrained"
                    ),
                )
                sys.fpga.ref_clock_constraint = ref_clock_constraint

                # sys.fpga.sys_clk_select = "XCVR_QPLL0"  # Use faster QPLL
                sys_clk_select = st.multiselect(
                    options=adijif.xilinx.sys_clk_selections,
                    label="XCVR System Clock Source Selection",
                    default=adijif.xilinx.sys_clk_selections,
                )
                sys.fpga.sys_clk_select = sys_clk_select

                # Enable all adijif.xilinx._out_clk_selections for selection by default
                out_clk_select = st.multiselect(
                    options=adijif.xilinx._out_clk_selections,
                    label="XCVR Output Clock Selection",
                    default=adijif.xilinx._out_clk_selections,
                )
                sys.fpga.out_clk_select = out_clk_select

                # sys.fpga.force_qpll = 1
                force_qpll_options = ["Auto", "Force QPLL", "Force QPLL1", "Force CPLL"]
                force_qpll_selection = st.selectbox(
                    options=force_qpll_options,
                    label="Transceiver PLL Selection",
                    index=0,
                )
                if force_qpll_selection == "Force QPLL":
                    sys.fpga.force_qpll = True
                elif force_qpll_selection == "Force QPLL1":
                    sys.fpga.force_qpll1 = True
                elif force_qpll_selection == "Force CPLL":
                    sys.fpga.force_cpll = True

        with st.expander("Converter Clock Source", expanded=False):
            # Pick converter mode
            if len(sys.converter.clocking_option_available) > 1:
                internal_clocking = st.radio(
                    "Converter Clocking Option",
                    options=["Internal PLL", "Direct"],
                    index=0,
                )
                if internal_clocking == "Internal PLL":
                    internal_clocking = "integrated_pll"
                else:
                    internal_clocking = "direct"
            else:
                available = sys.converter.clocking_option_available[0]
                st.radio(
                    "Converter Clocking Option",
                    options=[available],
                    format_func=lambda x: x.capitalize(),
                    index=0,
                )
                internal_clocking = available

            sys.converter.clocking_option = internal_clocking

            # Pick source for clocking
            if internal_clocking == "direct":
                plls_plus_clock_chip = adijif.plls.supported_parts + [
                    clock.lower() + " (Clock Chip)"
                ]
                ext_pll = st.selectbox(
                    label="Select an external PLL part",
                    options=plls_plus_clock_chip,
                    format_func=lambda x: x.upper(),
                    key="plls",
                )

                ext_pll = ext_pll.replace(" (Clock Chip)", "").lower()

                if ext_pll != clock.lower():
                    sys.add_pll_inline(ext_pll.lower(), reference_rate, sys.converter)
            else:  # integrated_pll
                st.radio("Integrated PLL source", options=[clock.upper()], index=0)

        with st.expander("Derived Settings", expanded=True):

            # Table with lane rate and core clock
            lane_rate = sys.converter.bit_clock
            core_clock = (
                sys.converter.bit_clock / 66
                if sys.converter.jesd_class == "jesd204c"
                else sys.converter.bit_clock / 40
            )
            sample_clock = sys.converter.sample_clock
            converter_clock = sys.converter.converter_clock

            # Build pandas DataFrame
            df = pd.DataFrame(
                {
                    "Setting": [
                        "Lane Rate (Gbps)",
                        "Needed Core Clock (MHz)",
                        "Sample Clock (MHz)",
                        "Converter Clock (MHz)",
                    ],
                    "Value": [
                        f"{lane_rate/1e9:.4f}",
                        f"{core_clock/1e6:.4f}",
                        f"{sample_clock/1e6:.4f}",
                        f"{converter_clock/1e6:.4f}",
                    ],
                }
            )
            # Remove index
            df.index = df["Setting"]
            df = df.drop(columns=["Setting"])
            st.table(df)

        with st.expander("System Configuration", expanded=False):
            try:
                cfg = sys.solve()

                st.subheader("Clock Configuration")
                st.write(cfg["clock"])

                st.subheader("Converter Configuration")
                st.write(cfg["converter"])

                st.subheader("FPGA Configuration")
                st.write(cfg["fpga_" + sys.converter.name.upper()])

                st.subheader("Converter JESD Configuration")
                st.write(cfg["jesd_" + sys.converter.name.upper()])

                diagram = sys.draw(cfg)

            except Exception as e:
                diagram = None
                st.error(f"Error solving system configuration: {e}")

        with st.expander("Diagram", expanded=False):
            if diagram:
                st.image(diagram, width="stretch")
            else:
                st.write("No diagram available.")
