import streamlit as st

st.set_page_config(layout="wide")

from ..utils import Page

# import pandas as pd

from adijif.clocks import supported_parts as sp

# from adijif.utils import get_jesd_mode_from_params
import adijif

options_to_skip = ["list_references_available", "d_syspulse"]
parts_to_ignore = ["ad9545", "ad9523_1"]
sp = [p for p in sp if p not in parts_to_ignore]


class ClockConfigurator(Page):
    def __init__(self, state):
        self.state = state

    def write(self):

        st.title("Clock Configurator")
        # sp = ["hmc7044"]

        sb = st.selectbox(
            label="Select a part",
            options=sp,
            format_func=lambda x: x.upper().replace("_", "-"),
        )

        with st.expander("Clock Inputs and Outputs"):
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

        class_def = eval(f"adijif.{sb}")
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

        clk_chip = eval(f"adijif.{sb}()")

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
        output_clocks_filtered = []
        output_names_filtered = []
        for i, clk in enumerate(output_clocks):
            if clk not in output_clocks_filtered:
                output_clocks_filtered.append(clk)
                output_names_filtered.append(output_names[i])

        clk_chip.set_requested_clocks(
            reference, output_clocks_filtered, output_names_filtered
        )

        try:
            clk_chip.solve()

            o = clk_chip.get_config()

            print(o)

            columns_results = st.columns(2)

            with columns_results[0]:
                with st.expander("Found Configuration"):
                    st.write(o)

            with columns_results[1]:
                if sb == "hmc7044":
                    import adidt as dt

                    clk = dt.hmc7044_dt(offline=True)
                    dtsi = clk.map_config_to_fragment(o)
                    with st.expander("Device Tree Fragment"):
                        st.code(dtsi)

            if hasattr(clk_chip, "draw"):
                # show = st.button("Generate Clock Tree Diagram")
                show = True

                if show:
                    clk_chip.output_image_filename = "clk.svg"
                    # with st.spinner("Generating Clock Tree Diagram"):
                    file = clk_chip.draw()
                    with st.container(border=True):
                        # st.markdown(file)
                        st.image(file, use_column_width=True)
        except Exception as e:
            print(e)
            st.warning("No valid configuration found")
