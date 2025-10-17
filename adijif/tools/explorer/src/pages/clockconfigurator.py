"""Clock configurator page for PyADI-JIF Tools Explorer."""

import logging
from typing import Optional

import streamlit as st

from adijif.clocks import supported_parts as sp

from ..utils import Page

try:
    import adidt as dt
except ImportError:
    dt = None

log = logging.getLogger(__name__)
log.setLevel(logging.ERROR)

# Parse parts and options to skip
options_to_skip = ["list_references_available", "d_syspulse"]
parts_to_ignore = ["ad9545", "ad9523_1"]
sp = [p for p in sp if p not in parts_to_ignore]
sp = [p for p in sp if p != "hmc7044"]
sp.insert(0, "hmc7044")


class ClockConfigurator(Page):
    """Clock configurator tool page."""

    def __init__(self, state: Optional[object]) -> None:
        """Initialize clock configurator page.

        Args:
            state: Application state object
        """
        self.state = state

    def write(self) -> None:
        """Render the clock configurator page."""
        st.title("Clock Configurator")
        # sp = ["hmc7044"]

        sb = st.selectbox(
            label="Select a part",
            options=sp,
            format_func=lambda x: x.upper().replace("_", "-"),
        )

        with st.expander("Clock Inputs and Outputs", expanded=True):
            reference = st.number_input(
                "Reference Clock",
                value=125000000,
                min_value=1,
                max_value=int(1e9),
                step=1,
            )

            with st.container(border=True):
                num_outputs = st.number_input(
                    "Number of Clock Outputs",
                    value=2,
                    min_value=1,
                    max_value=10,
                    step=1,
                )
                outputs = []
                output_names = []
                for i in range(num_outputs):
                    columns = st.columns(2)
                    with columns[0]:
                        outputs.append(
                            st.number_input(
                                f"Output Clock {i+1}",
                                value=125000000,
                                min_value=1,
                                max_value=int(1e9),
                                step=1,
                            )
                        )
                    with columns[1]:
                        output_names.append(
                            st.text_input(f"Output Clock Name {i+1}", f"CLK{i+1}")
                        )

        import adijif  # noqa: F401

        class_def = eval(f"adijif.{sb}")  # noqa: S307
        props = dir(class_def)

        props = [p for p in props if not p.startswith("__")]
        props = [p for p in props if not p.startswith("_")]
        configurable_props = [
            p.replace("_available", "") for p in props if "_available" in p
        ]

        prop_and_options = {}
        for prop in configurable_props:
            if prop in options_to_skip or prop + "_available" not in props:
                continue
            prop_and_options[prop] = getattr(class_def, prop + "_available")

        selections = {}
        with st.expander("Internal Clock Configuration"):
            for prop, options in prop_and_options.items():
                prop_docstring = getattr(class_def, prop).__doc__
                with st.container(border=True):
                    label = f"""
                    {prop} : {prop_docstring}"""
                    if len(options) > 16:
                        v_min, v_max = min(options), max(options)
                        start, end = st.select_slider(
                            label, options, value=(v_min, v_max)
                        )
                        selections[prop] = {"start": start, "end": end}
                    else:
                        selections[prop] = st.multiselect(label, options)

        clk_chip = eval(f"adijif.{sb}()")  # noqa: S307

        for prop, values in selections.items():
            if isinstance(values, dict):
                props_available = getattr(clk_chip, prop + "_available")
                if (
                    min(props_available) == values["start"]
                    and max(props_available) == values["end"]
                ):
                    continue
                picked = [
                    v for v in props_available if values["start"] <= v <= values["end"]
                ]
                setattr(clk_chip, prop, picked)
            else:
                if not values:
                    continue
                setattr(clk_chip, prop, values)

        output_clocks = outputs
        output_clocks = list(map(int, output_clocks))  # force to be ints

        # Remove duplicates
        output_clocks_filtered = output_clocks
        output_names_filtered = output_names

        clk_chip.set_requested_clocks(
            reference, output_clocks_filtered, output_names_filtered
        )

        try:
            clk_chip.solve()
            o = clk_chip.get_config()
            log.info("Solution found")
            log.info(o)

            # if dt:
            #     columns_results = st.columns(2)

            #     with columns_results[0]:
            #         with st.expander("Found Configuration"):
            #             st.write(o)

            #     with columns_results[1]:
            #         if sb == "hmc7044":

            #             clk = dt.hmc7044_dt(offline=True)
            #             dtsi = clk.map_config_to_fragment(o)
            #             with st.expander("Device Tree Fragment"):
            #                 st.code(dtsi)
            # else:
            #     with st.expander("Found Configuration"):
            #         st.write(o)

            config_out = o
            image_data = clk_chip.draw()

            warning = False

        except Exception as e:
            log.warning(e)

            warning = True

        with st.expander("Found Configuration", expanded=True):
            if warning:
                st.warning("No valid configuration found")
            else:
                st.write(config_out)

        with st.expander("Diagram", expanded=True):
            if warning:
                st.warning("No diagram to show")
            else:
                st.image(image_data, width="stretch")
