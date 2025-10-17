"""System configurator page."""

from typing import Optional

import streamlit as st

import adijif
from adijif.clocks import supported_parts as csp
from adijif.converters import supported_parts as xsp

# from adijif.utils import get_jesd_mode_from_params
from ..utils import Page

# import pandas as pd

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
            st.header("System Settings")
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

            vcxo = 125000000
            reference_rate = st.number_input(
                f"Reference Rate (VCXO) for {clock.upper()} (Hz)",
                value=vcxo,
                min_value=int(100e6),
                max_value=int(400e6),
            )

        sys = adijif.system(hsx.lower(), clock.lower(), "xilinx", vcxo)

        # Get Converter clocking requirements
        # sys.converter.set_quick_configuration_mode(str(0x88))
        # sys.converter.K = 32
        sys.Debug_Solver = False

        # Get FPGA clocking requirements
        sys.fpga.setup_by_dev_kit_name(fpga_kit.lower())

        # cfg = sys.solve()

        # pprint.pprint(cfg)

        # print("Clock config:")
        # pprint.pprint(cfg["clock"])

        # print("Converter config:")
        # pprint.pprint(cfg["converter"])

        print("FPGA config:")
        # pprint.pprint(cfg["fpga_AD9680"])

        # print("JESD config:")
        # pprint.pprint(cfg["jesd_AD9680"])

        # data = sys.draw(cfg)

        # st.image(data, width="stretch")

        converter_c, fpga_c = st.columns(2)

        with converter_c:
            st.header("Converter Configuration")

            sys.converter.sample_clock = 1e9
            sys.converter.decimation = 1

            qsm = sys.converter.quick_configuration_modes

            # Flatten dict for display as a list
            qsm_flat = {}
            for jesdclasses in qsm:
                for mode in qsm[jesdclasses]:
                    other_settings = f" (M={sys.converter.M}, F={sys.converter.F}, K={sys.converter.K}, Np={sys.converter.Np}, CS={sys.converter.CS}, L={sys.converter.L}, S={sys.converter.S})"
                    # qsm_flat[f"{jesdclasses.upper()}: Mode {mode}"] = f"{jesdclasses}:{mode}: {other_settings}"
                    qsm_flat[f"{jesdclasses.upper()} Mode: {mode} {other_settings}"] = {
                        "mode": mode,
                        "jesdclass": jesdclasses,
                    }

            mode = st.selectbox(
                label="Select Quick Configuration Mode",
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
            st.header("FPGA Configuration")

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
            sys_clk_select = st.selectbox(
                options=adijif.xilinx.sys_clk_selections,
                label="XCVR System Clock Source Selection",
                index=0,
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

        st.header("Diagram")

        with st.container(border=True):
            # st.markdown(file)
            # print(data)
            # st.image(data, width="stretch")
            ...
