import streamlit as st
from ..utils import Page

import pandas as pd

from adijif.converters import supported_parts as sp
from adijif.utils import get_jesd_mode_from_params
import adijif

options_to_skip = ["global_index", "decimations"]


class JESDModeSelector(Page):
    def __init__(self, state):
        self.state = state

    def write(self):
        # slider_value = st.slider(
        #     "Set Value from here See it on Page 2",
        #     value=self.state.client_config["slider_value"],
        # )
        # self.state.client_config["slider_value"] = slider_value

        # Get supported parts that have quick_configuration_modes
        supported_parts_filtered = []
        for part in sp:
            try:
                converter = eval(f"adijif.{part}()")
                qsm = converter.quick_configuration_modes
                supported_parts_filtered.append(part)
            except:
                pass
        supported_parts = supported_parts_filtered

        st.title("JESD204 Mode Selector")

        sb = st.selectbox(
            label="Select a part",
            options=supported_parts,
            format_func=lambda x: x.upper(),
        )

        converter = eval(f"adijif.{sb}()")

        if hasattr(converter, "decimation_available"):
            decimation = st.selectbox(
                "Decimation",
                options=converter.decimation_available,
                format_func=lambda x: str(x),
            )
            converter.decimation = decimation

        converter_rate = st.number_input("Converter Rate (Hz)", value=1e9)
        converter.sample_clock = converter_rate / converter.decimation
        print(converter.sample_clock)

        # Pick the first subclass and mode of that subclass to key list of possible settings
        all_modes = converter.quick_configuration_modes
        subclass = list(all_modes.keys())[0]
        subclasses = list(all_modes.keys())
        example_mode_key = list(all_modes[subclass].keys())[0]
        example_mode_settings = all_modes[subclass][example_mode_key]

        # Parse all options for each control
        options = {}
        for setting in example_mode_settings:
            if setting in options_to_skip:
                continue
            options[setting] = []
            for subclass in subclasses:
                for mode in all_modes[subclass]:
                    data = all_modes[subclass][mode][setting]
                    if type(data) == list:
                        continue
                    options[setting].append(data)


        # Make sure options only contain unique values
        for option in options:
            options[option] = list(set(options[option]))

        selections = {}

        with st.expander(label="JESD204 Configuration", expanded=True):
            for option in options:
                selections[option] = st.multiselect(option, options[option])

        # If None is selected, remove it from the dictionary
        selections = {k: v for k, v in selections.items() if v != []}

        try:
            found_modes = get_jesd_mode_from_params(converter, **selections)
        # except Exception as e:
        # st.write(e)
        # return
        except:
            found_modes = None

        if found_modes:
            # Get remaining mode parameters
            modes_all_info = {}
            for mode in found_modes:
                modes_all_info[mode["mode"]] = all_modes[mode["jesd_mode"]][
                    mode["mode"]
                ]
                # Remove options to skip
                for option in options_to_skip:
                    modes_all_info[mode["mode"]].pop(option, None)

            # For each mode calculate the clocks and if valid
            for mode in modes_all_info:
                rate = converter.sample_clock
                # print("A", converter.sample_clock)
                converter.set_quick_configuration_mode(mode, modes_all_info[mode]['jesd_class'])
                # print("B", converter.sample_clock)
                print("BUG")
                converter.sample_clock = rate

                clocks = {"Sample Rate (MSPS)": converter.sample_clock/1e6, "Lane Rate (GSPS)": converter.bit_clock/1e9}

                for clock in clocks:
                    modes_all_info[mode][clock] = clocks[clock]

                try:
                    converter.validate_config()
                    modes_all_info[mode]["Valid"] = "Yes"
                except Exception as e:
                    print(e)
                    modes_all_info[mode]["Valid"] = "No"


            # Convert to DataFrame so we can change orientation
            df = pd.DataFrame(modes_all_info).T

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

            # st.table(df)

            # # Get the mode number to appear as a column
            # df.columns.name = df.index.name
            # df.index.name = None
            # st.write(df.to_html(), unsafe_allow_html=True)

            # Change jesd_class column name to be JESD204 Class
            df = df.rename(columns={"jesd_class": "JESD204 Class"})
            df = df.rename(columns={"Mode": "Quickset Mode"})

            # Change data in jesd_class column to be more human readable
            df["JESD204 Class"] = df["JESD204 Class"].replace({"jesd204b": "204B", "jesd204c": "204C"})

            # Add column of buttons to dataframe
            # df["Select"] = ""
            # for mode in df.index:
            #     df.loc[mode, "Select"] = False

            to_disable = df.columns
            # # Remove the select column
            # to_disable = to_disable.drop("Select")

            # st.dataframe(df, use_container_width=True, selection_mode = 'single-row')
            de = st.data_editor(df, use_container_width=True, disabled=to_disable, hide_index=True)
            
            # Extract selected




        else:
            st.write("No modes found")
